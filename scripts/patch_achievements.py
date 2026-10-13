# -*- coding: utf-8 -*-
# 就地汉化 Third Crisis 0.57.1 的成就名称与描述（第三处）：成就名/描述是烘在
# ThirdCrisis_Data\resources.assets 里的英文字面量。
#
# 为什么只能改资产：本地化文件没有成就通道——DLL 的 ANToolkit.Localization 只有
# Missions/Items/Abilities/Journal/Scene/Dialogue/UILocalization/LocalizedStrings 八类接口，
# 没有成就接口；es/ja/ru/zh 四个随包语言文件里也都不含任何成就名或描述（实测 0 命中）。
#
# 写法（Unity 字符串字段 = [int32 长度][UTF-8 字节][补零到 4 字节对齐]）：
#   长度前缀改写为该槽"对齐后大小"，内容写中文后用空格补满同样字节数。
#   这样读取器读到的字节数与落点都不变 → 文件大小与后续所有字段偏移完全不变。
#   前缀必须随之改写：若沿用原长度，当中文比英文长（例如 "Revelations"=11 字节 vs
#   "真相大白"=12 字节）读取器会切在半个汉字上，显示乱码。
#
# 幂等：重复运行会重新定位并比对，内容已一致则报告无需改动、不写文件。
# 用法: python patch_achievements.py [--apply]     # 不带 --apply 只检查
import os, re, shutil, sys

ROOT = r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows"
ASSET = os.path.join(ROOT, r"ThirdCrisis_Data\resources.assets")
BAK = ASSET + ".bak-thirdcrisis-zh-ach"

# 成就 ID -> (中文名称, 中文描述)
ZH = {
 "ACH_COMBAT_DEFEAT_ENEMIES_1": ("斗士", "击败50名敌人"),
 "ACH_COMPLETE_GALLERY_CHAR":   ("角色收藏家", "集齐画廊中所有可解锁角色"),
 "ACH_COMPLETE_GALLERY_FULL":   ("画廊全收藏", "集齐整个画廊"),
 "ACH_COMPLETE_GALLERY_PINUPS": ("插画收藏家", "集齐画廊中所有插画"),
 "ACH_COMPLETE_GALLERY_SCENES": ("场景收藏家", "集齐画廊中所有场景"),
 "ACH_COMPLETE_JOURNAL":        ("博闻者", "集齐日志"),
 "ACH_DANCING_FC":              ("全连击", "不断拍完成一首歌"),
 "ACH_MONEY_EARN_1":            ("跑腿的", "赚取100fB"),
 "ACH_PERV_1":                  ("业余", "获得50堕落"),
 "ACH_PERV_2":                  ("变态", "获得100堕落"),
 "ACH_PERV_3":                  ("无耻", "获得200堕落"),
 "ACH_PET_CAT":                 ("爱猫人", "达到最高抚摸等级"),
 "ACH_PURE_1":                  ("挺直腰杆", "保持纯洁顶撞克劳斯"),
 "ACH_PURE_2":                  ("痛苦安眠", "保持纯洁与凯伦同眠"),
 "ACH_STORY_1":                 ("小小挫折", "完成序章"),
 "ACH_STORY_10":                ("多吃蔬菜", "在地下二层击败芙洛拉"),
 "ACH_STORY_11":                ("真相大白", "在地下二层击败野火"),
 "ACH_STORY_12":                ("背叛", "逃离枢纽"),
 "ACH_STORY_13":                ("新面孔", "结识隧道里的怪人们"),
 "ACH_STORY_14":                ("别乱动", "穿过迷雾洞穴"),
 "ACH_STORY_2":                 ("一尘不染", "首次打扫镇政厅"),
 "ACH_STORY_3":                 ("舞娘", "招募茱尔入队"),
 "ACH_STORY_4":                 ("爆炸性成就", "为黑市取得炸药"),
 "ACH_STORY_5":                 ("酒精运作", "取得GAG的酒"),
 "ACH_STORY_6":                 ("开阔眼界", "从Horizon救出市民"),
 "ACH_STORY_7":                 ("悸动时刻", "完成与悸动的巡逻"),
 "ACH_STORY_8":                 ("扑灭火势", "在伏击中击败野火"),
 "ACH_STORY_9":                 ("触动的故事", "在一层击败并改造受触者"),
 # "Too Fast Too Pure-ious" 是 "Too Fast Too Furious"(速度与激情) 的谐音双关
 "ACH_STORY_OPTIONAL_1":        ("速度与纯洁", "无伤且未被激光击中击败利思"),
 "ACH_STORY_OPTIONAL_2":        ("无情", "逃离枢纽时击败每一个魔徒"),
 "ACH_STORY_OPTIONAL_3":        ("烈焰不熄", "在野火无伤的情况下击败芙洛拉"),
 "ACH_STORY_OPTIONAL_4":        ("健忘", "在废墟据点忘掉内衣或内裤"),
 "ACH_STORY_OPTIONAL_5":        ("往右走", "你应该一直往右走，直到走不动为止"),
}
HEX32 = re.compile(r"[0-9a-f]{32}")


def align4(n):
    return (n + 3) // 4 * 4


def read_slot(buf, pos, maxlen=400):
    """pos 指向 int32 长度前缀。内容允许 ASCII 或 UTF-8 文本（补丁前后都能定位）。
    返回 (文本, 内容起点, 内容字节数, 下一字段位置)。"""
    if pos + 4 > len(buf):
        return None
    n = int.from_bytes(buf[pos:pos + 4], "little")
    if not (1 <= n <= maxlen):
        return None
    raw = bytes(buf[pos + 4:pos + 4 + n])
    if len(raw) != n:
        return None
    try:
        text = raw.decode("utf-8").rstrip(" ")
    except UnicodeDecodeError:
        return None
    if not text or any(c < " " for c in text):
        return None
    return text, pos + 4, n, pos + 4 + align4(n)


def find_slots(buf, aid):
    """定位 aid 的 (名称槽, 描述槽)。用"描述槽之后 8 字节内出现 32 位十六进制 guid 字符串"
    做结构校验，排除把其它字符串误当槽位的情况。"""
    out = []
    for m in re.finditer(re.escape(aid.encode()) + rb"(?![A-Za-z0-9_])", buf):
        start = m.end()
        for p in range(start, min(start + 80, len(buf) - 4)):
            r1 = read_slot(buf, p)
            if not r1 or len(r1[0]) < 2 or r1[0] == aid:
                continue
            for q in range(r1[3], min(r1[3] + 40, len(buf) - 4)):
                r2 = read_slot(buf, q)
                if not r2 or len(r2[0]) < 2 or r2[0] == aid:
                    continue
                for w in range(r2[3], min(r2[3] + 8, len(buf) - 4)):
                    r3 = read_slot(buf, w)
                    if r3 and HEX32.fullmatch(r3[0]):
                        out.append((r1, r2))
                        break
                break
            break
    return out


def main(apply=False):
    buf = bytearray(open(ASSET, "rb").read())
    orig_size = len(buf)
    slots, problems = {}, []

    for aid in sorted(ZH):
        found = find_slots(buf, aid)
        if len(found) != 1:
            problems.append("%s: 定位到 %d 条记录(应为 1)" % (aid, len(found)))
            continue
        r1, r2 = found[0]
        slots[aid] = {"name": r1[0], "desc": r2[0], "noff": r1[1], "nlen": r1[2],
                      "doff": r2[1], "dlen": r2[2],
                      "nb": align4(r1[2]), "db": align4(r2[2])}
        zn, zd = ZH[aid]
        for label, txt, budget, off, ln in (("名称", zn, align4(r1[2]), r1[1], r1[2]),
                                            ("描述", zd, align4(r2[2]), r2[1], r2[2])):
            if len(txt.encode("utf-8")) > budget:
                problems.append("%s %s 超出预算: 需 %d 字节, 可用 %d" % (aid, label, len(txt.encode("utf-8")), budget))
            if any(buf[off + ln: off + align4(ln)]):
                problems.append("%s %s 字符串后填充非零（对齐模型不成立）" % (aid, label))

    todo = [a for a in slots if slots[a]["name"] != ZH[a][0] or slots[a]["desc"] != ZH[a][1]]
    print("定位成就 %d/%d；已一致 %d 条；待改写 %d 条；问题 %d 条"
          % (len(slots), len(ZH), len(slots) - len(todo), len(todo), len(problems)))
    for p in problems:
        print("   !!", p)
    if problems:
        print("存在定位/预算问题, 中止。")
        return 1
    if not todo:
        print("无需改动（幂等: 内容已与目标一致）。")
        return 0
    if not apply:
        print("(未加 --apply, 未写入)")
        return 0

    if not os.path.exists(BAK):
        shutil.copyfile(ASSET, BAK)
        print("已备份原资产 -> %s (%d 字节)" % (os.path.basename(BAK), os.path.getsize(BAK)))
    for aid in sorted(todo):
        s = slots[aid]
        zn, zd = ZH[aid]
        for off, budget, txt in ((s["noff"], s["nb"], zn), (s["doff"], s["db"], zd)):
            raw = txt.encode("utf-8")
            assert len(raw) <= budget
            buf[off - 4:off] = budget.to_bytes(4, "little")     # 长度前缀 = 对齐后大小
            buf[off:off + budget] = raw + b" " * (budget - len(raw))
    assert len(buf) == orig_size, "文件大小发生变化, 拒绝写入"
    open(ASSET, "wb").write(buf)
    print("已写入 %s（%d 字节, 与改写前同大小）, 改写 %d 条" % (os.path.basename(ASSET), os.path.getsize(ASSET), len(todo)))
    return 0


if __name__ == "__main__":
    sys.exit(main(apply="--apply" in sys.argv))
