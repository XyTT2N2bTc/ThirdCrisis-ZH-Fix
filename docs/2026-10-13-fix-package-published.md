# Third Crisis 中文修复包发布（GitHub 公开仓库）

## 主体信息

- 主体：Third Crisis 0.57.1-r（Unity 2022.3.7f1）
- 发布物：把本台账前四份记录里的改动打包成可分发、可重放的脚本集
- 发布位置：https://github.com/XyTT2N2bTc/ThirdCrisis-ZH-Fix （public，默认分支 main，246 个文件）
- 本地工作副本：`C:\1\Special\Assessment-High\third_crisis_zh_fix`
- 发布动机（用户原话）：「几个小问题也修了吧，记得可追踪，回头导出一个修复包扔到github」
- 可见性依据：该账号已有同类公开仓（`XyTT2N2bTc/EroSlayers-PCK-Mods`，Ero Slayers 的 PCK 覆盖 mod），故按同一习惯建 public 仓；不新建私有仓。

## 本次修改（打包，不改游戏数据）

- 包内容：
  - `apply_all.py` —— 唯一入口；顺序固定：`translation/done` 重译回填 → 语言包四项修补 → 资产（成就、字体）
  - `scripts/` —— 六个修补脚本 + `merge.py`（均为 `…\third_crisis_0.57.1-r_windows\tmp\l10n\scripts\` 的逐字副本）
  - `translation/done/` —— 228 个译文语料文件（23705 条唯一原文）+ `glossary.md`
  - `docs/` —— 本台账五份记录的副本
  - `AGENTS.md`（仓的 agent 契约）、`README.md`（面向检索者：逐字报错、症状自诊表、实测数字、未运行项）、`checksums.txt`（245 个文件 sha256）
- 顺序约束（重要）：重译必须在语言包修补**之前**。日志标题按 `Name` 字段（如 `Entry 2`）匹配语料，而语言包修补会把 `Name` 改成当前构建的键（`Entry 02`）；先改名会导致标题退回随包旧机翻。此约束已写进 `apply_all.py` 与 `AGENTS.md`。
- 执行时间与命令：

```bash
cd C:/1/Special/Assessment-High/third_crisis_zh_fix
git init -b main && git add -A && git commit -m "…"
gh repo create ThirdCrisis-ZH-Fix --public --source . --push --description '…'
gh repo edit XyTT2N2bTc/ThirdCrisis-ZH-Fix --add-topic third-crisis --add-topic game-mod \
  --add-topic localization --add-topic chinese-translation --add-topic unity --add-topic fan-translation
```

## 备份与可逆性

- 发布不修改本机游戏数据；包内脚本自带备份（`*.bak`）与还原说明。
- 撤销发布：`gh repo delete XyTT2N2bTc/ThirdCrisis-ZH-Fix`（需用户明确指示；公开仓可能已被缓存/复刻，删除不等于消失）。
- 本机游戏当前状态未因发布而改变；交付状态的两个文件哈希仍为
  语言文件 `09f15105670129e3…`、`resources.assets` `b9aba8f8290c40b1…`。

## 行为影响与排查指引

- 对外发布内容不含游戏资源本体，只有脚本、译文语料与留档；请使用者自备正版。
- 排查指引：若本机游戏日后出现异常，先判断是否由本台账的补丁引起 —— 本机备份点：
  - `ThirdCrisis_Data\resources.assets.bak-thirdcrisis-zh-ach`（出厂原始）
  - `ThirdCrisis_Data\resources.assets.bak-thirdcrisis-zh-font`（含成就汉化、无字体修复）
  - `StreamingAssets\Languages\translated_zh_translation.json.bak`（出厂机翻版）
  - `…\translated_zh_translation.json.bak-before-prune`（重译+小修+清理之前）
  逐个还原即可二分定位是否本补丁所致。
- 排查指引：若使用者反馈"用了修复包后 X 坏了"，先让对方跑 `apply_all.py --game <目录>`（演练模式，不写文件）核对报告数字是否与本仓 README 的实测数字一致；不一致说明其游戏版本或文件状态不同。

## 验证与文件清单

- 发布前**端到端复现测试**：把语言文件还原为随包机翻版、`resources.assets` 还原为出厂版，执行
  `python apply_all.py --game <游戏目录> --apply --retranslate`，产出与本台账各记录交付的状态
  **sha256 完全一致**（语言文件 `09f15105670129e3…`、`resources.assets` `b9aba8f8290c40b1…`）。
- 幂等复验：对已修补状态重跑演练，全部步骤报 0 改动。
- 远端核对：`gh repo view` 返回 public / main；远端 blob 数 246；远端 README 首行 `# ThirdCrisis-ZH-Fix`。
- 打包期间修掉的两个自身缺陷（诚实记录）：
  1. `apply_all.py` 传给 grep 清理步骤的扫描目录少了一层（指到 `StreamingAssets`），演练时包内 786 个 guid 全被判定"无引用"。演练模式未写盘；已修正为 `<game>/ThirdCrisis_Data`，并在 `prune_stale_ui_guids.py` 加防呆：扫描到的构建引用 guid 少于包内一半时一律拒绝执行。
  2. `apply_all.py` 原先把"重译"排在语言包修补之后，导致日志标题被语料覆盖失败（实测产出 `第2项`/旧机翻值，而非语料的 `第2篇`）。已调整顺序并记录理由。
- **未运行项**：未启动游戏做界面级验证；未在其它游戏版本/其它语言包上测试（README 已声明）。

## 第三方工具清单

- 发布用 `git` 与 GitHub CLI `gh`（本机已有，账号 `XyTT2N2bTc`）。
- 包内脚本的运行时依赖：Python 标准库；资产相关两个脚本需 `pip install "UnityPy[ttgen]"`（离线资产编辑，游戏运行不需要）。
