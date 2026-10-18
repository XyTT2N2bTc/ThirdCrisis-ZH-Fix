# Third Crisis 0.57.1 场景画廊：532 条资源字符串汉化 + 旧版 Text 换中文字体

## 主体信息

- 主体：Third Crisis 0.57.1-r（Unity 2022.3.7f1，Mono）
- 被改文件：`…\ThirdCrisis_Data\resources.assets`
- 触发：用户反馈画廊里出现英文提示 `ask Klaus for information`（实际原文为
  `After unlocking the showers, the next time you enter the motel, ask Klaus for a way to earn money.`）。
- 定位结论：
  - 场景画廊数据是 `Gallery` ScriptableObject（resources.assets，pathID 125978），
    字段 `GalleryCategory.CategoryName`、`GalleryInfo.Name`、`GalleryInfo.UnlockSpoilerInfo`
    全部是**序列化在资源里的英文**，语言文件的 Dialogues/UILocalizations/Missions/JournalEntries/
    Items/SceneNames/Abilities 各段都没有画廊通道（`GalleryUI.PopulateSceneInfo` 直接
    `SceneInfoName.text = info.Name`、`SceneInfoSpoiler.text = "HINT: " + info.UnlockSpoilerInfo`）。
  - 画廊的解锁提示用的是**旧版 `UnityEngine.UI.Text`**（对象 `UnlockText`，组件 pathID 147572），
    字体 `m_Font = (fileID 4, pathID 13)` → `sharedassets0.assets` 的 `Roboto-Regular`；
    场景按钮的 `TooltipFont = (fileID 4, pathID 14)` → `Sentinel Type - BigNoodleTooOblique`。
    两者都没有中文字形，直接换文本会显示方块。
- 规模：38 个分类名 + 247 个条目名 + 247 条解锁提示 = **532 条字符串**（唯一文本 399 条）。

## 本次修改

- 工具：自己写的补丁脚本（UnityPy 只用于定位对象与顺序解析，写入为纯字节编辑）+ 反编译核对
- 脚本：`scripts/patch_gallery_zh.py`；译文映射：`translation/gallery_zh_map.json`
- 字符串（等长改写）：
  - 按字段顺序解析出每条字符串的 length 前缀偏移与原始长度 `n`，分配区 `A = align4(4+n)`。
  - 长度前缀写成 `A-4`，内容为「译文 + 空格补齐到 A-4 字节」。
    原因：Unity 读取时按 `align4(4 + 前缀长度)` 推进到下一个字段；若前缀只写译文实际长度，
    短译文会让后续字段整体前移（第一版就是因此把对象解析错位，已还原后改正）。
  - 中文均控制在 `A-4` 字节内；超预算条目在写入前拒绝执行。
- 字体（PPtr 改写）：
  - `147572 @0x58`：`(4, 13) Roboto-Regular` → `(0, 10547) NotoSerifSC-Regular`
    （游戏自带的 legacy Font，11.2MB，含中文字形）。
  - `130753 @0x50`：`(4, 14) Sentinel Type` → `(0, 10547)`。
- 未改动：`HINT: ` 前缀是代码字面量（`GalleryUI.PopulateSceneInfo` 拼在提示正文前），
  本次未动，界面上仍是 `HINT: 解锁淋浴后……`；`UnlockCounter` 只显示数字。

## 备份与可逆性

- `…\ThirdCrisis_Data\resources.assets.bak-thirdcrisis-gallery`（首次写入前状态；
  已包含更早的成就/字体/闲话/按钮补丁）。
- 还原：`cp -f resources.assets.bak-thirdcrisis-gallery resources.assets`。
- 注意：该备份是「画廊补丁之前」而非出厂状态；要回到出厂请按备份链继续回退
  （`.bak-thirdcrisis-actions` → `.bak-thirdcrisis-waiting` → `.bak-thirdcrisis-zh-font`
  → `.bak-thirdcrisis-zh-ach`）。

## 行为影响与排查指引

- 画廊三处文字（分类按钮、条目标题、解锁提示）显示中文；条目名同时用于场景按钮的
  Tooltip 与「Unlocked … in the Scene Gallery!」通知。
- 字体切换对英文也生效：画廊提示/场景按钮提示的英文字体由 Roboto/Sentinel 变为
  Noto Serif SC（可读，风格变化）。这是为了让中文有字形，无法按语言分别设置。
- 若画廊仍显示英文：说明 `resources.assets` 被官方还原（重跑 `apply_all.py --apply`）。
- 若画廊中文显示成方块：说明字体 PPtr 未生效（重跑脚本；脚本会先校验 PPtr 现场）。

## 验证与文件清单

- 解析完整性：`Gallery` 对象 138,620 字节，532 个字段项，解析后 `p == len(data)`。
- 回读：532/532 条字符串为目标译文；字符串起始偏移全部未变。
- 字体回读：两处 PPtr 均为 `(0, 10547)`。
- 字节差异：全部落在 532 条字符串分配区 + 2 处字体 PPtr 内，**区外 0**；文件大小不变。
- 幂等：重跑输出「已是补丁后的状态，无需改动」。
- 端到端：把语言文件与 assets 还原到出厂状态后运行
  `apply_all.py --apply --retranslate`，产出的语言文件与 assets 与交付状态 sha256 一致
  （见 README「Tested against」）。
- 未运行项：没有启动游戏进画廊目视确认；需用户确认提示与字体。

## 第三方工具清单

- UnityPy 1.25.4：读取 `resources.assets` 的对象表、对象原始字节与 byte_start；
  不做资产重序列化（写入是直接的等长字节编辑）。
- dnSpyEx（此前用于定位 `GalleryUI`/`GallerySceneButton` 的字段顺序）。
