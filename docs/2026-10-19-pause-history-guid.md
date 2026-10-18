# Third Crisis 0.57.1 暂停菜单：History 与 Options 共用 UILocalization guid

## 主体信息

- 主体：Third Crisis 0.57.1-r（Unity 2022.3.7f1，Mono）
- 被改文件：`…\ThirdCrisis_Data\resources.assets`、
  `…\ThirdCrisis_Data\StreamingAssets\Languages\translated_zh_translation.json`
- 触发：用户反馈 ESC/暂停菜单里 `History` 显示成「选项」。
- 定位结论（反编译 + 资源解析）：
  - `PauseCanvas/PauseMenu/MenuButtons/History/Text` 上的 `UILocalization`
    （component pathID **151279**）与 `…/Options/Text` 上的同类组件（**157749**）
    使用**同一个 guid** `042b7b07-f76d-4859-9959-20d92386540c`。
  - 语言包给该 guid 的条目是 `originalText: "OPTIONS", text: "选项"`，
    所以 `RequiresTranslation=true`（中文）时两个按钮都取到「选项」。
  - 两个 Text 组件各自序列化的原文分别是 `HISTORY` 与 `OPTIONS`；英文模式下
    `UILocalization.SetTextToTranslation()` 用缓存 `_originalText`，所以英文看不出问题。
  - 这是原游戏的 guid 复制错误，es/ja/ru 语言包同样会显示成各自语言的「选项」。
- 字段布局（UILocalization，76 字节）：`0x20` = guid 长度（36）、
  `0x24` = 36 字符 guid、`0x48` = `IgnoreTranslation`（bool，4 字节）。

## 本次修改

- 脚本：`scripts/fix_pause_history.py`（幂等）
- 资源：把 component 151279 的 guid（对象内偏移 `0x24`，36 字节）改为
  `b7c2e4a1-5f3d-4a86-9e21-0c8d7b6a4f52`。Options 组件（157749）保持原 guid。
- 语言包：在 `UILocalizations` 段首插入
  `{"guid":"b7c2e4a1-5f3d-4a86-9e21-0c8d7b6a4f52","originalText":"HISTORY","text":"历史记录"}`。
- 未改动：History 文本组件里序列化的 `HISTORY` 原文；`HINT`/其他 UI。

## 备份与可逆性

- `…\ThirdCrisis_Data\resources.assets.bak-thirdcrisis-pause-history`
  （首次写入前状态，已包含更早的画廊/按钮等补丁）。
- 语言包不另建备份：改动是 `UILocalizations` 段首的一条插入；还原时删掉该条目即可
  （或按 `.bak` 链回退）。
- 还原资源：`cp -f resources.assets.bak-thirdcrisis-pause-history resources.assets`。

## 行为影响与排查指引

- 中文下 History 显示「历史记录」；Options 仍显示「选项」；英文不受影响
  （英文仍用序列化原文 `HISTORY`/`OPTIONS`）。
- 其他菜单若也有引用旧 guid 的 History 标签，本脚本只处理暂停菜单这一处
  （实测全 resources.assets 只有 151279/157749 两个组件使用该 guid）。
- 若 History 仍显示「选项」：确认语言包有 `b7c2e4a1-…` 条目（缺了会抛
  `KeyNotFoundException`；重跑脚本即可）。
- 若 History 显示英文 `HISTORY`：说明组件的 guid 已换但语言包条目缺失，
  或游戏未重启（语言在启动时加载）。

## 验证与文件清单

- 回读：component 151279 guid = `b7c2e4a1-5f3d-4a86-9e21-0c8d7b6a4f52`；
  component 157749 guid = `042b7b07-…`（未变）。
- 语言包：`UILocalizations` 29291 → 29292 条；新 guid 条目恰好 1 条，`text` = `历史记录`；
  其余区块计数不变（Dialogues 2745、LocalizedStrings 80、Missions 53、
  JournalEntries 91、Items 179、SceneNames 85、Abilities 43）。
- 资源文件大小不变；只改 36 字节。
- 幂等：重跑输出「组件 guid 已切换；语言包条目 已存在」，回读通过。
- 未运行项：没有启动游戏进 ESC 菜单目视确认；需用户确认。

## 第三方工具清单

- UnityPy 1.25.4：定位 component 151279 的 `byte_start` 并读取原始字节；
  写入为直接字节编辑（36 字节 guid），不做资产重序列化。
