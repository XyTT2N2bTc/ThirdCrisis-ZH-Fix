# Third Crisis 0.57.1 中文缺字（方块）修复：把中文字体挂进 TMP 回退链

## 主体信息

- 主体：Third Crisis 0.57.1-r（Unity 2022.3.7f1）
- 安装位置：`C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows`
- 被改文件：`…\ThirdCrisis_Data\resources.assets`
- 故障现象（`Player.log` 逐字，共 2974 条，涉及 342 个不同字符）：

```
The character with Unicode value \u556A was not found in the [Roboto-Condensed_DialogueUI] font asset or any potential fallbacks. It was replaced by Unicode character \u25A1 in text object [Text].
```

缺失字符包含最基本的 我(91 次)、的、你、了、在、这、！(99 次)、。(93 次)、，(86 次)，即中文文本被拉丁字体渲染成 □。
- 对照：`Player-prev.log`（2026-10-12 01:05，826 行短会话）0 条缺字警告；`Player.log`（2026-10-13 00:58，3688 行）2974 条 —— 说明该会话里渲染了中文，且全部落到拉丁字体上。
- 根因（用 `Unity.TextMeshPro.dll` 生成类型树，实测读出对象字段）：
  - 游戏其实**带了**中文字体：`pathID 125747 = NotoSerifSC-Regular SDF`，`m_AtlasPopulationMode=1`（动态），源字体 `m_SourceFontFile = 10547`（内嵌 Noto Serif SC，11.2MB）——即本来可以动态补字形。
  - 对话字体 `pathID 125748 = Roboto-Condensed_DialogueUI` 的 `m_FallbackFontAssetTable = []`（空）。
  - 全局回退 `TMP Settings`（pathID 127537）的 `m_fallbackFontAssets = [125743 = Arial SDF]` —— Arial 同样无中文字形。
  - 于是逐级回退（字体自身表 → 全局表）都拿不到汉字 → □。
  - 附带证据：Noto 的图集当时只烘了 **736** 个字形，恰好是旧语言包的用字集合，进一步印证语言包是 0.39/0.40 时代产物（见 `2026-10-12-zh-translation-json-full-rewrite.md`）。
- 为什么必须改资产：字体接线是烘在 `resources.assets` 里的对象引用，语言 JSON 没有任何字体通道（四个语言包里字体相关条目实测 0 条）。

## 本次修改

- 工具：**UnityPy 1.25.4** + `typetreegeneratorapi 0.0.10`（PyPI，pip 安装；用游戏自带 `Managed/*.dll` 生成 MonoBehaviour 类型树，从而能按字段名读写）
- 脚本：`…\tmp\l10n\scripts\fix_font_fallback.py`（默认演练：写到 `ThirdCrisis_Data/_fontfix_dryrun.assets` 并全量校验；`--apply` 才就地写；幂等）
- 执行命令：

```bash
cd "C:/1/Special/Assessment-High/third_crisis_0.57.1-r_windows"
python tmp/l10n/scripts/fix_font_fallback.py            # 演练 + 校验
python tmp/l10n/scripts/fix_font_fallback.py --apply    # 就地写入（首次自动备份）
```

- 改动内容（16 + 1 个对象）：
  1. `TMP Settings.m_fallbackFontAssets`：`[Arial SDF]` → `[Arial SDF, NotoSerifSC-Regular SDF]`（全局兜底）
  2. 15 个 TMP 字体资产的 `m_FallbackFontAssetTable`：`[]` → `[Noto]`
     （Arial SDF、HVDComicSerifPro SDF、HoneyScript-Light/SemiBold SDF、**Roboto-Condensed_DialogueUI**、Roboto-Condensed_SignalUI、Roboto-Medium_TaskWidget、Roboto-Regular SDF、Sentinel Type - BigNoodleToo SDF(±Shadow)、Sentinel ...Oblique SDF(±DropShadow/NoOutline/Outline)、**Sentinel ..._DialogueUI_NameTags**）
  3. `NotoSerifSC-Regular SDF.m_IsMultiAtlasTexturesEnabled`：`0` → `1`
     理由：动态图集必须能开新页；现有单页 4096×4096（Alpha8，约 16.8MB）只烘了 736 字形，而当前中文译文用到 **2568** 种非 ASCII 字符（其中 2091 种不在现有图集内，涉及 112,403 次出现，占全部字符的 14%）。不开多图集，运行时补字形会把单页塞满后继续缺字。
- 执行时间：2026-10-13 17:17（回退链）／17:19（多图集）

### 中途记录

第一版只做了「全局回退表 + 各字体回退表」。随后核对字形覆盖时发现 Noto 图集只有 736 字形、而译文需要 2568 种字，于是补上多图集开关——若不补，修复只解决"回退链断了"，仍会在图集塞满后缺字。

## 备份与可逆性

- `…\ThirdCrisis_Data\resources.assets.bak-thirdcrisis-zh-font`，194,845,388 字节 —— **加字体修复之前**的状态（已含成就汉化）
- `…\ThirdCrisis_Data\resources.assets.bak-thirdcrisis-zh-ach`，194,845,388 字节 —— 未做任何汉化的**原始**资产
- 改后：`resources.assets`，194,845,592 字节，sha256 前缀 `b9aba8f8290c40b1`
- 可逆（一步还原到"含成就汉化、无字体修复"）：

```bash
cd "C:/1/Special/Assessment-High/third_crisis_0.57.1-r_windows/ThirdCrisis_Data"
cp -f resources.assets.bak-thirdcrisis-zh-font resources.assets
```

- 升级覆盖：游戏更新或 Steam 校验会还原 `resources.assets`，本修复与成就汉化同时丢失；届时先跑 `patch_achievements.py --apply`，再跑 `fix_font_fallback.py --apply`（脚本幂等，已改过的会跳过）。

## 行为影响与排查指引

- 只改字体资产的回退链与一个开关位，不改任何字形、图集像素、材质或文本内容。
- 运行时开销：中文缺字形时 TMP 会向 Noto 图集动态补字形，必要时新建 4096×4096 Alpha8 页（每页约 16.8MB 显存/内存）；这是显示中文的必要代价。
- 观感变化：中文将用 **Noto Serif SC（衬线）**，拉丁文字仍是 Roboto Condensed（无衬线），中英混排字体风格会不一致——这是开发者自己给中文选的字体，未改。
- 排查指引：若日后**中文仍显示方块**，按顺序排查 —— (1) `resources.assets` 是否被官方版本还原（`ls -l` 看大小是否回到 194,845,388）；(2) 重跑 `fix_font_fallback.py` 的演练模式，看回退表是否仍含 125747；(3) 看 `Player.log` 里缺字警告的字体名 —— 若仍报 `Roboto-Condensed_DialogueUI` 且"or any potential fallbacks"，说明回退链又被还原；若报的是 `NotoSerifSC-Regular SDF`，则是图集/源字体问题，另需排查。
- 排查指引：若出现**中文变成乱码块或字距异常**（而非方块），先还原上方备份排除本修复，再看是否与本修复无关。
- 未运行项（诚实声明）：**没有启动游戏实测**。已实测的是对象级与字节级证据——161,312 个对象里只有预期对象发生变化（非预期变化 0），且每个被改对象的原始字节恰为"表尾多一条 PPtr"或"单个布尔字节 0→1"，其余字节完全一致。实际显示效果需启动游戏确认（看对话与成就名是否还有 □）。

## 验证与文件清单

实测数据（脚本自带校验 + 独立复验）：

- 对象摘要比对：改前 161,312 / 改后 161,312，**非预期变化 0**
- 字节级：TMP Settings 284 → 296 字节（count 1→2 + 12 字节 PPtr）；各字体资产 +12 字节（count 0→1 + 12 字节 PPtr）；Noto 73068 → 73068 字节，仅偏移 50504 单字节 0→1
- 回读：`TMP Settings.m_fallbackFontAssets = [125743, 125747]`；`Roboto-Condensed_DialogueUI.m_FallbackFontAssetTable = [125747]`；`Sentinel ..._DialogueUI_NameTags = [125747]`；`Noto.m_AtlasPopulationMode=1`、`m_IsMultiAtlasTexturesEnabled=1`、`m_SourceFontFile=10547`
- 成就汉化复验（同一文件内，未被本次改动影响）：33/33 仍为中文
- 改后文件：194,845,592 字节，sha256 前缀 `b9aba8f8290c40b1`

## 第三方工具清单

- `UnityPy 1.25.4`（PyPI，pip 用户级安装）—— 用于读写 Unity 序列化资产并按类型树重排偏移
- `typetreegeneratorapi 0.0.10`（PyPI，`UnityPy[ttgen]` 附带）—— 用游戏自带 DLL 生成 MonoBehaviour 类型树；本机自带 `ThirdCrisis_Data\Managed\Unity.TextMeshPro.dll` 已确认可用于生成 TMP 类型
- 两者均为**离线资产编辑工具**，不随游戏分发、不是游戏运行时依赖；游戏本身未新增任何依赖
- UnityPy 自带 `save()` 前先做过**无损往返测试**：加载→保存→重新加载，161,312 个对象摘要全等、0 差异，才用于本次写入
