# Third Crisis 0.57.1 等待闲话（NPC 自言自语）汉化

## 主体信息

- 主体：Third Crisis 0.57.1-r（Unity 2022.3.7f1，Mono）
- 被改文件：`…\ThirdCrisis_Data\resources.assets`
- 故障现象（用户截图）：市政厅排队场景里 NPC 的对话仍是英文 —— 名字条 `Man`、正文 `I can't think! I need to get my dick inside something, anything!`；同时底部 UI 按钮已是中文（返回/隐藏/跳过/自动），说明语言文件本身工作正常。
- 根因（实测）：
  - 这条台词**不在**语言文件里：全文件搜 `I can't think! I need to get my dick inside something` 命中 0。
  - 它烤在 `resources.assets` 的一个对象里：`pathID 126253`，`m_Name = "Townhall_WaitingLine"`，内部是一串 7 句英文字符串；对象里**没有 guid**，也不属于 `Dialogues`/`UILocalizations` 任何一类，所以按 guid/原文匹配的全量重译覆盖不到。
  - 名字条 `Man` 来自对话行的 `Speaker` 字段（`Asuna/Dialogues/DialoguePopulateInfo.cs` 的 `GetSpeakerName()`：无 Character 时返回 `l.Speaker`，否则 `character.Name`），也是数据标识，语言文件无对应通道；`Man` 在资源里作为对象/预制体名出现（对齐字符串 `Man` 共 1002 处，多为动画/骨骼节点名），重命名会波及按名查找（`Character.GetByDisplayName` 等），风险高，本次未动。

## 本次修改

- 工具：自己临时写的一次性补丁脚本（纯标准库）
- 脚本：`…\tmp\l10n\scripts\patch_waiting_lines.py`（`ensure(asset, apply)`；幂等）
- 改动：该对象内 7 个字符串槽就地改成中文。沿用成就那套"等长改写"：长度前缀写成**对齐后字节数**，中文不足处用空格补齐，文件大小与所有字段偏移不变。
  原文与预算（对齐后字节）→ 译文：

| 原文 | 预算 | 译文 |
|---|---|---|
| You want a good fuck, baby? I got one right here for you. | 60 | 想爽一把吗，宝贝？我这儿正好有。 |
| I can't wait to pound one of the dumps. | 40 | 等不及去操一个精液桶了。 |
| Finally have enough fuckcreds to get my nut off. | 48 | 终于攒够操币，可以爽一发。 |
| Gonna make one of those dumps a `<b>very</b>` happy girl. | 56 | 我要让一个精液桶`<b>超</b>`开心。 |
| Nice legs, sweetie. They'd look better wrapped around me. | 60 | 腿真漂亮，宝贝。缠在我身上会更好看。 |
| Come bounce that ass on this dick, babe. | 40 | 来弹弹这根鸡巴，宝贝。 |
| I can't think! I need to get my dick inside something, anything! | 64 | 脑子转不动了！我得把鸡巴插进点什么！ |

- 约束：中文必须放得进原英文的对齐后字节预算（台词偏短，措辞需压缩，例如末句省略了 "anything"）；含 `<b></b>` 的句子按多重集原样保留标签。
- 执行时间：2026-10-13 当日

## 备份与可逆性

- 备份：`…\ThirdCrisis_Data\resources.assets.bak-thirdcrisis-waiting`，194,845,592 字节（本次改动前，已含成就汉化与字体修复）
- 改后：`resources.assets` 194,845,592 字节（大小不变）
- 还原：

```bash
cp -f "C:/1/Special/Assessment-High/third_crisis_0.57.1-r_windows/ThirdCrisis_Data/resources.assets.bak-thirdcrisis-waiting" \
      "C:/1/Special/Assessment-High/third_crisis_0.57.1-r_windows/ThirdCrisis_Data/resources.assets"
```

- 注意：还原到该备份会同时撤销本记录的 7 句（成就与字体仍在）。要回到出厂状态用 `resources.assets.bak-thirdcrisis-zh-ach`。

## 行为影响与排查指引

- 只改这 7 个字符串槽，不动任何其它字节；该对象是纯文本池，无逻辑字段受影响。
- 译文末尾会留少量补齐空格（对话框行尾不可见）。
- 排查指引：若该场景台词仍是英文，先确认 `resources.assets` 是否被官方版本还原（大小 194,845,588/388 之类），再跑 `patch_waiting_lines.py` 演练，脚本会报"已是补丁后的状态"或"命中 0 次"（后者说明对象形态变了，版本不同）。
- **未覆盖的同类内容**：只找到这一个 `*_WaitingLine` 对象；若其它场景还有别名的闲话池，需按本记录的方法另找对象再补。

## 验证与文件清单

- 定位：对象标记 `Townhall_WaitingLine` 在文件中出现 2 次（两个名称字段）；7 句原文各命中 1 次
- 写入后：改动 364 字节，**全部落在 7 个槽位内（槽位之外 0）**；按写入后的长度前缀读回并解码 = 目标中文 **7/7**；文件大小不变
- 幂等：再跑一次输出「已是补丁后的状态（7 条中文均在），无需改动」，退出码 0
- 未运行项：没有启动游戏验证台词显示；需用户在市政厅场景确认。

## 第三方工具清单

- 无（仅 Python 标准库）。
