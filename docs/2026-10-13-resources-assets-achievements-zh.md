# Third Crisis 0.57.1 成就名称/描述就地汉化（改 resources.assets）

## 主体信息

- 主体：Third Crisis 0.57.1-r（Unity 2022.3.7f1）
- 安装位置：`C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows`
- 被改文件：`…\ThirdCrisis_Data\resources.assets`
- 故障现象：成就界面里的成就名称与描述全部显示英文（用户反馈原文：“成就未翻译”）。
- 根因（实测定位，三条独立证据）：
  1. 33 条成就名称/描述只存在于 `ThirdCrisis_Data\resources.assets`：`grep -ral "Small Setback"`、`"Cat Lover"`、`"Complete the prologue"` 全目录只命中该文件（外加本会话自己生成的中间文件）。
  2. 本地化文件没有成就通道：`Assembly-CSharp.dll` 的 `ANToolkit.Localization` 只提供 `GetMissionTranslation`/`GetItemTranslation`/`GetAbilityTranslation`/`GetJournalEntryTranslation`/`GetSceneTranslation`/`GetDialogueLineTranslation`/`GetChoiceTranslation` 与 `LocalizedStrings`/`UILocalizations` 两套通用表，**没有成就 getter**；JSON 模型 `TranslationJson` 也没有成就区块（无 `TranslationJsonAchievement`）。
  3. 四个随包语言文件（es/ja/ru/zh）与本目录里重译前的 zh 原件，对 33 条名称与 33 条描述各有 **0 命中**；成就资产的 68 个 guid 与语言文件 `UILocalizations` 的 guid 集合交集为 **0**。
- 另外排除：`Achievements.sav` 只用 ID（`ACH_STORY_1` 等）记录解锁状态，不用名称，改名称不影响存档。

## 本次修改

- 工具：自己临时写的一次性补丁脚本（无第三方热修工具）
- 脚本：`…\tmp\l10n\scripts\patch_achievements.py`（默认 dry-run；`--apply` 才写；幂等）
- 写法（Unity 字符串字段 = `[int32 长度][UTF-8 字节][补零到 4 字节对齐]`）：把长度前缀改写为该槽**对齐后字节数**，内容写中文后用空格补满同样字节数。读取器读到的字节数与下一字段落点都不变，因此文件大小与后续所有字段偏移保持不变（实测改后 194,845,388 bytes，与原件同大小）。
- 执行命令：

```bash
cd "C:/1/Special/Assessment-High/third_crisis_0.57.1-r_windows"
python tmp/l10n/scripts/patch_achievements.py            # 先 dry-run 看预算
python tmp/l10n/scripts/patch_achievements.py --apply    # 写入（首次会创建备份）
```

- 执行时间：2026-10-13 01:15（首次写入）／01:17（修正后重写，见下）

### 中途修正（诚实记录）

第一版脚本只写内容、**未改写长度前缀**，于是中文比英文长的两处会被读取器切在半个汉字上：

- `ACH_PURE_1` 名称：`Standing Up`(11 字节) → `挺直腰杆`(12 字节)
- `ACH_STORY_11` 名称：`Revelations`(11 字节) → `真相大白`(12 字节)

独立复核脚本正是靠“按文件自身前缀读取并解码”这一条发现了它（`UnicodeDecodeError`，复解析只剩 31/33）。处置：从备份还原资产 → 脚本改为“前缀 = 对齐后大小” → 重新打补丁 → 重新逐条复验（结果见下）。上表两处现已正确。

## 备份与可逆性

- 备份：`…\ThirdCrisis_Data\resources.assets.bak-thirdcrisis-zh-ach`，194,845,388 bytes，SHA-256 `C47D81187EA5CCA1FF1940658D319FFE…`（改写前原件）
- 可逆：是，一步还原：

```bash
cd "C:/1/Special/Assessment-High/third_crisis_0.57.1-r_windows/ThirdCrisis_Data"
cp -f resources.assets.bak-thirdcrisis-zh-ach resources.assets
```

- 升级覆盖：**游戏更新或 Steam“校验文件完整性”都会用官方 `resources.assets` 覆盖本补丁**，成就回到英文；届时重跑脚本即可（脚本幂等，重跑只补差异）。

## 行为影响与排查指引

- 改写 66 处字符串槽（33 名称 + 33 描述），不新增/删除任何字段，不改文件长度。改动字节实测 1,681 个，全部落在这 66 个槽位区间内，**槽位之外 0 字节变动**。
- 成就 ID（`ACH_*` 字段）未动，存档兼容性不受影响。
- 尾部以空格补齐，成就名/描述末尾会带若干空格；TextMeshPro 计算排版时会忽略行尾空白，实际显示应不可见，但这是已知的观感折衷（受原字符串字节预算限制——名称 8–24 字节、描述 12–64 字节，中文必须比英文更简洁才放得下）。
- 排查指引：若日后成就界面出现**乱码或半个汉字**，首先怀疑本补丁与官方资产版本不匹配（游戏更新后脚本读到的槽位可能已变），执行上面的还原命令排掉；若还原后仍异常则与本补丁无关。
- 排查指引：若成就名仍是英文而其它文本正常，说明 `resources.assets` 已被官方版本还原，重跑脚本。

## 验证与文件清单

实测数据（脚本自身 + 独立复验脚本）：

- 文件大小：原件 194,845,388 bytes / 改后 194,845,388 bytes，**相同**
- 按文件自身长度前缀读取并 UTF-8 解码，内容等于目标中文：**66 / 66**
- 长度前缀 == 该槽对齐后大小：**66 / 66**（无截断风险）
- 改动字节：1,681 个，落在 66 个槽位区间之外 **0** 个
- 幂等：再跑一次输出 `定位成就 33/33；已一致 33 条；待改写 0 条` 并拒绝写入
- 改后 sha256：`614E9925B88C2DB3361A049D3A10C169…`；备份 sha256：`C47D81187EA5CCA1FF1940658D319FFE…`
- 命名对照（节选，全 33 条见 `tmp\l10n\_ach_from_assets.json` 与脚本内 `ZH` 表）：Fighter→斗士、Cat Lover→爱猫人、Amateur→业余、Shameless→无耻、Small Setback→小小挫折、Too Fast Too Pure-ious→速度与纯洁（保留“速度与激情”谐音双关）、"Forget"→健忘、Walk To The Right→往右走

**未运行项（诚实声明）**：没有启动游戏实测成就界面。显示路径是从证据推断的——那 66 条英文串在本机只存在于该资产，且本地化文件没有任何成就通道，因此显示源必为该资产（或以其为兜底），改写它即可显示中文；但“改后确实显示中文”这一条需用户启动游戏确认。另有已知风险：若该 UI 实际是按 guid 取预置文本（与证据不符，但未排除），则本补丁不生效——现象会是成就仍为英文，且此时还原资产即可，无副作用。

## 第三方工具清单

- 未使用第三方插件或热修工具；仅 Python 标准库，未安装新依赖。
