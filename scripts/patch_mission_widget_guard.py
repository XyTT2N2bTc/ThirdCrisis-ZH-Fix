# -*- coding: utf-8 -*-
# 修 MissionWidgetTask.Finish() 的空引用：
#   日志：ArgumentNullException: Value cannot be null. Parameter name: key
#         at MissionWidgetTask.Finish() → Dictionary.ContainsKey(Task)
#         （由 PlayMaker CallMethod.OnEnter 调用，异常会中断该动作/FSM）
#   原因：Task / Info 可能尚未赋值或已销毁。
# 做法：方法开头加空检查（Task/Widget 用 Unity op_Implicit，Info 判 null），
#   任一无效直接 return；新方法体放到 .reloc 尾部零区。
#
# 用法: python patch_mission_widget_guard.py [--dll <Assembly-CSharp.dll>] [--apply]
import os, struct, sys

ROOT = r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows"
DEFAULT_DLL = os.path.join(ROOT, r"ThirdCrisis_Data\Managed\Assembly-CSharp.dll")
BACKUP_SUFFIX = ".bak-thirdcrisis-mission-widget"

METHOD_RID = 9969
OLD_RVA = 0xBB02C
RVA_DELTA = 0x1E00
OLD_FILE = OLD_RVA - RVA_DELTA          # 0xB922C
CAVE_FILE = 0x434248
NEW_RVA = 0x438000 + (CAVE_FILE - 0x434000)

# guard: if (!Task || Info == null || !Widget) return;
RET = 0x82
GUARD = bytes.fromhex(
    "02" "7B44290004" "285400000A" "2C75"     # Task -> L_ret
    "02" "7B45290004" "2C6D"                  # Info -> L_ret
    "02" "7B40290004" "285400000A" "2C60"     # Widget -> L_ret
)
assert len(GUARD) == 0x22, len(GUARD)


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
    print("Finish RVA: 0x%X（原 0x%X，新 0x%X）" % (cur_rva, OLD_RVA, NEW_RVA))

    flags, maxstack, codesize, locsig = struct.unpack_from("<HHII", d, OLD_FILE)
    assert flags == 0x3013 and maxstack == 2 and codesize == 97 and locsig == 0, \
        (hex(flags), maxstack, codesize, locsig)
    code = bytes(d[OLD_FILE + 12:OLD_FILE + 12 + codesize])
    assert code[0x60] == 0x2A, hex(code[0x60])
    new_body = struct.pack("<HHII", flags, maxstack, len(GUARD) + codesize, 0) + GUARD + code
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
    if CAVE_FILE + len(new_body) > 0x434400:
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
