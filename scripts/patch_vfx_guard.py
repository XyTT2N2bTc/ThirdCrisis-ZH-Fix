# -*- coding: utf-8 -*-
# 修 PMA_CombatVisualEffect 在 Origin/TargetCharacter 为空或已销毁时，
# doAnimation 协程对 null 组件取 transform 抛 NRE、永远不发 VisualEffectDone，
# 导致使用该特效的 PlayMaker FSM 卡死（战斗中表现为回合结束不了）。
#
# 做法：OnEnter 开头按 SpawnAtTarget 选中的 CharacterHandler 做 Unity 判空；
#   不可用则直接 ProcessEvent(VisualEffectDone)+Finish() 结束动作，不再启动协程。
#   新方法体写在 .reloc 段尾部（扩展 RawData 0x200 字节，保证放得下）。
#
# 用法: python patch_vfx_guard.py [--dll <Assembly-CSharp.dll>] [--apply]
import os, struct, sys

ROOT = r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows"
DEFAULT_DLL = os.path.join(ROOT, r"ThirdCrisis_Data\Managed\Assembly-CSharp.dll")
BACKUP_SUFFIX = ".bak-thirdcrisis-vfx-guard"

METHOD_RID = 12391
OLD_RVA = 0xE99C4
RVA_DELTA = 0x1E00
OLD_FILE = OLD_RVA - RVA_DELTA          # 0xE7BC4
CAVE_FILE = 0x4341B8
NEW_RVA = 0x438000 + (CAVE_FILE - 0x434000)
RELOC_HDR = 0x1C8
NEW_RELOC_RAW = 0x400
NEW_RELOC_VIRT = 0x400

# 新 IL： guard + 原循环体（125 字节）
NEW_IL = bytes.fromhex(
    "02" "285C00000A"                       # ldarg.0; call base.OnEnter
    "02" "7B0F320004" "2C12"                # SpawnAtTarget ? -> L_origin
    "02" "7B1E320004" "6FA200000A" "75080A0002" "2B10"   # TargetCharacter.Value as CharacterHandler -> L_check
    # L_origin:
    "02" "7B1B320004" "6FA200000A" "75080A0002"         # Origin.Value as CharacterHandler
    # L_check:
    "25" "285400000A" "2D1A" "26"           # dup; op_Implicit; brtrue L_ok; pop
    "02" "286100000A" "02" "7B1F320004" "14" "6F6200000A"  # Fsm.ProcessEvent(VisualEffectDone,null)
    "02" "286300000A" "2A"                  # ldarg.0; Finish; ret
    # L_ok: pop
    "26"
    # 原 OnEnter 循环体（IL_0006..IL_0034，共 0x2F 字节）
    "02" "16" "7D21320004" "16" "0A" "2B1A"
    "02" "02" "06" "6B" "02" "7B15320004" "5A" "2868300006" "28CE02000A" "26" "06" "17" "58" "0A"
    "06" "02" "7B14320004" "32DD"
    "2A"
)
assert len(NEW_IL) == 130, len(NEW_IL)


def main():
    a = sys.argv[1:]
    dll = a[a.index("--dll") + 1] if "--dll" in a else DEFAULT_DLL
    apply = "--apply" in a
    d = bytearray(open(dll, "rb").read())
    D0 = len(d)

    t = 0x14A0E8
    _, _, _, heaps, _ = struct.unpack_from("<IBBBB", d, t)
    valid, _ = struct.unpack_from("<QQ", d, t + 8)
    p = t + 24
    counts = {}
    for i in range(64):
        if valid >> i & 1:
            counts[i] = struct.unpack_from("<I", d, p)[0]
            p += 4
    sidx = 4 if heaps & 1 else 2
    bidx = 4 if heaps & 4 else 2

    def ci(m):
        return 2 if m < (1 << 14) else 4

    sizes = {
        0x00: 2 + sidx + (4 if heaps & 2 else 2) * 3,
        0x01: 2 + sidx * 2,
        0x02: 4 + sidx * 2 + ci(max(counts.get(2, 0), counts.get(1, 0))) + 4,
        0x04: 2 + sidx + bidx,
        0x06: 4 + 2 + 2 + sidx + bidx + 2,
    }
    cur = p
    for tb in (0x00, 0x01, 0x02, 0x04):
        cur += sizes[tb] * counts.get(tb, 0)
    row = cur + (METHOD_RID - 1) * sizes[0x06]
    cur_rva = struct.unpack_from("<I", d, row)[0]
    print("OnEnter RVA: 0x%X（原 0x%X，新 0x%X）" % (cur_rva, OLD_RVA, NEW_RVA))

    flags, maxstack, codesize, locsig = struct.unpack_from("<HHII", d, OLD_FILE)
    assert flags == 0x3013 and codesize == 53 and locsig == 0x1100000B, \
        (hex(flags), maxstack, codesize, hex(locsig))
    new_body = struct.pack("<HHII", flags, maxstack, len(NEW_IL), locsig) + NEW_IL
    print("新方法体 %d 字节 @file 0x%X (RVA 0x%X)" % (len(new_body), CAVE_FILE, NEW_RVA))

    rawsize = struct.unpack_from("<I", d, RELOC_HDR + 16)[0]
    vsize = struct.unpack_from("<I", d, RELOC_HDR + 8)[0]
    print(".reloc VirtualSize=0x%X RawSize=0x%X" % (vsize, rawsize))

    if cur_rva == NEW_RVA:
        if bytes(d[CAVE_FILE:CAVE_FILE + len(new_body)]) == new_body:
            print("已是补丁后的状态，无需改动。")
            return 0
        print("!! RVA 已指向新位置但方法体不符，拒绝执行")
        return 1
    if cur_rva != OLD_RVA:
        print("!! 方法 RVA 现场不符（期望 0x%X），拒绝执行" % OLD_RVA)
        return 1
    if vsize != 0x200 or rawsize != 0x200:
        print("!! .reloc 段现场不符（期望 Virt/Raw = 0x200/0x200）")
        return 1
    assert CAVE_FILE + len(new_body) <= 0x434400, "超出扩展后的 .reloc 范围"

    if not apply:
        print("\n(未加 --apply, 未写入)")
        return 0

    bak = dll + BACKUP_SUFFIX
    if not os.path.exists(bak):
        import shutil
        shutil.copyfile(dll, bak)
        print("已备份 ->", os.path.basename(bak))

    # 扩展 .reloc：追加 0x200 零字节，更新 RawSize / VirtualSize
    d.extend(b"\x00" * (0x434400 - len(d)))
    struct.pack_into("<I", d, RELOC_HDR + 8, NEW_RELOC_VIRT)
    struct.pack_into("<I", d, RELOC_HDR + 16, NEW_RELOC_RAW)
    d[CAVE_FILE:CAVE_FILE + len(new_body)] = new_body
    struct.pack_into("<I", d, row, NEW_RVA)
    open(dll, "wb").write(d)

    e = open(dll, "rb").read()
    rva2 = struct.unpack_from("<I", e, row)[0]
    body2 = e[CAVE_FILE:CAVE_FILE + len(new_body)]
    vs2 = struct.unpack_from("<I", e, RELOC_HDR + 8)[0]
    rs2 = struct.unpack_from("<I", e, RELOC_HDR + 16)[0]
    print("回读: RVA=0x%X Virt=0x%X Raw=0x%X 方法体一致=%s 文件=%d"
          % (rva2, vs2, rs2, body2 == new_body, len(e)))
    return 0 if (rva2 == NEW_RVA and body2 == new_body and vs2 == NEW_RELOC_VIRT
                 and rs2 == NEW_RELOC_RAW) else 1


if __name__ == "__main__":
    sys.exit(main())
