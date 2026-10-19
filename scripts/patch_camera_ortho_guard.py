# -*- coding: utf-8 -*-
# 修 PMA_SetCameraOrthSize 在相机为空时抛 NRE、导致 PlayMaker FSM 协程中断
# （战斗里表现为敌人回合结束不了、敌方画像不消失）：
#   OnEnter 里 cachedCam = TargetCamera.Value as Camera 之后没有判空；
#   ShouldSnap 路径与 LerpOrtho 协程都会对 null 相机设 orthographicSize。
#
# 做法：把 OnEnter 复制到 .reloc 段尾部零区，插入一段“相机不可用则
#   ProcessEvent(OnFinished) + Finish()”的保护，再把 MethodDef 的 RVA 指过去；
#   .reloc 的 VirtualSize 扩到 0x200 覆盖新代码（该段数据仍在原 RawData 内）。
#
# 用法: python patch_camera_ortho_guard.py [--dll <Assembly-CSharp.dll>] [--apply]
import os, struct, sys

ROOT = r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows"
DEFAULT_DLL = os.path.join(ROOT, r"ThirdCrisis_Data\Managed\Assembly-CSharp.dll")
BACKUP_SUFFIX = ".bak-thirdcrisis-camera-guard"

METHOD_RID = 13569                  # 0x06003501 PMA_SetCameraOrthSize.OnEnter
OLD_RVA = 0x101680
RVA_DELTA = 0x1E00                  # .text: RVA = file + 0x1E00
OLD_FILE = OLD_RVA - RVA_DELTA      # 0xFF880
INSERT_AT = 0x8E                    # 代码内偏移（stfld cachedCam 之后）
CAVE_FILE = 0x434020                # .reloc 尾部零区，4 对齐
NEW_RVA = 0x438020                  # .reloc VA 0x438000 + 0x20
NEW_VIRTSIZE = 0x200

# 保护：if (!cachedCam_opImplicit) { Fsm.ProcessEvent(OnFinished,null); Finish(); return; }
GUARD = bytes.fromhex(
    "02"                # ldarg.0
    "7B66370004"        # ldfld cachedCam
    "285400000A"        # call UnityEngine.Object::op_Implicit
    "2D19"              # brtrue.s -> 原 IL_008E（在插入后）
    "02"                # ldarg.0
    "286100000A"        # call FsmStateAction::get_Fsm
    "02"                # ldarg.0
    "7B65370004"        # ldfld OnFinished
    "14"                # ldnull
    "6F6200000A"        # callvirt Fsm::ProcessEvent
    "02"                # ldarg.0
    "286300000A"        # call FsmStateAction::Finish
    "2A"                # ret
)


def main():
    a = sys.argv[1:]
    dll = a[a.index("--dll") + 1] if "--dll" in a else DEFAULT_DLL
    apply = "--apply" in a
    d = bytearray(open(dll, "rb").read())
    D0 = len(d)

    # 定位 MethodDef 行
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

    # 原始方法体
    hdr = d[OLD_FILE:OLD_FILE + 12]
    flags, maxstack, codesize, locsig = struct.unpack_from("<HHII", hdr, 0)
    assert flags in (0x3003, 0x3013) and codesize == 216 and locsig == 0, (hex(flags), maxstack, codesize, locsig)
    code = bytes(d[OLD_FILE + 12:OLD_FILE + 12 + codesize])
    assert code[INSERT_AT - 5:INSERT_AT] == bytes.fromhex("7D66370004"), code[INSERT_AT - 5:INSERT_AT].hex()
    new_code = code[:INSERT_AT] + GUARD + code[INSERT_AT:]
    new_body = struct.pack("<HHII", flags, maxstack, len(new_code), 0) + new_code
    print("新方法体 %d 字节（原 %d + 保护 %d）@file 0x%X (RVA 0x%X)"
          % (len(new_body), len(hdr) + codesize, len(GUARD), CAVE_FILE, NEW_RVA))

    # .reloc 段头
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    optsz = struct.unpack_from("<H", d, pe + 20)[0]
    sec = pe + 24 + optsz
    reloc_hdr = sec + 2 * 40
    assert d[reloc_hdr:reloc_hdr + 8].rstrip(b"\0") == b".reloc", d[reloc_hdr:reloc_hdr + 8]
    vsz = struct.unpack_from("<I", d, reloc_hdr + 8)[0]
    print(".reloc VirtualSize: 0x%X" % vsz)

    if cur_rva == NEW_RVA:
        body_ok = bytes(d[CAVE_FILE:CAVE_FILE + len(new_body)]) == new_body
        vsz_ok = struct.unpack_from("<I", d, reloc_hdr + 8)[0] >= NEW_VIRTSIZE
        if body_ok and vsz_ok:
            print("已是补丁后的状态，无需改动。")
            return 0
        print("!! RVA 已指向新位置但内容/段大小不符，拒绝执行")
        return 1
    if cur_rva != OLD_RVA:
        print("!! 方法 RVA 现场不符（期望 0x%X），拒绝执行" % OLD_RVA)
        return 1
    if vsz != 0xC:
        print("!! .reloc VirtualSize 现场不符: 0x%X" % vsz)
        return 1
    if any(d[0x43400C:0x434200]):
        print("!! .reloc 零区非空，拒绝执行")
        return 1
    assert CAVE_FILE + len(new_body) <= 0x434200

    if not apply:
        print("\n(未加 --apply, 未写入)")
        return 0

    bak = dll + BACKUP_SUFFIX
    if not os.path.exists(bak):
        import shutil
        shutil.copyfile(dll, bak)
        print("已备份 ->", os.path.basename(bak))

    d[CAVE_FILE:CAVE_FILE + len(new_body)] = new_body
    struct.pack_into("<I", d, row, NEW_RVA)
    struct.pack_into("<I", d, reloc_hdr + 8, NEW_VIRTSIZE)
    assert len(d) == D0
    open(dll, "wb").write(d)

    # 复核
    e = open(dll, "rb").read()
    rva2 = struct.unpack_from("<I", e, row)[0]
    vsz2 = struct.unpack_from("<I", e, reloc_hdr + 8)[0]
    body2 = e[CAVE_FILE:CAVE_FILE + len(new_body)]
    print("回读: RVA=0x%X .reloc.VirtualSize=0x%X 方法体一致=%s" % (rva2, vsz2, body2 == new_body))
    return 0 if (rva2 == NEW_RVA and vsz2 == NEW_VIRTSIZE and body2 == new_body) else 1


if __name__ == "__main__":
    sys.exit(main())
