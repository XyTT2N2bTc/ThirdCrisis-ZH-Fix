# Third Crisis 0.57.1 战斗卡死：PMA_SetCameraOrthSize 相机为空 NRE

## 主体信息

- 主体：Third Crisis 0.57.1-r（Unity 2022.3.7f1，Mono）
- 被改文件：`…\ThirdCrisis_Data\Managed\Assembly-CSharp.dll`
- 触发：用户反馈杀掉敌人后敌方画像不消失、回合无法结束。
- 日志：

```
NullReferenceException
  at (wrapper managed-to-native) UnityEngine.Camera.set_orthographicSize(UnityEngine.Camera,single)
  at Asuna.PlayMakerExtension.PMA_SetCameraOrthSize+<LerpOrtho>d__13.MoveNext ()
  at PlayMakerFSM+<DoCoroutine>d__37.MoveNext ()
```

（此前 `Queue empty` 已由 `patch_combat_turn_guard.py` 修掉；本次日志只剩这一条。）

## 根因

`PMA_SetCameraOrthSize.OnEnter()`：

```csharp
if (!this.TargetCamera.Value) this.TargetCamera.Value = Camera.main;
this.cachedCam = this.TargetCamera.Value as Camera;
if (this.ShouldSnap.Value) {
    this.cachedCam.orthographicSize = this.Size.Value;   // 相机为空 → NRE
    ...
}
base.StartCoroutine(this.LerpOrtho());                   // 协程里同样对 cachedCam 取值 → NRE
```

在战斗/场景切换时 `Camera.main` 可能返回 null，或相机对象已被销毁。动作没有判空，
协程抛异常后 `OnFinished` 事件永远不会发出；使用该动作的 PlayMaker FSM（战斗/摄像机
流程）就停在当前状态，表现为敌人回合结束不了、敌方画像（`CombatEnemyTurnUI` /
`CharacterUI`）不消失。

## 本次修改

- 脚本：`scripts/patch_camera_ortho_guard.py`（幂等）
- 把 `OnEnter` 的完整方法体复制到 `.reloc` 段的尾部零区（文件 `0x434020`，
  RVA `0x438020`），在 `cachedCam` 赋值之后插入保护：

```csharp
this.cachedCam = this.TargetCamera.Value as Camera;
if (!this.cachedCam) {                       // Unity op_Implicit，能识别已销毁对象
    base.Fsm.ProcessEvent(this.OnFinished, null);
    base.Finish();
    return;
}
```

- 把 `MethodDef` 表里 RID 13569（`0x06003501`，`OnEnter`）的 RVA 由 `0x101680`
  改为 `0x438020`；旧方法体保留为死代码。
- `.reloc` 段头的 `VirtualSize` 由 `0xC` 扩到 `0x200`，覆盖新代码（数据仍在原
  `SizeOfRawData` 内，文件大小不变）。该段原有内容（0xC 字节重定位表）不动，
  只使用其后全零的填充区。

## 备份与可逆性

- `…\ThirdCrisis_Data\Managed\Assembly-CSharp.dll.bak-thirdcrisis-camera-guard`
  （首次写入前状态，已包含战斗回合保护/装备店/按钮/分辨率补丁）。
- 还原：`cp -f Assembly-CSharp.dll.bak-thirdcrisis-camera-guard Assembly-CSharp.dll`。
- 逐次回退按备份链顺序（`.bak-thirdcrisis-actions` → `.bak-thirdcrisis-shop-texts`
  → `.bak-thirdcrisis-combat-turn` → `.bak-thirdcrisis-camera-guard`
  → `.bak-thirdcrisis-resolution`）。

## 行为影响与排查指引

- 相机不可用时，该动作直接结束（发 `OnFinished`），不再改相机尺寸；相机正常时行为不变
  （快照/插值逻辑原样保留）。
- 预期日志中不再出现 `PMA_SetCameraOrthSize.LerpOrtho` 的 NRE，战斗 FSM 不再卡住。
- 若仍有其它 `PMA_*`/`CombatLerpMovement` 的 NRE：它们各自是对已销毁对象取值，
  属于同类清理时序问题，可按同样方式逐个加保护。
- Steam 校验会还原 DLL，重跑 `apply_all.py --apply --patch-dll` 即可。

## 验证与文件清单

- dnSpy 反编译复核：`OnEnter` 显示
  `if (!this.cachedCam) { base.Fsm.ProcessEvent(this.OnFinished, null); base.Finish(); return; }`，
  其余逻辑与原文一致。
- 回读：MethodDef RVA = `0x438020`，`.reloc` VirtualSize = `0x200`，方法体字节一致。
- 游戏启动实测：`Loaded All Assemblies`，无程序集/类型/JIT 错误。
- 幂等：重跑输出「已是补丁后的状态，无需改动」。
- 未运行项：没有实机复现「击杀最后一个敌人→战斗结束」；需用户确认。

## 第三方工具清单

- dnSpyEx `dnSpy.Console.exe`：IL/反编译定位与复核。
- 纯 Python：解析 PE 段头与 `#~` MethodDef 表、复制并改写 IL 方法体、RVA/VirtualSize。
