# -*- coding: utf-8 -*-
# 修 Third Crisis 0.57.1 的"中文缺字"（对话等 TMP 文本显示为方块）。
#
# 根因（实测）：
#   Player.log 有 2974 条 "The character with Unicode value \uXXXX was not found in the
#   [Roboto-Condensed_DialogueUI] font asset or any potential fallbacks"，涉及 342 个字符，
#   含 我/的/你/了/在/这 等最常用字。
#   字体接线实测（用 Unity.TextMeshPro.dll 生成类型树读出）：
#     - 游戏里确实带了中文字体：pathID 125747 = "NotoSerifSC-Regular SDF"（73KB，含 SDF 图集）
#     - 对话字体：pathID 125748 = "Roboto-Condensed_DialogueUI"，其自身回退表为空
#     - 全局回退（TMP Settings，pathID 127537）m_fallbackFontAssets = [125743 = "Arial SDF"]
#       —— Arial 也没有中文字形，于是逐级回退都找不到汉字 → 显示 □
#
# 修法：把中文字体挂进回退链
#   1) TMP Settings.m_fallbackFontAssets 追加 NotoSerifSC-Regular SDF（全局兜底）
#   2) 各 TMP 字体资产的 m_FallbackFontAssetTable 追加 Noto（逐字体兜底，TMP 一定查这张表）
#   用 UnityPy + 类型树写回，工具负责重排文件内偏移；不改任何字形/图集数据。
#
# 用法: python fix_font_fallback.py [--apply]   # 不带 --apply 只做演练并校验
import json, os, shutil, sys

ROOT = r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows"
ASSET = os.path.join(ROOT, r"ThirdCrisis_Data\resources.assets")
MANAGED = os.path.join(ROOT, r"ThirdCrisis_Data\Managed")
BAK = ASSET + ".bak-thirdcrisis-zh-font"
TMP_DRY = os.path.join(ROOT, r"ThirdCrisis_Data\_fontfix_dryrun.assets")
UNITY_VERSION = "2022.3.7f1"

NOTO_PATH_ID = 125747      # NotoSerifSC-Regular SDF
TMP_SETTINGS_ID = 127537
# 需要补回退的字体资产（按名称校验，避免 pathID 漂移）
FALLBACK_FONT_IDS = [
    125743,  # Arial SDF
    125744,  # HVDComicSerifPro SDF
    125745,  # HoneyScript-Light SDF
    125746,  # HoneyScript-SemiBold SDF
    125748,  # Roboto-Condensed_DialogueUI  ← 缺字警告就出在它
    125749,  # Roboto-Condensed_SignalUI
    125750,  # Roboto-Medium_TaskWidget
    125751,  # Roboto-Regular SDF
    125752,  # Sentinel Type - BigNoodleToo SDF With Shadow
    125753,  # Sentinel Type - BigNoodleToo SDF
    125754,  # Sentinel Type - BigNoodleTooOblique SDF
    125755,  # Sentinel ... SDF_DropShadow
    125756,  # Sentinel ... SDF_NoOutline
    125757,  # Sentinel ... SDF_Outline
    125758,  # Sentinel ... _DialogueUI_NameTags  ← 名字条也报过缺字
]


def load_env(path):
    import UnityPy
    from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator
    env = UnityPy.load(path)
    gen = TypeTreeGenerator(UNITY_VERSION)
    gen.load_local_dll_folder(MANAGED)
    env.typetree_generator = gen
    return env


def by_path_id(env):
    return {o.path_id: o for o in env.objects}


def digests(sf):
    import hashlib
    m = {}
    for pid, o in sf.objects.items():
        m[pid] = (o.type.name, o.byte_size, hashlib.sha1(o.get_raw_data()).hexdigest())
    return m


def main(apply=False):
    env = load_env(ASSET)
    objs = by_path_id(env)
    sf = next(iter(env.files.values()))
    before = digests(sf)
    # 改动前先抓住待改对象的原始字节, 供字节级校验（必须在 save_typetree 之前取）
    old_raw = {pid: objs[pid].get_raw_data()
               for pid in set([TMP_SETTINGS_ID, NOTO_PATH_ID] + FALLBACK_FONT_IDS) if pid in objs}

    noto_name = objs[NOTO_PATH_ID].read_typetree().get("m_Name")
    if noto_name != "NotoSerifSC-Regular SDF":
        print("!! pathID %d 不是中文字体, 实为 %r — 中止" % (NOTO_PATH_ID, noto_name))
        return 1
    print("中文字体: %d = %r" % (NOTO_PATH_ID, noto_name))

    changed = []
    # 1) 全局回退
    ts = objs[TMP_SETTINGS_ID]
    d = ts.read_typetree()
    assert d.get("m_Name") == "TMP Settings", d.get("m_Name")
    cur = [p["m_PathID"] for p in (d.get("m_fallbackFontAssets") or [])]
    print("TMP Settings.m_fallbackFontAssets 现状: %s" % cur)
    if NOTO_PATH_ID in cur:
        print("   已含中文字体, 跳过")
    else:
        d["m_fallbackFontAssets"] = list(d.get("m_fallbackFontAssets") or []) + [
            {"m_FileID": 0, "m_PathID": NOTO_PATH_ID}]
        ts.save_typetree(d)
        changed.append(("TMP Settings", TMP_SETTINGS_ID))
        print("   已追加 Noto → %s" % [p["m_PathID"] for p in d["m_fallbackFontAssets"]])

    # 2) 逐字体回退表
    flag_edits = []
    for pid in FALLBACK_FONT_IDS:
        o = objs.get(pid)
        if o is None:
            print("   !! 缺 pathID %d" % pid); continue
        dd = o.read_typetree()
        nm = dd.get("m_Name")
        tbl = dd.get("m_FallbackFontAssetTable")
        if tbl is None:
            print("   %-46s 无 m_FallbackFontAssetTable, 跳过" % nm); continue
        ids = [p["m_PathID"] for p in tbl]
        if NOTO_PATH_ID in ids:
            print("   %-46s 已含 Noto, 跳过" % nm); continue
        dd["m_FallbackFontAssetTable"] = list(tbl) + [{"m_FileID": 0, "m_PathID": NOTO_PATH_ID}]
        o.save_typetree(dd)
        changed.append((nm, pid))
        print("   %-46s 回退表 %s → 追加 Noto" % (nm, ids))

    # 3) 中文字体开启多图集：现图集 4096x4096 只烘了 735 个字形（旧译文用字），
    #    而新译文用到 2568 种非 ASCII 字符；m_AtlasPopulationMode 已是动态(1)，
    #    但 m_IsMultiAtlasTexturesEnabled=0 时单页塞满后无法再补字形 → 仍会缺字。
    nt = objs[NOTO_PATH_ID]
    nd = nt.read_typetree()
    if not nd.get("m_IsMultiAtlasTexturesEnabled"):
        nd["m_IsMultiAtlasTexturesEnabled"] = 1
        nt.save_typetree(nd)
        changed.append((nd.get("m_Name") + " (开启多图集)", NOTO_PATH_ID))
        flag_edits.append(NOTO_PATH_ID)
        print("   %-46s m_IsMultiAtlasTexturesEnabled 0 → 1" % nd.get("m_Name"))
    else:
        print("   %-46s 已开启多图集, 跳过" % nd.get("m_Name"))

    print("\n共修改 %d 个对象" % len(changed))
    if not apply and not changed:
        return 0

    out = TMP_DRY if not apply else ASSET
    if apply and not os.path.exists(BAK):
        shutil.copyfile(ASSET, BAK)
        print("已备份原资产 -> %s (%d 字节)" % (os.path.basename(BAK), os.path.getsize(BAK)))
    data = sf.save()
    open(out, "wb").write(data)
    print("已写出 %s (%d 字节)" % (out, len(data)))

    # 校验 1：除被改对象外，所有对象摘要必须与改前一致
    env2 = load_env(out)
    sf2 = next(iter(env2.files.values()))
    after = digests(sf2)
    chg_ids = {pid for _, pid in changed}
    unexpected = [p for p in before if p in after and before[p] != after[p] and p not in chg_ids]
    print("对象摘要比对: 改前 %d, 改后 %d, 非预期变化 %d" % (len(before), len(after), len(unexpected)))
    for p in unexpected[:5]:
        print("   !! 非预期变化 pathID=%s %s -> %s" % (p, before[p], after[p]))

    # 校验 2：被改对象的原始字节必须恰好等于"该表 count 加一、表尾多一条 PPtr，其余原样"
    #        （仅对追加回退表生效；布尔开关改动只做回读校验）
    objs2 = by_path_id(env2)
    entry = (0).to_bytes(4, "little") + NOTO_PATH_ID.to_bytes(8, "little")
    for nm, pid in changed:
        if pid in flag_edits:
            a = old_raw[pid]
            b = objs2[pid].get_raw_data()
            d = [k for k in range(min(len(a), len(b))) if a[k] != b[k]]
            ok_flag = (len(a) == len(b) and len(d) == 1 and a[d[0]] == 0 and b[d[0]] == 1)
            print("   校验2 %-40s 恰为单个布尔字节 0→1: %s (长度 %d/%d, 差异字节 %s)"
                  % (nm, ok_flag, len(a), len(b), d))
            if not ok_flag:
                unexpected.append(("bytecheck-flag", pid))
            continue
        a = old_raw[pid]
        b = objs2[pid].get_raw_data()
        i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), None)
        if i is None:
            print("   校验2 %-40s 字节完全相同?! 跳过" % nm); unexpected.append(("bytecheck", pid)); continue
        n_old = int.from_bytes(a[i:i+4], "little")
        ok_split = (b[:i] == a[:i]
                    and int.from_bytes(b[i:i+4], "little") == n_old + 1
                    and b[i+4:i+4+12*n_old] == a[i+4:i+4+12*n_old]
                    and b[i+4+12*n_old:i+4+12*(n_old+1)] == entry
                    and b[i+4+12*(n_old+1):] == a[i+4+12*n_old:])
        print("   校验2 %-40s 恰为表尾多一条PPtr: %s (count %d→%d, 原 %d → 新 %d 字节)"
              % (nm, ok_split, n_old, n_old + 1, len(a), len(b)))
        if not ok_split:
            unexpected.append(("bytecheck", pid))

    objs3 = by_path_id(env2)
    print("回读 TMP Settings.m_fallbackFontAssets:", [p["m_PathID"] for p in objs3[TMP_SETTINGS_ID].read_typetree()["m_fallbackFontAssets"]])
    for nm, pid in changed:
        if pid in objs3:
            dd = objs3[pid].read_typetree()
            key = "m_fallbackFontAssets" if pid == TMP_SETTINGS_ID else "m_FallbackFontAssetTable"
            print("   回读 %-40s %s" % (nm, [p["m_PathID"] for p in dd[key]]))
    return 0 if not unexpected else 1


if __name__ == "__main__":
    sys.exit(main(apply="--apply" in sys.argv))
