# -*- coding: utf-8 -*-
# 修战斗「Queue empty」崩溃：
#   CombatFaction.StartTurn() 在 Characters 为空时仍执行
#   new Queue(this.Characters) -> HandleCharacterFromQueue -> Dequeue()，
#   抛 InvalidOperationException。空阵营出现在 HasParticipants 检查之后、
#   真正开回合之前（PreTurnStart 的约束里角色被移除时）。
#
# 做法：在 .text 段末尾的零填充区写一个新的 StartTurn 方法体：
#   先建立 CanTurnEnd（保证管理器随后的 RunWhenClear 有有效对象），
#   若 Characters.Count == 0 则直接调用 DelayedStartTurn（1 秒后清约束、跳过该阵营），
#   否则走原来的入队逻辑。
#   然后把 MethodDef(0x06002EFD) 的 RVA 指向新方法体，并把 .text 的 VirtualSize
#   扩到覆盖新代码（新代码仍在原 RawData 范围内）。
#
# 用法: python patch_combat_turn_guard.py [--dll <Assembly-CSharp.dll>] [--apply]
import os, struct, sys

ROOT = r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows"
DEFAULT_DLL = os.path.join(ROOT, r"ThirdCrisis_Data\Managed\Assembly-CSharp.dll")
BACKUP_SUFFIX = ".bak-thirdcrisis-combat-turn"

TEXT_RVA = 0x2000
TEXT_RAW = 0x200
CAVE_FILE = 0x433B48                 # 4 对齐，位于 .text 末尾零填充区
NEW_RVA = CAVE_FILE - TEXT_RAW + TEXT_RVA
OLD_RVA = 0x000E3714                 # CombatFaction.StartTurn 原方法头
METHOD_RID = 12029                   # token 0x06002EFD
NEW_VIRTSIZE = 0x433A00              # 覆盖到文件 0x433C00（原 RawSize）


def build_body():
    """fat header + IL"""
    il = bytes.fromhex(
        "02"                    # ldarg.0
        "7331370006"            # newobj Restraint::.ctor
        "7DCE300004"            # stfld CanTurnEnd
        "02"                    # ldarg.0
        "7BCE300004"            # ldfld CanTurnEnd
        "72DFF30070"            # ldstr "CombatFaction_StartTurn"
        "6F2801000A"            # callvirt GenericRestraint<string>::Add
        "02"                    # ldarg.0
        "7BC7300004"            # ldfld Characters
        "6F7B14000A"            # callvirt List<CombatCharacter>::get_Count
        "2D07"                  # brtrue.s IL_002F
        "02"                    # ldarg.0
        "28FF2E0006"            # call DelayedStartTurn
        "2A"                    # ret
        "02"                    # ldarg.0
        "02"                    # ldarg.0
        "7BC7300004"            # ldfld Characters
        "737C14000A"            # newobj Queue<CombatCharacter>::.ctor
        "28FE2E0006"            # call HandleCharacterFromQueue
        "2A"                    # ret
    )
    assert len(il) == 0x41, len(il)
    hdr = struct.pack("<HHII", 0x3003, 3, len(il), 0)   # fat header, maxstack 3
    return hdr + il


def parse_pe(d):
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    optsz = struct.unpack_from("<H", d, pe + 20)[0]
    sec = pe + 24 + optsz
    for i in range(nsec):
        o = sec + i * 40
        name = d[o:o + 8].rstrip(b"\0").decode()
        vsz, va, rsz, rp = struct.unpack_from("<IIII", d, o + 8)
        if name == ".text":
            return o, va, vsz, rp, rsz
    raise RuntimeError("找不到 .text 段")


def parse_metadata(d):
    md = d.find(b"BSJB")
    vlen = struct.unpack_from("<I", d, md + 12)[0]
    p = md + 16 + vlen
    _, nstreams = struct.unpack_from("<HH", d, p)
    p += 4
    tbl = None
    for _ in range(nstreams):
        off, size = struct.unpack_from("<II", d, p)
        p += 8
        e = d.index(b"\0", p)
        name = d[p:e].decode()
        p = (e + 1 + 3) & ~3
        if name == "#~":
            tbl = (md + off, size)
    if tbl is None:
        raise RuntimeError("找不到 #~")
    t = tbl[0]
    _, _, _, heaps, _ = struct.unpack_from("<IBBBB", d, t)
    valid, _ = struct.unpack_from("<QQ", d, t + 8)
    p = t + 24
    counts = {}
    for i in range(64):
        if valid >> i & 1:
            counts[i] = struct.unpack_from("<I", d, p)[0]
            p += 4
    sidx = 4 if heaps & 1 else 2
    gidx = 4 if heaps & 2 else 2
    bidx = 4 if heaps & 4 else 2

    def ci(maxrows):
        return 2 if maxrows < (1 << 14) else 4

    sizes = {
        0x00: 2 + sidx + gidx * 3,
        0x01: ci(max(counts.get(0, 0), counts.get(0x1A, 0), counts.get(0x23, 0), counts.get(1, 0))) + sidx * 2,
        0x02: 4 + sidx * 2 + ci(max(counts.get(2, 0), counts.get(1, 0))) + 4,
        0x04: 2 + sidx + bidx,
        0x06: 4 + 2 + 2 + sidx + bidx + 2,
    }
    cur = p
    for tb in (0x00, 0x01, 0x02, 0x04):
        cur += sizes[tb] * counts.get(tb, 0)
    row = cur + (METHOD_RID - 1) * sizes[0x06]
    return row, t


def main():
    a = sys.argv[1:]
    dll = a[a.index("--dll") + 1] if "--dll" in a else DEFAULT_DLL
    apply = "--apply" in a
    d = bytearray(open(dll, "rb").read())
    D0 = len(d)
    body = build_body()
    sec, va, vsz, rp, rsz = parse_pe(d)
    row, _ = parse_metadata(d)
    cur_rva = struct.unpack_from("<I", d, row)[0]
    print("方法 RID %d 的 RVA: 0x%X（原 0x%X，新 0x%X）" % (METHOD_RID, cur_rva, OLD_RVA, NEW_RVA))
    print(".text: VA=0x%X VirtSize=0x%X RawPtr=0x%X RawSize=0x%X" % (va, vsz, rp, rsz))
    assert va == TEXT_RVA and rp == TEXT_RAW, "PE 布局与预期不符"
    assert rsz >= CAVE_FILE - rp + len(body), "RawData 不够放新方法体"

    cave = bytes(d[CAVE_FILE:CAVE_FILE + len(body)])
    if cur_rva == NEW_RVA:
        if cave == body:
            print("已是补丁后的状态，无需改动。")
            return 0
        print("!! RVA 已指向新位置，但方法体内容不符，拒绝执行")
        return 1
    if cur_rva != OLD_RVA:
        print("!! 方法 RVA 现场不符（期望 0x%X），拒绝执行" % OLD_RVA)
        return 1
    if any(cave):
        print("!! 目标零填充区非空，拒绝执行")
        return 1
    if vsz != 0x433948:
        print("!! .text VirtualSize 现场不符: 0x%X" % vsz)
        return 1
    print("新方法体 %d 字节 @file 0x%X (RVA 0x%X)" % (len(body), CAVE_FILE, NEW_RVA))
    if not apply:
        print("\n(未加 --apply, 未写入)")
        return 0

    bak = dll + BACKUP_SUFFIX
    if not os.path.exists(bak):
        import shutil
        shutil.copyfile(dll, bak)
        print("已备份 ->", os.path.basename(bak))

    d[CAVE_FILE:CAVE_FILE + len(body)] = body
    struct.pack_into("<I", d, row, NEW_RVA)
    struct.pack_into("<I", d, sec + 8, NEW_VIRTSIZE)   # VirtualSize
    assert len(d) == D0
    open(dll, "wb").write(d)

    # 复核
    e = open(dll, "rb").read()
    sec2, _, vsz2, _, _ = parse_pe(e)
    row2, _ = parse_metadata(e)
    rva2 = struct.unpack_from("<I", e, row2)[0]
    body2 = e[CAVE_FILE:CAVE_FILE + len(body)]
    print("回读: RVA=0x%X VirtSize=0x%X 方法体一致=%s" % (rva2, vsz2, body2 == body))
    return 0 if (rva2 == NEW_RVA and vsz2 == NEW_VIRTSIZE and body2 == body) else 1


if __name__ == "__main__":
    sys.exit(main())
