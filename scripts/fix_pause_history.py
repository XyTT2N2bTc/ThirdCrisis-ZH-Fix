# -*- coding: utf-8 -*-
# 修 UI 标签共用 UILocalization guid 的缺陷（原游戏复制按钮时没换 guid）：
#   1) 暂停菜单 History 与 Options 共用 042b7b07-…（语言包 →「选项」）
#   2) 对话 HUD History 与 Auto 共用 f39bd612-…（语言包 →「自动」）
#   做法：给 History 标签换独立 guid，并在语言包补 HISTORY / History →「历史记录」。
#
# 用法: python fix_pause_history.py [--asset <resources.assets>] [--lang <json>] [--apply]
import os, struct, sys, json

ROOT = r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows"
DEFAULT_ASSET = os.path.join(ROOT, r"ThirdCrisis_Data\resources.assets")
DEFAULT_LANG = os.path.join(ROOT, r"ThirdCrisis_Data\StreamingAssets\Languages\translated_zh_translation.json")

GUID_OFF = 0x24                    # 0x20 = guid 长度, 0x24 = 36 字符 guid
# (组件 pathID, 旧 guid, 新 guid, 序列化原文, 译文, 说明)
FIXES = [
    (151279, "042b7b07-f76d-4859-9959-20d92386540c",
     "b7c2e4a1-5f3d-4a86-9e21-0c8d7b6a4f52", "HISTORY", "历史记录", "暂停菜单 History"),
    (157278, "f39bd612-e901-4176-9834-4777d6e81723",
     "c4e1d9a2-7b3f-4e58-a6d0-9f2c8b5e1a47", "History", "历史记录", "对话 HUD History"),
]


def ensure_asset(path, apply):
    import UnityPy
    env = UnityPy.load(path)
    byid = {o.path_id: o for o in env.objects}
    pending, done = [], 0
    for pid, old, new, orig, text, label in FIXES:
        o = byid.get(pid)
        if o is None:
            raise RuntimeError("找不到组件 %d（%s）" % (pid, label))
        d = o.get_raw_data()
        n = struct.unpack_from("<i", d, 0x20)[0]
        if n != 36:
            raise RuntimeError("%s: guid 长度异常 %d" % (label, n))
        cur = d[GUID_OFF:GUID_OFF + 36].decode("utf-8")
        if cur == new:
            done += 1
        elif cur == old:
            pending.append((label, o.byte_start, cur, new))
        else:
            raise RuntimeError("%s: guid 现场不符 %r（既不是旧 guid 也不是新 guid）" % (label, cur))
    if not pending:
        return 0, 0
    if apply:
        bak = path + ".bak-thirdcrisis-pause-history"
        if not os.path.exists(bak):
            import shutil
            shutil.copyfile(path, bak)
        with open(path, "r+b") as f:
            for label, off, cur, new in pending:
                f.seek(off + GUID_OFF)
                f.write(new.encode("ascii"))
    return len(pending), done


def ensure_json(path, apply):
    raw = open(path, "rb").read()
    text = raw.decode("utf-8")
    d = json.loads(text)
    arr = d.get("UILocalizations")
    if not isinstance(arr, list):
        raise RuntimeError("语言包缺少 UILocalizations 段")
    have = {e.get("guid"): e for e in arr}
    missing, fix_text = [], []
    for pid, old, new, orig, zh, label in FIXES:
        e = have.get(new)
        if e is None:
            missing.append((new, orig, zh))
        elif e.get("text") != zh:
            fix_text.append((e, zh))
    if not missing and not fix_text:
        return 0
    if not apply:
        return len(missing) + len(fix_text)
    if fix_text:
        for e, zh in fix_text:
            e["text"] = zh
        json.dump(d, open(path, "w", encoding="utf-8", newline="\n"),
                  ensure_ascii=False, separators=(",", ":"))
        return len(missing) + len(fix_text)
    needle = '"UILocalizations":['
    i = text.find(needle)
    if i < 0:
        raise RuntimeError("语言包结构不符，找不到 %s" % needle)
    entries = ",".join(json.dumps({"guid": g, "originalText": o, "text": z},
                                  ensure_ascii=False, separators=(",", ":"))
                       for g, o, z in missing)
    new = text[:i + len(needle)] + entries + "," + text[i + len(needle):]
    json.loads(new)                     # 写入前先验证仍是合法 JSON
    open(path, "wb").write(new.encode("utf-8"))
    return len(missing)


def main(apply, asset=DEFAULT_ASSET, lang=DEFAULT_LANG):
    print("资源:", asset)
    print("语言包:", lang)
    try:
        na, done = ensure_asset(asset, apply)
        nl = ensure_json(lang, apply)
    except RuntimeError as e:
        print("  !!", e)
        return 1
    print("组件 guid: %d 处已切换，%d 处%s；语言包条目 %d 条%s"
          % (done, na, "待切换" if not apply else "已写入", nl,
             "待补" if not apply else "已补"))
    if not apply and (na or nl):
        print("\n(未加 --apply, 未写入)")
        return 0
    # 复核
    import UnityPy
    env = UnityPy.load(asset)
    byid = {o.path_id: o for o in env.objects}
    d = json.load(open(lang, encoding="utf-8"))
    have = {e.get("guid"): e for e in d["UILocalizations"]}
    ok = True
    for pid, old, new, orig, zh, label in FIXES:
        cur = byid[pid].get_raw_data()[GUID_OFF:GUID_OFF + 36].decode("utf-8")
        e = have.get(new)
        print("  %s: guid=%s；条目=%r" % (label, cur, e))
        ok = ok and cur == new and e is not None and e.get("text") == zh
    return 0 if ok else 1


if __name__ == "__main__":
    a = sys.argv[1:]
    def opt(k, d):
        return a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else d
    sys.exit(main("--apply" in a, opt("--asset", DEFAULT_ASSET), opt("--lang", DEFAULT_LANG)))
