# -*- coding: utf-8 -*-
# 修暂停菜单（ESC）里的 History 标签：
#   History 与 Options 两个标签的 UILocalization 组件用了同一个 guid
#   042b7b07-f76d-4859-9959-20d92386540c（语言包里 →「选项」），
#   所以中文（以及所有语言）下 History 都显示成 Options 的译文。
#   做法：给 History 标签（组件 pathID 151279）换一个独立 guid，
#   并在语言包的 UILocalizations 段补一条 HISTORY →「历史记录」。
#
# 用法: python fix_pause_history.py [--asset <resources.assets>] [--lang <json>] [--apply]
import os, struct, sys, json

ROOT = r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows"
DEFAULT_ASSET = os.path.join(ROOT, r"ThirdCrisis_Data\resources.assets")
DEFAULT_LANG = os.path.join(ROOT, r"ThirdCrisis_Data\StreamingAssets\Languages\translated_zh_translation.json")

COMPONENT_ID = 151279              # History → Text 上的 UILocalization
GUID_OFF = 0x24                    # 0x20 = guid 长度, 0x24 = 36 字符 guid
OLD_GUID = "042b7b07-f76d-4859-9959-20d92386540c"
NEW_GUID = "b7c2e4a1-5f3d-4a86-9e21-0c8d7b6a4f52"
TEXT = "历史记录"
ORIGINAL = "HISTORY"


def ensure_asset(path, apply):
    import UnityPy
    env = UnityPy.load(path)
    objs = [o for o in env.objects if o.path_id == COMPONENT_ID]
    if len(objs) != 1:
        raise RuntimeError("找不到唯一的 UILocalization 组件 %d" % COMPONENT_ID)
    o = objs[0]
    d = o.get_raw_data()
    n = struct.unpack_from("<i", d, 0x20)[0]
    if n != 36:
        raise RuntimeError("guid 长度异常: %d" % n)
    cur = d[GUID_OFF:GUID_OFF + 36].decode("utf-8")
    if cur == NEW_GUID:
        return 0
    if cur != OLD_GUID:
        raise RuntimeError("组件 guid 现场不符: %r（既不是旧 guid 也不是新 guid）" % cur)
    if not apply:
        return 1
    bak = path + ".bak-thirdcrisis-pause-history"
    if not os.path.exists(bak):
        import shutil
        shutil.copyfile(path, bak)
    with open(path, "r+b") as f:
        f.seek(o.byte_start + GUID_OFF)
        f.write(NEW_GUID.encode("ascii"))
    return 1


def ensure_json(path, apply):
    raw = open(path, "rb").read()
    text = raw.decode("utf-8")
    d = json.loads(text)
    arr = d.get("UILocalizations")
    if not isinstance(arr, list):
        raise RuntimeError("语言包缺少 UILocalizations 段")
    cur = [e for e in arr if e.get("guid") == NEW_GUID]
    if cur:
        if cur[0].get("text") == TEXT:
            return 0
        if not apply:
            return 1
        cur[0]["text"] = TEXT
        json.dump(d, open(path, "w", encoding="utf-8", newline="\n"),
                  ensure_ascii=False, separators=(",", ":"))
        return 1
    entry = json.dumps({"guid": NEW_GUID, "originalText": ORIGINAL, "text": TEXT},
                       ensure_ascii=False, separators=(",", ":"))
    needle = '"UILocalizations":['
    i = text.find(needle)
    if i < 0:
        raise RuntimeError("语言包结构不符，找不到 %s" % needle)
    new = text[:i + len(needle)] + entry + "," + text[i + len(needle):]
    json.loads(new)                     # 写入前先验证仍是合法 JSON
    if not apply:
        return 1
    open(path, "wb").write(new.encode("utf-8"))
    return 1


def main(apply, asset=DEFAULT_ASSET, lang=DEFAULT_LANG):
    print("资源:", asset)
    print("语言包:", lang)
    try:
        na = ensure_asset(asset, apply)
        nl = ensure_json(lang, apply)
    except RuntimeError as e:
        print("  !!", e)
        return 1
    print("组件 guid %s；语言包条目 %s"
          % ("已切换" if na == 0 else ("待切换" if not apply else "已写入"),
             "已存在" if nl == 0 else ("待补" if not apply else "已补")))
    if not apply and (na or nl):
        print("\n(未加 --apply, 未写入)")
        return 0
    # 复核
    import UnityPy
    env = UnityPy.load(asset)
    o = [x for x in env.objects if x.path_id == COMPONENT_ID][0]
    cur = o.get_raw_data()[GUID_OFF:GUID_OFF + 36].decode("utf-8")
    d = json.load(open(lang, encoding="utf-8"))
    hit = [e for e in d["UILocalizations"] if e.get("guid") == NEW_GUID]
    ok = cur == NEW_GUID and hit and hit[0].get("text") == TEXT
    print("回读: 组件 guid=%s；条目=%r" % (cur, hit[0] if hit else None))
    return 0 if ok else 1


if __name__ == "__main__":
    a = sys.argv[1:]
    def opt(k, d):
        return a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else d
    sys.exit(main("--apply" in a, opt("--asset", DEFAULT_ASSET), opt("--lang", DEFAULT_LANG)))
