# -*- coding: utf-8 -*-
# 修 Third Crisis 0.57.1 中文包里两处"陈旧版本号"文本。
#
# 依据（实测）：
#   - 语言包 UILocalizations 里 guid=677b7acf-1f8a-4de7-a039-a637eea40670 的条目共 84 条，
#     文本是 "0.39.0-pr - (2019.4.12f1)"（83 条）与 "0.40.0-pr - (2019.4.12f1)"（1 条）。
#     该 guid 挂在 GameObject「Version (1)」上的翻译组件（pathID 153000，字段 guid + IgnoreTranslation=0）
#     → 文本由语言包按 guid 提供，改 text 即可改显示。
#   - 另一处 guid=af32b929-5862-4d10-b237-c373cc00c056 的 84 条文本是
#     "Third Crisis (0.39.0-pr) on WindowsEditor"（83 条）/"…0.40.0-pr…"（1 条）。
#   - 本作实际版本：bundleVersion = 0.57.1-r（ThirdCrisis_Data/globalgamemanagers），
#     引擎 Unity 2022.3.7f1（Player.log 的 Initialize engine version）。
# 只改 text，不动 originalText —— 游戏按 guid 查表，保留 originalText 可让旧键值仍能被文本匹配，
# 万一别处按原文查找也不受影响。
#
# 用法: python fix_version_strings.py [--apply]
# merge.py --write 之后会自动调用本模块。
import json, os, sys

ROOT = r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows"
SRC = os.path.join(ROOT, r"ThirdCrisis_Data\StreamingAssets\Languages\translated_zh_translation.json")

VERSION = "0.57.1-r"
UNITY = "2022.3.7f1"
FIXES = {
    "677b7acf-1f8a-4de7-a039-a637eea40670": "%s - (%s)" % (VERSION, UNITY),
    "af32b929-5862-4d10-b237-c373cc00c056": "Third Crisis (%s) on WindowsEditor" % VERSION,
}


def ensure(path=SRC, apply=False, quiet=False):
    d = json.load(open(path, encoding="utf-8"))
    n = 0
    for x in d["UILocalizations"]:
        g = x.get("guid")
        if g in FIXES and x.get("text") != FIXES[g]:
            if not quiet:
                print("   改: guid=%s %r → %r" % (g, (x.get("text") or "")[:40], FIXES[g]))
            x["text"] = FIXES[g]
            n += 1
    if not quiet:
        print("版本号文本: 改动 %d 条" % n)
    if n and apply:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
        if not quiet:
            print("已写入 %s" % os.path.basename(path))
    return n


if __name__ == "__main__":
    k = ensure(apply="--apply" in sys.argv)
    if "--apply" not in sys.argv:
        print("(未加 --apply, 未写入; 待改动 %d 条)" % k)
