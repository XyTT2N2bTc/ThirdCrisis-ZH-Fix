# Third Crisis 0.57.1 战斗余留问题：相机转场/战斗特效 NRE + 战斗提示 + 占位纸条

## 主体信息

- 主体：Third Crisis 0.57.1-r（Unity 2022.3.7f1，Mono）
- 被改文件：`…\ThirdCrisis_Data\Managed\Assembly-CSharp.dll`、
  `…\ThirdCrisis_Data\StreamingAssets\Languages\translated_zh_translation.json`
- 触发：
  1. 相机为空保护上线后，战斗卡死概率大幅下降但仍偶发；
  2. 战斗里切换装备的提示仍是英文；
  3. 任务/资料里有一处“未知语言”的占位文本。

## 一、余留的两条战斗 NRE

### 1) PMA_CameraTransitionBetweenPositions.OnEnter

```
NullReferenceException
  at UnityEngine.Component.get_transform()
  at PMA_CameraTransitionBetweenPositions.OnEnter()
  ... ← CreateAbilityAnnouncement.AnnouncementFinished()
       ← PopulateAbilityAnnouncement.OnDestroy()
```

`PositionA.Value as Component` / `PositionB.Value as Component` 可能为空或已销毁，随后直接
取 `.transform.position` 抛 NRE；`Finish()` 不会执行，FSM 卡在当前状态。

修法：把 `OnEnter` 的完整方法体复制到 `.reloc` 尾部（文件 `0x43412C`，RVA `0x43812C`），
在两处 `get_transform` 前插入 Unity 判空（`op_Implicit`）；任一为空则 `Finish()` 直接结束。
`MethodDef` RID 335 的 RVA 由 `0x6450` 改为 `0x43812C`。

### 2) PMA_CombatVisualEffect.doAnimation

```
NullReferenceException
  at UnityEngine.Component.get_transform()
  at Asuna.NewCombat.PMA_CombatVisualEffect+<doAnimation>d__20.MoveNext()
```

协程里对 `(TargetCharacter.Value as CharacterHandler)` / `(Origin.Value as CharacterHandler)`
取 `.transform.position`；为空/已销毁时协程中断，`done()` 不执行、`VisualEffectDone` 不发出，
使用该特效的 FSM 卡住。

修法：`OnEnter` 开头按 `SpawnAtTarget` 选中的 `CharacterHandler` 做判空；不可用则
`ProcessEvent(VisualEffectDone)` + `Finish()`，不再启动协程。新方法体写在 `.reloc`
文件 `0x4341B8`（RVA `0x4381B8`），并把 `.reloc` 的 `RawSize`/`VirtualSize` 由 `0x200`
扩到 `0x400`（文件增长 `0x200` 字节，仍在原段内追加）。
`MethodDef` RID 12391 的 RVA 由 `0xE99C4` 改为 `0x4381B8`。

## 二、战斗里的装备/物品提示

`CombatItemUsage.cs` 里写死的四条英文（换装备/用物品的体力提示）在 `#US` 里按相同
UTF-16 字符数改写：

| 原文 | 新文 |
|---|---|
| `I don't have enough energy to swap my gear right now!` | `我现在没有足够体力更换装备！` |
| `Gonna have to make sure I don't run out of energy with all this gear swapping.` | `换这么多装备，得注意别把体力用光。` |
| `I don't have enough energy to use any items right now!` | `我现在没有足够体力使用物品！` |
| `Gonna have to make sure I don't run out of energy while using items.` | `得注意别在使用物品时把体力用光。` |

尾部用空格补齐，对话框里不可见；四条均只有 1 处引用。

## 三、占位纸条

日志条目 `fiend_notes:crumpled_note`（皱巴巴的字条）的英文原文是占位乱码
`dfefg hlaehm mgeomga agoergm poeag vefgy`，中文包原样保留，看起来像“未知语言”。
本次把 `TranslatedContents` 改为「（字迹潦草，无法辨认）」，保留“读不懂”的设定。

## 备份与可逆性

- DLL：`.bak-thirdcrisis-camera-transition`、`.bak-thirdcrisis-vfx-guard`
  （各自首次写入前状态，按备份链回退）。
- 语言包：`fix_journal_entries.py` 的 `CONTENT_FIXES` 幂等修正；还原可把该条目正文改回乱码。

## 验证与文件清单

- dnSpy 反编译复核：
  - `PMA_CameraTransitionBetweenPositions.OnEnter` 显示两处
    `if (!component) { base.Finish(); return; }`；
  - `PMA_CombatVisualEffect.OnEnter` 显示
    `if (!((!SpawnAtTarget) ? Origin.Value as CharacterHandler : TargetCharacter.Value as CharacterHandler)) { ProcessEvent(VisualEffectDone); Finish(); return; }`。
- 战斗提示四条回读为中文；DLL 改动 278 字节，区间外 0。
- 游戏启动实测：`Loaded All Assemblies`，无程序集/类型/JIT 错误（含扩展后的 `.reloc`）。
- 幂等：全部脚本重跑报「已是补丁后的状态」。
- 未运行项：没有实机复现“击杀敌人→回合结束”的完整流程；需用户确认。

## 踩坑记录

- 第一版相机转场保护把 IL 的 `dup`/`pop` 操作码写反了（`dup=0x25`、`pop=0x26`），
  dnSpy 反编译显示为 `if (!0)`；已从备份还原并改正，改正后反编译正常。
- `.reloc` 段原来只有 `0xC` 字节重定位数据 + 零填充；把 `RawSize` 扩到 `0x400`
  后新代码仍在段内，PE 的 `SizeOfImage` 无需改动。

## 第三方工具清单

- dnSpyEx `dnSpy.Console.exe`：IL/反编译定位与复核。
- 纯 Python：PE 段头与 `#~` MethodDef 表解析、方法体复制与改写、RVA/RawSize/VirtualSize。
