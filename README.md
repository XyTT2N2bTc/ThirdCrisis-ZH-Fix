# ThirdCrisis-ZH-Fix

针对 **Third Crisis 0.57.1-r（Windows, Unity 2022.3.7f1）** 中文语言包的一组修复脚本：修好三处会导致报错或英文残留的问题，并把中文语言文件补成完整可读的状态。

修复的报错/现象原文（便于检索命中）：

```
KeyNotFoundException: The given key 'Settings.ToysTab' was not present in the dictionary.
  at ANToolkit.Localization.Translation.Get (System.String identifier)
  at ANToolkit.UI.PopulateCategory.Populate (System.String category, ANToolkit.UI.PopulateOptions options)
  at ANToolkit.UI.PopulateOptions.PopulateCategoryList ()
  at ANToolkit.UI.PopulateOptions.Awake ()
  …
  at ANToolkit.UI.MenuManager:OpenOptionsMenu()

KeyNotFoundException: The given key 'Settings.SeasonalEvents' was not present in the dictionary.

The character with Unicode value \u556A was not found in the [Roboto-Condensed_DialogueUI] font asset or any potential fallbacks. It was replaced by Unicode character \u25A1 in text object [Text].

No translation for Journal project_mindcrush:entry_02
No translation for Journal project_mindcrush:entry_05
```

## 这是给谁用的？

| 你遇到的现象 | 是否本仓解决 |
|---|---|
| 打开「选项」菜单时游戏报错/菜单显示不全，日志里有 `KeyNotFoundException: 'Settings.ToysTab'` / `'Settings.SeasonalEvents'` | ✅ 补 11 条缺失设置项键 |
| 对话/界面中文显示成方块 □，日志里成片 `was not found in the [Roboto-Condensed_DialogueUI] font asset` | ✅ 把内置中文字体挂进 TMP 回退链并开启多图集 |
| 成就列表的名称/描述是英文 | ✅ 就地汉化 33 个成就（66 条字符串） |
| 日志（Journal）里某些条目是英文，日志里有 `No translation for Journal …` | ✅ 校正 11 条旧键 + 补 21 条缺失条目（含译文） |
| 界面显示的版本号是 `0.39.0-pr` / `0.40.0-pr` 之类旧版本 | ✅ 改为本作实际版本 |
| 改了分辨率，重启游戏又变回原来的分辨率（窗口甚至超出屏幕显示不全） | ✅ 需要 `--patch-dll`（改 Assembly-CSharp.dll 一处多余调用） |
| 城镇里 NPC 的自言自语（如市政厅排队时那句）仍是英文 | ✅ 汉化资源里烤死的 7 句等待闲话（同名资产内就地改） |
| 背包里物品的操作按钮全显示同一个词（如三个「使用」） | ✅ 关掉标签上的固定译文覆盖（接线）+ 动作名汉化；`Use`/`Cancel` 因同时是按键绑定名仍为英文 |
| Steam 校验后中文包被还原成英文机翻 | ✅ 重跑本仓脚本即可恢复（脚本幂等） |
| 想要整份中文全部重译（不只是上述几处） | ⚠️ 需要 `--retranslate`（见下），会整体替换语言文件 |

## 根因（30 秒版）

随包语言文件（`ThirdCrisis_Data/StreamingAssets/Languages/translated_zh_translation.json`）比游戏本体落后很多代：

1. **键缺失**：游戏本体的默认英文表内嵌在 `resources.assets`（`Settings.*` 段位于约字节 `185119708..185122592`），其中有 11 个设置项键（`Settings.ToysTab`、`Settings.SeasonalEvents`、`Settings.EnableMultiplayer` 及 Lovense 整组）在 es/ja/ru/zh **四个随包语言文件里都不存在** → 打开选项菜单时字典查找抛异常。
2. **字体没接线**：游戏自带中文字体 `NotoSerifSC-Regular SDF`（pathID 125747，动态图集、源字体内嵌），但对话字体 `Roboto-Condensed_DialogueUI`（pathID 125748）的 `m_FallbackFontAssetTable` 是空的，全局回退（TMP Settings，pathID 127537）只有 `Arial SDF`（无中文字形）→ 中文逐级回退失败，渲染成 □。
3. **本地化落后**：语言包里带 guid 的版本号文本写着 `0.39.0-pr - (2019.4.12f1)`（而本作是 `0.57.1-r` / Unity `2022.3.7f1`）；日志条目按 `Id`（= 当前构建的 `Category:Name` 生成）匹配，包里 11 条是旧键（如 `entry_2` vs 现在的 `entry_02`）、21 条整条缺失；另有 141 个 guid 在当前构建里完全无引用（旧版 UI 残留）。

## 修复前后对照

| 位置 | 修复前 | 修复后 |
|---|---|---|
| 选项菜单 | 打开即抛 `KeyNotFoundException`（缺 `Settings.ToysTab` / `Settings.SeasonalEvents`） | 键已存在，字典查找成功 |
| 对话文本 | 中文渲染为 □（日志 2974 条缺字告警 / 342 个字符） | 回退链含中文字体，且允许动态补字形开新图集页 |
| 成就名/描述 | 英文 | 中文（就地改写资产里的 66 条字符串，文件大小不变） |
| 日志条目 | 11 条查不到 + 21 条无条目 | Id 与构建一致，91/91 覆盖 |
| 版本号显示 | `0.39.0-pr - (2019.4.12f1)` | `0.57.1-r - (2022.3.7f1)` |
| 过期 UI 条目 | 141 个 guid / 755 条死数据 | 已清理；包内 guid 全部被构建引用 |

## Quick Start

前置：Python 3.10+；若要改 `resources.assets`（成就、字体）需 `pip install "UnityPy[ttgen]"`（离线资产编辑工具，**游戏运行不需要它**）。

```bash
# 1) 先演练（不写任何文件，只报告将要改什么并校验）
python apply_all.py --game "D:\SteamLibrary\steamapps\common\Third Crisis"

# 2) 确认无误后应用（语言包 + 成就 + 字体）
python apply_all.py --game "D:\SteamLibrary\steamapps\common\Third Crisis" --apply

# 3) 如果你还想要整份中文重译（用本仓 translation/done 的译文语料重建语言文件）
python apply_all.py --game "D:\SteamLibrary\steamapps\common\Third Crisis" --apply --retranslate

# 只修语言包、不碰二进制资产：
python apply_all.py --game "<游戏目录>" --apply --skip-assets

# 附带修「分辨率设置不生效」（改 Assembly-CSharp.dll 的 11 字节，会先备份）：
python apply_all.py --game "<游戏目录>" --apply --patch-dll
```

各条路线覆盖范围：

- `--skip-assets`：只做语言包四项修补（设置项键、日志、版本号、清理过期条目）。**不覆盖**成就与缺字。
- 默认（含资产）：额外做成就汉化 + 字体回退修复。**不覆盖**整份重译、也不改代码。
- `--retranslate`：在语言包修补**之前**先用 `translation/done` 的语料回填整份中文（顺序有意如此：日志标题按 `Name` 匹配，后置的改名会让语料匹配不上）。语料要求你的语言文件与本仓基于同一版本（0.57.1）；不匹配时 `merge.py` 会报"未命中落点"。
- `--patch-dll`：唯一会改游戏代码的一项，见下面「分辨率设置为什么不生效」。

备份与还原：脚本第一次写入前会留 `.bak`（语言文件为 `.bak`，资产为 `.bak-thirdcrisis-zh-ach` / `.bak-thirdcrisis-zh-font`）。还原就是把对应 `.bak` 拷回原名。

## 分辨率设置为什么不生效（`--patch-dll`）

反编译 `Assembly-CSharp.dll` 可见 `ANToolkit/UI/GraphicsOptions.cs` 的启动钩子（`[RuntimeInitializeOnLoadMethod(AfterSceneLoad)]`）每次都执行：

```csharp
resOption = Options.Add("Settings.Resolution", num, "Settings.VideoTab", list);
resOption.SetInt(num);      // ← 把「当前显示分辨率的下标」写回选项，并立刻落盘
…
OnResSet();                 // 于是 Screen.SetResolution(cachedResolutions[num]) 被调用
```

`num` 是去重后的分辨率列表里 `Screen.currentResolution`（显示器原生模式）的下标；`Option.SetInt()` 会 `PlayerSettings.SetInt(...)` 立刻写存档。结果是：**玩家选的分辨率每次启动都被覆盖成显示器原生模式的下标**，所以选择永远留不住；窗口被顶到原生分辨率，在开了显示缩放的笔记本上就会超出可用桌面区域（即"显示不全"）。

修法是把 `AddOptions()` 里那三条件中性指令就地改成 IL 的 NOP（`0x00`），等长改写：

```
0x0010D53D  ldsfld   GraphicsOptions::resOption    7E F3390004
0x0010D542  ldloc.1                                 07
0x0010D543  callvirt Option::SetInt(int32)          6F 2A360006
```

栈净效果 +1+1−2 = 0，改 NOP 后仍平衡；该 11 字节序列全 DLL 唯一，且核对过没有分支跳入这段。改后启动时保留存档里的值，`OnResSet()` 照它应用，玩家之后的选择即可持久。

## 安全论证

- 默认流程**不改游戏可执行文件**：只改两个数据文件（语言 JSON、`resources.assets`）。
- **资产改动是定量的**：成就改写是"原字节 + 仅字符串槽内变化"（长度前缀按原对齐大小回填，文件大小不变）；字体改动只动回退表与一个开关位 —— 实测 161,312 个对象里非预期变化 0，且改动对象的字节恰为"表尾多一条 PPtr"或"单字节 0→1"。
- `--patch-dll`（可选）**会改 `Managed/Assembly-CSharp.dll`**，但只改上面那 11 字节，且：
  - 先备份为 `Assembly-CSharp.dll.bak-thirdcrisis-resolution`；脚本定位不到唯一序列时**拒绝执行**（版本不符不会被误改）；
  - 等长改写，文件大小与所有 IL 偏移不变；改后把整个程序集重新反编译，与改前逐文件比对，**唯一差异就是那一行 `resOption.SetInt(num);` 消失**（3242 个文件，其余全同）；
  - 还原：把 `.bak-thirdcrisis-resolution` 覆盖回 `Assembly-CSharp.dll` 即可。Steam 校验文件完整性也会还原它。
- 本仓**不改存档目录**（`%USERPROFILE%\AppData\LocalLow\Anduo Games\Third Crisis`）；分辨率/按键等设置存在那里的 `Settings.sav`，脚本不碰。
- **fail-closed 保留**：清理过期 UI 条目设有防呆 —— 若扫描到的构建引用 guid 少于包内一半（例如扫描目录给错），一律拒绝执行；日志条目只增/改 Id，不删任何条目；版本号只改 `text`，保留 `originalText`（设置项的存盘键正是由 `originalText` 派生，改名会让所有设置失联，故绝不动它）。

## Tested against

以下数字均为本仓脚本在本机对 Third Crisis 0.57.1-r 实测输出：

- 语言包：`LocalizedStrings` 69 → 80 条（补 11 条设置项键）；`JournalEntries` 70 → 91 条（改 11 条 Id + 新增 21 条），构建侧 91 条**缺失 0**；版本号 168 条更新；`UILocalizations` 30046 → 29291 条（清理 141 个无引用 guid / 755 条）。其余区块不变：Dialogues 2745、Missions 53、Items 179、SceneNames 85、Abilities 43。
- 语言包不变式：包内 786 个 guid **全部**被当前构建引用（未引用数 0）。
- 资产（成就）：33/33 条复解析读回中文；按文件自身长度前缀读取并 UTF-8 解码 = 目标中文 66/66；长度前缀 = 对齐后大小 66/66；改动字节 1681 个，全部落在 66 个字符串槽内（槽外 0）。
- 资产（字体）：`TMP Settings.m_fallbackFontAssets` = `[Arial SDF, NotoSerifSC-Regular SDF]`；15 个字体资产回退表含中文字体；`NotoSerifSC-Regular SDF.m_IsMultiAtlasTexturesEnabled` = 1（其图集原只有 736 字形，而中文译文用到 2568 种非 ASCII 字符）。对象摘要比对：改前 161,312 / 改后 161,312，**非预期变化 0**。
- **端到端复现**：把语言文件与资产还原成随包原始状态后运行 `apply_all.py --apply --retranslate`，产出与交付状态 **sha256 完全一致**（语言文件 `09f15105670129e3…`、`resources.assets` `b9aba8f8290c40b1…`）。
- **DLL 补丁（分辨率）**：定位到的 11 字节序列全 DLL 唯一（出现 1 次）；改后与出厂 DLL 的差异恰为 `0x10D53D..0x10D547`；整程序集反编译 3242 个 `.cs` 与改前逐文件比对，唯一差异是 `GraphicsOptions.cs` 里 `resOption.SetInt(num);` 一行消失；脚本对已打过补丁的文件报"已经是补丁后的状态，无需改动"。
- 幂等：对已修补状态重跑，全部步骤报 0 改动。
- **打包期自查**：第一版 DLL 补丁误把 NOP 写成 `0x90`（那是 x86 的 nop；IL 的 nop 是 `0x00`），反编译复核时发现该处被解成 11 条 `ldelem.i1`（栈会失衡），已改正为 `0x00` 并重新验证。

**未运行项**：没有启动游戏做界面级验证。上述均为文件级（结构 / 对象 / 字节 / 反编译）实测；"选项菜单不再报错、中文不再显示方块、分辨率选择重启后保留"需你在游戏里确认。

## Known limits 与 FAQ

- **Q：会影响存档吗？** 不会。脚本不碰 `%USERPROFILE%\AppData\LocalLow\Anduo Games\Third Crisis`；成就与字体的改动也不改成就 ID（存档按 ID 记录）。
- **Q：Steam 校验文件完整性之后怎么办？** 官方文件会覆盖回英文/旧机翻。重跑 `apply_all.py --apply` 即可恢复（幂等）。
- **Q：中文用什么字体？看起来和英文不一样。** 中文用游戏自带、但原本没接上的 `Noto Serif SC`（衬线），拉丁文仍是 Roboto Condensed（无衬线），中英混排风格会不一致 —— 这是开发者自己给中文选的字体，本仓没有替换。
- **Q：内存占用会变大吗？** 会。中文缺字形时 TMP 会向字体图集动态补字形，必要时新建 4096×4096 Alpha8 页（每页约 16.8MB）—— 这是显示中文的必要代价（原本多图集开关是关的，单页塞满即缺字）。
- **Q：能用在 0.5x 其他版本或 es/ja/ru 吗？** 语言包四项修补只依赖 `Id`/`guid`/键名与构建一致，同版本其他语言包理论可套用但未测试；成就与字体脚本依赖具体 pathID（125747/125748/127537 等），换版本可能漂移 —— 脚本会先校验对象名，不符即中止。**未测试**（本机只有 0.57.1 的中文包）。
- **Q：改了分辨率还是留不住？** 确认用的是 `--patch-dll`（默认流程不改代码，那个 bug 只存在于代码里）；改完启动游戏，设一次分辨率、退出、再启动，应保留。若仍不保留，把 `Settings.sav` 里 `Resolution` 的值在两次启动前后贴给我 —— 值不变说明存档写入路径还有别的问题，值变了说明应用路径还有别的问题。
- **Q：`--patch-dll` 会影响 Steam 成就/校验吗？** 单机游戏，运行时无校验；Steam"校验文件完整性"会把 DLL 还原成官方版本（本补丁随之失效，重跑即可）。
- **Q：`--retranslate` 的译文是我要的吗？** 那是本仓附带的一份完整重译语料（23705 条唯一原文），风格偏直白、含成人内容原义不软化。不想要整体替换就别加该参数。
- **Q：为什么操作按钮里的 `Use` / `Cancel` 还是英文？** 这两个词同时是 `InputManager` 的按键绑定名（`GetBindDown("Use")`/`GetBindDown("Cancel")` 遍布代码），与按钮标签共用同一个 #US 字面量，改写会破坏按键绑定，故只汉化了只作显示用的 `Equip`/`Remove` 与资源里的动作名（`Open Top` 等）。
- **Q：为什么 NPC 的名字还显示 `Man`？** 名字来自对话行的 `Speaker` 字段（`DialoguePopulateInfo.GetSpeakerName` 直接返回它或 `character.Name`），是**数据里的标识**，语言文件没有对应通道；而重命名会波及按名字查角色的调用（`GetByDisplayName` 等），风险高，故本仓未动。
- **Q：为什么物品提示里还有英文 `Slots: Shirt, Pants`、`(Intact)`？** 这两处是**代码里写死的**，语言文件够不到：`Asuna/Items/Item.cs` 的 `GetTooltipString()` 里 `"Slots: "` 是硬编码英文字面量（约第 231 行），槽位名来自 `EquipmentSlot.ToString()`（枚举名）；耐久等级用 `Enum.GetName(typeof(DurabilityLevel), …)`（约第 297 行）拼出来。要翻译它们得改 DLL 代码（不是简单的等长替换），不属于本仓当前范围。
- **Q：为什么物品操作按钮在中文下全显示「使用」？** 这三个按钮的标签是**运行时数据**：`PopulateInventoryItem.PopulateFunctions()` 依次加入 `AddFunction("Cancel")`、`AddFunction(Item.UseText)` 和各物品自定义动作的 `DisplayName`（都在代码/资源里，英文，且不经过翻译表）。中文下它们被按钮预制体上的翻译组件按固定 guid 覆盖成同一个词（例：`Use`→使用），所以三个都一样。修这个同样要改代码/资源并关闭该组件的覆盖，属另一档改动。
- **Q：那物品名/描述/数值呢？** 物品名与描述走 `Items` 段（`TranslatedName`/`TranslatedDescription`），已翻译；数值（如 +7、50/50）是纯数字，不需要翻译。
- **Q：为什么脚本注释和留档是中文？** 本仓维护者与使用者是中文用户；README 面向中文搜索。

## 目录

```
apply_all.py              唯一入口（重译 → 语言包修补 → 资产 → 可选 DLL 补丁）
scripts/
  add_missing_keys.py            补 11 条缺失设置项键
  fix_journal_entries.py         日志 Id 校正 + 21 条新增条目
  fix_version_strings.py         版本号文本
  prune_stale_ui_guids.py        清理构建不再引用的 guid 条目（带防呆）
  patch_achievements.py          成就名称/描述就地汉化（同大小改写）
  fix_font_fallback.py           中文字体接入 TMP 回退链 + 开多图集
  patch_resolution_persist.py    改 DLL 11 字节，修分辨率设置不持久（仅 --patch-dll 时运行）
  merge.py                       用 translation/done 语料回填语言文件（管线）
translation/
  done/                   译文语料（按原文配对，23705 条）
  glossary.md             译名表与排版约定
docs/                     逐次改动的留档记录（主体版本、逐字报错、实测数字、还原命令）
checksums.txt             全部文件 sha256
```

## Credits 与许可

- 游戏本体、原始英文文本与内置字体版权属 **Anduo Games**；本仓只包含补丁脚本、译文语料与留档，不含游戏资源本体。请自备正版游戏。
- 脚本可自由使用与修改，无任何担保；按「改动前先备份、事后可还原」使用。
