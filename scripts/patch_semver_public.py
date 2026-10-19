# -*- coding: utf-8 -*-
# 手动修改移植：ANToolkit.Utility.SemanticVersion.IsPublic 恒返回 false。
#   反编译源码改动（tmp/decomp/.../SemanticVersion.cs）：
#       //return !this.IsPatron && !this.IsSteam;
#       return false;
#   直接改 DLL 的 get_IsPublic 方法体（小头 1 字节 + 代码），不重编译整个程序集，
#   以免丢掉现有的分辨率/按钮/装备店/战斗保护等 IL 补丁。
#
# 用法: python patch_semver_public.py [--dll <Assembly-CSharp.dll>] [--apply]
import os, struct, sys

ROOT = r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows"
DEFAULT_DLL = os.path.join(ROOT, r"ThirdCrisis_Data\Managed\Assembly-CSharp.dll")
BACKUP_SUFFIX = ".bak-thirdcrisis-semver-public"

HDR = 0x108AA7          # 小头（code size 20 -> 0x52）
CODE = HDR + 1          # 0x108AA8
ORIG_HDR = 0x52
NEW_HDR = 0x0A          # code size 2
ORIG_PROLOGUE = bytes.fromhex("0228493700062D0A")
NEW_CODE = bytes.fromhex("162A")      # ldc.i4.0; ret


def main():
    a = sys.argv[1:]
    dll = a[a.index("--dll") + 1] if "--dll" in a else DEFAULT_DLL
    apply = "--apply" in a
    d = bytearray(open(dll, "rb").read())
    cur_hdr = d[HDR]
    cur_code = bytes(d[CODE:CODE + 2])
    print("get_IsPublic @file 0x%X 头=0x%02X 前两字节=%s" % (HDR, cur_hdr, cur_code.hex()))
    if cur_hdr == NEW_HDR and cur_code == NEW_CODE:
        print("已是补丁后的状态，无需改动。")
        return 0
    if cur_hdr != ORIG_HDR or bytes(d[CODE:CODE + len(ORIG_PROLOGUE)]) != ORIG_PROLOGUE:
        print("!! 现场不符，拒绝执行")
        return 1
    if not apply:
        print("待改：IsPublic() -> return false;（代码 20 -> 2 字节）")
        print("\n(未加 --apply, 未写入)")
        return 0

    bak = dll + BACKUP_SUFFIX
    if not os.path.exists(bak):
        import shutil
        shutil.copyfile(dll, bak)
        print("已备份 ->", os.path.basename(bak))
    d[HDR] = NEW_HDR
    d[CODE:CODE + 2] = NEW_CODE
    open(dll, "wb").write(d)
    e = open(dll, "rb").read()
    print("回读: 头=0x%02X 前两字节=%s" % (e[HDR], bytes(e[CODE:CODE + 2]).hex()))
    return 0 if (e[HDR] == NEW_HDR and bytes(e[CODE:CODE + 2]) == NEW_CODE) else 1


if __name__ == "__main__":
    sys.exit(main())
