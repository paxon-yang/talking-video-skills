# 英文版适配层（纯英文视频：口播、字幕、屏幕文字全英文；零汉字）

> 何时读：用户说"英文版/纯英文/English video"，或 notes.md 记了 lang=en。中文版参数不动，本文件只列"英文版替换值"。
> 数值依据标记：【码】=来自工程代码（文件名）；【实测】=已在工程里实现并出样张/字体文件校准；【估】=常识/字体经验估算，必须出样张或听样后校准。
> **状态（2026-10 起）：英文支持已在工程 `<工程目录>/src/` 实现**：timeline `meta.lang:'en'` 即切换字体/字号/lint；缺省 `'zh'`，中文样片不受影响（example / sample_A / sample_B lint 仍 15/15，出图与旧成片 PSNR 39–47dB 一致）。英文占位样片：`public/projects/bee-level8/timeline.json`（生成脚本 `scripts/make_en_timeline.py`）。
> 数字人 HeyGen；配音 Fish Audio 克隆声音生成英文音频。

## 1. 度量换算（字/秒 → 词/秒）
| 项 | 中文版 | 英文版 | 依据 |
|---|---|---|---|
| 语速（含停顿） | 4.5–5 字/秒 | **2.2–2.6 词/秒**（≈130–155 wpm） | 【估】讲解类英文常见 130–160 wpm；以 Fish 成片实测为准 |
| 60s / 120s / 180s 词数 | 280–320 / 560–640 / 850–960 字 | **132–156 / 264–312 / 396–468 词** | 【估】= 时长×2.2–2.6 |
| 钩子 0–12s | 约 58 字 | 26–31 词 | 【估】 |
| 每句 | ≤20 字 | 目标 8–14 词，**硬上限 16 词**（≈6.5s） | 【估】 |
| 数据型上限 | 6.0 字/秒 | 2.9 词/秒 | 【估】 |
| 字幕每条 | 8–10 字，≤14 | **4–6 词，硬上限 7 词 / 38 字符（含空格）**，单行 | 【估】Netflix 类规范约 42 字符/行；这里压到 38 |
| 每条时长 | 1.7–2.3s | **1.7–2.5s**（4.1–5.5 词按 2.4 词/秒≈1.7–2.3s；7 词≈2.9s 偏长，只在慢句用） | 【估】 |
- 英文长词（≥4 音节）多，词数相同时比中文更"累"：同一段内容英文版建议比中文少 5–10% 信息点。
- 字数估时仍不是真时间戳；用 Fish 音频实际时长回算词/秒并写进 notes.md。

## 2. 版式与字体（拉丁字体：已实现）
字幕保持不变【码】tokens.ts layout.subtitle：Noto Sans SC 700 的拉丁字形、46px、y 0.905H、box 底 rgba(0,0,0,.8)；stroke 主题 56px/y 0.885H/4px 描边同样不变。**字幕用句首大写的普通大小写，不全大写。**
**关键校准（读字体文件 hhea/glyph bounds 得到，估算值作废）：Anton cap-height = 0.859em（不是 .72），大写平均 advance 0.474em；Barlow Condensed 700 cap-height = 0.70em，大写平均 advance 0.468em。** 所以"墨迹对齐中文原版"的字号比 v1 估算小：夹头词 290px 而非 340px，关键词 190px 而非 200px。逐字符宽度表在 `src/lib/textWidth.ts`（`antonEm()` / `barlowEm()`），组件用它自动缩小，不在浏览器里量字。
| 位置 | 中文版（码） | 英文版（已实现，【实测】） | 单行上限 |
|---|---|---|---|
| 夹头词 HeadFlankWords | Noto 900，240px，scaleX .8，墨迹 .23H | **Anton 400 全大写，290px（墨迹 249px=.23H），scaleX=1，nowrap（无 break-all）**；字号 = min(290, 区宽 ÷ 词宽em)，下限 110px。区宽 528(左)/582(右)px：3–4 字母 290、5→≈240–260、6→≈210–230、7→≈155–195（视字母宽窄） | 1 词，**≤6 字母**（≤8 绝对上限）。两个夹头词同屏时各自按字母数缩放，大小会不一致（EARLY 约 240px vs WARNING 约 150px），要齐就选字母数相近的词 |
| 关键词卡 KeywordCard | Noto 900，xl 168 / l 136 / m 110，字距 .08em | **Anton 全大写，xl 190 / l 158 / m 130，字距 .04em**（墨迹 .15H）；单行超 .9W 自动缩小 | ≤12 字母/行，≤2 行，≤3 词 |
| 　on_broll | 180px，字距 .3em | **同上字号（不 +12），字距 .07em**（.3em 套在英文单词上太散）；白色柔光不变 | 同上 |
| 　ghost_word | Ma Shan Zheng 毛笔，前景 250px，幽灵字 1104px scaleX 压缩 | **Anton；前景 260px 无描边；幽灵字 #1A1A1A，字号 = min(1000, .93W ÷ 词宽em)，无 scaleX** | 幽灵字 ≤7 字母；前景和幽灵字最好同一个词（只放 1 行前景） |
| 章节卡 ChapterCard | 标题 159px，标签 76px Noto 900，幽灵字 648px | **标题 Anton 全大写 185px（墨迹 .147H），宽度 >.9W 自动缩小（≤21 字符一般仍是 185px，24 字符≈175px）；标签 Barlow Condensed 700 92px 全大写字距 2px；幽灵字 Anton 648px，>.94W 自动缩小** | 标题建议 ≤16 字符（更长也不会出画，但字变小）；标签 ≤10 字符；幽灵字 ≤5 字母（或单个数字 `8` `3`） |
| HUD stack | 0.042H=45px 斜体 900 | **Barlow Condensed 700 斜体全大写 50px，宽度 >(.12W−36px) 自动缩小**（"LEVEL 8"≈50px 放得下） | ≤8 字符 |
| HUD single | 55px | Barlow Condensed 700 全大写 55px，超宽自动缩小 | ≤18 字符 |
| 大数字 BigNumber | Barlow Condensed 540px；标题 56px ZCOOL | 数字/单位/副标 **不变**；顶部标题 Barlow 700 ×1.2=67px，**句首大写**；`prefix` 可用 `~`，`unit` 用 `%` `K` `M` `bn` `x` | 数字 ≤8 位含逗号 |
| 药丸 PillsVs | ZCOOL 140px；条目 62px | **Barlow Condensed 700 全大写 168px（×1.2），药丸宽 ≤640(左)/800(右)px 自动缩小；条目 68px（×1.1）句首大写，按列宽自动缩小** | 药丸标签 ≤12 字符；条目 ≤24 字符 |
| 步骤卡 StepList | ZCOOL 104px | **Barlow 700 全大写 125px，缩到"序号竖线→缩略图"的 399px 内**（BOARD 125px，MANAGEMENT/PROCUREMENT 缩到约 85px） | 标题 ≤12 字符 |
| 总结卡 SummaryCard | ZCOOL 80px/175px 渐变标题 | single 条目 Barlow 700 ×1.2=97px（按框宽自动缩小）；渐变标题 ×1.2 全大写，按框宽缩小；double 左列统一一个字号；**quote 变体仍用 Noto Serif SC 900 的拉丁字形（衬线，观感好），英文自动 `text-wrap:balance`** | 条目 ≤28 字符；quote ≤8 词 |
| 问题卡 QuestionCard | ZCOOL 标题 140、正文 88、5 帧/字 | 标题 Barlow 700 147px；正文 101px（×1.15）、`word-break:normal`；**打字机缺省 2 帧/字**；**幽灵字缺省 `?`**（不再是"问题"），居中 Anton 1026px，建议显式传 | 正文 ≤90 字符 |
| 三图卡 ImageCards3 / 药丸栈 PillStack | Noto 900 112px / Poppins 82px | 图卡标签 Anton 全大写 130px，缩到 .29W 内；药丸 Barlow 700 ×1.25（gray 102px / color 75px），**药丸宽度自动增长到文字宽（≤.30W）** | 标签 ≤12 字符 |
| 抠像姓名 CutoutNameTag | 中文名 112px + 英文 46px | **`name` 填英文名（不要留汉字）**：Barlow 700 全大写 120px，缩到 .34W 内，居中 x .71；`en` 可选作职务小字（Barlow 600 52px，同样居中 x .71） | 名字 ≤22 字符 |
| 对比图 result_pair / three_col | ZCOOL 92px / 毛笔 170px、标签 100px | result_pair 标签 Barlow 全大写 97px；three_col 标题 **Anton 全大写 ≤150px 缩到列宽**，标签 Barlow 全大写 120px 缩到列宽 | 标题 ≤12 字符，标签 ≤16 字符 |
| 录屏标注 / 聚光灯 | Noto 900 60px / ZCOOL 104px | 标注 label 沿用 Noto 900 的拉丁字形 60px（粗黑无衬线，观感 OK）；聚光灯 label Barlow ×1.2=125px | ≤3 词 |
| 手机样机 / fixed 层 keyword、pill | ZCOOL 64/100px；Noto 130/110/90 | Barlow ×1.2；fixed keyword = Anton 全大写 ×1.4（182/154/126px）；fixed pill = Barlow 全大写 ×1.2 | — |
- **大小写**：夹头词、关键词卡、章节标题/标签、HUD、药丸标签、步骤标题、three_col = 全大写（组件里 `toUpperCase()`，timeline 里写大小写都行）；大数字标题、条目/总结正文、question 卡正文、字幕 = 句首大写（Sentence case）；不用 Title Case。
- **字幕标点用 ASCII**：`? , . ' "` 与 `-`；避免 “ ” — … 等。已出样张：ASCII 在 Noto Sans SC 700 里字距正常。
- 一行英文最大宽度（1920 画布，安全边 5%→可用 1728px）：字幕 46px 拉丁平均 ≈.52–.58em → 物理上限 ≈65 字符，**lint 阈值 ≤38 字符**；实测 36–38 字符的行宽约 840px（不到半屏）。
- 观感对照（和 `compare/` 原片图比）：Anton 比 Noto 900 窄得多且笔画更直，同墨迹高度下字块更瘦；夹头词/关键词/幽灵字的"体量感"靠加大到 290/190px、幽灵字撑满 .93W 来补，气质接近；章节卡/药丸/步骤卡与原片相近（Barlow 700 比 ZCOOL 轻，所以 ×1.2）。毛笔体的"情绪感"英文版没有对应物（ghost_word 前景改为 Anton 红字）。
- 旧的"不改代码的过渡法"（全部沿用 Noto Sans SC、字数上限乘 0.7）已作废。

## 3. Remotion 英文支持（已实现；状态表）
| 组件 / 文件 | 实现内容 | 状态 |
|---|---|---|
| types.ts `Timeline.meta` | `lang?: 'zh'\|'en'`（缺省 zh）；`subtitleMultiline?: boolean`（仅英文，字幕允许 `\n` 分两行） | 已实现 |
| fonts.ts | 加载 Anton 400(latin)；Barlow Condensed 补 normal 800 与 italic 700（现为 normal 500/600/700/800 + italic 500/600/700） | 已实现 |
| tokens.ts | `font.anton`、`font.condEn`；`EN` 常量块（所有英文字号/字距/上限） | 已实现 |
| lib/lang.ts、lib/textWidth.ts | `useLang()`（读 TimelineContext，无 context=zh）、`useCond()`（窄体字体+×1.2 缩放）；Anton/Barlow 逐字符宽度表 | 已实现 |
| HeadFlankWords / KeywordCard / ChapterCard / HudTag | 见 §2 表；去掉 break-all；scaleX=1；ghost_word 英文版；章节标题自动缩放 | 已实现 |
| CompareCard / StepList / SummaryCard / BigNumber / Cards（图卡、药丸栈、抠像姓名）/ SpotlightFocus / PhoneMockup / Player 的 fixed overlay | 窄体字体换 Barlow 700 ×1.2 并按宽度自动缩小；英文全大写规则见 §2 | 已实现 |
| QuestionCard | 缺省 ghostText 英文版 `?`；英文打字机 2 帧/字 | 已实现 |
| SubtitleBar | 字体字号位置不变；一条一行（nowrap）；`meta.subtitleMultiline=true` 时 `white-space:pre-line` 支持 `\n` 两行（框中心仍 .905H） | 已实现（两行默认关） |
| lint.ts / targets.ts | `meta.lang==='en'` 时第 7 项改为 `字幕行 ≤7 词/38 字符`（有 `\n` 时逐行判），阈值在 `targets.ts` 的 `subtitleEn`；其余 14 项不变；**英文 timeline 可 15/15** | 已实现 |
| **未适配（仍是中文版行为）** | `big_number` 的 `gold_card` 变体（标签带弯引号 “ ”、`en` 小字 Poppins、金色字用 ZCOOL）；`BrandCard` 名称用 Noto 900 拉丁字形（够用，没单独校准）；`ClosingCard`/`chart` 未实现；summary `quote` 衬线用 Noto Serif SC 拉丁字形 | 待改（用到再做） |
**lint 英文版**：`字幕行 ≤7 词/38 字符`，其余检查按时间/帧，不用换算。随手自查命令（不跑 lint 时）：`python3 -I -c "import json,sys;t=json.load(open(sys.argv[1]));print([(s['id'],len(s['text'].split()),len(s['text'])) for s in t['subtitles'] if len(s['text'].split())>7 or len(s['text'])>38] or 'OK')" public/projects/<slug>/timeline.json`
**英文 timeline 写法要点**：`meta.lang:'en'`；夹头词 `text` ≤6 字母；`chapters[].hud.stack` 每项 ≤8 字符（如 `LEVEL 8` `RIGHT` `WATCH` `ACTION`）；three_col 等占满左侧的镜头把 scene id 写进 `chapters[].hud.hideInSceneIds`（HUD 会盖住左列标题）；`atWord.word` 与 `sentences[].words[].text` 同名即可（大小写敏感，标点不要带）；`ghostText` 显式传；`name`/`label`/`unit` 一律英文。
**占位素材**：`public/placeholder/` 里的新闻图、logo、录屏、`gen_placeholders.py` 产物含汉字，英文版不能用；用 `scripts/gen_placeholders_en.py` 生成的 `public/placeholder/en/`（`host_full_150s.mp4`/`host_pip_150s_480.mp4`/`host_150s.wav`=旧 2 分钟占位+前 30 秒拼成 2:30、`news_en_1-4.png`、`logo_en.png`、`screen_ledger.mp4`、`screen_board.mp4`）；`broll_*.jpg`、`cutout.png` 本来就是纯英文，可直接用。
**出样张提示**：Google Fonts 一次要拉 ~180 个字体文件，网络慢时 Remotion 默认的 delayRender 超时（约 58s）会失败。工程里 `scripts/stills_tl.mjs <outDir> <timelineSrc> name:frame ...` 用**同一个浏览器实例**（缓存字体）+ 重试 + 240s 超时，比 Skill 里的 `stills_timeline.mjs` 稳；Skill 脚本失败时改用它。

## 4. 零中文清单（屏幕上不得出现任何汉字，含片头片尾、占位、调试）
| 位置 | 默认带中文处 | 英文替代 |
|---|---|---|
| p1/QuestionCard.tsx | 中文版缺省 `ghostText ?? '问题'` | **英文版缺省已是 `?`**（`meta.lang==='en'`），仍建议显式传 |
| p1/BigNumber.tsx | unit 示例 `万`，prefix 示例 `约`（types.ts 注释）；含汉字时切 ZCOOL | `%` `K` `M` `bn` `x`；`~` `R` `$` |
| ChapterCard / types.ts Chapter.label | 示例 `实测` `优势` | `STEP 1` `TEST` `RESULT` |
| HudTag / chapters[].hud.stack | 阶段名常为中文 | ≤8 字符英文 |
| CalloutBox / SpotlightFocus 的 label | 录屏标注文案 | 英文短语 ≤3 词 |
| cutout_name（p1.cutout） | `name` 112px 中文名 + `en` 46px 英文小字 | **`name` 直接填英文名**（已实现：Barlow 120px 全大写居中），`en` 填职务小字或不填；不要留汉字 |
| keyword_card `en` | Poppins 英文副标 | 不填（正文已是英文） |
| fonts.ts / tokens.ts | 中文版仍加载 ZCOOL/Ma Shan Zheng 等 | 英文版组件已改用 Anton / Barlow Condensed / Noto Sans SC 拉丁字形，不再依赖 ZCOOL 的拉丁覆盖 |
| stubs.tsx | `P2 scene not implemented`（英文红底） | 不应出现；出现即失败 |
| 素材 | 录屏/截图里的浏览器、系统、网页中文界面；`public/placeholder/` 里的新闻图/logo/录屏含汉字 | 录屏前把系统/软件/网页切成英文；占位用 `public/placeholder/en/`（见 §3） |
| 数字人视频 | HeyGen 烧入字幕/水印；背景里的字 | 关闭自带字幕；背景纯色（见 §6） |
| 封面/片尾 | 封面、片头、片尾卡 | 英文；ClosingCard 本就未实现 |
| 不上屏所以不用管 | timeline 的 `note`/`id`、lint 提示文字、文件名 | — |
**交付前自检（零汉字，必做）**：
1. 静态：`jq 'del(.. | .note?)' public/projects/<slug>/timeline.json | grep -nP '[\x{4e00}-\x{9fff}\x{3000}-\x{303f}\x{ff00}-\x{ffef}]' || echo NO_CJK`
2. 抽帧 OCR（Vision，中英双语；工具 `tools/ocr` 在原片目录下，输出 JSON，bbox 归一化）：
```bash
OCR="<素材目录>"
mkdir -p <工程目录>/out/<slug>/zh_check && cd <工程目录>/out/<slug>
ffmpeg -v error -i final.mp4 -vf fps=1/2 zh_check/f%04d.png     # 每 2 秒一帧；章节卡/大数字再补 still
"$OCR" zh_check/f*.png | python3 -I -c "import json,sys,re;d=json.load(sys.stdin);h={p:[b['text'] for b in v['blocks'] if re.search(r'[　-〿一-鿿＀-￯]',b['text'])] for p,v in d.items()};h={p:t for p,t in h.items() if t};print(h or 'NO_CJK')"
```
命中的帧用 Read 看图确认。**已知假阳性**：① Anton 大写字母在入场模糊帧里会被误识成 `【0！` 这类符号；② Vision 会把 ASCII 的 `, ? :` 识别成全角 `，？：`（落在 3000–303F/FF00–FFEF 范围内）——对照 timeline 里的 ASCII 字幕即可排除。**只要没有 4E00–9FFF 的汉字命中，就判通过**（建议把上面命令的正则拆成两档：`[一-鿿]` 严格档必须为空，标点档人工确认）。OCR 看不到的极小/极暗字，仍要抽 5–8 帧人工看。已跑过的实测：bee-level8 英文样片 8 类 still + 抽帧小片段共 42 张，严格档 0 命中。

## 5. 英文口播稿写法
- 句长见 §1；一句一个意思；数字单独成句。多用缩略（it's, don't, we're），口语更像真人；避免长从句和连续 3 个以上名词堆叠（TTS 易断错）。
- 数字：写成读法。`10%`→`ten percent`，`2026`→`twenty twenty-six`，`R50m`→`fifty million rand`；`Level 8`→`Level eight`。屏幕字幕仍可用阿拉伯数字（口播稿与字幕可不同，字幕按口播句拆分）。
- 缩略词（Fish 读法不确定，**需听后调整**）：`XYZ` 稿里写 `B-B-B-E-E`（逐字母，连字符促使拆读）；`DMPR`→`D-M-P-R`，首次出现先说全称（Department of Mineral and Petroleum Resources，全称请按用户稿核对）；`示例项目` 若读成单词 "bee" 则写 `B-E-E`。字幕里仍显示 `XYZ`。能读成单词的（ESG, NATO 式）不加连字符。
- 停顿：主稿保留 `/`（短，0.3–0.5s）与 `//`（长，≈0.8s）；**粘贴给 Fish 的版本**转换：`/`→逗号，`//`→句号+换行（标点停顿最稳）；是否识别 `...`/`(break)` 一类标签**需按 Fish Audio 实测**，不要默认可用。
- 重读：主稿**保持 `【】`**（它是 ScriptJSON `marks` 与贴字对齐的依据，中英共用）；粘贴版去掉括号，重读靠"把关键词放到句末/用短句独占"实现。`*词*` 或大写在 Fish 里是否改变重音**需按 Fish Audio 实测**（大写可能被当缩写逐字母读，慎用）。
- 克隆声音是中文参考样本时，英文可能带口音/语调偏中文；有英文参考音频更稳【估】，听 10 秒样再定。
- 先用 Fish 生成 10–15s 样音，确认读音、语速、停顿，再整条生成（整条一次生成，避免分段音色跳）。

## 6. 开头钩子：9 手法英文填空（对应 hooks-and-copy.md ①–⑨）
1. 问句+关键词红："Is {thing} really {a safe bet / worth it} for {audience}?"
2. 夹头词+承诺："You won't believe it. {A} can {B}." （夹头词 `{A}` / `{B}` 各 ≤6 字母）
3. 以前/现在："It used to take {cost1}, {cost2} and {cost3}. Now it takes {one action}."
4. 成品预告："Here's {N} seconds of the result. Stay for the {surprise}."
5. 最高级/反常识数字："{Number}. That's what {subject} {verb} in a year. More than {reference}."
6. 反转："The {free thing} you already have hides {Y}. Most people never check."
7. 新闻冷开场："In {month year}, {authority} ruled {fact}. So was {earlier effort} wasted?"
8. 极端设定（≤8s）："What if, tomorrow, {extreme scenario}? What would you do?"
9. 亲历："Last month I went to {place}. The first thing I felt was {sensory contrast}. And no, I don't mean {usual meaning}. I mean {surprising detail}."
- 英文钩子同样 3 秒内出现，≤16 词/句；问句句末 `?`，升调靠问号。

## 7. HeyGen 与 Fish Audio
- 口型由音频驱动，与语言无关；本地 ffprobe 验收仍按 SKILL.md 第 0 轮。
- **需用户确认**：① HeyGen 是否关闭自带字幕/水印（必须关，零汉字且字幕由 Remotion 出）；② 导出 1080p、横屏 16:9、30fps（HeyGen 默认帧率需确认）；③ 是否用"上传音频驱动"模式及该模式的时长/大小上限（**需确认**）；④ 数字人背景为暗色单色（digital-human.md §2）；⑤ 英文稿的缩略词读音由谁听审。
- Fish 导出：优先 **WAV，PCM 16-bit，单声道，44.1 或 48kHz**；若上传限制太小用 MP3 ≥192kbps。Remotion 的 `host.wav` 仍由 HeyGen 成片提取（48k mono），不是 Fish 原文件（保证音画同步）。HeyGen 对音频文件大小/时长的上限**需确认**。
- 词级时间戳：Fish 是否返回词时间**需按 Fish Audio 实测**；没有则对成片 wav 做英文强制对齐/转写（英文模型成熟度高于中文，但本机未装，仍属"待搭建"，未验证误差）。

## 8. 示例项目 实跑后的补充/修正（2026-10-18，与上文冲突处以本节为准）
- **语速**：Fish 克隆声音实测 ≈1.75 词/秒（3:21），明显低于 §1 的 2.2–2.6。本地 `silenceremove`（停顿封顶 0.40s）+ `atempo 1.2` 压到 2:31（约 2.2 词/秒）。词数预算按**实测语速**回算，必要时先压稿再生成。
- **HeyGen 帧率 25fps，不是 30**（§7 的"需确认"已确认）：转 30fps 用帧复制，host 不插值（mci 扭曲手、blend 出重影）；详见 production-playbook.md S5。
- **HeyGen 自带字幕**：下载对话框有"字幕"tab，导出 SRT（句级，34 条）；词级仍没有，句内时间按词数估算 ±0.3s，强制对齐仍待搭建。
- **背景**：用户选**保留 HeyGen 房间背景**（浅色薰衣草墙+书架，非暗色），在包装里压暗/冷调，卡片底用"房间延续"（模糊的房间图，无网格）。与 digital-human.md 的"暗色背景"建议冲突时，以用户确认为准。
- **字幕拼写**保持 SRT 的 "level eight / level one"；屏幕上的标题/章节/HUD/大数字用阿拉伯数字（LEVEL 8、8）。
- **零汉字 OCR**：建议每 1.5s 抽一帧（示例项目 用 2s 也可）；新增已知误报：B-roll 栅栏里的 "WARNING!" 的 `!` 被识成 `犯`。B-roll 自带英文牌子（CONTRACT、NO ENTRY、WARNING）是允许的。
- **HeyGen/Fish 浏览器上传限制 <10MB**；整条音频 mp3 可传；HeyGen 渲染成本 ≈0.8 积分/秒。
