# Third Crisis 0.57.1 补入缺失的设置项本地化键（修选项菜单崩溃）

## 主体信息

- 主体：Third Crisis 0.57.1-r（Unity 2022.3.7f1）
- 安装位置：`C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows`
- 被改文件：`…\ThirdCrisis_Data\StreamingAssets\Languages\translated_zh_translation.json`
- 故障现象原文（`Player.log` 逐字）：

```
KeyNotFoundException: The given key 'Settings.ToysTab' was not present in the dictionary.
  at ANToolkit.Localization.Translation.Get (System.String identifier)
  at ANToolkit.UI.PopulateCategory.Populate (System.String category, ANToolkit.UI.PopulateOptions options)
  at ANToolkit.UI.PopulateOptions.PopulateCategoryList ()
  at ANToolkit.UI.PopulateOptions.Awake ()
  …
  at ANToolkit.UI.MenuManager:OpenOptionsMenu()

KeyNotFoundException: The given key 'Settings.SeasonalEvents' was not present in the dictionary.
  at ANToolkit.Localization.Translation.Get (System.String identifier)
  at ANToolkit.UI.PopulateDropdown.OnPopulate (ANToolkit.Option toUse)
  …
```

- 触发时机：打开“选项”菜单时（`MenuManager.OpenOptionsMenu`）。
- 根因（实测定位）：游戏的默认（英文）本地化表内嵌在 `ThirdCrisis_Data\resources.assets`，其 `Settings.*` 段位于约字节 `185119708..185122592`，其中包含 `Settings.ToysTab`(=Toys)、`Settings.SeasonalEvents`(=Seasonal Events)、`Settings.EnableMultiplayer` 与 Lovense 系列共 11 个键；而 es/ja/ru/zh 四个随包语言文件的 `LocalizedStrings` 都不含它们（实测各文件 `ACH_`/该批键 0 命中），于是字典查找抛 `KeyNotFoundException`。
- 与本记录无关但同期查清的两点：这两条异常在 `Player-prev.log`（2026-10-12 01:05，即重译之前约 21 小时）中已存在 6 次，证明不是重译引入；存档亦与本案无关（日志无任何存档反序列化错误，2024 年旧存档无当前版本不认识的 `$type`）。
- 排除项：`Items.*`、`stat_perversion_AddStat_*`、`station.com` 等字符串同形但经字节区间核对**不在**本地化表内（分别是 C# 类型名、`Achievements.sav` 里的存档标记键、致谢网址），故未补入。

## 本次修改

- 工具：自己临时写的一次性补丁脚本（无第三方热修工具）
- 脚本：`…\tmp\l10n\scripts\add_missing_keys.py`（幂等；`--apply` 才写）
- 附带改动：`…\tmp\l10n\scripts\merge.py` 的 `--write` 分支在写完后自动调用 `add_missing_keys.ensure_keys()`，避免日后重跑全量回填时把这 11 条清掉（重建会以 `done/` 为准重写整个文件）。
- 执行命令：

```bash
cd "C:/1/Special/Assessment-High/third_crisis_0.57.1-r_windows"
python tmp/l10n/scripts/add_missing_keys.py --apply
```

- 补入内容（`Identifier` / `originalText` / `text`），插在 `Settings.OpenDataPrivacyPage` 之后，与 resources.assets 表内顺序一致：

| Identifier | originalText | text |
|---|---|---|
| Settings.ToysTab | Toys | 玩具 |
| Settings.LovenseEnabled | Lovense: Enabled | Lovense：启用 |
| Settings.LovenseIP | Lovense: Local IP | Lovense：本地 IP |
| Settings.LovensePort | Lovense: Port | Lovense：端口 |
| Settings.LovenseUseHTTP | Lovense: Use HTTP | Lovense：使用 HTTP |
| Settings.LovenseSetup | Lovense: How to Setup | Lovense：如何设置 |
| Settings.LovenseBuy | Buy a Lovense Toy Here | 在此购买 Lovense 玩具 |
| Settings.LovenseDialogueLine | Vibrate in Dialogue | 对话中振动 |
| Settings.LovenseUserInterface | Vibrate in Interface | 界面中振动 |
| Settings.SeasonalEvents | Seasonal Events | 季节性活动 |
| Settings.EnableMultiplayer | Enable Multiplayer | 启用多人游戏 |

- 执行时间：2026-10-13 01:04（本地时间）

## 备份与可逆性

- 备份：同目录 `translated_zh_translation.json.bak`（7,866,123 bytes，改写前的原始机翻版），SHA-256 `C0DCCABCABB7E3BDB2E14D6E98C74FEA…`
- 可逆：是。还原命令见 `2026-10-12-zh-translation-json-full-rewrite.md`（同一条）。
- 注意：还原到 `.bak` 会同时丢掉全部重译，不只是这 11 条。

## 行为影响与排查指引

- 只新增 11 条键，不改任何已有键、不改其它区块。实测：插入前后对其余内容做深层比较，`其余内容与插入前完全一致: True`。
- 与重译文件的既有重复项 `Settings.ControlsTab`（原文 69 条里本就重复两次，两条内容相同）无关，未处理。
- 排查指引：若日后选项菜单再次抛 `KeyNotFoundException: The given key '…'`，先看该键是否属于本批 11 个；若属于，说明文件被官方版本或全量重建覆盖了，重跑 `add_missing_keys.py --apply` 即可。若报错是别的键（例如 `ACH_*`），不是本修改的遗漏，见成就那份记录。
- 升级/校验覆盖：游戏更新或 Steam 校验会还原该文件，这 11 条随之丢失。

## 验证与文件清单

实测数据：

- `LocalizedStrings` 69 → 80 条
- 幂等验证：再次运行输出 `现有 80 条, 待补 0 条 / 无需改动`
- 回归验证：重跑 `python tmp/l10n/scripts/merge.py --write` 后仍为 80 条，门禁 `唯一原文 23705 / 落点 54117 / 校验错误 0`
- 其它区块条数不变：Dialogues 2745、UILocalizations 30046、Missions 53、JournalEntries 70、Items 179、SceneNames 85、Abilities 43
- 改后文件：7,665,640 bytes，SHA-256 `68EA7F841B00A3F2952995337A5D491E…`

**未运行项（诚实声明）**：没有启动游戏实测“选项菜单不再抛异常”。已验证的是“字典里已存在这 11 个键、其余内容零改动”，即崩溃前提已被消除；实际运行确认需由用户启动游戏完成。

## 第三方工具清单

- 未使用第三方插件或热修工具；仅 Python 标准库。
