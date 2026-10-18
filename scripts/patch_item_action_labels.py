# -*- coding: utf-8 -*-
# 修「物品操作按钮」：接线（UILocalization 覆盖动态文字）+ 动作名本地化（含 Cancel）。
#
# 背景（反编译实测）：
#   PopulateInventoryItem.PopulateFunctions() 依次加三个按钮：
#       AddFunction("Cancel")            ← #US 字面量（同时也被 InputManager 的按键绑定名使用）
#       AddFunction(this.Item.UseText)   ← Equipment/Apparel 赋 "Equip"/"Remove"，否则默认 "Use"
#       各物品自定义动作的 DisplayName（资源数据，如 "Open Top"）
#   而按钮预制体标签上的 ANToolkit.Localization.UILocalization 在 OnEnable 时
#   SetText(LanguageManager.UILocalizations[guid].text)，把动态文字覆盖成固定译文
#   （实测 guid fa183eac…→「使用」、dfd805db…→「表情」）。
#
# 修法：
#   1) 接线：两个标签组件的 IgnoreTranslation 置 1（布局实测：0x20=guid 长度, 0x24=guid, 0x48=bool）。
#   2) 动作名（资源，等长改写）：Open Top→掀开、Open Suit→掀开上衣、Use on yourself→对自己使用。
#   3) UseText（DLL #US 字面量，等 UTF-16 字符数）：Equip→"装备   "、Remove→"脱下    "。
#      实测 "Equip"/"Remove" 只用于 UseText 赋值，不是按键绑定名，故安全。
#   4) Cancel（DLL）：**不能改字面量**（同一 #US 条目被 26 处引用，其中多数是
#      InputManager 的绑定名查找 "Cancel"，改了会废掉取消键）。
#      改为只动"显示"路径：把 PopulateFunctions 里那条 ldstr("Cancel") 的 token
#      指向 #US 里一个**语义上只用于日志**的条目（"WIN" @0xAA0B：全程序集仅 1 处
#      ldstr，紧跟 Debug.Log），把该条目内容改写成「取消」+ 空格补齐。
#      条目长度不变，堆布局不动；唯一副作用是那条日志文本变成「取消」。
#      注：#US 里不存在"无人引用"的条目（2784 条全部被 ldstr 引用），故只能这样做。
#
# 用法: python patch_item_action_labels.py [--asset <resources.assets>] [--dll <Assembly-CSharp.dll>]
#                                        [--skip-dll] [--apply]
import os, struct, sys

DEFAULT_ROOT = r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows"
DEFAULT_ASSET = os.path.join(DEFAULT_ROOT, r"ThirdCrisis_Data\resources.assets")
DEFAULT_DLL = os.path.join(DEFAULT_ROOT, r"ThirdCrisis_Data\Managed\Assembly-CSharp.dll")

IGNORE_GUIDS = [
    "fa183eac-ac36-40f0-8904-2742ac91fcf8",   # CustomFunction 预制体标签（译文「使用」）
    "dfd805db-ff55-4148-92ab-c541de709659",   # FunctionButton 预制体标签（译文「表情」）
]
DATA_NAMES = [("Open Top", "掀开"), ("Open Suit", "掀开上衣"), ("Use on yourself", "对自己使用")]
DLL_LITERALS = [("Equip", "装备   "), ("Remove", "脱下    ")]
CANCEL_US, CANCEL_SLOT, CANCEL_ZH = 0x823, 0xAA0B, "取消"
CANCEL_SLOT_OLD = "WIN"            # 仅 1 处 ldstr，紧跟 Debug.Log（反编译核对）
DEBUG_LOG_TOK = 0x0A000187         # 该 ldstr 之后紧跟的 call 目标（Debug.Log）


def align4(n):
    return (n + 3) // 4 * 4


def us_literal(s):
    n = 2 * len(s) + 1
    return bytes([n]) + s.encode("utf-16-le") + b"\x00"


def cint(buf, p):
    """ECMA-335 压缩整数。"""
    b = buf[p]
    if b & 0x80 == 0:
        return b, 1
    if b & 0xC0 == 0x80:
        return ((b & 0x3F) << 8) | buf[p + 1], 2
    if b & 0xE0 == 0xC0:
        return ((b & 0x1F) << 24) | (buf[p + 1] << 16) | (buf[p + 2] << 8) | buf[p + 3], 4
    raise ValueError("bad compressed int at %#x: %#x" % (p, b))


def us_heap(buf):
    base = buf.find(b"BSJB")
    hdr = buf.find(b"#US\x00")
    off, size = struct.unpack_from("<II", buf, hdr - 8)
    return base + off, size


def us_entry(buf, off):
    """返回 (文本, 长度前缀字节数, 长度值)；越界返回 None。"""
    us, size = us_heap(buf)
    if off >= size:
        return None
    n, w = cint(buf, us + off)
    if n < 1 or off + w + n > size:
        return None
    return buf[us + off + w: us + off + w + n - 1].decode("utf-16-le"), w, n


def main():
    a = sys.argv[1:]

    def opt(k, d):
        return a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else d

    asset, dll = opt("--asset", DEFAULT_ASSET), opt("--dll", DEFAULT_DLL)
    apply = "--apply" in a
    skip_dll = "--skip-dll" in a
    print("资源:", asset)
    print("DLL :", dll, "(跳过)" if skip_dll else "")

    A = bytearray(open(asset, "rb").read())
    D = bytearray(open(dll, "rb").read())
    A0, D0 = len(A), len(D)
    # 本脚本的校验基线：本次运行前的快照（不与其他补丁的改动互相误报）
    Abefore, Dbefore = bytes(A), bytes(D)

    # ---------------- 计算各段 ----------------
    # 1) 接线
    wire = []
    for g in IGNORE_GUIDS:
        gb = g.encode()
        slot = len(gb).to_bytes(4, "little") + gb
        offs, i = [], 0
        while True:
            j = A.find(slot, i)
            if j < 0:
                break
            offs.append(j)
            i = j + 1
        print("  guid %s 槽位 %d 个" % (g[:8], len(offs)))
        for j in offs:
            wire.append(j + 4 + align4(len(gb)))

    # 2) 资源动作名
    data_edits = []
    for en, zh in DATA_NAMES:
        b = en.encode()
        slot = len(b).to_bytes(4, "little") + b
        offs, i = [], 0
        while True:
            j = A.find(slot, i)
            if j < 0:
                break
            offs.append(j)
            i = j + 1
        budget = align4(len(b))
        need = len(zh.encode("utf-8"))
        if not offs and zh.encode("utf-8") in A:
            print("  %-16r 已是中文，跳过" % en)
            continue
        print("  %-16r → %-8r 槽位 %d, 预算 %d / 需 %d %s"
              % (en, zh, len(offs), budget, need, "✓" if need <= budget else "✗"))
        if need > budget:
            print("  !! 超预算，拒绝执行")
            return 1
        for j in offs:
            data_edits.append((j + 4, budget, zh.encode("utf-8")))

    # 3) DLL 字面量（Equip/Remove）
    lit_edits = []
    for en, zh in (() if skip_dll else DLL_LITERALS):
        old, new = us_literal(en), us_literal(zh)
        offs, i = [], 0
        while True:
            j = D.find(old, i)
            if j < 0:
                break
            offs.append(j)
            i = j + 1
        if not offs and new in D:
            print("  字面量 %-8r 已是中文，跳过" % en)
            continue
        print("  字面量 %-8r → %-8r 出现 %d 次" % (en, zh, len(offs)))
        if len(offs) != 1:
            print("  !! 出现次数不为 1，拒绝执行")
            return 1
        lit_edits.append((offs[0], old, new))

    # 4) Cancel 显示路径（复用一个仅用于 Debug.Log 的条目 + 改 token）
    cancel = None
    if not skip_dll:
        us_abs, us_size = us_heap(D)
        e1 = us_entry(D, CANCEL_US)
        e2 = us_entry(D, CANCEL_SLOT)
        if e1 is None or e2 is None:
            print("  !! #US 条目越界，拒绝执行")
            return 1
        s1 = e1[0]
        s2, w2, n2 = e2
        print("  #US: Cancel@0x%X=%r, 槽@0x%X=%r" % (CANCEL_US, s1, CANCEL_SLOT, s2))
        if not s2.startswith(CANCEL_ZH):
            if s1 != "Cancel" or s2 != CANCEL_SLOT_OLD:
                print("  !! #US 现场不符预期，拒绝执行")
                return 1
            # 槽位必须只有 1 处 ldstr 引用，且紧跟 Debug.Log
            tok2 = (0x70000000 | CANCEL_SLOT).to_bytes(4, "little")
            sites, i = [], 0
            while True:
                j = D.find(b"\x72" + tok2, i)
                if j < 0:
                    break
                sites.append(j)
                i = j + 1
            if len(sites) != 1:
                print("  !! 槽位 ldstr 引用 %d 处（期望 1），拒绝执行" % len(sites))
                return 1
            after = D[sites[0] + 5: sites[0] + 10]
            if after[0] != 0x28 or int.from_bytes(after[1:5], "little") != DEBUG_LOG_TOK:
                print("  !! 槽位引用点不是 Debug.Log，拒绝执行")
                return 1
            # 槽位文本在 #US 里必须唯一
            dup, p = 0, 0
            while p < us_size:
                n, w = cint(D, us_abs + p)
                if n == 0:
                    p += w
                    continue
                if p != CANCEL_SLOT:
                    t = D[us_abs + p + w: us_abs + p + w + n - 1].decode("utf-16-le", "replace")
                    if t == CANCEL_SLOT_OLD:
                        dup += 1
                p += w + n
            if dup:
                print("  !! 槽位文本在 #US 中不唯一（%d 处重复），拒绝执行" % dup)
                return 1
            chars = (n2 - 1) // 2
            payload = (CANCEL_ZH + " " * (chars - len(CANCEL_ZH))).encode("utf-16-le")
            assert len(payload) == n2 - 1
            site = D.find(bytes.fromhex("7223080070") + bytes.fromhex("28E82D0006"))
            print("  Cancel ldstr+call 站点: %s" % (hex(site) if site >= 0 else "未找到"))
            if site < 0:
                print("  !! 未找到唯一站点，拒绝执行")
                return 1
            cancel = (us_abs + CANCEL_SLOT + w2, payload, n2 - 1, site)
        else:
            print("  Cancel 显示路径已指向复用槽位，跳过该段")

    # ---------------- 幂等 ----------------
    def wire_ok(g):
        gb = g.encode()
        slot = len(gb).to_bytes(4, "little") + gb
        j = A.find(slot)
        if j < 0:
            return False
        bo = j + 4 + align4(len(gb))
        return int.from_bytes(A[bo:bo + 4], "little") == 1

    data_done = all(zh.encode("utf-8") in A for _, zh in DATA_NAMES)
    lit_done = skip_dll or all(us_literal(zh) in D for _, zh in DLL_LITERALS)
    cancel_done = cancel is None
    already = data_done and lit_done and cancel_done and all(wire_ok(g) for g in IGNORE_GUIDS)
    if already:
        print("  已是补丁后的状态（接线已关、动作名/字面量已中文、Cancel 已指向复用槽位），跳过写入，仅校验。")
    elif not apply:
        print("\n(未加 --apply, 未写入)")
        return 0

    # ---------------- 写入 ----------------
    if not already:
        pairs = [(asset, asset + ".bak-thirdcrisis-actions")]
        if not skip_dll:
            pairs.append((dll, dll + ".bak-thirdcrisis-actions"))
        for p, b in pairs:
            if not os.path.exists(b):
                import shutil
                shutil.copyfile(p, b)
                print("已备份 ->", os.path.basename(b))

        for off in wire:
            A[off:off + 4] = (1).to_bytes(4, "little")
        for off, budget, raw in data_edits:
            A[off - 4:off] = budget.to_bytes(4, "little")
            A[off:off + budget] = raw + b" " * (budget - len(raw))
        for off, old, new in lit_edits:
            assert bytes(D[off:off + len(old)]) == old
            D[off:off + len(new)] = new
        if cancel:
            off, payload, ln, site = cancel
            D[off:off + ln] = payload
            D[site + 1:site + 5] = (0x70000000 | CANCEL_SLOT).to_bytes(4, "little")

        assert len(A) == A0 and len(D) == D0, "文件大小变化，拒绝写入"
        open(asset, "wb").write(A)
        if not skip_dll:
            open(dll, "wb").write(D)

    # ---------------- 校验 ----------------
    An = open(asset, "rb").read()
    da = [i for i in range(A0) if An[i] != Abefore[i]]
    allowed = set()
    for off in wire:
        allowed.update(range(off, off + 4))
    # 动作名：本次写入或上一轮已写入的都算已知改动
    for en, zh in DATA_NAMES:
        zb = zh.encode("utf-8")
        budget = align4(len(en.encode()))
        pat = budget.to_bytes(4, "little") + zb + b" " * (budget - len(zb))
        i = 0
        while True:
            j = An.find(pat, i)
            if j < 0:
                break
            allowed.update(range(j, j + 4 + budget))
            i = j + 1
    da_out = [i for i in da if i not in allowed]
    print("\n资源改动 %d 字节（预期外 %d）" % (len(da), len(da_out)))

    dd_out = []
    if not skip_dll:
        Dn = open(dll, "rb").read()
        dd = [i for i in range(D0) if Dn[i] != Dbefore[i]]
        exp = set()
        for en, zh in DLL_LITERALS:
            lit = us_literal(zh)
            i = 0
            while True:
                j = Dn.find(lit, i)
                if j < 0:
                    break
                exp.update(range(j, j + len(lit)))
                i = j + 1
        # Cancel：无论是本次改指还是上一轮已改指，token 与槽位都属于已知改动
        for tok in (CANCEL_US, CANCEL_SLOT):
            p = b"\x72" + (0x70000000 | tok).to_bytes(4, "little") + bytes.fromhex("28E82D0006")
            j = Dn.find(p)
            if j >= 0:
                exp.update(range(j + 1, j + 5))
                break
        e = us_entry(Dn, CANCEL_SLOT)
        if e and e[0].startswith(CANCEL_ZH):
            us_abs2, _ = us_heap(Dn)
            exp.update(range(us_abs2 + CANCEL_SLOT, us_abs2 + CANCEL_SLOT + e[1] + e[2]))
        dd_out = [i for i in dd if i not in exp]
        print("DLL 改动 %d 字节（预期外 %d）" % (len(dd), len(dd_out)))
        for en, zh in DLL_LITERALS:
            print("   字面量回读: %s -> %r" % ("ok" if us_literal(zh) in Dn else "MISSING", zh))
        if cancel:
            off, payload, ln, site = cancel
            print("   复用槽位回读: %r" % Dn[off:off + ln].decode("utf-16-le"))
            print("   Cancel ldstr token 回读: 0x%X (期望 0x%X)"
                  % (int.from_bytes(Dn[site + 1:site + 5], "little"), 0x70000000 | CANCEL_SLOT))
        # Cancel 绑定名必须保持原样（26 处引用）
        cnt = 0
        i = 0
        pat = b"\x72" + (0x70000000 | CANCEL_US).to_bytes(4, "little")
        while True:
            j = Dn.find(pat, i)
            if j < 0:
                break
            cnt += 1
            i = j + 1
        print("   Cancel 字面量引用数: %d (期望 25 = 原 26 处减去改指的显示站点)" % cnt)

    okwire = sum(1 for g in IGNORE_GUIDS if wire_ok(g))
    print("接线回读: %d/%d" % (okwire, len(IGNORE_GUIDS)))
    for en, zh in DATA_NAMES:
        zb = zh.encode("utf-8")
        budget = align4(len(en.encode()))
        pat = budget.to_bytes(4, "little") + zb + b" " * (budget - len(zb))
        print("   动作名回读: %s -> %r" % ("ok" if pat in An else "MISSING", zh))
    return 0 if (okwire == len(IGNORE_GUIDS) and not da_out and not dd_out) else 1


if __name__ == "__main__":
    sys.exit(main())
