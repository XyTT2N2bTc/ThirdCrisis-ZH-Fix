# -*- coding: utf-8 -*-
# 修 Third Crisis 0.57.1「改了分辨率，重启又变回去」。
#
# 根因（反编译 Assembly-CSharp.dll 所得，ANToolkit/UI/GraphicsOptions.cs）：
#   [RuntimeInitializeOnLoadMethod(AfterSceneLoad)] AddOptions() 每次启动都会执行：
#       resOption = Options.Add("Settings.Resolution", num, "Settings.VideoTab", list);
#       resOption.SetInt(num);          // ← 罪魁：把"当前显示分辨率的下标"写回选项并存盘
#       …
#       OnResSet();                     // 于是 Screen.SetResolution(cachedResolutions[num])
#   其中 num = 去重后的分辨率列表里 Screen.currentResolution 的下标（即显示器原生模式）。
#   而 Option.SetInt() 会 PlayerSettings.SetInt(SerializationName, …) 立刻落盘
#   （见 ANToolkit/Option.cs: SetInt → this.Int = toSet; PlayerSettings.SetInt(...)），
#   于是玩家选的分辨率每次启动都被覆盖成显示器原生模式的下标 → 设置永远不生效，
#   窗口被顶到原生分辨率（在带显示缩放的笔记本上就会超出可用桌面区域，即"显示不全"）。
#
# 修法：把 AddOptions() 里那三条件中性指令就地改成 NOP（等长改写，不改变文件大小与 IL 偏移）：
#   0x0010D53D  ldsfld  GraphicsOptions::resOption      7E F3390004
#   0x0010D542  ldloc.1                                 07
#   0x0010D543  callvirt Option::SetInt(int32)          6F 2A360006
#   栈净效果：+1 +1 -2 = 0，改成 NOP 后栈仍平衡；该 11 字节序列全 DLL 唯一，
#   且按 dnSpy 的 IL 列表核对没有分支跳入这段（IL_02D1/02D6/02D7 只作为标号出现一次）。
#   改后 Options.Add() 载入的仍是玩家存档里的值，OnResSet() 会照它应用 → 选择得以保留。
#
# 用法: python patch_resolution_persist.py [--dll <Assembly-CSharp.dll 路径>] [--apply]
# 还原: 用同目录 .bak-thirdcrisis-resolution 覆盖回去。
import os, shutil, sys

DEFAULT_DLL = os.path.join(
    r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows",
    r"ThirdCrisis_Data\Managed\Assembly-CSharp.dll")
SITE = 0x0010D53D
OLD = bytes.fromhex("7EF3390004" "07" "6F2A360006")   # 11 字节
NEW = b"\x00" * 11   # 11 个 NOP（IL 的 nop 是 0x00，不是 x86 的 0x90）


def _opt(name, default=None):
    a = sys.argv[1:]
    if name in a and a.index(name) + 1 < len(a):
        return a[a.index(name) + 1]
    return default


def main():
    dll = _opt("--dll", DEFAULT_DLL)
    apply = "--apply" in sys.argv
    bak = dll + ".bak-thirdcrisis-resolution"
    d = open(dll, "rb").read()
    print("目标: %s (%d 字节)" % (dll, len(d)))

    n_old, n_new = d.count(OLD), d.count(NEW)
    at_site = d[SITE:SITE + 11]
    print("  原序列出现次数: %d（应为 1）" % n_old)
    print("  偏移 0x%X 处字节: %s" % (SITE, at_site.hex(" ").upper()))

    if n_old == 0 and at_site == NEW:
        print("  已经是补丁后的状态（该处为 NOP），无需改动。")
        return 0
    if n_old != 1 or at_site != OLD:
        print("  !! 定位失败：字节与预期不符，拒绝执行（可能版本不同或已被改过）。")
        return 1
    if not apply:
        print("  (未加 --apply, 未写入) 将把该 11 字节改为 %s" % NEW.hex(" ").upper())
        return 0

    if not os.path.exists(bak):
        shutil.copyfile(dll, bak)
        print("  已备份 -> %s (%d 字节)" % (os.path.basename(bak), os.path.getsize(bak)))
    patched = bytearray(d)
    patched[SITE:SITE + 11] = NEW
    assert len(patched) == len(d), "长度变化，拒绝写入"
    open(dll, "wb").write(patched)

    chk = open(dll, "rb").read()
    diff = [i for i in range(len(d)) if d[i] != chk[i]]
    print("  已写入 %d 字节（大小不变）" % len(chk))
    print("  改动字节: %d 个，位置 %s（应恰为 0x%X..0x%X 共 11 字节）"
          % (len(diff), (hex(diff[0]) + ".." + hex(diff[-1])) if diff else "无", SITE, SITE + 10))
    print("  复核: 原序列残留 %d 个, 该处现为 %s" % (chk.count(OLD), chk[SITE:SITE + 11].hex(" ").upper()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
