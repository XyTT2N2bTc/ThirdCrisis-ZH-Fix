# -*- coding: utf-8 -*-
# PMA_SetCameraOrthSize 的 OnEnter 判空只能保证“进入时相机有效”；
# 相机在 LerpOrtho 协程运行期间被销毁时仍会 NRE（最新日志复现），协程中断 → FSM 卡死。
#
# 本补丁把 OnEnter 里 ShouldSnap 的分支改成 NOP：永远走“立即设置 orthographicSize +
# ProcessEvent(OnFinished) + Finish()”的快照路径，不再启动 LerpOrtho 协程。
# 代价：相机缩放由平滑插值变为瞬时（通常 0.1 秒，视觉差异很小），换来不再有协程空引用。
#
# 用法: python patch_camera_ortho_snap.py [--dll <Assembly-CSharp.dll>] [--apply]
import os, sys

ROOT = r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows"
DEFAULT_DLL = os.path.join(ROOT, r"ThirdCrisis_Data\Managed\Assembly-CSharp.dll")
BACKUP_SUFFIX = ".bak-thirdcrisis-camera-snap"

# 相机为空保护写入的新方法体：file 0x434020，代码起点 0x43402C；
# 原 IL_0099 的 brfalse.s（跳过快照路径）在新体里位于代码偏移 0xBF。
SITE = 0x43402C + 0xBF
OLD = bytes.fromhex("2C2F")
NEW = bytes.fromhex("2600")   # pop; nop（消耗 Skip 的 bool）


def main():
    a = sys.argv[1:]
    dll = a[a.index("--dll") + 1] if "--dll" in a else DEFAULT_DLL
    apply = "--apply" in a
    d = bytearray(open(dll, "rb").read())
    cur = bytes(d[SITE:SITE + 2])
    print("站点 0x%X 当前字节: %s" % (SITE, cur.hex()))
    if cur == NEW:
        print("已是补丁后的状态，无需改动。")
        return 0
    if cur != OLD:
        print("!! 现场不符（期望 2c2f），拒绝执行")
        return 1
    if not apply:
        print("待改：brfalse.s -> pop nop（强制快照路径）")
        print("\n(未加 --apply, 未写入)")
        return 0

    bak = dll + BACKUP_SUFFIX
    if not os.path.exists(bak):
        import shutil
        shutil.copyfile(dll, bak)
        print("已备份 ->", os.path.basename(bak))
    d[SITE:SITE + 2] = NEW
    open(dll, "wb").write(d)
    e = open(dll, "rb").read()
    print("回读: %s" % e[SITE:SITE + 2].hex())
    return 0 if e[SITE:SITE + 2] == NEW else 1


if __name__ == "__main__":
    sys.exit(main())
