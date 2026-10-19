# -*- coding: utf-8 -*-
# 战斗里「切换装备/使用物品」的提示是写死在 CombatItemUsage.cs 里的英文：
#   换装备时体力不足 / 换装备消耗体力的提醒；使用物品的同款两条。
# 做法：#US 里按相同 UTF-16 字符数就地改写（尾部空格不可见）。
#
# 用法: python patch_combat_prompt_texts.py [--dll <Assembly-CSharp.dll>] [--apply]
import os, struct, sys

ROOT = r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows"
DEFAULT_DLL = os.path.join(ROOT, r"ThirdCrisis_Data\Managed\Assembly-CSharp.dll")
BACKUP_SUFFIX = ".bak-thirdcrisis-combat-prompts"

# (原 #US 偏移, 原字符串, 新字符串)
EDITS = [
    (0xEF6D, "I don't have enough energy to use any items right now!",
     "我现在没有足够体力使用物品！"),
    (0xF080, "Gonna have to make sure I don't run out of energy while using items.",
     "得注意别在使用物品时把体力用光。"),
    (0xF10B, "I don't have enough energy to swap my gear right now!",
     "我现在没有足够体力更换装备！"),
    (0xF21C, "Gonna have to make sure I don't run out of energy with all this gear swapping.",
     "换这么多装备，得注意别把体力用光。"),
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


def main():
    a = sys.argv[1:]
    dll = a[a.index("--dll") + 1] if "--dll" in a else DEFAULT_DLL
    apply = "--apply" in a
    d = bytearray(open(dll, "rb").read())
    D0 = len(d)
    us, _ = us_heap(d)

    plan = []
    for off, old, zh in EDITS:
        n, w = cint(d, us + off)
        cur = d[us + off + w: us + off + w + n - 1].decode("utf-16-le")
        chars = (n - 1) // 2
        assert cur in (old, zh + " " * (chars - len(zh))), (off, cur)
        assert len(zh) <= chars, (off, len(zh), chars)
        payload = (zh + " " * (chars - len(zh))).encode("utf-16-le")
        assert len(payload) == n - 1
        if cur != payload.decode("utf-16-le"):
            plan.append((off, w, chars, zh, payload))
    if not plan:
        print("已是补丁后的状态，无需改动。")
        return 0
    print("待改 %d 条：" % len(plan))
    for off, w, chars, zh, payload in plan:
        print("  0x%X %d 字符 -> %r" % (off, chars, zh))
    if not apply:
        print("\n(未加 --apply, 未写入)")
        return 0

    bak = dll + BACKUP_SUFFIX
    if not os.path.exists(bak):
        import shutil
        shutil.copyfile(dll, bak)
        print("已备份 ->", os.path.basename(bak))
    allowed = []
    for off, w, chars, zh, payload in plan:
        d[us + off + w: us + off + w + len(payload)] = payload
        allowed.append((us + off + w, us + off + w + len(payload)))
    assert len(d) == D0
    open(dll, "wb").write(d)

    e = open(dll, "rb").read()
    us2, _ = us_heap(e)
    ok = True
    for off, old, zh in EDITS:
        n, w = cint(e, us2 + off)
        cur = e[us2 + off + w: us2 + off + w + n - 1].decode("utf-16-le")
        print("  回读 0x%X: %r" % (off, cur))
        ok = ok and cur.rstrip() == zh
    orig = open(bak, "rb").read()
    diff = [i for i in range(D0) if e[i] != orig[i]]
    outside = [i for i in diff if not any(x <= i < y for x, y in allowed)]
    print("DLL 改动 %d 字节（区间外 %d，文件大小不变 %s）"
          % (len(diff), len(outside), len(e) == len(orig)))
    return 0 if (ok and not outside) else 1


if __name__ == "__main__":
    sys.exit(main())
