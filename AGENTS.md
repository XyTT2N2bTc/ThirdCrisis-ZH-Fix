# ThirdCrisis-ZH-Fix

Agent 契约。与全局 AGENTS 冲突时以本仓规则为准。

## 本仓是什么

Third Crisis 0.57.1-r 中文语言包/资产的**脚本化修复包**：用脚本就地修补玩家本机的游戏数据文件，
不重新分发游戏资源本体。修复项与证据见 `README.md` 与 `docs/`。

## 模块

- `apply_all.py` —— **唯一入口**。顺序固定：`translation/done` 重译回填 → 语言包四项修补 → 资产（成就、字体）→ 可选 DLL 补丁。
  该顺序不可是别的：日志标题按 `Name` 字段匹配语料，语言包修补会把 `Name` 改成当前构建的键，先改名会导致语料匹配不上。
- `scripts/` —— 各修复脚本，一个语义一处维护；每个脚本自带判据注释（来源、实测依据）与幂等保证。
  `patch_resolution_persist.py` 是**唯一改游戏代码**的脚本（只改 `Managed/Assembly-CSharp.dll` 的 11 字节，且仅在 `--patch-dll` 时运行）。
- `translation/done/` —— 译文语料（`{"t": 英文原文, "x": 中文}`，按唯一原文去重），`scripts/merge.py` 的输入。
- `docs/` —— 逐次改动的留档记录（第三方本体留档的统一台账在 `C:\1\third-party-patches\third-crisis\`，本目录是其副本）。
- 唯一的第三方依赖是 `UnityPy[ttgen]`，且只被 `patch_achievements.py` / `fix_font_fallback.py` 使用（离线资产编辑，游戏运行不需要）。

## 完成条件（改动本仓后必须跑）

```bash
python -m py_compile apply_all.py scripts/*.py           # 语法
python apply_all.py --game "<已修补的游戏目录>"            # 演练：应全部报 0 改动（幂等）
python apply_all.py --game "<已修补的游戏目录>" --patch-dll  # DLL 步骤也应报"已经是补丁后的状态"
```

改脚本后额外做一次**端到端复现**（最强的验收）：把语言文件与 `resources.assets` 还原成随包原始状态，
再 `python apply_all.py --game "<游戏目录>" --apply --retranslate`，产出应与改动前的交付状态 sha256 一致。

改 `patch_resolution_persist.py` 后额外做**反编译比对**：改前后各把整个 `Assembly-CSharp.dll` 反编译一遍
（`dnSpy.Console.exe -o <dir> --asm-path <Managed>`），逐文件比对，差异必须**只有** `GraphicsOptions.cs`
里那一行 `resOption.SetInt(num);` 消失。

## 契约

| 路径 | 用途（给 agent） |
|------|------------------|
| `AGENTS.md` | 本文件 |
| `README.md` | 面向使用者与检索者的说明（含逐字报错、症状自诊表、实测数字、未运行项） |
| `docs/` | 留档记录；结论必须写明域与实测数字，未运行项如实声明 |
| `checksums.txt` | 全部文件 sha256，用于校验分发内容与本地是否一致 |

## 红线

- 默认只改数据文件（语言 JSON 与 `resources.assets`）；`Managed/Assembly-CSharp.dll` 只在显式 `--patch-dll` 时改，
  且必须：先留 `.bak`、定位不到唯一字节序列就拒绝执行、等长改写、改后做整程序集反编译比对（差异只允许是目标那一行）。
- 任何写入前必须留 `.bak`；脚本必须幂等，重复运行报 0 改动。
- 判据/数字必须实测（可复现命令写在留档里）；未运行项不得写成已发生。
- 不提交任何密钥、凭据、游戏资源本体或用户存档。
- 不要改语言文件 LocalizedStrings 的 `originalText`：设置项的存盘键由 `Translation.GetOriginal(identifier)` 派生，
  改名会让玩家的所有设置失联。
