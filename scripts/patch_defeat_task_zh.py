# -*- coding: utf-8 -*-
# 任务/任务栏里「击败敌人」类任务的英文前缀：
#   PlayMaker FSM "Mission_Generic_DefeatEnemyAmount_Logic" 用字符串拼接生成
#   "Defeat " + 敌人名 + " (当前 / 目标)"，结果写进 NewTask.OverrideDisplayName，
#   而 OverrideDisplayName 的优先级高于语言包的译文，所以中文下仍是英文。
#   做法：把 FSM 里两处字符串常量 "Defeat "（任务名与任务栏名各一处）等字节数改成
#   「击败 」——UTF-8 都是 7 字节，长度前缀与对齐不变，FSM 二进制不动。
#
# 用法: python patch_defeat_task_zh.py [--asset <resources.assets>] [--apply]
import os, sys

ROOT = r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows"
DEFAULT_ASSET = os.path.join(ROOT, r"ThirdCrisis_Data\resources.assets")
BACKUP_SUFFIX = ".bak-thirdcrisis-defeat-task"

OLD = b"\x07\x00\x00\x00Defeat "
NEW_TEXT = "击败 "
NEW = b"\x07\x00\x00\x00" + NEW_TEXT.encode("utf-8")
assert len(NEW) == len(OLD)


def find_all(buf, pat):
    out, i = [], 0
    while True:
        j = buf.find(pat, i)
        if j < 0:
            return out
        out.append(j)
        i = j + 1


def main():
    a = sys.argv[1:]
    asset = a[a.index("--asset") + 1] if "--asset" in a else DEFAULT_ASSET
    apply = "--apply" in a
    d = bytearray(open(asset, "rb").read())
    old_hits = find_all(d, OLD)
    new_hits = find_all(d, NEW)
    if len(new_hits) == 2 and not old_hits:
        print("已是补丁后的状态，无需改动。")
        return 0
    if len(old_hits) != 2:
        print("!! 现场不符：旧串 %d 处（期望 2），新串 %d 处" % (len(old_hits), len(new_hits)))
        return 1
    if new_hits:
        print("!! 旧串与新串同时存在，拒绝执行")
        return 1
    print("待改 2 处：%s -> %r（各 7 字节）" % ([hex(x) for x in old_hits], NEW_TEXT))
    if not apply:
        print("\n(未加 --apply, 未写入)")
        return 0

    bak = asset + BACKUP_SUFFIX
    if not os.path.exists(bak):
        import shutil
        shutil.copyfile(asset, bak)
        print("已备份 ->", os.path.basename(bak))
    for off in old_hits:
        d[off:off + len(OLD)] = NEW
    open(asset, "wb").write(d)

    # 复核
    e = open(asset, "rb").read()
    nh, oh = find_all(e, NEW), find_all(e, OLD)
    print("回读：新串 %d 处 %s；旧串 %d 处" % (len(nh), [hex(x) for x in nh], len(oh)))
    # 结构校验：UnityPy 能正常加载
    import UnityPy
    env = UnityPy.load(asset)
    print("对象数:", len(env.objects))
    return 0 if (len(nh) == 2 and not oh and len(env.objects) > 0) else 1


if __name__ == "__main__":
    sys.exit(main())
