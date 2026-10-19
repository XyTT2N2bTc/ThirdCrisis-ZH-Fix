# Third Crisis 0.57.1 战斗崩溃：CombatFaction.StartTurn 空队列

## 主体信息

- 主体：Third Crisis 0.57.1-r（Unity 2022.3.7f1，Mono）
- 被改文件：`…\ThirdCrisis_Data\Managed\Assembly-CSharp.dll`
- 触发：用户反馈战斗时一直崩溃/卡死。
- 日志（`%USERPROFILE%\AppData\LocalLow\Anduo Games\Third Crisis\Player.log`）：

```
InvalidOperationException: Queue empty.
  at System.Collections.Generic.Queue`1[T].Dequeue ()
  at Asuna.NewCombat.CombatFaction.HandleCharacterFromQueue (Queue`1 queue)
  at Asuna.NewCombat.CombatFaction.StartTurn ()
  at Asuna.NewCombat.CombatTurnManager.<DelayedStartTurn>b__20_0 ()
  ...
```

之后跟着一连串 `NullReferenceException`（`PMA_SetCameraOrthSize`、`CombatLerpMovement`、
`PMA_CameraTransitionBetweenPositions`、`PMA_CombatVisualEffect`、`ScrollRect`）——
这是回合协程被异常打断后，对已销毁对象的连锁反应。

## 根因

`CombatFaction.StartTurn()`：

```csharp
this.CanTurnEnd = new Restraint();
this.CanTurnEnd.Add("CombatFaction_StartTurn");
this.HandleCharacterFromQueue(new Queue<CombatCharacter>(this.Characters));
```

`HandleCharacterFromQueue()` 第一行就是 `queue.Dequeue()`，空队列直接抛
`InvalidOperationException`。

回合管理器在 `AdvanceTurn()` 里检查过 `combatFaction.HasParticipants`，但检查之后还有
`PreTurnStart` 约束（`CombatTurnManager.PreTurnStart.Invoke(restraint)`）——如果最后一个
角色在这段时间被移除（死亡/离场/脚本移除），轮到 `StartTurn` 时 `Characters` 已为空，
`Dequeue()` 抛异常，回合协程中断，战斗状态机崩掉。

## 本次修改

- 脚本：`scripts/patch_combat_turn_guard.py`（幂等）
- 在 `.text` 段末尾的零填充区（文件 `0x433B48`，RVA `0x435948`）写入新的
  `StartTurn` 方法体（fat header 12 字节 + 65 字节 IL，共 77 字节）：

```
CanTurnEnd = new Restraint();
CanTurnEnd.Add("CombatFaction_StartTurn");
if (Characters.Count == 0) { DelayedStartTurn(); return; }
HandleCharacterFromQueue(new Queue<CombatCharacter>(Characters));
```

- 把 `MethodDef` 表里 RID 12029（`0x06002EFD`，`StartTurn`）的 RVA 由 `0xE3714`
  改为 `0x435948`（旧方法体保留为死代码）。
- 把 `.text` 段头的 `VirtualSize` 由 `0x433948` 扩到 `0x433A00`，使新 RVA 落在段的
  虚拟范围内（新代码仍在原 `SizeOfRawData` 范围内，文件大小不变）。
- 空阵营分支先建立 `CanTurnEnd` 再调用 `DelayedStartTurn()`：管理器随后的
  `CanTurnEnd.RunWhenClear(EndTurn)` 拿到的是有效约束对象，`DelayedStartTurn` 会在
  1 秒后移除 `CombatFaction_StartTurn`，从而正常结束并跳过该阵营的回合。

## 备份与可逆性

- `…\ThirdCrisis_Data\Managed\Assembly-CSharp.dll.bak-thirdcrisis-combat-turn`
  （首次写入前状态，已包含分辨率/按钮/装备店等更早 DLL 补丁）。
- 还原：`cp -f Assembly-CSharp.dll.bak-thirdcrisis-combat-turn Assembly-CSharp.dll`。
- 逐次回退按备份链顺序（`.bak-thirdcrisis-actions` → `.bak-thirdcrisis-shop-texts`
  → `.bak-thirdcrisis-combat-turn` → `.bak-thirdcrisis-resolution`）。

## 行为影响与排查指引

- 空阵营的回合会被跳过（1 秒后结束），不再抛异常；正常阵营的回合逻辑不变。
- 预期日志中不再出现 `Queue empty`，后续那串相机/移动/视觉 NRE 是其连锁反应，
  应随之消失；若仍有残留 NRE，属于独立的清理时序问题，需另行定位。
- 若战斗行为异常：确认用的是打过补丁的 DLL（`--patch-dll`）；Steam 校验会还原 DLL。
- 新方法体只影响 `StartTurn` 的入口 RVA；其他方法、字段、字符串、元数据均未动。

## 验证与文件清单

- dnSpy 反编译复核：`StartTurn` 显示为
  `if (this.Characters.Count == 0) { this.DelayedStartTurn(); return; }` 后再入队。
- 回读：MethodDef RVA = `0x435948`，`.text` VirtualSize = `0x433A00`，方法体字节一致。
- 游戏启动实测：`Begin MonoManager ReloadAssembly` → `Loaded All Assemblies`，
  无程序集加载/类型/JIT 错误；主菜单正常。
- 幂等：重跑输出「已是补丁后的状态，无需改动」。
- 未运行项：没有进入实际战斗验证空阵营场景；需用户在战斗中确认。

## 第三方工具清单

- dnSpyEx `dnSpy.Console.exe`：IL/反编译定位与复核。
- 纯 Python：解析 PE 段头与 `#~` MethodDef 表、写新 IL 方法体与 RVA/VirtualSize。
