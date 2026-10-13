# Third Crisis 0.57.1 中文语言文件全量重译（就地覆盖）

## 主体信息

- 主体：Third Crisis 0.57.1-r（Unity 2022.3.7f1 / 引擎版本实测 `Initialize engine version: 2022.3.7f1 (b16b3b16c7a0)`）
- 安装位置：`C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows`
- 用户存档目录（未改动）：`C:\Users\nian_\AppData\LocalLow\Anduo Games\Third Crisis`
- 被改文件：`C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows\ThirdCrisis_Data\StreamingAssets\Languages\translated_zh_translation.json`
- 故障/诉求原文：用户要求“重做这个本地化文件”，并在选项中确认范围为“全量重译”。原文件内容为旧机翻，存在大量硬错，例如 `Back`→“溯源”、`Items`→“项目”、`Savename`→“诗文名”、`Language (Machine Translation)`→“语言（机器翻译”（括号未闭合）。
- 根因（实测）：该文件 `text` / `Translated*` 字段由旧机器翻译批量生成，未按游戏术语与富文本规则校对。不是文件损坏：JSON 结构合法，8 个区块字段齐全。

## 本次修改

- 工具：自己临时写的一次性补丁脚本（无第三方热修工具）
- 脚本目录：`C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows\tmp\l10n\scripts\`（`extract.py` 抽批、`_w0xxx.py` 分批译文生成、`normalize.py` 排版统一、`merge.py` 回填+门禁、`autofill.py` 符号串自动照抄）
- 数据目录：`tmp\l10n\{batches,done,manifest.json,glossary.md}`
- 路线：以 `originalText` 为源，按唯一原文去重后重译，再按原文回填到全部结构落点（同一原文的重复出现由 `merge.py` 统一写回，不逐条改）
- 执行命令：

```bash
cd "C:/1/Special/Assessment-High/third_crisis_0.57.1-r_windows"
python tmp/l10n/scripts/merge.py --write     # 创建 .bak 备份并写回全部译文
```

- 执行时间：2026-10-12 22:11（本地时间）
- 判据：`merge.py` 门禁（标签多重集相等、首尾空白一致、换行数一致、非空译文）

## 备份与可逆性

- 备份：`translated_zh_translation.json.bak`，7,866,123 bytes，SHA-256 `C0DCCABCABB7E3BDB2E14D6E98C74FEA…`（改写前原件）
- 可逆：是。`merge.py` 仅在 `SRC.bak` 不存在时创建它，已有备份不会被覆盖。
- 还原命令：

```bash
cd "C:/1/Special/Assessment-High/third_crisis_0.57.1-r_windows/ThirdCrisis_Data/StreamingAssets/Languages"
cp -f translated_zh_translation.json.bak translated_zh_translation.json
```

## 行为影响与排查指引

- 只改语言数据文件，不触碰用户存档、设置、画廊与成就数据；不改游戏可执行文件与资产。
- 保留了原文的 Unity 富文本标签多重集，包括故意破损的结构（未闭合 `<i>`、未闭合 `<size=50>`、大写闭合 `</B>`/`</I>`、大小写不匹配的成对标签、无开标签的孤立 `</i>`、`<<i>` 双尖括号），以及 zalgo 乱码字节。
- 排版统一（`normalize.py`，幂等）：`…`/`..` → `……`；`~` 紧贴前字不加空格；CJK 标点后不留空格；`X- Y` 结巴 → `X——Y`。原文中的 `#Syn_Tits#`、`#TableNum#` 等占位符一律保留。
- 排查指引：若游戏出现文本异常（对话乱序、标签错乱、换行丢失），先执行上面的还原命令把本修改排掉；若还原后仍异常，则与本修改无关。
- 升级/校验覆盖：游戏更新会替换该文件；Steam“校验文件完整性”会还原为英文/官方版本，本修改随之丢失。

## 验证与文件清单

实测数据（`merge.py` 输出 + 独立复核脚本）：

- `唯一原文 23705 / 已翻译 23705 / 落点应用 54117 / 校验错误 0 / 未命中落点 0`
- 独立复核（另写脚本、不复用门禁代码）覆盖 55,639 个落点：标签多重集不一致 0、换行数不一致 0、首尾空白不一致 0、原文非空而译文为空 0
- 相对旧机翻发生改动的落点 39,280 个；与旧译完全相同的落点 14,837 个（多为纯符号/数字串与本就相同的短词）
- 区块条数前后一致：Dialogues 2745、UILocalizations 30046、Missions 53、JournalEntries 70、Items 179、SceneNames 85、Abilities 43（LocalizedStrings 见另两份记录）

- 改后文件：`…\Languages\translated_zh_translation.json`，7,665,640 bytes，SHA-256 `68EA7F841B00A3F2952995337A5D491E…`（含同日追加 11 条设置项键，见 `2026-10-13-zh-settings-keys-added.md`）
- 备份文件：`…\Languages\translated_zh_translation.json.bak`，7,866,123 bytes

## 第三方工具清单

- 未使用第三方插件或热修工具；全部为本会话临时编写的 Python 脚本，仅依赖 Python 标准库。
