# -*- coding: utf-8 -*-
# 修物品 TranslationGuid 冲突（原游戏资产复制缺陷）：
#   多个物品资产共用同一个 TranslationGuid，中文下都查到同一条译文，
#   于是装备店里一堆物品显示成「渔网装」「啦啦队乳贴」等。
#   本脚本按 translation/item_guid_map.json 把 49 个冲突物品的 GUID 换成唯一值
#   （32 字符等长，直接改资产里的字符串），语言包条目由 fix_item_translations.py 补。
#
# 用法: python patch_item_guids.py [--asset <resources.assets>] [--map <json>] [--apply]
import os, json, struct, sys

ROOT = r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows"
DEFAULT_ASSET = os.path.join(ROOT, r"ThirdCrisis_Data\resources.assets")
_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MAP = next(
    (p for p in (os.path.join(_HERE, "..", "item_guid_map.json"),
                 os.path.join(_HERE, "..", "translation", "item_guid_map.json"))
     if os.path.exists(p)),
    os.path.join(_HERE, "..", "item_guid_map.json"),
)
BACKUP_SUFFIX = ".bak-thirdcrisis-item-guids"


def main():
    a = sys.argv[1:]
    asset = a[a.index("--asset") + 1] if "--asset" in a else DEFAULT_ASSET
    mpath = a[a.index("--map") + 1] if "--map" in a else DEFAULT_MAP
    apply = "--apply" in a
    rows = json.load(open(mpath, encoding="utf-8"))
    print("映射条目:", len(rows), "资源:", asset)

    import UnityPy
    env = UnityPy.load(asset)
    byid = {o.path_id: o for o in env.objects}
    d = bytearray(open(asset, "rb").read())

    plan, done, bad = [], 0, []
    for r in rows:
        o = byid.get(r["path_id"])
        if o is None:
            bad.append((r["obj"], "对象不存在"))
            continue
        off = o.byte_start + r["guid_off"] + 4
        cur = bytes(d[off:off + 32]).decode("ascii", "replace")
        old, new = r["old_guid"], r["new_guid"]
        if len(old) != 32 or len(new) != 32:
            bad.append((r["obj"], "GUID 长度不为 32"))
        elif cur == new:
            done += 1
        elif cur == old:
            plan.append((r["obj"], off, old, new))
        else:
            bad.append((r["obj"], "现场不符: %r" % cur))
    print("待改 %d, 已是新值 %d, 异常 %d" % (len(plan), done, len(bad)))
    for b in bad[:10]:
        print("  !!", b)
    if bad:
        return 1
    if not plan:
        print("已是补丁后的状态，无需改动。")
        return 0
    if not apply:
        print("\n(未加 --apply, 未写入)")
        return 0

    bak = asset + BACKUP_SUFFIX
    if not os.path.exists(bak):
        import shutil
        shutil.copyfile(asset, bak)
        print("已备份 ->", os.path.basename(bak))
    for obj, off, old, new in plan:
        d[off:off + 32] = new.encode("ascii")
    open(asset, "wb").write(d)

    e = open(asset, "rb").read()
    again = 0
    for obj, off, old, new in plan:
        if bytes(e[off:off + 32]) != new.encode("ascii"):
            print("  !! 回读不符:", obj)
            again += 1
    print("回读: %d/%d 条已写入" % (len(plan) - again, len(plan)))
    return 0 if again == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
