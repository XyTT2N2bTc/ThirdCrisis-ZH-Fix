# Third Crisis 0.57.1 「击败敌人」任务：名称由 PlayMaker FSM 拼出

## 主体信息

- 主体：Third Crisis 0.57.1-r（Unity 2022.3.7f1，Mono）
- 被改文件：`…\ThirdCrisis_Data\resources.assets`
- 触发：用户反馈任务条目里「击败敌人」相关描述未汉化（显示 `Defeat Rat Grunt (0 / 5)` 一类文本）。
- 定位结论（资源解析 + 反编译）：
  - `Combat_DefeatEnemyAmount` 是**动态生成**的跑腿/击杀任务，任务资产
    `Combat_DefeatEnemyAmount.DefeatEnemies` 的 `DefaultDisplayName` 是空串，
    语言包里对应的 `TranslatedDisplayName` 也是空串。
  - 真正的任务名由 PlayMaker FSM `Mission_Generic_DefeatEnemyAmount_Logic` 运行时拼接：
    `"Defeat " + BaseEnemyDisplayName + " (" + DefeatAmount + " / " + TargetAmount + ")"`，
    再用 `SetTaskName` 写入 `NewTask.OverrideDisplayName`（任务栏另一处用
    `SetMissionName` 写 `NewMission.DisplayName`）。
  - `NewTask.GetDisplayName()` 里 `OverrideDisplayName` 的优先级**高于**语言包译文：
    `text2 = !string.IsNullOrEmpty(overrideDisplayName) ? overrideDisplayName : text;`
    所以语言包即使补了译文也不会生效。
  - 敌人名来自 `GetCharacterDisplayName` → `Character.Get().Name`（角色数据里的原始
    `Name`，如 `Rat Grunt`），与战斗界面共用。
- FSM 字符串存储：Unity 字符串（4 字节长度 + UTF-8 + 对齐填充）。`"Defeat "` 为
  7 字节，前后可读串为 `FinalTaskName` / `DefeatEnemyID` / `BaseEnemyDisplayName`。

## 本次修改

- 脚本：`scripts/patch_defeat_task_zh.py`（幂等）
- 在 `resources.assets` 中把两处长度前缀为 `07 00 00 00` 的 `Defeat ` 等字节数改写为
  `击败 `（UTF-8 同为 7 字节：`e5 87 bb e5 87 bb 20`）：
  - `0xAFFE334`（任务名 `FinalTaskName` 拼接处）
  - `0xB001298`（任务栏/任务名 `FinalMissionName` 拼接处）
- 长度前缀与 4 字节对齐均不变，FSM 二进制布局不动。
- 未改动：敌人名 `Rat Grunt`（`Character.Name`，与战斗界面、按名查找共用，改它有存档/
  查找风险）；进度格式 ` (x / y)` 由 PlayMaker 的 `StringAppend` 拼接，无需翻译。

## 备份与可逆性

- `…\ThirdCrisis_Data\resources.assets.bak-thirdcrisis-defeat-task`
  （首次写入前状态，已包含画廊/History 等更早补丁）。
- 还原：`cp -f resources.assets.bak-thirdcrisis-defeat-task resources.assets`。

## 行为影响与排查指引

- 任务栏与任务详情里的击杀任务显示 `击败 Rat Grunt (0 / 5)`（动词中文，敌人名保持英文）。
- 任务的**关卡内逻辑**不读这个显示名（只用于 `OverrideDisplayName` 显示），不影响计数/完成。
- 若仍显示 `Defeat …`：确认 `resources.assets` 未被官方还原；重跑脚本（幂等）。
- 若任务名变成空：说明 FSM 字符串被改坏（长度前缀/字节数不符），按备份还原后重跑。

## 验证与文件清单

- 改写后回读：新串 `击败 ` 2 处（`0xAFFE334`、`0xB001298`），旧串 0 处。
- UnityPy 重新加载 `resources.assets`：161,312 个对象，正常。
- 文件大小不变；改动仅这 14 字节（两处 7 字节）。
- 幂等：重跑输出「已是补丁后的状态，无需改动」。
- 未运行项：没有启动游戏接取该任务目视确认；需用户确认。

## 第三方工具清单

- UnityPy 1.25.4：重新加载资产做结构校验。
- dnSpyEx：反编译 `NewTask.GetDisplayName()`、`SetTaskName`、`GetCharacterDisplayName`
  与任务 UI 的文本来源。
