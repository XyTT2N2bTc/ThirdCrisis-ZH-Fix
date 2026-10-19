# -*- coding: utf-8 -*-
# 为 patch_item_guids.py 换过 GUID 的 49 个物品补语言包 Items 条目。
# 条目来自 translation/item_guid_map.json（英文名/描述 + 中文译文）。
#
# 用法: python fix_item_translations.py [--src <json>] [--map <json>] [--apply]
import os, json, sys

ROOT = r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows"
SRC = os.path.join(ROOT, r"ThirdCrisis_Data\StreamingAssets\Languages\translated_zh_translation.json")
_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MAP = next(
    (p for p in (os.path.join(_HERE, "..", "item_guid_map.json"),
                 os.path.join(_HERE, "..", "translation", "item_guid_map.json"))
     if os.path.exists(p)),
    os.path.join(_HERE, "..", "item_guid_map.json"),
)


# 历史命名差异校正： (Id, 正确的英文名, 正确的中文名)
NAME_FIXES = {
    "440c1e78bf30a704786e52201a9491b6": ("Pink Stomach Heart Tattoo", "粉色腹部爱心纹身"),
}


def ensure(path=SRC, apply=False, quiet=False):
    rows = json.load(open(DEFAULT_MAP, encoding="utf-8"))
    d = json.load(open(path, encoding="utf-8"))
    items = d["Items"]
    have = {e.get("Id") for e in items}
    by_id = {e.get("Id"): e for e in items}
    fixed = 0
    for gid, (nm, zh) in NAME_FIXES.items():
        e = by_id.get(gid)
        if e and (e.get("Name") != nm or e.get("TranslatedName") != zh):
            e["Name"] = nm
            e["TranslatedName"] = zh
            fixed += 1
            if not quiet:
                print("   命名校正: %s -> %r / %r" % (gid[:8], nm, zh))
    added = 0
    for r in rows:
        gid = r["new_guid"]
        if gid in have:
            continue
        items.append({
            "Id": gid,
            "Name": r["name"],
            "Description": r["desc"],
            "TranslatedName": r["zh"],
            "TranslatedDescription": r["zh_desc"],
        })
        have.add(gid)
        added += 1
        if not quiet:
            print("   新增物品: %-32s %s" % (r["obj"], r["zh"]))
    if not quiet:
        print("物品条目: 现有 %d 条, 新增 %d 条, 命名校正 %d 条" % (len(items), added, fixed))
    if (added or fixed) and apply:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
        if not quiet:
            print("已写入 %s（Items %d 条）" % (os.path.basename(path), len(items)))
    return added + fixed


if __name__ == "__main__":
    a = sys.argv[1:]
    src = a[a.index("--src") + 1] if "--src" in a else SRC
    n = ensure(src, apply="--apply" in a)
    if "--apply" not in a:
        print("(未加 --apply, 未写入; 待新增 %d 条)" % n)
