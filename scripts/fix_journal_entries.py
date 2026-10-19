# -*- coding: utf-8 -*-
# 修 Third Crisis 0.57.1 中文包里的"日志(Journal)未翻译"。
#
# 匹配机制（实测）：日志条目按 Id 查表，Id = 当前构建的 (Category, Name) 经
#   lower() + 空格→下划线 生成，形如 "<category_slug>:<name_slug>"。
#   证据：资源里 91 个日志条目对象带 Category/Name/Contents 字段；
#   语言包 70 条带 Id 字段；按正文配对后 58/69 条 Id 与规则完全吻合。
#   游戏日志里 "No translation for Journal project_mindcrush:entry_02" 正是构建侧 Id。
#
# 缺口（实测）：
#   - 11 条 Id 是旧版键 → 查不到：
#       * 补零规则改过：entry_2 → entry_02（Mindcrush/Flytrap 各若干）
#       * Pump 四条旧键的 Category 段是空的（生成 bug）：":pump_..." → "pump_apparatus_development:log_..."
#   - 21 条条目语言包里完全没有（Audiologs 5 条、EBT 网络 4 条、Flytrap 5 条、
#     Tower 7 条）→ 标题与正文都显示英文
#
# 用法: python fix_journal_entries.py [--apply]
# merge.py --write 之后会自动调用本模块，避免重建时丢掉这些条目。
import json, os, sys

ROOT = r"C:\1\Special\Assessment-High\third_crisis_0.57.1-r_windows"
SRC = os.path.join(ROOT, r"ThirdCrisis_Data\StreamingAssets\Languages\translated_zh_translation.json")

# 旧 Id → (新 Id, 新 Name)
ID_FIXES = {
    "project_mindcrush:entry_2": ("project_mindcrush:entry_02", "Entry 02"),
    "project_mindcrush:entry_5": ("project_mindcrush:entry_05", "Entry 05"),
    "project_flytrap:entry_2":   ("project_flytrap:entry_02",   "Entry 02"),
    "project_flytrap:entry_3":   ("project_flytrap:entry_03",   "Entry 03"),
    "project_flytrap:entry_5":   ("project_flytrap:entry_05",   "Entry 05"),
    "project_flytrap:entry_7":   ("project_flytrap:entry_07",   "Entry 07"),
    "project_flytrap:entry23":   ("project_flytrap:entry_23",   "Entry 23"),
    ":pump_apparatus_development_log_1_-_conceptualization_and_planning___":
        ("pump_apparatus_development:log_1_-_conceptualization_and_planning___",
         "Log 1 - Conceptualization and Planning   "),
    ":pump_apparatus_development_log_2_-_early_development_":
        ("pump_apparatus_development:log_2_-_early_development_",
         "Log 2 - Early Development  "),
    ":pump_apparatus_development_log_3_-_functioning_prototype_and_extra_additions_":
        ("pump_apparatus_development:log_3_-_functioning_prototype_and_extra_additions_",
         "Log 3 - Functioning Prototype and Extra Additions  "),
    ":pump_apparatus_development_log_4_-_discontinuation_of_the_project":
        ("pump_apparatus_development:log_4_-_discontinuation_of_the_project",
         "Log 4 - Discontinuation of the Project"),
}

# 已有条目的正文修正（原文是不可读的占位乱码时，给出可读的中文提示）
CONTENT_FIXES = {
    "fiend_notes:crumpled_note": "（字迹潦草，无法辨认）",
}

# (Id, Name, Contents 英文原文, TranslatedName, TranslatedContents)
NEW = [
 ("audiologs:audiolog_1", "Audiolog 1",
  "This is Dr. Amy Weber lead researcher on Project Ambrosia log entry 1. Losing subject Jenna Wright was a massive setback for me and my research. Mistress Leath transferred me to this research facility as punishment, but I will continue to give it my all so Mistress Leath can see my worth again.  ",
  "录音日志 1",
  "我是安布罗西亚计划的首席研究员艾米·韦伯博士，录音日志第一条。失去实验对象珍娜·赖特，对我和我的研究是巨大的挫折。利思女士把我调到这处研究设施作为惩罚，但我会继续全力以赴，好让利思女士再次看到我的价值。  "),
 ("audiologs:audiolog_2_", "Audiolog 2 ",
  "This is Dr. Amy Weber log entry 3. After the incident that occurred 2 weeks ago while we tried to transplant the predecessor of project Mindcrush into the slime, Dr. Anderson started to act out of place and I had to put him under quarantine. I also got a notification from the headquarter about getting new subjects in the next couple of days.",
  "录音日志 2 ",
  "我是艾米·韦伯博士，录音日志第三条。两周前我们试图把心碎计划的前身移植进那团黏液时发生了事故，之后安德森博士开始举止异常，我只好把他隔离起来。总部也通知我，接下来几天会送来新的实验对象。"),
 ("audiologs:audiolog_3", "Audiolog 3",
  "This is Dr. Amy Weber log entry 5. The subjects arrived yesterday. We lost 30% to the modified slime which is a great success. However, we didn’t find a way to undo the effects even after injecting the subjects with counter measurements.\r",
  "录音日志 3",
  "我是艾米·韦伯博士，录音日志第五条。实验对象昨天到了。我们只在那团改造过的黏液上损失了30%，算是极大的成功。不过，即使给对象注射了对抗手段，我们仍找不到消除影响的办法。\r"),
 ("audiologs:audiolog_4", "Audiolog 4",
  "This is Dr. Amy Weber log entry 8. It seems we can’t undo the effect if the subject is exposed to a certain quantity. HQ notified me to stop the research, but I will not let my results go to waste. I can make them obedient. I'm the only one that can. All the remaining test subjects show no sign of self-consciousness but react to biological life.\r",
  "录音日志 4",
  "我是艾米·韦伯博士，录音日志第八条。看来只要对象接触到一定剂量，影响就无法逆转。HQ通知我停止研究，但我不会让我的成果白费。我能让它们听话。只有我能做到。剩下的实验对象全都毫无自我意识的迹象，却会对生命体产生反应。\r"),
 ("audiologs:audiolog_5", "Audiolog 5",
  "This is Dr. Amy Weber log entry 9. The subjects react especially to lifeforms to reproduce at any cost. Since they also have the properties of Project Ambrosia and can emit gas in a short area that will affect the libido of everyone in range. I changed the name to Project Pandora so HQ won’t find out that we keep researching this matter. It may have risks to keep researching but I’m confident it is worth it.\r\n",
  "录音日志 5",
  "我是艾米·韦伯博士，录音日志第九条。实验对象对生命体的反应格外强烈，会不惜代价地繁殖。由于它们还带有安布罗西亚计划的特性，能在小范围内释放气体，影响范围内所有人的情欲。我把名字改成了潘多拉计划，这样HQ就不会发现我们还在研究这件事。继续研究或许有风险，但我相信值得。\r\n"),
 ("project_flytrap:entry_103", "Entry 103",
  "We've had to go through a few more iterations.\n\nOur latest clone has become volatile, more volatile than the original. Something needs to be done. We cannot lose the progress we've made.\n\nOur current plan is to separate mind from matter. What we need does not require a body.",
  "第103篇",
  "我们又做了好几次迭代。\n\n最新的克隆体变得很不稳定，比原体还不稳定。必须想办法。我们不能丢掉已经取得的进展。\n\n目前的计划是把意识与物质分离。我们需要的东西并不需要一具身体。"),
 ("project_flytrap:entry_107", "Entry 107",
  "We've done it after countless iterations we finally did it.\r\n\r\nOur latest clone has far exceeded expectations. The only problem is that we can not control it to the full extent. But I am sure we will also overcome this last hindrance.\r\n \r\n Ms. Leath will be delighted with our work here.",
  "第107篇",
  "我们做到了，经过无数次迭代，我们终于做到了。\r\n\r\n最新的克隆体远超预期。唯一的问题是，我们还无法完全控制它。但我相信这最后的障碍我们也能克服。\r\n \r\n 利思女士会为我们这里的工作感到高兴。"),
 ("project_flytrap:entry_62", "Entry 62",
  "Project Flytrap has been reactivated after confirmed sightings of Psychotria Viridis, otherwise known as 'Floria'. Reports that the subject was pacified seem to be mistaken.\n\nUsing DNA taken from the subject, we have begun work on a new phase of the project.",
  "第62篇",
  "在确认目击到Psychotria Viridis（又名“芙洛拉”）之后，捕蝇草计划已重新启动。此前关于该对象已被制服的报告看来是错的。\n\n我们利用从对象身上取得的DNA，开始了项目的新阶段。"),
 ("project_flytrap:entry_74", "Entry 74",
  "After mere days of work we've been able to synthesize a new subject with experimental cloning technology.\n\nUnfortunately this clone did not exhibit powers as strong as the original. The clone has been pacified while we continue work to create a more viable specimen.",
  "第74篇",
  "仅用几天，我们就用实验性克隆技术合成出了新的实验对象。\n\n不幸的是，这个克隆体表现出的能力不如原体强大。克隆体已被制服，我们则继续努力制造更可用的样本。"),
 ("project_flytrap:entry_92", "Entry 92",
  "Progress has been made on the cloning technology and we've been able to produce a more viable clone.\n\nVarious personnel are already complaining about voices in their heads. Good. The clone is showing promise.",
  "第92篇",
  "克隆技术已有进展，我们成功造出了更可用的克隆体。\n\n已经有不少人员抱怨脑海里听到声音。很好。这个克隆体很有希望。"),
 ("tower:the_cartel_", "The Cartel ",
  "Weakening the local government of Neon City might have been a bit hasty of us. A few paramilitary groups seem to be trying to establish themselves as powers within the city limits now.\r\n\r\nThey’re still new, small, but most are diorganized. I am confident we can crush them all if needed. \r\nBut there is a particular group, they call themselves The Cartel, that has been making incredible strides as smugglers.\r\n\r\nI think we can extort them. Control them. Not through explicit force, mind you, but manipulate them through political influence and get them to move hardware, drugs, and whatever else might be necessary to expedite our plans.\r\n\r\nI will contact their leader soon and see exactly how beneficial we can make this partnership.",
  "卡特尔 ",
  "削弱霓虹城的地方政府，也许是我们操之过急了。现在似乎有几支准军事团体想在城区范围内立起自己的势力。\r\n\r\n它们都还很新、很小，而且大多组织涣散。我确信必要时能把它们全部碾碎。 \r\n不过有一个特别的团体，自称“卡特尔”，在走私上进展惊人。\r\n\r\n我想我们可以敲诈它们、控制它们。当然不是靠赤裸裸的武力，而是通过政治影响操纵它们，让它们替我们运送硬件、毒品，以及任何能加快我们计划的东西。\r\n\r\n我很快会联系它们的头目，看看这段合作究竟能带来多大好处。"),
 ("tower:neon_city_takeover", "Neon City Takeover",
  "Neon City Notes - June 27th, 2048\n\r\nCity Takeover:\r\nWe are progressing quickly with the government takeover in the larger urban centers like Neon City.\n\r\nThe city's government posed a small resistance once they realized we were moving things behind the curtains, but our usual methods were more than enough to strip them of any vestige of their former power. The final obstacle was finally removed earlier today.\r\n\r\nWe are now adapting the government hierarchy and all urban systems to facilitate our experimentation. There should be no lack of subjects here, especially in the slums.\r\n\r\nI look forward to testing our new products. Make sure to send them once the new gas compound is finalized.\r",
  "霓虹城接管",
  "霓虹城笔记 - 2048年6月27日\n\r\n城市接管：\r\n我们在霓虹城这类大城市里的政府接管进展很快。\n\r\n当地政府意识到我们在幕后操作后做出了一点抵抗，但我们惯用的手段足以彻底剥夺他们昔日的任何权力。最后的障碍也在今天早些时候被清除。\r\n\r\n我们正在改造政府层级与所有城市系统，以方便我们的实验。这里不会缺实验对象，贫民窟尤其如此。\r\n\r\n我很期待测试我们的新产品。新式气体合成完成后记得送来。\r"),
 ("tower:no_more_mr._nice_toys_", "No More Mr. Nice Toys ",
  "Dear dildo thief.\r\n\r\nThis is the third time this week one of my dildos has gone missing. Now, I could let it slide when you took my Hunk o’ Hunk away. Even when you snatched my precious Willy-Wonky I still forgave you.\r\n\r\nBut I swear if you don’t give back my Giddy-up Henchman, your problems will be much bigger than a horse-sized dildo.\r\n\r\nI’m done playing. We are all responsible adults here. Respect other people’s property and put them back where you found them.\r\n\r\n[Someone scribbled a reply under the note]\r\n\r\n“No”.\r\n",
  "好玩具先生不忍了 ",
  "亲爱的假阳具小偷。\r\n\r\n这是本周第三次我的假阳具失踪了。你拿走我的“猛男块块”时，我可以不计较。你抢走我心爱的“威利摇摇”时，我依然原谅了你。\r\n\r\n但我发誓，你要是不把我的“骑乘跟班”还回来，你的麻烦会比一根马那么大的假阳具大得多。\r\n\r\n我不再陪你玩了。我们都是负责任的成年人。尊重别人的财物，把它们放回你拿走的地方。\r\n\r\n[有人在纸条下面潦草地回了一句]\r\n\r\n“不”。\r\n"),
 ("tower:emergency_report", "Emergency Report",
  "One of our SEX Androids has escaped. I have no idea how or why that thing left the laboratory, but I’ll be in big trouble if anyone finds it outside the facility.\r\nSpread the word around, but carefully! We’ve got a deviant and we need to find it!\r\n\r\n\r\nI repeat! We have a SEX deviant out there! And I need to stop it!\r\n",
  "紧急报告",
  "我们的一台性爱安卓逃走了。我完全不知道那东西是怎么、为什么离开实验室的，但要是有人在外面发现它，我就有大麻烦了。\r\n把消息传出去，但要小心！我们有一个越轨体，必须找到它！\r\n\r\n\r\n重复一遍！外面有一个性爱越轨体！我必须阻止它！\r\n"),
 ("the_touch_approach:experimental_brainwashing_technique_network", "Experimental Brainwashing Technique Network",
  "Our prototype is looking great. We decided to go for a three-way assault on the subject’s senses in order to overwhelm their nervous systems with complete and utter pleasure.\r\n\r\nFirst, the Touch Approach: We gave our network half a dozen limbs with a special vibrating function. These “tentacles”, as my team keeps referring to them, can vibrate in 45 different patterns, and are programmed to cycle through them as you experience the conversion therapy.\r\nWe also implemented tiny reservoirs close to each limb’s tip. This allows the machine to lubricate the subject simultaneously with the kinetic stimulation.\r\nWe are currently developing a special lubricant using the same chemicals present in our gas to achieve full immersion.",
  "实验性洗脑技术网络",
  "我们的原型看起来非常出色。我们决定从三个方向同时进攻对象的感官，用彻底而完全的快感压垮他们的神经系统。\r\n\r\n第一，触手接触法：我们给网络装了六条带有特殊振动功能的肢体。我的团队一直把它们叫作“触手”，它们能以45种不同模式振动，并被编程为在你接受转化治疗时循环切换。\r\n我们还在每条肢体末端附近做了微型储液腔。这让机器能在进行动态刺激的同时为对象润滑。\r\n我们目前正在开发一种特殊润滑剂，使用与气体中相同的化学物质，以实现完全沉浸。"),
 ("first_trial_results:experimental_brainwashing_technique_network", "Experimental Brainwashing Technique Network",
  "Ten different subjects have completed their first session with the EBT. The results were incredibly promising, as every single subject became agreeable and obedient for a short period of time after the exposure.\r\n\r\nLonger exposure might be necessary to generate permanent results. I’m still looking into the possible side effects of prolonged exposure to such potent elation.\r\n",
  "实验性洗脑技术网络",
  "十名不同的对象完成了第一次实验性洗脑治疗。结果极有希望：每次暴露之后，每个对象都会在短时间内变得顺从听话。\r\n\r\n要产生永久效果，可能需要更长的暴露时间。我仍在研究长时间暴露于如此强烈的快感之下可能产生的副作用。\r\n"),
 ("fifth_trial_results:experimental_brainwashing_technique_network", "Experimental Brainwashing Technique Network",
  "Our Network is an absolute success. Every single subject has been converted after a maximum of five sessions in the network. Seems like I didn’t even need to worry about our employees’ health so much.\r\n\r\nTen, fifteen sessions? As if! My intellect knows no limits! Mistress Leath is bound to compensate me well for all my effort! \r\n\r\n[There is an edit made to this note, it’s the same handwriting, but looks somewhat artificial.]\r\n\t\r\nMaster Leath has ordered me to continue work on these machines. I will make sure to strive for perfection.\r\nI am glad to be of service. We are all here to serve.\r\n",
  "实验性洗脑技术网络",
  "我们的网络是绝对的成功。每个对象最多在网络里接受五次治疗就完成了转化。看来我根本不必那么担心员工的健康。\r\n\r\n十次、十五次？想得美！我的才智没有极限！利思女士一定会好好补偿我的全部付出！\r\n\r\n[这张纸条上有修改痕迹，笔迹相同，但看起来有些刻意。]\r\n\t\r\n利思主人已命令我继续这些机器的工作。我定会力求完美。\r\n我很高兴能为她效劳。我们在这里都是为了效劳。\r\n"),
 ("intro_file:experimental_brainwashing_technique_network", "Experimental Brainwashing Technique Network",
  "It has become clear that our previous advances in behavioral manipulation were not good enough at reprogramming the subjects permanently. Mistress Leath finally has approved the resources necessary for the development of my latest prototype. We will not waste the opportunity.\r\n\r\nOur goal is clear and non-negotiable: Complete personality conversion.\r\n\r\nBy the end of our treatment, the subjects need to be absolutely agreeable and dependable, no matter who they were or what they believed in before the conversion. \r\n\r\nI will finalize my work on the schematics soon, and right after approval, I will need a mechatronic engineering crew to help me assemble it. \r\r\n",
  "实验性洗脑技术网络",
  "已经很清楚，我们此前在行为操控上的进展，不足以把对象永久地重新编程。利思女士终于批准了我开发最新原型所需的资源。我们不会浪费这个机会。\r\n\r\n我们的目标明确且不容妥协：完成人格转化。\r\n\r\n到治疗结束时，对象必须绝对顺从、绝对可靠，无论他们在转化前是谁、信仰什么。 \r\n\r\n我很快就会完成图纸，一旦获批，我需要一支机电工程团队来帮我装配它。 \r\r\n"),
 ("tower:fuckmachine_maintenance_for_dummies_2", "Fuckmachine Maintenance for Dummies 2",
  "File#2\r\nWARNING\r\n\r\nDo NOT open the engine doors without putting away your genitals first.\r\nStarting in July the company will no longer cover any surgery costs for anyone who gets their parts stuck on the engines. \r\n\r\n\r\nBe responsible: work first, fun after.\r\nHave safe cybersex.\r\n",
  "操机维护傻瓜指南 2",
  "档案#2\r\n警告\r\n\r\n先把你的生殖器收好，再打开引擎舱门。\r\n从七月起，公司不再为任何把部位卡在引擎上的人报销手术费用。 \r\n\r\n\r\n请负起责任：先工作，后享乐。\r\n祝你网络性爱安全。\r\n"),
 ("tower:fuckmachine_maintenance_for_dummies", "Fuckmachine Maintenance for Dummies",
  "File#1\r\nCongratulations, you have been chosen for maintenance duty. \r\nMake sure you have brought the appropriate tools from the maintenance shed before continuing.\r\n\r\nFirst, open the Engine door. You will now have to look through all the spinning parts and make sure they are all spinning.\r\nThen you will look at all the stationary parts and make sure they are all stationary.\r\n\r\nFound anything weird? Well fucking fix it, Einstein.\r\nWhen you’re done duct-taping your way to success, don’t forget to take the tools back to maintenance.\r\n",
  "操机维护傻瓜指南",
  "档案#1\r\n恭喜，你被选中执行维护任务。 \r\n继续之前，确认你已从维护棚带齐了合适的工具。\r\n\r\n首先，打开引擎舱门。然后你要检查所有旋转部件，确认它们都在旋转。\r\n接着检查所有静止部件，确认它们都保持静止。\r\n\r\n发现了什么不对劲？那就他妈去修好它，爱因斯坦。\r\n等你用胶带糊出一条成功之路之后，别忘了把工具送回维护棚。\r\n"),
 ("tower:workout_for_all_soldiers", "Workout for all Soldiers",
  "Grunt Training Regiment\r\nThe following regiment is to be followed precisely every single week. Failure to comply will lead to heavy disciplinary action.\r\n\r\nRegiment A\r\nFront Squats   15x3\r\nHack Squats    15x3\r\nDildo Squats    20x5\r\nHip Thrusts      20x5\r\nJust the tip      10min\r\nDoggystyle      20min\r\n\r\nRegiment B\r\nPush-Ups        20x3\r\nPull-Ups          15x3\r\nChin-Ups         15x3\r\nDick-Ups          20x5\r\nStanding 69     05min\r\nAnal Friction    15min      \r\n\r\nRegiment C\r\nShoulder Press    12x3\r\nBench Press        15x3\r\nDumbbell Press   15x3\r\nNipple Press        20x5\r\nTitfucking            15min\r\nDeepthroating     10min\r\n",
  "全体士兵训练计划",
  "步兵训练规程\r\n以下规程必须每周严格执行。不遵守将受到严厉处分。\r\n\r\n规程A\r\n前蹲   15x3\r\n哈克深蹲    15x3\r\n假阳具深蹲    20x5\r\n髋部挺举      20x5\r\n只进顶端      10分钟\r\n后入      20分钟\r\n\r\n规程B\r\n俯卧撑        20x3\r\n引体向上          15x3\r\n反手引体         15x3\r\n鸡巴上拉          20x5\r\n站立69     05分钟\r\n肛内摩擦    15分钟      \r\n\r\n规程C\r\n肩推    12x3\r\n卧推        15x3\r\n哑铃推   15x3\r\n乳头推        20x5\r\n乳交            15分钟\r\n深喉     10分钟\r\n"),
]


def ensure(path=SRC, apply=False, quiet=False):
    """补齐日志条目并改回正确的 Id；apply=False 只报告。返回改动条数。"""
    d = json.load(open(path, encoding="utf-8"))
    je = d["JournalEntries"]
    by_id = {}
    for x in je:
        by_id.setdefault(x.get("Id"), x)
    n_id = n_new = 0
    for old, (new, nm) in ID_FIXES.items():
        if new in by_id:      # 已经改过
            continue
        e = by_id.get(old)
        if e is None:
            if not quiet: print("   !! 找不到旧 Id %r" % old)
            continue
        e["Id"] = new
        e["Name"] = nm
        n_id += 1
        if not quiet: print("   改 Id: %s → %s" % (old, new))
    n_fix = 0
    for ident, txt in CONTENT_FIXES.items():
        e = by_id.get(ident)
        if e and e.get("TranslatedContents") != txt:
            e["TranslatedContents"] = txt
            n_fix += 1
            if not quiet: print("   正文修正: %s → %r" % (ident, txt))
    have = {x.get("Id") for x in je}
    for ident, nm, contents, tname, tcontents in NEW:
        if ident in have:
            continue
        je.append({"Id": ident, "Name": nm, "Contents": contents,
                   "TranslatedName": tname, "TranslatedContents": tcontents})
        n_new += 1
        if not quiet: print("   新增: %-58s %s / %s" % (ident, tname, tcontents[:18]))
    if not quiet:
        print("日志条目: 现有 %d 条, 改 Id %d 条, 新增 %d 条, 正文修正 %d 条"
              % (len(je), n_id, n_new, n_fix))
    if (n_id or n_new or n_fix) and apply:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
        if not quiet:
            print("已写入 %s（JournalEntries %d 条）" % (os.path.basename(path), len(je)))
    return n_id + n_new + n_fix


if __name__ == "__main__":
    n = ensure(apply="--apply" in sys.argv)
    if "--apply" not in sys.argv:
        print("(未加 --apply, 未写入; 待改动 %d 条)" % n)
