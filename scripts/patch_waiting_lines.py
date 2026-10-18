# -*- coding: utf-8 -*-
# 汉化烤在资源里的"等待闲话"（NPC 在城镇里等着的自言自语）：
#   ThirdCrisis_Data/resources.assets 里 pathID 126253 的对象 m_Name = "Townhall_WaitingLine"，
#   内部是一串英文字符串（7 句），不经过语言文件、也没有 guid，所以全量重译覆盖不到，
#   这就是玩家截图里 "I can't think! I need to get my dick inside something, anything!" 的来源。
#
# 判据：该对象的原始字节里 9 个对齐字符串槽（[int32 长度][ASCII][补零到 4 字节]）：
#   Townhall_WaitingLine ×2（名称）, 然后是 7 句台词。台词没有富文本标签，
#   仅第 4 句含 <b>very</b>，译文必须保留 <b></b>。
#
# 写法沿用成就那套：长度前缀写成"对齐后字节数"，中文不足处用空格补齐 —— 文件大小与
# 后续所有字段偏移保持不变。中文必须放得进原英文的对齐后字节预算（台词偏短，需压缩措辞）。
#
# 用法: python patch_waiting_lines.py [--asset <resources.assets>] [--apply]
import os, sys

DEFAULT_ASSET = os.path.join(
    r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows",
    r"ThirdCrisis_Data\resources.assets")
OBJ_MARK = b"Townhall_WaitingLine"      # 仅用于定位对象，不改它

# 原英文 → 中文（按对齐后字节预算压缩；含 <b></b> 者保留标签）
LINES = [
 ("You want a good fuck, baby? I got one right here for you.",
  "想爽一把吗，宝贝？我这儿正好有。"),
 ("I can't wait to pound one of the dumps.",
  "等不及去操一个精液桶了。"),
 ("Finally have enough fuckcreds to get my nut off.",
  "终于攒够操币，可以爽一发。"),
 ("Gonna make one of those dumps a <b>very</b> happy girl.",
  "我要让一个精液桶<b>超</b>开心。"),
 ("Nice legs, sweetie. They'd look better wrapped around me.",
  "腿真漂亮，宝贝。缠在我身上会更好看。"),
 ("Come bounce that ass on this dick, babe.",
  "来弹弹这根鸡巴，宝贝。"),
 ("I can't think! I need to get my dick inside something, anything!",
  "脑子转不动了！我得把鸡巴插进点什么！"),
]


def align4(n):
    return (n + 3) // 4 * 4


def find_slot(buf, text):
    """返回 (内容起始偏移, 原长度, 对齐预算) """
    b = text.encode("ascii")
    prefix = len(b).to_bytes(4, "little")
    pat = prefix + b
    hits = []
    start = 0
    while True:
        i = buf.find(pat, start)
        if i < 0:
            break
        hits.append(i)
        start = i + 1
    if len(hits) != 1:
        raise SystemExit("!! %r 命中 %d 次（应为 1）" % (text[:30], len(hits)))
    i = hits[0]
    return i + 4, len(b), align4(len(b))


def ensure(asset=DEFAULT_ASSET, apply=False):
    bak = asset + ".bak-thirdcrisis-waiting"
    d = bytearray(open(asset, "rb").read())
    orig_size = len(d)

    # 确认对象存在且唯一
    n_obj = d.count(OBJ_MARK)
    print("对象标记 %r 出现 %d 次（应为 2：两个名称字段）" % (OBJ_MARK.decode(), n_obj))
    if n_obj != 2:
        print("  !! 不是预期形态，拒绝执行"); return 1

    # 幂等：若 7 条中文都已存在（各 1 次），说明已打过补丁
    done = sum(1 for _, zh in LINES if len(d) and d.count(zh.encode("utf-8")) >= 1)
    if done == len(LINES):
        print("  已是补丁后的状态（7 条中文均在），无需改动。")
        return 0

    plan = []
    for en, zh in LINES:
        off, ln, budget = find_slot(d, en)
        need = len(zh.encode("utf-8"))
        tag_ok = en.count("<b>") == zh.count("<b>") and en.count("</b>") == zh.count("</b>")
        print("  %-64r → %-30r 预算 %2d / 需 %2d 字节 %s%s"
              % (en[:60], zh, budget, need, "✓" if need <= budget else "✗ 超预算",
                 "" if tag_ok else " ✗ 标签不符"))
        if need > budget or not tag_ok:
            print("  !! 该条无法按等长方式写入，拒绝执行整批"); return 1
        plan.append((off, budget, zh.encode("utf-8")))

    if not apply:
        print("(未加 --apply, 未写入)")
        return 0

    if not os.path.exists(bak):
        import shutil; shutil.copyfile(asset, bak)
        print("已备份 -> %s (%d 字节)" % (os.path.basename(bak), os.path.getsize(bak)))
    for off, budget, raw in plan:
        d[off - 4:off] = budget.to_bytes(4, "little")
        d[off:off + budget] = raw + b" " * (budget - len(raw))
    assert len(d) == orig_size
    open(asset, "wb").write(d)

    # 校验：只允许这些槽位变化；逐条按写入后的前缀读回
    new = open(asset, "rb").read()
    o = open(bak, "rb").read()
    diff = [i for i in range(orig_size) if new[i] != o[i]]
    allowed = set()
    for off, budget, raw in plan:
        allowed.update(range(off - 4, off + budget))
    outside = [i for i in diff if i not in allowed]
    print("已写入 %d 字节；改动 %d 字节，槽位之外 %d 字节" % (len(new), len(diff), len(outside)))
    ok = 0
    for (en, zh), (off, budget, raw) in zip(LINES, plan):
        n = int.from_bytes(new[off - 4:off], "little")
        got = new[off:off + n].decode("utf-8").rstrip(" ")
        if got == zh: ok += 1
        else: print("  !! 回读不符 %r != %r" % (got, zh))
    print("回读校验: %d/%d 条一致" % (ok, len(plan)))
    return 0 if ok == len(plan) and not outside else 1


def main():
    a = sys.argv[1:]
    asset = a[a.index("--asset") + 1] if "--asset" in a and a.index("--asset") + 1 < len(a) else DEFAULT_ASSET
    return ensure(asset, apply="--apply" in a)


if __name__ == "__main__":
    sys.exit(main())
