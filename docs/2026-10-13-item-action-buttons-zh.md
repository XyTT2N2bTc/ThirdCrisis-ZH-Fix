# Third Crisis 0.57.1 物品操作按钮：接线修复 + 动作名汉化

## 主体信息

- 主体：Third Crisis 0.57.1-r（Unity 2022.3.7f1，Mono）
- 被改文件：`…\ThirdCrisis_Data\resources.assets`、`…\ThirdCrisis_Data\Managed\Assembly-CSharp.dll`
- 故障现象（用户截图）：背包里选中物品后，下方三个操作按钮在中文下**全部显示「使用」**；英文下同一位置显示 `Cancel` / `Remove` / `[Perversion 0/60] Open Top`。
- 根因（反编译 + 数据核对，两件事叠加）：
  1. **接线**：按钮预制体的标签对象上挂着 `ANToolkit.Localization.UILocalization` 组件。它的 `OnEnable → SetTextToTranslation()` 会执行
     `SetText(LanguageManager.UILocalizations[this.guid].text)`，把 `PopulateItemCustomFunction.Populate()` 刚写进去的动态文字**覆盖**成该 guid 的固定译文。
     英文下 `LanguageManager.RequiresTranslation=false`，`SetText` 用的是缓存 `_originalText`（恰好是动态写入后的文字），所以英文看着正常 —— 中文下才暴露。
     实测：`CustomFunction` 预制体标签 Text 上的组件 `guid=fa183eac-ac36-40f0-8904-2742ac91fcf8` → 语言包译文为「使用」；`FunctionButton` 预制体标签 `guid=dfd805db-ff55-4148-92ab-c541de709659` → 「表情」。
  2. **本地化**：三个按钮的文字本来都是**英文数据/字面量**，不经过翻译表：
     - `AddFunction("Cancel")`（`PopulateInventoryItem.PopulateFunctions`，代码字面量）
     - `AddFunction(this.Item.UseText)`（`Equipment.cs:401/474/489` 赋 `"Equip"`/`"Remove"`，`Apparel.cs:94` 赋 `"Remove"`，默认 `"Use"`）
     - 各物品自定义动作的 `DisplayName`（资源里的数据，如 `"Open Top"`）
- 字段布局实测（UILocalization，76 字节）：`0x20` = guid 长度、`0x24` = guid（36 字符带连字符）、`0x48` = `IgnoreTranslation`（bool，4 字节）。

## 本次修改

- 工具：自己临时写的一次性补丁脚本（纯标准库）+ dnSpyEx 反编译核验
- 脚本：`…\tmp\l10n\scripts\patch_item_action_labels.py`（`--apply` 写入；`--skip-dll` 只改资源；幂等）
- 改动（等长改写，两个文件大小都不变）：
  1. **接线**：把上述两个标签组件的 `IgnoreTranslation` 由 0 置 1（`SetText` 会直接 return，动态文字不再被覆盖）。
  2. **动作名（资源）**：`"Open Top"`→`掀开`（3 处）、`"Open Suit"`→`掀开上衣`（1 处）、`"Use on yourself"`→`对自己使用`（2 处）。
  3. **动作名（DLL 字面量）**：`"Equip"`→`"装备   "`、`"Remove"`→`"脱下    "`（UTF-16 字符数相同，故 #US 堆长度不变）。
- 未改动、并说明原因：`"Use"` 与 `"Cancel"` **不翻译** —— 它们同时是 `InputManager` 的按键绑定名（`GetBindDown("Use")` / `GetBindDown("Cancel")` 遍布代码），与该按钮标签共用同一个 #US 字面量，改写会连带破坏按键绑定；实测 `"Equip"`/`"Remove"` 只用于 `UseText` 赋值（全库各 1 次），故可安全改写。
- 执行时间：2026-10-13 当日

## 备份与可逆性

- `…\ThirdCrisis_Data\resources.assets.bak-thirdcrisis-actions`，194,845,592 字节
- `…\ThirdCrisis_Data\Managed\Assembly-CSharp.dll.bak-thirdcrisis-actions`，4,407,808 字节
- 还原：

```bash
cd "C:/1/Special/Assessment-High/third_crisis_0.57.1-r_windows/ThirdCrisis_Data"
cp -f resources.assets.bak-thirdcrisis-actions resources.assets
cp -f Managed/Assembly-CSharp.dll.bak-thirdcrisis-actions Managed/Assembly-CSharp.dll
```

- 注意：DLL 的还原会同时撤掉 `2026-10-13-resolution-reset-dll-patch.md` 里的分辨率补丁（两份备份都含此前状态，逐次回退请按备份链顺序）。

## 行为影响与排查指引

- 接线改动只影响这两个标签组件：它们不再被固定译文覆盖，显示 `PopulateItemCustomFunction` 写入的动态文字。
- 动作名改写是纯显示文字；`UseText` 同时被用作动作 ID（`UseCustomFunction` 里 `functionName == this.UseText` 与按钮 ID 同源），两边一起变，行为不变。反编译复核：`Equipment.cs` 的两处赋值已是 `"装备   "`/`"脱下    "`，其余代码未动。
- 排查指引：若按钮仍全是同一个词，说明 `resources.assets` 被官方还原（重跑脚本）；若按钮文字成了英文而各项功能正常，说明只打了资源部分没打 DLL（加 `--patch-dll` 重跑）。
- 已知残留：`Use`/`Cancel` 两个词在界面上仍是英文（原因见上）。要汉化需改按键绑定体系，属另一档改动。

## 验证与文件清单

- 资源改动 73 字节、DLL 改动 15 字节，**预期外改动均为 0**；两个文件大小不变
- 回读：两个标签 `IgnoreTranslation=1`（2/2）；动作名回读为 `掀开`×3、`掀开上衣`、`对自己使用`×2
- DLL 反编译复核：`this.UseText = "装备   ";`、`this.UseText = "脱下    ";`（3 处），方法其余部分未变
- 幂等：重跑输出「已是补丁后的状态（接线已关、动作名与字面量均已是中文），无需改动」
- 未运行项：没有启动游戏验证按钮显示；需用户进背包选中物品确认。

## 第三方工具清单

- `dnSpyEx dnSpy.Console.exe`（`…\tmp\dnspy\`）—— 仅用于反编译定位与复核，不参与游戏运行。
