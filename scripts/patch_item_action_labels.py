# -*- coding: utf-8 -*-
# 修「物品操作按钮」的两件事：接线 + 本地化。
#
# 背景（反编译 Concurren/实测）：
#   PopulateInventoryItem.PopulateFunctions() 依次加三个按钮：
#       AddFunction("Cancel")            ← 代码字面量
#       AddFunction(this.Item.UseText)   ← 装备类由 Equipment.cs/Apparel.cs 赋成 "Equip"/"Remove"，否则默认 "Use"
#       各物品自定义动作 function.DisplayName（资源里的数据，如 "Open Top"）
#   PopulateItemCustomFunction.Populate() 把文字直接写进标签：
#       this.Label.text = text + function.DisplayName;  this.tmpLabel.text = ...
#   但按钮预制体的标签对象上挂着 ANToolkit.Localization.UILocalization 组件，它的 OnEnable →
#   SetTextToTranslation() 会执行 SetText(LanguageManager.UILocalizations[this.guid].text)，
#   把动态文字**覆盖**成该 guid 的固定译文 —— 于是三个按钮全显示同一个词（中文包里是「使用」；
#   英文下 LanguageManager.RequiresTranslation=false，SetText 用的是缓存 _originalText，
#   恰好是动态写入后的文字，所以英文看着正常）。
#   实测：预制体 CustomFunction 的标签 Text 上的组件 guid=fa183eac-…→「使用」；
#        FunctionButton 预制体的标签 guid=dfd805db-…→「表情」。
#
# 修法：
#   1) 接线：把这两个 UILocalization 的 IgnoreTranslation 置 1（SetText 会直接 return），
#      动态文字不再被覆盖。字段布局实测：0x20=guid 长度, 0x24=guid, 0x48=IgnoreTranslation(bool,4B)。
#   2) 本地化：把**只作显示用**的动作名改成中文（等长改写）：
#      - 资源里的动作名："Open Top"→掀开、"Open Suit"→掀开上衣、"Use on yourself"→对自己使用
#      - DLL 里 UseText 的字面量："Equip"→装备␣␣␣、"Remove"→脱下␣␣␣␣
#        （实测 "Equip"/"Remove" 只用于 UseText 赋值，不是按键绑定名；"Use"/"Cancel" 同时是
#          InputManager 的绑定名，共用一个 #US 字面量，**不能**改，故保持英文。）
#
# 用法: python patch_item_action_labels.py [--asset <resources.assets>] [--dll <Assembly-CSharp.dll>] [--apply]
import os, sys

DEFAULT_ROOT = r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows"
DEFAULT_ASSET = os.path.join(DEFAULT_ROOT, r"ThirdCrisis_Data\resources.assets")
DEFAULT_DLL = os.path.join(DEFAULT_ROOT, r"ThirdCrisis_Data\Managed\Assembly-CSharp.dll")

IGNORE_GUIDS = [                      # 需要关掉"固定译文覆盖"的标签 guid
    "fa183eac-ac36-40f0-8904-2742ac91fcf8",   # CustomFunction 预制体标签（原译文「使用」）
    "dfd805db-ff55-4148-92ab-c541de709659",   # FunctionButton 预制体标签（原译文「表情」）
]
DATA_NAMES = [                        # 资源里的动作名 → 中文（预算=对齐后字节）
    ("Open Top",        "掀开"),
    ("Open Suit",       "掀开上衣"),
    ("Use on yourself", "对自己使用"),
]
DLL_LITERALS = [                      # #US 字面量：等 UTF-16 字符数改写
    ("Equip",  "装备   "),
    ("Remove", "脱下    "),
]


def align4(n):
    return (n + 3) // 4 * 4


def us_literal(s):
    n = 2 * len(s) + 1
    return bytes([n]) + s.encode("utf-16-le") + b"\x00"


def main():
    a = sys.argv[1:]
    def opt(k, d):
        return a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else d
    asset, dll = opt("--asset", DEFAULT_ASSET), opt("--dll", DEFAULT_DLL)
    apply = "--apply" in a
    skip_dll = "--skip-dll" in a
    print("资源:", asset)
    print("DLL :", dll)

    A = bytearray(open(asset, "rb").read())
    D = bytearray(open(dll, "rb").read())
    A0, D0 = len(A), len(D)

    # ---- 0) 幂等：全部已是目标状态就直接返回 ----
    def _bool_done(buf, g):
        gb = g.encode(); slot = len(gb).to_bytes(4, "little") + gb
        j = buf.find(slot)
        if j < 0: return False
        bo = j + 4 + align4(len(gb))
        return int.from_bytes(buf[bo:bo+4], "little") == 1
    data_done = all(zh.encode("utf-8") in A for _, zh in DATA_NAMES)
    lit_done = skip_dll or all(us_literal(zh) in D for _, zh in DLL_LITERALS)
    if data_done and lit_done and all(_bool_done(A, g) for g in IGNORE_GUIDS):
        print("  已是补丁后的状态（接线已关、动作名与字面量均已是中文），无需改动。")
        return 0

    # ---- 1) 接线：guid 槽后的 bool 置 1 ----
    wire = []
    for g in IGNORE_GUIDS:
        gb = g.encode()
        slot = len(gb).to_bytes(4, "little") + gb
        offs = []
        i = 0
        while True:
            j = A.find(slot, i)
            if j < 0: break
            offs.append(j)
            i = j + 1
        print("  guid %s 的 UILocalization 槽位数: %d" % (g[:8], len(offs)))
        for j in offs:
            # j 指向长度前缀；guid 内容在 j+4，长 36 且已对齐 → bool 在 j+4+align4(36)
            bool_off = j + 4 + align4(len(gb))
            wire.append(bool_off)
            print("     @0x%X 当前 IgnoreTranslation=%d" % (bool_off, int.from_bytes(A[bool_off:bool_off+4], "little")))

    # ---- 2) 资源里的动作名 ----
    data_edits = []
    for en, zh in DATA_NAMES:
        b = en.encode()
        slot = len(b).to_bytes(4, "little") + b
        offs = []
        i = 0
        while True:
            j = A.find(slot, i)
            if j < 0: break
            offs.append(j)
            i = j + 1
        budget = align4(len(b))
        need = len(zh.encode("utf-8"))
        print("  %-16r → %-8r 槽位 %d 个, 预算 %d / 需 %d %s"
              % (en, zh, len(offs), budget, need, "✓" if need <= budget else "✗ 超预算"))
        if need > budget:
            print("  !! 超预算，拒绝执行"); return 1
        for j in offs:
            data_edits.append((j + 4, budget, zh.encode("utf-8")))

    # ---- 3) DLL 字面量 ----
    lit_edits = []
    for en, zh in (() if skip_dll else DLL_LITERALS):
        old, new = us_literal(en), us_literal(zh)
        assert len(old) == len(new), (en, len(old), len(new))
        offs = []
        i = 0
        while True:
            j = D.find(old, i)
            if j < 0: break
            offs.append(j)
            i = j + 1
        print("  字面量 %-8r → %-8r 出现 %d 次" % (en, zh, len(offs)))
        if len(offs) != 1:
            print("  !! 出现次数不为 1，拒绝执行"); return 1
        lit_edits.append((offs[0], old, new))

    if not apply:
        print("\n(未加 --apply, 未写入)")
        return 0

    # 备份
    bakpairs = [(asset, asset + ".bak-thirdcrisis-actions")]
    if not skip_dll:
        bakpairs.append((dll, dll + ".bak-thirdcrisis-actions"))
    for p, b in bakpairs:
        if not os.path.exists(b):
            import shutil; shutil.copyfile(p, b)
            print("已备份 ->", os.path.basename(b))

    for off in wire:
        A[off:off + 4] = (1).to_bytes(4, "little")
    for off, budget, raw in data_edits:
        A[off - 4:off] = budget.to_bytes(4, "little")
        A[off:off + budget] = raw + b" " * (budget - len(raw))
    for off, old, new in lit_edits:
        assert bytes(D[off:off + len(old)]) == old
        D[off:off + len(new)] = new
    assert len(A) == A0 and len(D) == D0, "文件大小变化，拒绝写入"
    open(asset, "wb").write(A)
    if not skip_dll:
        open(dll, "wb").write(D)

    # 校验
    An = open(asset, "rb").read()
    Ao = open(asset + ".bak-thirdcrisis-actions", "rb").read()
    da = [i for i in range(A0) if An[i] != Ao[i]]
    if skip_dll:
        dd, Dn, Do, D0 = [], D, D, D0
    else:
        Dn = open(dll, "rb").read(); Do = open(dll + ".bak-thirdcrisis-actions", "rb").read()
        dd = [i for i in range(D0) if Dn[i] != Do[i]]
    allowed = set()
    for off in wire: allowed.update(range(off, off + 4))
    for off, budget, raw in data_edits: allowed.update(range(off - 4, off + budget))
    da_out = [i for i in da if i not in allowed]
    expected_dll = set()
    for off, old, new in lit_edits: expected_dll.update(range(off, off + len(old)))
    dd_out = [i for i in dd if i not in expected_dll]
    print("\n资源改动 %d 字节（预期外 %d）；DLL 改动 %d 字节（预期外 %d）" % (len(da), len(da_out), len(dd), len(dd_out)))
    ok = 0
    for g in IGNORE_GUIDS:
        gb = g.encode(); slot = len(gb).to_bytes(4, "little") + gb
        j = An.find(slot)
        bo = j + 4 + align4(len(gb))
        if int.from_bytes(An[bo:bo+4], "little") == 1: ok += 1
    print("接线回读: %d/%d 个标签 IgnoreTranslation=1" % (ok, len(IGNORE_GUIDS)))
    for off, budget, raw in data_edits:
        n = int.from_bytes(An[off-4:off], "little")
        got = An[off:off+n].decode("utf-8").rstrip(" ")
        print("   动作名回读: %r" % got)
    for off, old, new in lit_edits:
        got = Dn[off:off+len(new)]
        print("   字面量回读: %r" % got.decode("utf-16-le").rstrip("\x00"))
    return 0 if (not da_out and not dd_out and ok == len(IGNORE_GUIDS)) else 1


if __name__ == "__main__":
    sys.exit(main())
