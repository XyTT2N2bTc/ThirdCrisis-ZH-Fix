# -*- coding: utf-8 -*-
# 汉化「场景画廊」：Gallery 资产（resources.assets, pathID 125978）里的
#   分类名 CategoryName / 条目名 GalleryInfo.Name / 解锁提示 UnlockSpoilerInfo
# 这些字符串不走语言文件，是资源里写死的英文；按原分配长度等长改写（空格补齐）。
# 另外把两处旧版 UI.Text 的字体从 Roboto/Sentinel 换成自带中文字体 NotoSerifSC-Regular，
# 否则中文会显示成方块：
#   - 147572 画廊解锁提示 UnlockText 的 m_Font（Roboto-Regular，无中文字形）
#   - 130753 场景按钮的 TooltipFont（Sentinel Type，无中文字形）
#
# 用法: python patch_gallery_zh.py [--asset <resources.assets>] [--map <gallery_zh_map.json>] [--apply]
import os, struct, sys, json

ROOT = r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows"
DEFAULT_ASSET = os.path.join(ROOT, r"ThirdCrisis_Data\resources.assets")
_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MAP = next(
    (p for p in (os.path.join(_HERE, "..", "gallery_zh_map.json"),
                 os.path.join(_HERE, "..", "translation", "gallery_zh_map.json"))
     if os.path.exists(p)),
    os.path.join(_HERE, "..", "gallery_zh_map.json"),
)
PATH_ID = 125978
BACKUP_SUFFIX = ".bak-thirdcrisis-gallery"

# (pathID, 字段内偏移, 期望的当前 PPtr, 说明)
# PPtr 布局：4 字节 fileID + 8 字节 pathID
FONT_TARGET = (0, 10547)          # resources.assets 的 legacy Font: NotoSerifSC-Regular
FONT_PATCHES = [
    (147572, 0x58, (4, 13), "UnlockText(Text).m_Font"),
    (130753, 0x50, (4, 14), "SceneButton.TooltipFont"),
]


def align4(n):
    return (n + 3) // 4 * 4


class Reader:
    """顺序解析 MonoBehaviour 原始字段，同时记录字符串 length 前缀的偏移。"""

    def __init__(self, d):
        self.d = d
        self.p = 0

    def i32(self):
        v = struct.unpack_from("<i", self.d, self.p)[0]
        self.p += 4
        return v

    def u32(self):
        v = struct.unpack_from("<I", self.d, self.p)[0]
        self.p += 4
        return v

    def boolean(self):
        v = bool(self.d[self.p])
        self.p = align4(self.p + 1)
        return v

    def pp(self):
        self.i32()
        self.p += 8

    def string(self):
        off = self.p
        n = self.i32()
        assert 0 <= n <= 20000, (n, off)
        raw = self.d[self.p:self.p + n]
        self.p = align4(self.p + n)
        return raw.decode("utf-8"), off, n


def read_sprite(r):
    r.boolean()
    r.string(); r.string(); r.string()
    r.boolean()


def read_info(r, out):
    name, off, n = r.string()
    out.append(("name", name, off, n))
    r.pp()                      # Scene
    r.i32(); r.i32(); r.i32()   # Version
    for _ in range(r.i32()):    # ScenesToPlay
        r.pp()
    r.pp()                      # PreviewDialogue
    r.string()                  # PreviewLine
    read_sprite(r)              # Background
    r.boolean()                 # StartHidden
    r.boolean()                 # AvailableInPublic
    read_sprite(r)              # ThumbnailResource
    for _ in range(r.i32()):    # ThumbnailResources
        read_sprite(r)
    r.boolean()                 # StartUnlocked
    hint, off, n = r.string()
    out.append(("hint", hint, off, n))


def parse(d):
    r = Reader(d)
    r.pp(); r.u32(); r.pp()
    obj_name, _, _ = r.string()
    out = []
    for _ in range(r.i32()):
        cat, off, n = r.string()
        out.append(("cat", cat, off, n))
        read_sprite(r)
        for _ in range(r.i32()):
            read_info(r, out)
    assert r.p == len(d), "解析未对齐: %d/%d" % (r.p, len(d))
    return obj_name, out


def load_objects(path):
    import UnityPy
    env = UnityPy.load(path)
    byid = {o.path_id: o for o in env.objects}
    ids = [PATH_ID] + [p[0] for p in FONT_PATCHES]
    return {pid: (byid[pid].byte_start, byid[pid].get_raw_data()) for pid in ids}


def main():
    a = sys.argv[1:]
    asset = a[a.index("--asset") + 1] if "--asset" in a else DEFAULT_ASSET
    mpath = a[a.index("--map") + 1] if "--map" in a else DEFAULT_MAP
    apply = "--apply" in a
    mp = json.load(open(mpath, encoding="utf-8"))
    tr = {"cat": mp["categories"], "name": mp["names"], "hint": mp["hints"]}

    objs = load_objects(asset)
    base, raw = objs[PATH_ID]
    obj_name, items = parse(raw)
    print("对象 %r @0x%X size=%d 字段项=%d" % (obj_name, base, len(raw), len(items)))

    # 英文原文以首次写入前留下的 .bak 为准（重跑时当前对象里已是译文）
    bak = asset + BACKUP_SUFFIX
    if os.path.exists(bak):
        _, bk_items = parse(load_objects(bak)[PATH_ID][1])
        assert len(bk_items) == len(items), (len(bk_items), len(items))
        for x, y in zip(bk_items, items):
            assert x[0] == y[0] and x[2] == y[2], (x, y)
        src = bk_items
    else:
        src = items

    # 覆盖检查 + 预算检查
    plan = []
    missing, over = [], []
    for kind, en, off, n in src:
        zh = tr[kind].get(en)
        if zh is None:
            missing.append((kind, en))
            continue
        alloc = align4(4 + n)
        if len(zh.encode("utf-8")) > alloc - 4:
            over.append((kind, en, zh))
            continue
        plan.append((kind, en, zh, off, n))
    print("待改 %d 条；缺译文 %d；超预算 %d" % (len(plan), len(missing), len(over)))
    for x in missing[:10]:
        print("  缺:", x)
    for x in over[:10]:
        print("  超:", x)
    if missing or over:
        return 1

    def read_cur(buf, off, n0):
        alloc = align4(4 + n0)
        ln = struct.unpack_from("<i", buf, off)[0]
        return buf[off + 4:off + 4 + ln].decode("utf-8"), ln, alloc

    strings_done = all(
        read_cur(raw, off, n0)[0].rstrip(" ") == zh and read_cur(raw, off, n0)[1] == align4(4 + n0) - 4
        for kind, en, zh, off, n0 in plan
    )

    font_plan = []
    for pid, off, expect, label in FONT_PATCHES:
        b0, r0 = objs[pid]
        cur = (struct.unpack_from("<i", r0, off)[0], struct.unpack_from("<q", r0, off + 4)[0])
        if cur != expect and cur != FONT_TARGET:
            print("  !! 字体引用现场不符 %s: %r（期望 %r 或 %r）" % (label, cur, expect, FONT_TARGET))
            return 1
        font_plan.append((pid, b0, r0, off, cur, label))
    fonts_done = all(x[4] == FONT_TARGET for x in font_plan)
    print("字符串%s；字体%s" % ("已汉化" if strings_done else "待改",
                              "已切换" if fonts_done else "待切换"))

    if strings_done and fonts_done:
        print("  已是补丁后的状态，无需改动。")
        return 0
    if not apply:
        print("\n(未加 --apply, 未写入)")
        for kind, en, zh, off, n in plan[:5]:
            print("  %s @0x%X %r -> %r" % (kind, off, en, zh))
        for pid, b0, r0, off, cur, label in font_plan:
            print("  font %s: %r -> %r" % (label, cur, FONT_TARGET))
        return 0

    # ---------------- 写入 ----------------
    path = asset
    bak = path + BACKUP_SUFFIX
    if not os.path.exists(bak):
        import shutil
        shutil.copyfile(path, bak)
        print("已备份 ->", os.path.basename(bak))

    writes = []
    buf = bytearray(raw)
    changed = 0
    for kind, en, zh, off, n in plan:
        alloc = align4(4 + n)
        cur, ln, _ = read_cur(buf, off, n)
        if cur.rstrip(" ") == zh and ln == alloc - 4:
            continue
        # Unity 按 align4(4 + 前缀长度) 推进，前缀必须写成“原分配长度-4”，
        # 内容用空格补齐到同样长度，后续字段才不会错位。
        nb = zh.encode("utf-8")
        payload = nb + b" " * (alloc - 4 - len(nb))
        struct.pack_into("<i", buf, off, alloc - 4)
        buf[off + 4:off + alloc] = payload
        changed += 1
    assert len(buf) == len(raw)
    writes.append((base, buf))

    for pid, b0, r0, off, cur, label in font_plan:
        if cur == FONT_TARGET:
            continue
        b = bytearray(r0)
        struct.pack_into("<i", b, off, FONT_TARGET[0])
        struct.pack_into("<q", b, off + 4, FONT_TARGET[1])
        assert len(b) == len(r0)
        writes.append((b0, b))
        print("字体 %s: %r -> %r" % (label, cur, FONT_TARGET))

    orig_file = open(path, "rb").read()   # 校验基线：本次写入前
    with open(path, "r+b") as f:
        for off, b in writes:
            f.seek(off)
            f.write(b)
    print("已写入 %d 条字符串 + %d 处字体（文件大小不变）" % (changed, len(writes) - 1))

    # ---------------- 复核 ----------------
    objs2 = load_objects(asset)
    base2, raw2 = objs2[PATH_ID]
    assert base2 == base and len(raw2) == len(raw)
    _, items2 = parse(raw2)
    bad = 0
    for kind, en, zh, off, n0 in plan:
        cur, ln, alloc = read_cur(raw2, off, n0)
        if cur.rstrip(" ") != zh or ln != align4(4 + n0) - 4:
            bad += 1
            print("  回读不符:", kind, en, repr(cur), ln)
    print("字符串回读: %d/%d 条一致" % (len(plan) - bad, len(plan)))

    fbad = 0
    for pid, off, expect, label in FONT_PATCHES:
        _, r = objs2[pid]
        cur = (struct.unpack_from("<i", r, off)[0], struct.unpack_from("<q", r, off + 4)[0])
        print("  字体回读 %s: %r" % (label, cur))
        fbad += (cur != FONT_TARGET)

    # 字节差异：必须全部落在字符串分配区或字体 PPtr 内
    orig = orig_file
    now = open(path, "rb").read()
    assert len(orig) == len(now)
    allowed = set()
    for kind, en, zh, off, n0 in plan:
        allowed.update(range(base + off, base + off + align4(4 + n0)))
    for pid, off, expect, label in FONT_PATCHES:
        b0, _ = objs[pid]
        allowed.update(range(b0 + off, b0 + off + 12))
    diff = [i for i in range(len(now)) if now[i] != orig[i]]
    outside = [i for i in diff if i not in allowed]
    print("文件改动 %d 字节（区间外 %d，文件大小不变 %s）" % (len(diff), len(outside), len(now) == len(orig)))
    return 0 if (bad == 0 and fbad == 0 and not outside) else 1


if __name__ == "__main__":
    sys.exit(main())
