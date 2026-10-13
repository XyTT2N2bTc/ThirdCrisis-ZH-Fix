# -*- coding: utf-8 -*-
# 向语言文件的 LocalizedStrings 补入当前版本(0.57.1)新增、但随包语言文件缺失的设置项标识符。
#
# 缺口的判定依据：
#   ThirdCrisis_Data/resources.assets 内嵌的默认(英文)本地化表
#   (Settings.* 段位于约 185119708..185122592 字节) 列出了这些标识符，
#   而 es/ja/ru/zh 四个随包语言文件都不含它们 → 游戏打开"选项"菜单时
#   ANToolkit.Localization.Translation.Get 抛 KeyNotFoundException。
# 只补 Settings.* 组：Items.* / stat_perversion_AddStat_* / station.com 虽同形，
#   但经字节区间核对不在本地化表内（分别是 C# 类型名、存档标记键与致谢网址），不得补入。
#
# 用法: python add_missing_keys.py [--apply]   # 不带 --apply 只做检查
# merge.py --write 会在写完后自动调用本模块，故补入的条目不会被后续重建清掉。
import json, os, sys

ROOT = r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows"
SRC = os.path.join(ROOT, r"ThirdCrisis_Data\StreamingAssets\Languages\translated_zh_translation.json")

AFTER = "Settings.OpenDataPrivacyPage"   # 插入位置：与 resources.assets 表中的顺序一致
NEW = [
    ("Settings.ToysTab",             "Toys",                    "玩具"),
    ("Settings.LovenseEnabled",      "Lovense: Enabled",        "Lovense：启用"),
    ("Settings.LovenseIP",           "Lovense: Local IP",       "Lovense：本地 IP"),
    ("Settings.LovensePort",         "Lovense: Port",           "Lovense：端口"),
    ("Settings.LovenseUseHTTP",      "Lovense: Use HTTP",       "Lovense：使用 HTTP"),
    ("Settings.LovenseSetup",        "Lovense: How to Setup",   "Lovense：如何设置"),
    ("Settings.LovenseBuy",          "Buy a Lovense Toy Here",  "在此购买 Lovense 玩具"),
    ("Settings.LovenseDialogueLine", "Vibrate in Dialogue",     "对话中振动"),
    ("Settings.LovenseUserInterface","Vibrate in Interface",    "界面中振动"),
    ("Settings.SeasonalEvents",      "Seasonal Events",         "季节性活动"),
    ("Settings.EnableMultiplayer",   "Enable Multiplayer",      "启用多人游戏"),
]


def ensure_keys(path=SRC, apply=False, quiet=False):
    """确保 path 含 NEW 中的标识符；apply=False 时只报告。返回补入条数。"""
    d = json.load(open(path, encoding="utf-8"))
    ls = d["LocalizedStrings"]
    have = {x["Identifier"] for x in ls}
    todo = [t for t in NEW if t[0] not in have]
    if not quiet:
        print("LocalizedStrings 现有 %d 条, 待补 %d 条" % (len(ls), len(todo)))
        for ident, en, zh in todo:
            print("   + %-32s %-26s %s" % (ident, en, zh))
    if not todo or not apply:
        if not todo and not quiet:
            print("无需改动。")
        return 0
    idx = next(i for i, x in enumerate(ls) if x["Identifier"] == AFTER) + 1
    for k, (ident, en, zh) in enumerate(todo):
        ls.insert(idx + k, {"Identifier": ident, "originalText": en, "text": zh})
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
    if not quiet:
        print("已写入: LocalizedStrings %d -> %d 条" % (len(ls) - len(todo), len(ls)))
    return len(todo)


if __name__ == "__main__":
    ensure_keys(apply="--apply" in sys.argv)
    if "--apply" not in sys.argv:
        print("(未加 --apply, 未写入)")
