# 回填 done/*.json (按唯一原文匹配) 到 zh 结构, 跑校验门禁。
# 用法: python merge.py [--write] [--root <游戏目录>] [--done <译文语料目录>]
#   默认路径是本机工作目录; 分发给他人时用 --root / --done 指定。
import json, os, re, sys, glob

def _opt(name, default):
    a = sys.argv[1:]
    if name in a and a.index(name) + 1 < len(a):
        return a[a.index(name) + 1]
    return default

ROOT = _opt("--root", r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows")
SRC = _opt("--src", os.path.join(ROOT, r"ThirdCrisis_Data\StreamingAssets\Languages\translated_zh_translation.json"))
DONE_DIR = _opt("--done", os.path.join(ROOT, r"tmp\l10n\done"))
BAK = SRC + ".bak"

d = json.load(open(SRC, encoding="utf-8"))
T = {}  # orig -> translated
for fp in sorted(glob.glob(os.path.join(DONE_DIR, "*.json"))):
    for x in json.load(open(fp, encoding="utf-8")):
        t, x2 = x["t"], x["x"]
        if t in T and T[t] != x2:
            print("!! 原文重复且译文不一致: %r" % t[:40])
        T[t] = x2

TAG = re.compile(r"</?[a-zA-Z]+(?:=[^>]+)?>")
def tags(s): return TAG.findall(s or "")

# SET[kind](对象, 译文): 把译文写入对应字段
SET = {
    "U":  lambda o, v: o.__setitem__("text", v),
    "D":  lambda o, v: o.__setitem__("text", v),
    "C":  lambda o, v: o.__setitem__("text", v),
    "S":  lambda o, v: o.__setitem__("text", v),
    "MN": lambda o, v: o.__setitem__("TranslatedName", v),
    "MD": lambda o, v: o.__setitem__("TranslatedDescription", v),
    "MT": lambda o, v: o.__setitem__("TranslatedDisplayName", v),
    "JN": lambda o, v: o.__setitem__("TranslatedName", v),
    "JC": lambda o, v: o.__setitem__("TranslatedContents", v),
    "IN": lambda o, v: o.__setitem__("TranslatedName", v),
    "ID": lambda o, v: o.__setitem__("TranslatedDescription", v),
    "SN": lambda o, v: o.__setitem__("TranslatedName", v),
    "AN": lambda o, v: o.__setitem__("TranslatedName", v),
    "AT": lambda o, v: o.__setitem__("TranslatedToolTip", v),
}

def targets(t):
    """返回所有落点 [(kind, 对象, sid), ...]"""
    out = []
    for i, x in enumerate(d["UILocalizations"]):
        if x.get("originalText") == t: out.append(("U", x, "U%d" % i))
    for di, dg in enumerate(d["Dialogues"]):
        for li, ln in enumerate(dg["Lines"]):
            if ln.get("originalText") == t: out.append(("D", ln, "D%d_%d" % (di, li)))
            for ci, ch in enumerate(ln.get("Choices") or []):
                if ch.get("originalText") == t: out.append(("C", ch, "C%d_%d_%d" % (di, li, ci)))
    for i, x in enumerate(d["LocalizedStrings"]):
        if x.get("originalText") == t: out.append(("S", x, "S%d" % i))
    for i, x in enumerate(d["Missions"]):
        if x.get("Name") == t: out.append(("MN", x, "MN%d" % i))
        if x.get("Description") == t: out.append(("MD", x, "MD%d" % i))
        for ti, tk in enumerate(x.get("Tasks") or []):
            if tk.get("DisplayName") == t: out.append(("MT", tk, "MT%d_%d" % (i, ti)))
    for i, x in enumerate(d["JournalEntries"]):
        if x.get("Name") == t: out.append(("JN", x, "JN%d" % i))
        if x.get("Contents") == t: out.append(("JC", x, "JC%d" % i))
    for i, x in enumerate(d["Items"]):
        if x.get("Name") == t: out.append(("IN", x, "IN%d" % i))
        if x.get("Description") == t: out.append(("ID", x, "ID%d" % i))
    for i, x in enumerate(d["SceneNames"]):
        if x.get("Name") == t: out.append(("SN", x, "SN%d" % i))
    for i, x in enumerate(d["Abilities"]):
        if x.get("Name") == t: out.append(("AN", x, "AN%d" % i))
        if x.get("Tooltip") == t: out.append(("AT", x, "AT%d" % i))
    return out

errors, applied, missing = [], 0, []
for orig, x2 in T.items():
    pts = targets(orig)
    if not pts:
        missing.append(orig[:60]); continue
    if not (x2 or "").strip():
        errors.append(("空译文", orig[:50])); continue
    if sorted(tags(orig)) != sorted(tags(x2)):
        errors.append(("标签不匹配", orig[:40], tags(orig), tags(x2))); continue
    if (orig.rstrip() != orig) != (x2.rstrip() != x2) or (orig.lstrip() != orig) != (x2.lstrip() != x2):
        errors.append(("首尾空白不一致", repr(orig[-12:]), repr(x2[-12:]))); continue
    if orig.count("\n") != x2.count("\n"):
        errors.append(("换行数不一致", orig[:40])); continue
    for kind, obj, sid in pts:
        SET[kind](obj, x2); applied += 1

if "--write" in sys.argv:
    if errors:
        print("存在 %d 处校验错误, 拒绝写入" % len(errors))
    else:
        if not os.path.exists(BAK):
            import shutil; shutil.copyfile(SRC, BAK)
        with open(SRC, "w", encoding="utf-8", newline="\n") as f:
            json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
        # 重建是"按 done/ 重写整个文件", 会丢掉不来自 done/ 的补丁; 写完后依次补回。
        # 三份清单各自只在一处维护（见各模块头部说明）。
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import add_missing_keys, fix_journal_entries, fix_version_strings, prune_stale_ui_guids
        n1 = add_missing_keys.ensure_keys(SRC, apply=True, quiet=True)
        n2 = fix_journal_entries.ensure(SRC, apply=True, quiet=True)
        n3 = fix_version_strings.ensure(SRC, apply=True, quiet=True)
        n4 = prune_stale_ui_guids.ensure(SRC, apply=True, quiet=True)
        print("已写入(原文件备份于 .bak): 补设置项 %d 条, 补/改日志条目 %d 条, 改版本号 %d 条, 清过期 UI %d 条"
              % (n1, n2, n3, n4))

print("唯一原文 %d, 已翻译 %d, 落点应用 %d, 校验错误 %d, 未命中落点 %d" %
      (len(T), len(T), applied, len(errors), len(missing)))
for e in errors[:15]: print("  ERR", e)
for m in missing[:10]: print("  MISS", m)
