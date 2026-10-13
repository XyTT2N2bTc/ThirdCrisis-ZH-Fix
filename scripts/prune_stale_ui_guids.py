# -*- coding: utf-8 -*-
# 清理中文包里"构建已不再引用"的过期 UILocalizations 条目。
#
# 依据（实测）：UI 文本按 guid 查表（资源里的翻译组件存 guid 字符串，例如
#   pathID 153000 的组件就带 guid=677b7acf-… 与 IgnoreTranslation 字段）。
#   因此把 ThirdCrisis_Data 全目录（排除 Languages 与 *.bak*）逐字节搜索该 36 位 guid 字符串，
#   搜不到即说明当前构建没有任何 UI 元素引用它 —— 该条目是旧版残留，删掉不影响任何显示。
#
# 用法: python prune_stale_ui_guids.py [--apply]
# merge.py --write 之后会自动调用本模块（done/ 里仍有这些条目，重建后会被再次清掉）。
import json, os, sys

ROOT = r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows"
SRC = os.path.join(ROOT, r"ThirdCrisis_Data\StreamingAssets\Languages\translated_zh_translation.json")
SCAN_ROOT = os.path.join(ROOT, "ThirdCrisis_Data")


def referenced_guids(scan_root=SCAN_ROOT, quiet=False):
    """返回构建侧实际引用的 guid 集合（排除 Languages 目录与备份文件）。"""
    found = set()
    scanned = 0
    for dp, dn, fn in os.walk(scan_root):
        if os.path.basename(dp) == "Languages":
            continue
        for f in fn:
            if ".bak" in f:
                continue
            p = os.path.join(dp, f)
            try:
                with open(p, "rb") as fh:
                    data = fh.read()
            except OSError:
                continue
            scanned += 1
            for g in set(__import__("re").findall(rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", data)):
                found.add(g.decode())
    if not quiet:
        print("扫描 %d 个文件, 构建侧引用 guid %d 个" % (scanned, len(found)))
    return found


def ensure(path=SRC, scan_root=SCAN_ROOT, apply=False, quiet=False):
    live = referenced_guids(scan_root, quiet=quiet)
    d = json.load(open(path, encoding="utf-8"))
    pg_ids = {x.get("guid") for x in d["UILocalizations"]}
    before = len(d["UILocalizations"])
    keep, drop = [], {}
    for x in d["UILocalizations"]:
        g = x.get("guid")
        if g in live:
            keep.append(x)
        else:
            drop[g] = drop.get(g, 0) + 1
    if not quiet:
        print("UILocalizations %d 条 → 保留 %d 条（%d 个 guid 无引用，共 %d 条）"
              % (before, len(keep), len(drop), sum(drop.values())))
    # 防呆：扫描目录给错（例如指到 StreamingAssets）会得到"引用 guid 极少"，
    # 那样几乎整包都会被判定无引用。引用数不到包内 guid 的一半时一律拒绝执行。
    if len(live) * 2 < len(pg_ids):
        print("!! 扫描到的构建引用 guid 仅 %d 个, 远少于包内 %d 个 —— 扫描目录很可能给错了, 拒绝执行"
              % (len(live), len(pg_ids)))
        return 0
    if not drop:
        return 0
    d["UILocalizations"] = keep
    if apply:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
        if not quiet:
            print("已写入 %s" % os.path.basename(path))
    return sum(drop.values())


if __name__ == "__main__":
    n = ensure(apply="--apply" in sys.argv)
    if "--apply" not in sys.argv:
        print("(未加 --apply, 未写入; 待清理 %d 条)" % n)
