# Third Crisis 0.57.1 分辨率设置不持久：改 DLL 11 字节

## 主体信息

- 主体：Third Crisis 0.57.1-r（Unity 2022.3.7f1，**Mono** 构建 —— `Player.log` 有 `Mono path[0] = …/ThirdCrisis_Data/Managed`）
- 被改文件：`C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows\ThirdCrisis_Data\Managed\Assembly-CSharp.dll`
- 故障现象（用户原话）：「还有一个bug，更改分辨率后重新开游戏会重置回原本的分辨率，哪怕这个分辨率屏幕显示不全」
- 根因（反编译所得，`ANToolkit/UI/GraphicsOptions.cs`，`[RuntimeInitializeOnLoadMethod(AfterSceneLoad)] AddOptions()`）：

```csharp
resOption = Options.Add("Settings.Resolution", num, "Settings.VideoTab", list);
resOption.SetInt(num);      // ← 多余：把「当前显示分辨率的下标」写回选项，并立刻落盘
…
OnResSet();                 // → Screen.SetResolution(cachedResolutions[num].width, height, fullscreen)
```

  - `num` = 去重后的分辨率列表（`Screen.resolutions` 按 "WxH" 去重，枚举顺序）里 `Screen.currentResolution`（显示器原生模式）的下标。
  - `Option.SetInt()` 会 `this.Int = toSet; PlayerSettings.SetInt(SerializationName, this.Int);` 立刻写存档
    （见 `ANToolkit/Option.cs`；`SetInt` 亦会 `OnIntSet.Invoke`）。
  - 于是**玩家选的分辨率每次启动都被覆盖成显示器原生模式的下标**：选择留不住；窗口被顶到原生分辨率，
    在开了显示缩放的笔记本上就超出可用桌面区域（用户说的"显示不全"）。
  - 相关佐证：`Settings.sav` 里确实有 `Resolution`（下标）与 `Fullscreen`（布尔）；`Fullscreen` 走的是
    `OnFullScreenSet` → `Screen.fullScreen = value`，所以只有分辨率这一项不持久，与用户描述一致。
  - 存档键来源（顺带查清，影响面大因此记录）：`Option.SerializationName = Translation.GetOriginal(identifier)`，
    即设置项的存盘键 = 该 LocalizedStrings 条目的 **`originalText`**。这解释了 `Settings.sav` 里同时存在
    `Language` 与 `Language (Machine Translation)` 两个键（英文包与机翻包的 `Settings.Language` 原文不同）。
    **推论：绝不可改 LocalizedStrings 的 `originalText`，否则玩家所有设置失联。**本台账此前各次改动均只改 `text`，实测 `originalText` 变化数为 0（已复核）。

## 本次修改

- 工具：自己临时写的一次性补丁脚本 + dnSpyEx 的 `dnSpy.Console.exe`（只用于反编译核验，非运行时依赖）
- 脚本：`…\tmp\l10n\scripts\patch_resolution_persist.py`（`--dll <路径>` + `--apply`；幂等；定位失败即拒绝执行）
- 改动：`GraphicsOptions.AddOptions()` 中三条件中性指令就地改为 IL 的 NOP（`0x00`），等长改写 11 字节：

```
0x0010D53D  ldsfld   GraphicsOptions::resOption     7E F3390004
0x0010D542  ldloc.1                                  07
0x0010D543  callvirt Option::SetInt(int32)           6F 2A360006
        ↓ 全部替换为 00 00 00 00 00 00 00 00 00 00 00
```

- 安全性依据（实测）：栈净效果 +1+1−2 = 0，改 NOP 后仍平衡；该 11 字节序列**全 DLL 唯一**（出现 1 次）；
  dnSpy 的 IL 列表核对 `IL_02D1/02D6/02D7` 只作为标号出现一次，**没有分支跳入**；等长改写使文件大小与所有 IL 偏移不变。
- 执行时间：2026-10-13 当日

### 中途错误（诚实记录）

第一版脚本把 NOP 写成了 `0x90`。`0x90` 是 **x86** 的 nop，在 IL 里是 `ldelem.i1` —— 反编译复核时看到该处变成 11 条
`ldelem.i1`（会破坏栈平衡、JIT 时非法），随即把该 11 字节改正为 `0x00`。教训：IL 的 nop 是 `0x00`；改机器码的直觉在这里不成立。
另有两次脚本自身缺陷：`NEW` 常量的替换先因空格不匹配静默失败、后因转义写出真的 NUL 字节导致源码无法编译 —— 均已修正，
并已用 `py_compile` + 直接运行复核。

## 备份与可逆性

- 备份：`…\Managed\Assembly-CSharp.dll.bak-thirdcrisis-resolution`，4,407,808 字节（出厂原版）
- 改后：`Assembly-CSharp.dll`，4,407,808 字节（大小不变）；与出厂版的差异恰为 `0x10D53D..0x10D547`
- 还原：

```bash
cp -f "C:/1/Special/Assessment-High/third_crisis_0.57.1-r_windows/ThirdCrisis_Data/Managed/Assembly-CSharp.dll.bak-thirdcrisis-resolution" \
      "C:/1/Special/Assessment-High/third_crisis_0.57.1-r_windows/ThirdCrisis_Data/Managed/Assembly-CSharp.dll"
```

- 升级覆盖：游戏更新或 Steam 校验文件完整性会还原 DLL，本补丁随之失效（重跑脚本即可）。

## 行为影响与排查指引

- 改后行为：启动时 `Options.Add` 载入存档里的值并保留（不再被覆盖），`OnResSet()` 按该值 `Screen.SetResolution`；
  玩家之后在选项里改分辨率 → 落盘 → 下次启动保留。
- 未改动的既有缺陷（供知悉，未处理）：`OnResSet()` 的范围判断是 `if (cachedResolutions.Count >= resOption.Int)`，
  正确应为 `> Int`；当存档下标恰好等于列表长度时会 `IndexOutOfRangeException`（正常路径下下标来自同一列表，通常不会触发）。
- 另一既有缺陷（未处理）：分辨率列表每次启动由 `Screen.resolutions` 重建，若显示器配置变化（换屏/改缩放/插拔外接屏），
  存档里的下标可能指向另一个模式。这是游戏自身设计，非本补丁引入。
- 排查指引：若改后游戏无法启动或行为异常，先按上面命令还原 DLL，即可判断是否本补丁所致；
  若分辨率仍不保留，按 README 的 FAQ 让对方在两次启动前后贴出 `Settings.sav` 里 `Resolution` 的值。

## 验证与文件清单

- 定位：11 字节序列出现次数 1；偏移 `0x10D53D` 处字节 `7E F3390004 07 6F2A360006`
- 写入后：与出厂 DLL 差异字节 9 个（另 2 个原就是 0x00），区间恰为 `0x10D53D..0x10D547`，文件大小不变
- **反编译比对**：修补前后各用 `dnSpy.Console.exe -o <dir> --asm-path <Managed> Assembly-CSharp.dll` 全量反编译，
  均产出 3242 个 `.cs`；逐文件比对差异**只有** `ANToolkit/UI/GraphicsOptions.cs` 少一行
  `GraphicsOptions.resOption.SetInt(num);`（`.csproj`/`.sln` 的差异来自生成时间戳）
- 幂等：对已打过补丁的 DLL 再跑脚本，输出「已经是补丁后的状态（该处为 NOP），无需改动」，退出码 0
- 未触及：`SetToCustom()`（画质等级）里另一处 `SetInt` 属正常路径，未改；`Settings.sav`、存档目录未动

**未运行项**：没有启动游戏做界面级验证（不启动游戏就无法确认"设置一次分辨率、重启后仍在"）。
可从 README 拿到复现步骤与期望结果。

## 第三方工具清单

- `dnSpyEx dnSpy.Console.exe`（GitHub Releases 的 `dnSpy-net-win64.zip`，解压在 `…\tmp\dnspy\`）—— 仅用于反编译核验与定位补丁点，不参与游戏运行；未安装到系统。
- 本机**没有** .NET SDK（只有 runtime），故 `dotnet tool install ilspycmd` 不可用，改用 dnSpy 的官方命令行版。
