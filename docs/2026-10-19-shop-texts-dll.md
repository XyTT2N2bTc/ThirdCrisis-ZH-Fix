# Third Crisis 0.57.1 装备店：购买弹窗与错误提示写死在代码里

## 主体信息

- 主体：Third Crisis 0.57.1-r（Unity 2022.3.7f1，Mono）
- 被改文件：`…\ThirdCrisis_Data\Managed\Assembly-CSharp.dll`
- 触发：用户反馈装备店有三条文本未汉化。
- 定位结论（反编译 `Asuna/Items/PopulateItemShop.cs`）：
  - `ShowPurchasePopup()`：
    `Popup.Create(new PopupData("Are you sure you want to purchase '" + text + "'?", …, "Yes", "No"))`
    → 弹窗正文 + Yes + No 三条文本，全部是代码字面量，不经过语言文件。
  - `PopulateItem()` / `PurchaseItem()`：已拥有标记
    `"> <b>OWNED</b></color> "` 同样是写死的。
  - `PurchaseItem()` 的两条错误提示：`"I already have that one!"`、
    `"I don't have enough money for that!"`。
  - `Popup.Populate()` 只做 `YesText.text = CachedData.YesLabel` 等赋值；
    `YesLabel`/`NoLabel` 仅用于显示（代码里没有任何 `== "Yes"`/`"No"` 比较）。
- #US 字面量引用（实测）：
  - `"Yes"` / `"No"` 各 7 处，分布在 `PopupData` 构造函数默认值、`GalleryImage.UnlockPinup`、
    `PopulateSaveInfo.ConfirmDelete`、`SaveManager.WriteGame`、`DebugUIPanel.boolToYesNo` 与装备店。
  - 购买确认语的两段（`"Are you sure you want to purchase '"`、`"'?"`）各只有 1 处引用（装备店）。
  - `"> <b>OWNED</b></color> "` 2 处（装备店）；两条错误提示各 1 处（装备店）。

## 本次修改

- 脚本：`scripts/patch_shop_texts.py`（幂等；仅 `--patch-dll` 时运行）
- 独立字符串：在 #US 堆里**等 UTF-16 字符数**改写（长度前缀与堆布局不变）：

| 原文 | 新文 |
|---|---|
| `Yes` | `是  ` |
| `No` | `否 ` |
| `> <b>OWNED</b></color> ` | `> <b>已拥有  </b></color> ` |
| `I already have that one!` | `我已经有这个了！` + 16 空格 |
| `I don't have enough money for that!` | `我没那么多钱买这个！` + 25 空格 |

- 购买确认语（拼接片段，不能补空格，否则空格会出现在物品名两侧）：
  - 复用两条**只被 `Debug.Log` 引用**的 #US 槽位：
    `"Ending"` @0x8DEC → `确定要购买「`；`'.` @0xB3E4 → `」？`。
  - 把 `ShowPurchasePopup` 里两条 `ldstr` 的 token 改指过去：
    0xDCD26 `0x7000E482` → `0x70008DEC`；0xDCD2C `0x7000E4CA` → `0x7000B3E4`。
- 结果：弹窗显示 `确定要购买「<物品名>」？`，按钮为「是」「否」。

## 备份与可逆性

- `…\ThirdCrisis_Data\Managed\Assembly-CSharp.dll.bak-thirdcrisis-shop-texts`
  （首次写入前状态，已包含分辨率/按钮标签补丁）。
- 还原：`cp -f Assembly-CSharp.dll.bak-thirdcrisis-shop-texts Assembly-CSharp.dll`。
- 注意：还原会同时撤掉此前打在该 DLL 上的分辨率与按钮标签补丁；逐次回退按备份链顺序
  （`.bak-thirdcrisis-actions` → `.bak-thirdcrisis-shop-texts` → `.bak-thirdcrisis-resolution`）。

## 行为影响与排查指引

- 装备店：确认框与错误提示变中文；已拥有标记显示「已拥有」。
- 全局影响：`Yes`/`No` 是所有弹窗共用的显示标签，改为「是」/「否」后
  **所有弹窗按钮**都会变中文（代码里没有把它们当逻辑键使用）。
- 副作用：两条只用于日志的字符串被复用槽位覆盖，日志文本变成
  `确定要购买「` 与 `」？`（只写 `Player.log`，不进游戏界面）。
- 未改动：`PeithOSSlaveDetailDisplay`/`PeithOSUpgradeDetails` 里另有一条独立的
  `"OWNED"`（5 字符）用于奴隶管理界面，非本次用户报告的装备店，未动。
- 若装备店仍显示英文：确认用了 `--patch-dll`；Steam 校验会还原 DLL，重跑即可。

## 验证与文件清单

- 反编译复核：`Popup.Create(new PopupData("确定要购买「" + text + "」？", …, "是  ", "否 "))`；
  `GenerateErrorDialogue(player, "我已经有这个了！…")` / `"我没那么多钱买这个！…"`；
  已拥有标记为 `"> <b>已拥有  </b></color> "`。
- 回读：#US 7 条字符串全部为预期值；两处 token 指向槽位（`0x70008DEC` / `0x7000B3E4`）。
- 字节差异：DLL 改动 105 字节，全部落在 #US 字符串负载与 token 内（**区外 0**），文件大小不变。
- 幂等：重跑输出「已是补丁后的状态，无需改动」。
- 未运行项：没有启动游戏进装备店目视确认；需用户确认。

## 第三方工具清单

- dnSpyEx `dnSpy.Console.exe`：反编译定位与复核（不参与游戏运行）。
- 纯 Python 字节编辑：解析 #US 压缩长度、等字符数改写、token 改指；不做元数据重写。
