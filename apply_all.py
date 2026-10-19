#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Third Crisis 0.57.1 中文修复包 · 一键应用 / 还原。

用法（先备份，再改）：
    python apply_all.py --game "D:\\SteamLibrary\\steamapps\\common\\Third Crisis" --apply
    python apply_all.py --game "<同上>"                 # 只演练并校验，不写文件

做五件事（各自幂等，可重复运行）：
  1. 语言包修补：补 11 条缺失设置项键、修 11 条日志 Id 并补 21 条日志条目、
     把陈旧版本号改成本作实际版本、清理 141 个构建已不引用的过期 UI 条目
  2. 成就汉化：把 resources.assets 里 33 个成就的名称/描述就地改成中文（同大小改写）
  3. 字体修复：把游戏自带的中文字体 Noto Serif SC 挂进 TMP 回退链，并为其开启多图集
  4. 场景画廊汉化：分类名/条目名/解锁提示（资源里写死的英文）就地汉化，
     并把两处旧版 UI.Text 的字体换成中文 Noto Serif SC（否则中文显示成方块）
  5. 可选整体重译：用 translation/done 的译文语料回填整个中文语言文件（--retranslate）

依赖：第 2、3 步需要 `pip install "UnityPy[ttgen]"`（离线资产编辑；游戏运行不需要它）。
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))


def paths(game):
    lang = os.path.join(game, "ThirdCrisis_Data", "StreamingAssets", "Languages",
                        "translated_zh_translation.json")
    assets = os.path.join(game, "ThirdCrisis_Data", "resources.assets")
    managed = os.path.join(game, "ThirdCrisis_Data", "Managed")
    return lang, assets, managed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True, help="Third Crisis 安装目录（含 ThirdCrisis_Data）")
    ap.add_argument("--apply", action="store_true", help="写入；不加则只演练")
    ap.add_argument("--retranslate", action="store_true",
                    help="额外用 translation/done 的语料回填整个中文语言文件（会先备份为 .bak）")
    ap.add_argument("--skip-assets", action="store_true", help="只修语言包，不动 resources.assets")
    ap.add_argument("--patch-dll", action="store_true",
                    help="额外修补 Assembly-CSharp.dll：修「改了分辨率重启后失效」（显式可选，会备份）")
    a = ap.parse_args()

    lang, assets, managed = paths(a.game)
    if not os.path.isfile(lang):
        sys.exit("找不到语言文件: %s" % lang)

    print("语言文件:", lang)
    ok = True

    # ---- 0. 可选整体重译（必须在语言包修补【之前】做）----
    # merge.py 按"原文匹配"回填译文：日志条目的标题是按 Name 字段（如 "Entry 2"）匹配的，
    # 而下面的日志修补会把 Name 改成当前构建的键（"Entry 02"），改名后语料就匹配不上了，
    # 标题会退回随包旧机翻。顺序颠倒会导致标题不一致，故重译先行。
    if a.retranslate:
        import subprocess
        cmd = [sys.executable, os.path.join(HERE, "scripts", "merge.py"),
               "--src", lang, "--done", os.path.join(HERE, "translation", "done")]
        if a.apply:
            cmd.append("--write")
        print("整体重译: merge.py --src <%s> --done <translation/done>" % os.path.basename(lang))
        ok = subprocess.call(cmd) == 0 and ok

    # ---- 1. 语言包修补 ----
    import add_missing_keys, fix_journal_entries, fix_version_strings, prune_stale_ui_guids
    n1 = add_missing_keys.ensure_keys(lang, apply=a.apply)
    n2 = fix_journal_entries.ensure(lang, apply=a.apply)
    n3 = fix_version_strings.ensure(lang, apply=a.apply)
    n4 = prune_stale_ui_guids.ensure(lang, scan_root=os.path.join(a.game, "ThirdCrisis_Data"),
                                     apply=a.apply)
    print("语言包: 设置项 %d 条, 日志 %d 条, 版本号 %d 条, 过期 UI %d 条" % (n1, n2, n3, n4))

    if a.skip_assets:
        print("(--skip-assets: 未处理 resources.assets)")
        return 0 if ok else 1

    # ---- 2. 成就汉化 ----
    import patch_achievements
    patch_achievements.ASSET = assets
    patch_achievements.BAK = assets + ".bak-thirdcrisis-zh-ach"
    print("\n成就汉化:", assets)
    ok = (patch_achievements.main(apply=a.apply) == 0) and ok

    # ---- 3. 字体回退修复 ----
    import fix_font_fallback
    fix_font_fallback.ASSET = assets
    fix_font_fallback.MANAGED = managed
    fix_font_fallback.BAK = assets + ".bak-thirdcrisis-zh-font"
    fix_font_fallback.TMP_DRY = os.path.join(os.path.dirname(assets), "_fontfix_dryrun.assets")
    print("\n字体修复:", assets)
    ok = (fix_font_fallback.main(apply=a.apply) == 0) and ok

    # ---- 3b. 等待闲话（NPC 在城镇里的自言自语，烤在资源里，语言文件够不到）----
    import patch_waiting_lines
    print("\n等待闲话:", assets)
    ok = (patch_waiting_lines.ensure(assets, a.apply) == 0) and ok

    # ---- 3c. 物品操作按钮：接线（关掉固定译文覆盖）+ 动作名汉化 ----
    import subprocess
    print("物品操作按钮:", assets)
    cmd = [sys.executable, os.path.join(HERE, "scripts", "patch_item_action_labels.py"),
           "--asset", assets,
           "--dll", os.path.join(a.game, "ThirdCrisis_Data", "Managed", "Assembly-CSharp.dll")]
    if not a.patch_dll:
        cmd.append("--skip-dll")
    if a.apply:
        cmd.append("--apply")
    ok = subprocess.call(cmd) == 0 and ok

    # ---- 3d. 场景画廊：分类/条目名/解锁提示汉化 + 旧版 Text 换中文字体 ----
    import subprocess as _sp
    print("\n场景画廊汉化:", assets)
    cmd = [sys.executable, os.path.join(HERE, "scripts", "patch_gallery_zh.py"), "--asset", assets]
    if a.apply:
        cmd.append("--apply")
    ok = _sp.call(cmd) == 0 and ok

    # ---- 3e. 暂停菜单 History 标签：与 Options 共用了同一个 UILocalization guid ----
    import fix_pause_history
    print("\n暂停菜单 History 标签:", assets)
    ok = (fix_pause_history.main(a.apply, assets, lang) == 0) and ok

    # ---- 3f. 击败敌人任务名：PlayMaker FSM 里的 "Defeat " 前缀 ----
    import subprocess as _sp2
    print("\n击败敌人任务名:", assets)
    cmd = [sys.executable, os.path.join(HERE, "scripts", "patch_defeat_task_zh.py"), "--asset", assets]
    if a.apply:
        cmd.append("--apply")
    ok = _sp2.call(cmd) == 0 and ok

    # ---- 4. 可选：修"改了分辨率重启后失效"（改 Assembly-CSharp.dll，11 字节改 NOP）----
    if a.patch_dll:
        import subprocess
        dll = os.path.join(a.game, "ThirdCrisis_Data", "Managed", "Assembly-CSharp.dll")
        print("\n分辨率持久化修复:", dll)
        cmd = [sys.executable, os.path.join(HERE, "scripts", "patch_resolution_persist.py"), "--dll", dll]
        if a.apply:
            cmd.append("--apply")
        ok = subprocess.call(cmd) == 0 and ok

        # 装备店里写死的英文：购买确认语 / Yes-No / 已拥有标记 / 两条错误提示
        print("装备店文本:", dll)
        cmd = [sys.executable, os.path.join(HERE, "scripts", "patch_shop_texts.py"), "--dll", dll]
        if a.apply:
            cmd.append("--apply")
        ok = subprocess.call(cmd) == 0 and ok

        # 战斗回合空阵营保护：修 "InvalidOperationException: Queue empty"
        print("战斗回合空阵营保护:", dll)
        cmd = [sys.executable, os.path.join(HERE, "scripts", "patch_combat_turn_guard.py"), "--dll", dll]
        if a.apply:
            cmd.append("--apply")
        ok = subprocess.call(cmd) == 0 and ok

        # 相机为空保护：修 PMA_SetCameraOrthSize 的 NRE 导致 FSM 卡死（敌人回合结束不了）
        print("相机为空保护:", dll)
        cmd = [sys.executable, os.path.join(HERE, "scripts", "patch_camera_ortho_guard.py"), "--dll", dll]
        if a.apply:
            cmd.append("--apply")
        ok = subprocess.call(cmd) == 0 and ok

        # 相机缩放缓动改为快照：避免相机在协程期间被销毁 → LerpOrtho NRE
        print("相机缩放快照化:", dll)
        cmd = [sys.executable, os.path.join(HERE, "scripts", "patch_camera_ortho_snap.py"), "--dll", dll]
        if a.apply:
            cmd.append("--apply")
        ok = subprocess.call(cmd) == 0 and ok

        # 相机转场保护：修 PMA_CameraTransitionBetweenPositions 的 NRE
        print("相机转场保护:", dll)
        cmd = [sys.executable, os.path.join(HERE, "scripts", "patch_camera_transition_guard.py"), "--dll", dll]
        if a.apply:
            cmd.append("--apply")
        ok = subprocess.call(cmd) == 0 and ok

        # 特效保护：修 PMA_CombatVisualEffect 空引用导致 VisualEffectDone 不发
        print("战斗特效保护:", dll)
        cmd = [sys.executable, os.path.join(HERE, "scripts", "patch_vfx_guard.py"), "--dll", dll]
        if a.apply:
            cmd.append("--apply")
        ok = subprocess.call(cmd) == 0 and ok

        # 任务 HUD 空引用保护：MissionWidgetTask.Finish 的字典空键
        print("任务 HUD 保护:", dll)
        cmd = [sys.executable, os.path.join(HERE, "scripts", "patch_mission_widget_guard.py"), "--dll", dll]
        if a.apply:
            cmd.append("--apply")
        ok = subprocess.call(cmd) == 0 and ok

        # 战斗提示文本：换装备/使用物品的体力提示
        print("战斗提示文本:", dll)
        cmd = [sys.executable, os.path.join(HERE, "scripts", "patch_combat_prompt_texts.py"), "--dll", dll]
        if a.apply:
            cmd.append("--apply")
        ok = subprocess.call(cmd) == 0 and ok

        # 手动修改移植：SemanticVersion.IsPublic 恒返回 false（解锁 public 限制内容）
        print("IsPublic 恒 false:", dll)
        cmd = [sys.executable, os.path.join(HERE, "scripts", "patch_semver_public.py"), "--dll", dll]
        if a.apply:
            cmd.append("--apply")
        ok = subprocess.call(cmd) == 0 and ok

    print("\n%s" % ("全部完成。" if ok else "存在失败项，请查看上面的输出。"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
