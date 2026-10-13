# Third Crisis 0.57.1 中文包三处小修：日志 Id/缺条目、陈旧版本号、过期 UI 条目

## 主体信息

- 主体：Third Crisis 0.57.1-r（Unity 2022.3.7f1）
- 安装位置：`C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows`
- 被改文件：`…\ThirdCrisis_Data\StreamingAssets\Languages\translated_zh_translation.json`（纯数据文件，不改游戏二进制）
- 涉及的三处问题、现象与根因：

### 1) 日志(Journal)条目未翻译

- 现象（`Player.log` 逐字）：`No translation for Journal project_mindcrush:entry_02`（12 次）、`entry_05`（14 次）。
- 根因（实测）：日志按 **Id** 查表，Id = 当前构建的 `(Category, Name)` 经 `lower()` + 空格→下划线 生成。资源里 91 个日志条目对象（含 `Category`/`Name`/`Contents` 字段）与语言包 70 条（含 `Id` 字段）按正文配对后，**58/69 条 Id 与规则完全吻合**，据此确认规则。缺口：
  - **11 条 Id 是旧版键**：补零规则改过（`entry_2`→`entry_02`、`entry_5`→`entry_05`、`entry_3/7/23` 同理，涉及 Project Mindcrush / Project Flytrap）；Pump 四条旧 Id 的 Category 段为空（生成 bug）`:pump_apparatus_development_log_1_-_…`，正确键是 `pump_apparatus_development:log_1_-_…`。
  - **21 条条目语言包里完全没有**（Audiologs 5 条、EBT/实验性洗脑技术网络 4 条、Project Flytrap 5 条、Tower 7 条）→ 标题与正文都是英文。
- 判定证据：`resources.assets` 里的条目对象如 `m_Name='ISH_TerminalEntry2'`、`Name='Entry 02'`、`Category='Project Mindcrush'`、`Contents='Animal trials have begun…'`。

### 2) 版本号文本陈旧

- 现象：界面/窗口标题里的版本显示为旧版本。
- 根因（实测）：语言包 `UILocalizations` 中 `guid=677b7acf-1f8a-4de7-a039-a637eea40670` 的 84 条文本是 `0.39.0-pr - (2019.4.12f1)`（83 条）与 `0.40.0-pr - (2019.4.12f1)`（1 条）；`guid=af32b929-5862-4d10-b237-c373cc00c056` 的 84 条是 `Third Crisis (0.39.0-pr) on WindowsEditor`。而本作实际是 `0.57.1-r`（`ThirdCrisis_Data/globalgamemanagers` 的 bundleVersion）、引擎 `2022.3.7f1`（`Player.log` 的 `Initialize engine version`）。
- 该 guid 由 GameObject「Version (1)」上的翻译组件引用（`pathID 153000`，字段 `guid` + `IgnoreTranslation=0`）→ 文本由语言包按 guid 提供，改 `text` 即可改显示。

### 3) 过期 UI 条目

- 现象：语言包 927 个 guid 中有 141 个在当前构建里**完全找不到引用**（旧版删除/改名的 UI 残留），共 755 条。
- 判定方法：UI 文本按 guid 查表，资源里的翻译组件把 guid 存成字符串（已用两个实例验证）；因此把 `ThirdCrisis_Data` 全目录（排除 `Languages` 与 `*.bak*`）逐字节搜索 36 位 guid 字符串，搜不到即无引用。

## 本次修改

- 工具：自己临时写的一次性补丁脚本（纯 Python 标准库）
- 脚本（`…\tmp\l10n\scripts\`）：
  - `fix_journal_entries.py` —— 11 条 Id/Name 校正 + 21 条新增（含中文标题与正文）
  - `fix_version_strings.py` —— 168 条版本号文本（两处 guid 各 84 条）
  - `prune_stale_ui_guids.py` —— 清理无引用的 141 个 guid / 755 条
  - `merge.py` 的 `--write` 分支依次调用以上三个（外加既有的 `add_missing_keys.py`），保证全量重建后补丁不丢
- 命令：

```bash
cd "C:/1/Special/Assessment-High/third_crisis_0.57.1-r_windows"
python tmp/l10n/scripts/fix_journal_entries.py --apply
python tmp/l10n/scripts/fix_version_strings.py --apply
python tmp/l10n/scripts/prune_stale_ui_guids.py --apply
```

- 执行时间：2026-10-13（当日）
- 只改 `text` / `Translated*` / `Id` / `Name` 字段与过期条目，**未动 `originalText`**：游戏按 guid 查表，保留原文可让旧键值仍能被文本匹配，避免万一存在按原文查找的路径被破坏。

## 备份与可逆性

- 快照：`translated_zh_translation.json.bak-before-prune`，7,685,209 字节（清理与两处小修之前的状态）
- 原始机翻版：`translated_zh_translation.json.bak`，7,866,123 字节
- 可逆：恢复快照即回到"小修与清理之前、全量重译之后"的状态：

```bash
cd "C:/1/Special/Assessment-High/third_crisis_0.57.1-r_windows/ThirdCrisis_Data/StreamingAssets/Languages"
cp -f translated_zh_translation.json.bak-before-prune translated_zh_translation.json
```

- 升级覆盖：游戏更新/Steam 校验会整体替换语言文件，本记录的三处修正随之丢失；用 `C:\1\Special\Assessment-High\third_crisis_zh_fix`（修复包）可一键重放。

## 行为影响与排查指引

- 新增的 21 条日志条目用当前构建的原文与中文译文成对写入，Id 与构建一致 → 游戏查得到；标题也补了中文（如 `audiologs:audiolog_1` → 「录音日志 1」）。
- 清理只删"构建无引用"的 guid 条目；清理后不变式成立：**包内 786 个 guid 全部被构建引用**（实测未引用数 0）。若某个 UI 文本将来显示英文，说明该 guid 的条目被误判删除 —— 从快照恢复该条目即可。
- 版本号文本改动在"语言包是显示来源"的前提下才可见；若游戏运行时用 `Application.version` 覆盖（DLL 里有 `SetTextToVersion`），则改动不生效但无害。**未运行时验证**（见下）。
- 排查指引：日志再次出现 `No translation for Journal <键>` 时，把该键与包内 Id 比对；若键带补零（`entry_0X`）而包内没有，说明包被官方版本还原，重跑修复包即可。

## 验证与文件清单

实测数据：

- 日志覆盖：构建侧 91 条，包内 91 条，**缺失 0**；`JournalEntries` 70 → 91 条
- 版本号：`677b7acf` ×84 → `0.57.1-r - (2022.3.7f1)`；`af32b929` ×84 → `Third Crisis (0.57.1-r) on WindowsEditor`
- 清理：`UILocalizations` 30046 → 29291 条（141 个 guid / 755 条）；不变式"包内 guid 全部被构建引用"实测成立（未引用 0）
- 结构其余部分不变：Dialogues 2745、LocalizedStrings 80、Missions 53、Items 179、SceneNames 85、Abilities 43
- 交付文件：`translated_zh_translation.json`，7,608,006 字节，sha256 前缀 `09f15105670129e3`
- **流水线复现测试**：对同一文件重跑 `merge.py --write`（含四次后置修补），前后 sha256 完全一致 → 交付状态可由脚本精确重建

**未运行项（诚实声明）**：没有启动游戏。已实测的是"键/Id/guid 与构建一致、文件结构合法、流水线可复现"；界面实际显示需用户启动游戏确认。

## 第三方工具清单

- 未使用第三方插件或热修工具；仅 Python 标准库。
