# Third Crisis 0.57.1 暂停菜单 / 对话 HUD：History 共用 UILocalization guid

## 主体信息

- 主体：Third Crisis 0.57.1-r（Unity 2022.3.7f1，Mono）
- 被改文件：`…\ThirdCrisis_Data\resources.assets`、
  `…\ThirdCrisis_Data\StreamingAssets\Languages\translated_zh_translation.json`
- 触发：用户反馈 ESC/暂停菜单里 `History` 显示成「选项」。进一步审计发现对话 HUD 的
  `History` 与 `Auto` 也共用 guid（中文下 History 会显示「自动」），一并修复。
- 定位结论（反编译 + 资源解析）：
  - 暂停菜单：`PauseCanvas/PauseMenu/MenuButtons/History/Text` 的 `UILocalization`
    （component **151279**）与 `…/Options/Text`（**157749**）共用
    `042b7b07-f76d-4859-9959-20d92386540c`（语言包 →「选项」）。
  - 对话 HUD：`Menu/TextBox/ButtonPanel/HistoryButton/Label`（**157278**）与
    `…/AutoButton/Label`（**158411**）共用
    `f39bd612-e901-4176-9834-4777d6e81723`（语言包 →「自动」）。
  - `RequiresTranslation=true`（中文）时 `UILocalization.SetTextToTranslation()` 执行
    `LanguageManager.UILocalizations[guid].text`，两个按钮都取同一条译文；英文模式用各
    文本组件缓存的 `_originalText`（`HISTORY`/`OPTIONS`、`History`/`Auto`），所以英文正常。
  - 这是原游戏复制按钮时没换 guid 的缺陷，es/ja/ru 语言包同样存在。
- 字段布局（UILocalization，76 字节）：`0x20` = guid 长度（36）、
  `0x24` = 36 字符 guid、`0x48` = `IgnoreTranslation`（bool，4 字节）。

## 本次修改

- 脚本：`scripts/fix_pause_history.py`（表驱动、幂等）
- 资源（每处只改 36 字节）：

| 标签 | component | 旧 guid | 新 guid |
|---|---|---|---|
| 暂停菜单 History | 151279 | `042b7b07-…` | `b7c2e4a1-5f3d-4a86-9e21-0c8d7b6a4f52` |
| 对话 HUD History | 157278 | `f39bd612-…` | `c4e1d9a2-7b3f-4e58-a6d0-9f2c8b5e1a47` |

- 语言包：在 `UILocalizations` 段首插入两条：
  - `{"guid":"b7c2e4a1-…","originalText":"HISTORY","text":"历史记录"}`
  - `{"guid":"c4e1d9a2-…","originalText":"History","text":"历史记录"}`
- 未改动：Options（157749）与 Auto（158411）保持原 guid；两个 History 文本组件里
  序列化的原文保持 `HISTORY` / `History`。

## 备份与可逆性

- `…\ThirdCrisis_Data\resources.assets.bak-thirdcrisis-pause-history`
  （首次写入前状态，已包含更早的画廊/按钮等补丁）。
- 语言包不另建备份：改动是 `UILocalizations` 段首的两条插入；还原时删掉对应条目即可
  （或按 `.bak` 链回退）。
- 还原资源：`cp -f resources.assets.bak-thirdcrisis-pause-history resources.assets`。

## 行为影响与排查指引

- 中文下两个 History 都显示「历史记录」；Options 仍「选项」、Auto 仍「自动」；
  英文不受影响。
- 若 History 仍显示别的按钮文字：确认对应组件 guid 已换（脚本会先校验现场）。
- 若 History 显示英文：语言包缺新 guid 条目会抛 `KeyNotFoundException`；
  条目存在则可能是游戏未重启（语言在启动时加载）。
- 审计中发现的其它共享 guid（本次**未**处理）：
  - `761bb858-…`：任务按钮的 Text——文字由 `PopulateMissionButton.Populate()` 在运行时
    按任务数据重写，非固定译文，不受影响。
  - `abc157ec-…`：Animation State Changer 调试面板；`c07fa61e-…`：SDT 相机录制浮层；
    `d03ea4e0-…`：Animation Viewer 的占位 Toggle；`9db52643-…`：开发中占位面板。
    均非本次用户报告的界面，且部分对象是占位/调试用，故未动。

## 验证与文件清单

- 回读：151279 → `b7c2e4a1-…`；157278 → `c4e1d9a2-…`；157749 仍 `042b7b07-…`；
  158411 仍 `f39bd612-…`。
- 语言包：`UILocalizations` 29291 → 29293 条；两条新 guid 各 1 条，`text` = `历史记录`；
  其余区块计数不变（Dialogues 2745、LocalizedStrings 80、Missions 53、
  JournalEntries 91、Items 179、SceneNames 85、Abilities 43）。
- 资源文件大小不变；两处共改 72 字节。
- 幂等：重跑输出「2 处已切换；语言包条目已存在」，回读通过。
- 未运行项：没有启动游戏进 ESC 菜单/对话界面目视确认；需用户确认。

## 第三方工具清单

- UnityPy 1.25.4：定位两个 component 的 `byte_start` 并读取原始字节；
  写入为直接字节编辑（36 字节 guid），不做资产重序列化。
