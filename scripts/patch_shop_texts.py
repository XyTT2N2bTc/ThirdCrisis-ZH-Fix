# -*- coding: utf-8 -*-
# 装备店 UI 里写死在代码中的英文：
#   购买确认框： "Are you sure you want to purchase '" + 物品名 + "'?"  +  Yes / No
#   已拥有标记： "> <b>OWNED</b></color> "
#   错误提示：   "I already have that one!" / "I don't have enough money for that!"
#
# 做法：
#   - 独立字符串（OWNED 片段、两条错误提示、Yes/No 全局弹窗标签）：在 #US 里等字符数改写
#     （Yes/No 的 7 处引用全是显示标签；Popup.Populate 只判断是否为空，没有逻辑比较）。
#   - 购买确认语是拼接片段，不能靠补空格（空格会出现在句子中间），改为：
#       1) 复用两条只被 Debug.Log 引用的 #US 槽位，写入「确定要购买「」/「」？」；
#       2) 把 ShowPurchasePopup 里两条 ldstr 的 token 指过去。
#
# 用法: python patch_shop_texts.py [--dll <Assembly-CSharp.dll>] [--apply]
import os, struct, sys

ROOT = r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows"
DEFAULT_DLL = os.path.join(ROOT, r"ThirdCrisis_Data\Managed\Assembly-CSharp.dll")
BACKUP_SUFFIX = ".bak-thirdcrisis-shop-texts"

# (原 #US 偏移, 原字符串, 新字符串) —— 等 UTF-16 字符数
INPLACE = [
    (0xBE7, "No", "否 "),
    (0xBED, "Yes", "是  "),
    (0xE430, "> <b>OWNED</b></color> ", "> <b>已拥有  </b></color> "),
    (0xE4D0, "I already have that one!", "我已经有这个了！" + " " * 16),
    (0xE502, "I don't have enough money for that!", "我没那么多钱买这个！" + " " * 25),
]
# 复用槽位： (槽位偏移, 槽位原字符串, 新字符串)
SLOTS = [
    (0x8DEC, "Ending", "确定要购买「"),
    (0xB3E4, "'.", "」？"),
]
# 改指的站点： (文件偏移, 原 token, 新 token)
SITES = [
    (0xDCD26, 0x7000E482, 0x70008DEC),   # "Are you sure you want to purchase '"
    (0xDCD2C, 0x7000E4CA, 0x7000B3E4),   # "'?"
]


def cint(buf, p):
    b = buf[p]
    if b & 0x80 == 0:
        return b, 1
    if b & 0xC0 == 0x80:
        return ((b & 0x3F) << 8) | buf[p + 1], 2
    if b & 0xE0 == 0xC0:
        return ((b & 0x1F) << 24) | (buf[p + 1] << 16) | (buf[p + 2] << 8) | buf[p + 3], 4
    raise ValueError("bad compressed int at %#x" % p)


def us_heap(buf):
    base = buf.find(b"BSJB")
    hdr = buf.find(b"#US\x00")
    off, size = struct.unpack_from("<II", buf, hdr - 8)
    return base + off, size


def entry(buf, us, off):
    n, w = cint(buf, us + off)
    return buf[us + off + w: us + off + w + n - 1].decode("utf-16-le"), w, n


def refs(buf, off):
    tok = (0x70000000 | off).to_bytes(4, "little")
    out, i = [], 0
    while True:
        j = buf.find(b"\x72" + tok, i)
        if j < 0:
            return out
        out.append(j)
        i = j + 1


def main():
    a = sys.argv[1:]
    dll = a[a.index("--dll") + 1] if "--dll" in a else DEFAULT_DLL
    apply = "--apply" in a
    d = bytearray(open(dll, "rb").read())
    D0 = len(d)
    us, size = us_heap(d)

    # ---- 现场校验 ----
    for off, old, new in INPLACE:
        cur, w, n = entry(d, us, off)
        assert cur == old or cur == new, (off, cur, old)
        assert (n - 1) // 2 == len(new), (off, len(new), (n - 1) // 2)
    for off, old, new in SLOTS:
        cur, w, n = entry(d, us, off)
        assert cur == old or cur.startswith(new), (off, cur)
        assert (n - 1) // 2 == len(new), (off, len(new), (n - 1) // 2)
        # 首跑前只有 Debug.Log 一处引用；已改指后多出装备店站点，共 2 处。
        rs = refs(d, off)
        assert 1 <= len(rs) <= 2, ("槽位引用数异常", off, rs)
    for site, old_tok, new_tok in SITES:
        assert d[site] == 0x72, hex(site)
        cur = struct.unpack_from("<I", d, site + 1)[0]
        assert cur in (old_tok, new_tok), (hex(site), hex(cur))

    done = (all(entry(d, us, off)[0] == new for off, old, new in INPLACE)
            and all(entry(d, us, off)[0] == new for off, old, new in SLOTS)
            and all(struct.unpack_from("<I", d, site + 1)[0] == new for site, old, new in SITES))
    if done:
        print("已是补丁后的状态，无需改动。")
        return 0
    if not apply:
        print("待改 #US 条目 %d 个、复用槽位 %d 个、改指 %d 处"
              % (len(INPLACE), len(SLOTS), len(SITES)))
        for off, old, new in INPLACE:
            print("  0x%X %r -> %r" % (off, old, new))
        for off, old, new in SLOTS:
            print("  槽 0x%X %r -> %r" % (off, old, new))
        print("\n(未加 --apply, 未写入)")
        return 0

    bak = dll + BACKUP_SUFFIX
    if not os.path.exists(bak):
        import shutil
        shutil.copyfile(dll, bak)
        print("已备份 ->", os.path.basename(bak))

    allowed = []
    for off, old, new in INPLACE + SLOTS:
        cur, w, n = entry(d, us, off)
        payload = new.encode("utf-16-le")
        d[us + off + w: us + off + w + len(payload)] = payload
        allowed.append((us + off + w, us + off + w + len(payload)))
    for site, old_tok, new_tok in SITES:
        d[site + 1:site + 5] = new_tok.to_bytes(4, "little")
        allowed.append((site + 1, site + 5))
    assert len(d) == D0
    open(dll, "wb").write(d)

    # ---- 复核 ----
    e = open(dll, "rb").read()
    us2, _ = us_heap(e)
    ok = True
    for off, old, new in INPLACE + SLOTS:
        cur, _, _ = entry(e, us2, off)
        print("  #US 0x%X: %r" % (off, cur))
        ok = ok and cur == new
    for site, old_tok, new_tok in SITES:
        cur = struct.unpack_from("<I", e, site + 1)[0]
        print("  站点 0x%X token=0x%X (期望 0x%X)" % (site, cur, new_tok))
        ok = ok and cur == new_tok
    orig = open(bak, "rb").read()
    diff = [i for i in range(D0) if e[i] != orig[i]]
    outside = [i for i in diff if not any(a <= i < b for a, b in allowed)]
    print("DLL 改动 %d 字节（区间外 %d，文件大小不变 %s）"
          % (len(diff), len(outside), len(e) == len(orig)))
    return 0 if (ok and not outside) else 1


if __name__ == "__main__":
    sys.exit(main())
