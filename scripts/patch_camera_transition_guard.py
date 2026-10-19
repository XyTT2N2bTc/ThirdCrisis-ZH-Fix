# -*- coding: utf-8 -*-
# 修 PMA_CameraTransitionBetweenPositions.OnEnter 在 PositionA/PositionB 为空
# 或已销毁时对 null 组件取 transform 抛 NRE、导致 PlayMaker FSM 卡死：
#   （日志栈：PMA_CameraTransitionBetweenPositions.OnEnter → Component.get_transform，
#     由 CreateAbilityAnnouncement.AnnouncementFinished → PopulateAbilityAnnouncement.OnDestroy 触发）
#
# 做法：把 OnEnter 的完整方法体复制到 .reloc 段尾部零区（相机保护之后），
#   在两处 get_transform 之前插入 Unity 对象判空（op_Implicit）；
#   任一为空则 Finish() 直接结束动作，再把 MethodDef 的 RVA 指过去。
#
# 用法: python patch_camera_transition_guard.py [--dll <Assembly-CSharp.dll>] [--apply]
import os, struct, sys

ROOT = r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows"
DEFAULT_DLL = os.path.join(ROOT, r"ThirdCrisis_Data\Managed\Assembly-CSharp.dll")
BACKUP_SUFFIX = ".bak-thirdcrisis-camera-transition"

METHOD_RID = 335
OLD_RVA = 0x6450
RVA_DELTA = 0x1E00
OLD_FILE = OLD_RVA - RVA_DELTA          # 0x4650
CAVE_FILE = 0x43412C                    # 相机保护方法体之后（0x43412A 起，4 对齐）
NEW_RVA = 0x438000 + (CAVE_FILE - 0x434000)

# 新 IL（127 字节）：在原逻辑的两处 get_transform 前插入判空
NEW_IL = bytes.fromhex(
    "02"                # ldarg.0
    "285C00000A"        # call FsmStateAction::OnEnter
    "02" "7B01010004" "6FA200000A" "7507000001"   # PositionA.Value as Component
    "25"                # dup
    "285400000A"        # call Object::op_Implicit
    "2D08"              # brtrue.s L_a
    "26"                # pop
    "02" "286300000A" "2A"                         # ldarg.0; Finish; ret
    # L_a:
    "6F9700000A" "6F9800000A" "0A"                 # get_transform; get_position; stloc.0
    "02" "7B02010004" "6FA200000A" "7507000001"   # PositionB.Value as Component
    "25"                # dup
    "285400000A"        # call Object::op_Implicit
    "2D08"              # brtrue.s L_b
    "26"                # pop
    "02" "286300000A" "2A"                         # ldarg.0; Finish; ret
    # L_b:
    "6F9700000A" "6F9800000A" "0B"                 # get_transform; get_position; stloc.1
    "7EC13D0004"                                   # ldsfld FollowUnit::Instance
    "06" "07"                                      # ldloc.0; ldloc.1
    "02" "7B03010004" "6FD201000A"                 # this.TransitionSplit.Value
    "28D301000A"                                   # call Vector3::Lerp
    "6FD93C0006"                                   # callvirt PushCameraTarget
    "02" "286300000A" "2A"                         # ldarg.0; Finish; ret
)
assert len(NEW_IL) == 0x7F, len(NEW_IL)


def main():
    a = sys.argv[1:]
    dll = a[a.index("--dll") + 1] if "--dll" in a else DEFAULT_DLL
    apply = "--apply" in a
    d = bytearray(open(dll, "rb").read())
    D0 = len(d)

    # MethodDef 行
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

    # 原方法体头
    flags, maxstack, codesize, locsig = struct.unpack_from("<HHII", d, OLD_FILE)
    assert flags == 0x3013 and codesize == 95 and locsig == 0x1100003F, \
        (hex(flags), maxstack, codesize, hex(locsig))
    new_body = struct.pack("<HHII", flags, maxstack, len(NEW_IL), locsig) + NEW_IL
    print("新方法体 %d 字节 @file 0x%X (RVA 0x%X)" % (len(new_body), CAVE_FILE, NEW_RVA))

    if cur_rva == NEW_RVA:
        if bytes(d[CAVE_FILE:CAVE_FILE + len(new_body)]) == new_body:
            print("已是补丁后的状态，无需改动。")
            return 0
        print("!! RVA 已指向新位置但方法体不符，拒绝执行")
        return 1
    if cur_rva != OLD_RVA:
        print("!! 方法 RVA 现场不符（期望 0x%X），拒绝执行" % OLD_RVA)
        return 1
    if any(d[CAVE_FILE:CAVE_FILE + len(new_body)]):
        print("!! 目标零区非空，拒绝执行")
        return 1
    if CAVE_FILE + len(new_body) > 0x434200:
        print("!! 超出 .reloc RawData 范围")
        return 1

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
    assert len(d) == D0
    open(dll, "wb").write(d)

    e = open(dll, "rb").read()
    rva2 = struct.unpack_from("<I", e, row)[0]
    body2 = e[CAVE_FILE:CAVE_FILE + len(new_body)]
    print("回读: RVA=0x%X 方法体一致=%s" % (rva2, body2 == new_body))
    return 0 if (rva2 == NEW_RVA and body2 == new_body) else 1


if __name__ == "__main__":
    sys.exit(main())
