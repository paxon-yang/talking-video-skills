---
name: combo-style
description: 用户提供自己的数字人视频（或先拿 Claude 写的口播稿去数字人工具生成），和 Claude 多轮沟通、逐轮打磨，按 combo 风格（博主A × 博主B 合并后的"暗底固定框架 + 数字人口播 + 少而准的动效"）做出 1–3 分钟横屏精品讲解视频，目标是成片和原片一样精美。用户说"按 combo 风格/博主A风格/博主B 风格做视频""我有数字人视频，帮我包装/加动效""帮我写数字人口播稿/脚本""出分镜表""给剪映剪辑说明""做 Remotion 动效视频/写 timeline.json/出样张/预览/渲染""这条视频不够精致，再改改"时使用。流程是协作轮次：素材接收 → 稿子 → 分镜 → 关键帧样张（与原片并排） → 低清预览 → 精修终版；每轮交给用户看、请用户确认、按反馈修改，可随时回到前面任一轮。
---

# combo 风格（博主A × 博主B）

## 定位与工作方式
**暗底固定框架，数字人口播当"逻辑节点"、少而准的动效当"证据"，每一刀都跟着嘴走。**
质感关键词：**钉死的框架 / 跟着嘴走 / 少而准**。
默认以博主A的教程框架为骨架（暗底网格、字幕条、左下圆形 PIP、录屏推拉、关键词卡、章节卡、荧光绿 HUD），借博主B 六点：大景每 15–20s 回归；所有静态素材线性慢推；数据选题用图表当证据；PIP 叠在图表/B-roll 上可"喊话放大"；3 分钟数据型可加章节角标；大数字卡。
目标成片 1–3 分钟、16:9、1920×1080、30fps（原片是 20 分钟长视频，只迁移可迁移的部分）。

**这是协作，不是一次性生成。** 数字人视频由用户提供（或用户拿我们写的稿子去数字人工具生成），素材（录屏、截图、数据）由用户提供；Claude 负责稿子、分镜、动效和渲染，每一轮把东西交给用户看，按反馈改，直到成片和原片一样精美。
- **质量标准是"像原片"**：对照原片证据帧逐项比（字体、阴影、间距、缓动、节奏），不是 lint 通过。lint 只是底线检查。
- **每轮只交一小份东西**，请用户做具体选择（见 references/collaboration.md），不要把整条流程闷头跑完再交。
- **用户的每个确认和偏好记进该项目的 notes.md**；跨项目通用的偏好回写 references。
- 没有的素材、没有的工具如实说"缺/待搭建"，不编造、不假装已有。

## 全流程阶段与闸门（细节见 references/production-playbook.md）
S1 稿子（Notion 原稿→压缩口播→钩子改写→英文改编，按实测语速回算词数）→ S2 声音（用户 Fish 克隆声音，**绝不用 HeyGen TTS**；本地 silenceremove 封顶停顿 + atempo；**G2 用户选最终时长**）→ **S2.5 素材提示词包（用户用 Gemini 生成全部视频/图片，Claude 给每条提示词+秒数；入库质检；G2.5，见 references/gemini-asset-prompts.md）** → S3 HeyGen（浏览器驱动；形象/背景/13s 样片 **G3**；整条渲染 ≈0.8 积分/秒；身份验证/付款/删除只由用户做）→ S4 样张 **G4** → S5 B-roll（Pexels，记 LICENSES，30fps，航拍才插值）→ S6 timeline（**字幕/关键词时间必须来自词级强制对齐，不得估算；预览前过 G5.5 字幕同步检查，见 references/subtitle-sync.md**）→ S7 低清预览轮 v1..vN **G5** → S8 动效精修+SFX+创意图形（references/motion-polish-and-sfx.md）→ S9 终版 crf18 + loudnorm -16 LUFS（`-c:v copy`）→ S10 自检 + 拷到桌面 **G6**（130MB 不进云盘）。
**默认不做 BGM**：交付"人声+SFX"版，用户自己在剪映加音乐；`assets.bgm` 不写，SFX 保持安静。

## 用户在意什么（每条视频动手前过一遍）
- 画面要**丰富的真实 B-roll**，不是只有关键词卡；缺素材就去免费商用库找，别降级成字。
- 动效**丝滑精致**：弹簧/缓动、遮罩+模糊出现、运动模糊、精确退场；逐帧自查。
- **有退场也有音效**（SFX 轻、密度 ≤0.8/s）；结构点用**创意图形**（链/阶梯/闸门/图标）而不是字，图形用粗 Anton 数字、粗线。
- 英文视频**屏幕零汉字**（含 B-roll 里的牌子，OCR 抽检）。
- 原片是**参考不是照抄**：撞 PIP/字幕就按实际改，小设计自己定，只把改变观感的大选择交给用户。
- 协作不是一键：每个闸门停下给用户看，确认后写 notes.md。

## 为什么看着舒服（核心原理，数值见 references/comfort-rules.md）
1. **剪辑跟着嘴走**：约七成切点落在字幕换句处（博主A中位 69%、博主B 70–88%）；每 2–3 句一个主画面（4–7s）；贴字在说到那个词时出现（−2~+4 帧，宁晚勿早）。
2. **固定框架里只换内容**：字幕全片一个样式、y 抖动 ≤1% 画高；只用两种底（#010101 网格 / 压暗 B-roll）；强调色 ≤3；一屏 ≤1 主标题 + 3–4 要素。
3. **运镜少而有目的**：录屏推近只到 1.12 倍、约 28 帧 ease-in-out；主播 punch-in 1.08 倍、≤2 次/分；B-roll 线性慢推 1→1.08；运镜只作用于内容层，PIP/字幕/HUD 不动。
4. **主播 = 判断，动效 = 证明**：提问、转折、总结给主播大景；事实、数字、流程、界面、比喻给动效。大景每 15–20s 回来一次，无脸段 ≤10s。
5. **动效时长有档位**：硬切 0 / 快 6 帧 / 标准 12 帧（慢 18 帧）；停留 ≥40 帧。

## 语言开关（中文版 / 英文版）
- **默认中文版**：本文件与其他 references 的数值都是中文版参数，不变。
- **英文版**（用户说"英文版/纯英文视频"，或 notes.md 记 lang=en）：先读 references/english.md，它给出英文替换值（词/秒、字幕词数、拉丁字体与字号、lint 英文阈值、TTS 读法、英文钩子、HeyGen/Fish Audio 注意点）；与中文参数冲突时英文版以 english.md 为准，其余（节奏、运镜、色值、字幕位置 y 0.905H 与字号 46px）沿用。
- **英文版硬规则：屏幕上零汉字**（字幕、关键词、夹头词、章节卡、HUD、单位、标注、占位、片头片尾、录屏界面、数字人烧入字幕全部英文/数字/符号）。清单与检查命令见 english.md §4。
- 英文版的字体/字号/lint 已在工程里实现：timeline 写 `meta.lang:'en'` 即切换（缺省 zh，中文不受影响）；只有 english.md §3 末行列的少数变体（gold_card 等）未适配。英文版占位素材用 `public/placeholder/en/`（旧占位含汉字）。第 0 轮先问清：HeyGen 是否关字幕、导出分辨率/帧率、Fish 音频格式。

## 文件地图（按需读取，不要一次全读）
| 文件 | 何时读 |
|---|---|
| references/collaboration.md | **每轮都用**：交付物清单、怎么提问、用户反馈→参数对照表、notes.md 写法、偏好回写 |
| references/digital-human.md | 第 0 轮：数字人构图/背景/语速/导出文件、时间戳获取、各工具注意点 |
| references/thinking.md | 第 1 轮：选题 5 问、开头/结构/心理节奏、信息密度、句子角色→谁出镜、20 分钟压成 1–3 分钟 |
| references/templates.md | 第 1 轮：模板 A/B/C 的 60/120/180s 分段时间表与字数预算 |
| references/hooks-and-copy.md | 第 1 轮：开头手法库（填空模板）、文案规则、口播标记、结尾 CTA |
| references/visual-mapping.md | 第 2 轮：内容类型→画面→组件映射；四拍/演示序列；主播回归；PIP 预设与切换；禁入区 |
| references/packaging.md | 第 2–5 轮：字幕、色值、字体、关键词卡、夹头词、HUD、章节卡、标注框、宽银幕等版式参数；两种主题差异 |
| references/motion-and-camera.md | 第 2–5 轮：全部动效目录（含博主B N23–N30）与虚拟运镜参数表 |
| references/comfort-rules.md | 第 2、5 轮：11 条舒适度规律（量化）与检查方法；lint 15 条；必须/应当/可选 |
| references/remotion-pipeline.md | 路径 B（第 3–5 轮）：timeline.json 字段、组件 props、P2 未实现与替代、数字人接入、lint、渲染命令、常见坑 |
| references/jianying-guide.md | 路径 A：剪映逐项操作（字幕、关键帧推镜、圆形 PIP、文字动画时长、转场、音效、配乐） |
| references/production-playbook.md | **从零做一条完整视频（HeyGen+Fish+英文）**：S1–S10 阶段/闸门/成本/坑，示例项目 实跑记录 |
| references/gemini-asset-prompts.md | **素材一律由用户用 Gemini 生成（S2.5）**：shotlist→提示词包、style bible、视频/图片提示词结构、秒数、命名、入库质检、重出模板；脚本 make_prompt_pack.py / ingest_gen_assets.py |
| references/motion-polish-and-sfx.md | 退场编排、新转场、SFX 库与 cue 规则、无 BGM 默认、mg 图形套件与何时用图形 |
| references/english.md | **英文版**：词/秒换算、拉丁字体与字号、零汉字清单与 OCR 检查、lint 英文阈值与待改代码、英文口播/钩子、HeyGen+Fish Audio |
| references/forbidden.md | 第 1 轮与交付前：不能复制的标志性元素与替换 |
| templates/output-template.md | 最终交付汇总模板（各轮产物拼起来即是；见该文件顶部说明） |
| templates/timeline.example.json | 组件渲染样例（占位素材，模板 A 90s，lint 15/15）——只用来看组件长什么样、复制 JSON 结构，**不是示例选题** |
| templates/build_demo_timeline.py | 用工程里的 builder 从"beat 列表"生成 timeline 的写法参考 |
| templates/grid_bg_1920x1080.png | 网格底图（#010101 + #1A1A1A、72px），剪映路径直接用 |
| scripts/README.md | 可复用脚本清单（SFX 合成/cue、混音检查、联系表、转场模式、出图）及 TS 组件如何带进新工程 |
| scripts/stills_timeline.mjs | 对任意 timeline 一次打包出多张关键帧 PNG（第 3 轮用，已验证） |
| examples/demo-script.md | 一次协作过程示例：第 0–4 轮每轮交什么、用户可能怎么反馈、怎么改 |
| video-asset-prep/SKILL.md | **高级动效**：口播片里加 fx 动效积木、做纯动效宣传片、拆新的参考动效视频（规律 / 积木目录 / 拆解方法） |

Remotion 工程：`<工程目录>/`（本机，不在云盘）。**`src/tokens.ts` 与组件是参数唯一事实来源**；与 references 冲突以工程代码为准。`src/` 不是只读：按需求需要就改（新增/扩展积木、改共享文件都可以，用户 2026-10-19 明确认可）；改完建议跑 ae-motion-craft 的回归检查确认没弄坏旧流程；不要 git commit，除非用户要求。

## 每个视频项目的目录约定
Remotion 的 `staticFile` 只能读 `public/`，而 `public/` 会被整个打包进每次渲染/出图——**大体积原始素材不要放进 public/**。所以每个项目分两处，slug 用英文小写短横线（如 `meeting-notes`）：
```
<工程目录>/projects/<slug>/          # 工作区（不被打包）
  input/        用户交来的原始文件：数字人原视频、录屏、截图、数据（只读，不覆盖）
  script.md     口播稿 + 句子角色表（第 1 轮）
  storyboard.md 分镜表 + 素材清单（第 2 轮）
  words.json    句级/词级时间戳（第 0 轮取得；工具见下）
  notes.md      决定与偏好日志（格式见 references/collaboration.md）
  review/       每轮给用户看的图/视频（stills、compare、preview，带轮次与版本号）
<工程目录>/public/projects/<slug>/   # 渲染用（会被打包，只放处理后的成品素材）
  host_full.mp4  host_pip_480.mp4  host.wav         # 由 input/ 转码得到，规格见 digital-human.md §8
  assets/…                                          # 渲染要用的录屏/图/B-roll/Logo
  timeline.json                                     # timelineSrc = "projects/<slug>/timeline.json"
```
- timeline 里所有路径相对 `public/`，如 `assets.hostVideo = "projects/<slug>/host_full.mp4"`、`assets.files` 指向 `projects/<slug>/assets/…`（其余字段见 remotion-pipeline.md §1）。
- 渲染输出放 `out/<slug>/`（工程已 .gitignore 掉 out/）。`lint:timeline` 接受任意路径：`npm run lint:timeline -- public/projects/<slug>/timeline.json`。
- 本约定没有改工程 src/；`projects/` 目录需要时由 Claude 新建。

## 协作工作流（第 0–5 轮；任何时候都可以回到前面任一轮）
每轮格式：**交给用户看什么 → 请用户确认什么 → 用户反馈后怎么改**。具体提问句式、反馈翻译表见 references/collaboration.md。用户确认后写进 notes.md，再进下一轮。用户回头改前面的轮次时，只重做受影响的部分（改稿 → 分镜/时间戳/timeline 要重对；改分镜 → 样张要重出；改视觉参数 → 不动稿子）。

### 第 0 轮 素材接收（用户给数字人视频，或先写稿再生成）
两种起点：
- **A. 用户已有数字人视频** → 按下面验收；通过后取音频和文字。
- **B. 用户还没有视频** → 先做第 1 轮的稿子，用户确认后拿 digital-human.md §6 的粘贴版去数字人工具生成（构图/背景要求先告诉用户，生成后无法在后期改），再交回视频，回到本轮验收。

**数字人视频验收**（先 `ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,avg_frame_rate,duration,pix_fmt -of default=nw=1 in.mp4` 取客观数据，再抽 3–5 帧用 Read 看图；标准全文见 digital-human.md §1–§4、§8）：
| 检查项 | 合格 | 不合格时请用户怎么办 |
|---|---|---|
| 分辨率 | 1920×1080，横屏 16:9 | 重新导出 1080p 横版；720p 以下或竖屏需重做，不要拉伸 |
| 帧率 | 30fps 恒定（avg=r） | 可由我们转码（`-r 30`）；若是变帧率先告知转码有口型漂移风险 |
| 时长 | 与目标 60/90/120/180s 相符，一次生成整条（不是多段拼接） | 分段生成的肤色/光线会跳变，请合并成一次生成，或说明要接受拼缝 |
| 构图 | 半身正面、双手入镜；脸高约 0.30H、脸中心约 (0.48W, 0.38H)；头顶留白约 0.07H；脸两侧 x 0.03–0.305、0.667–0.97、y 0.07–0.35 干净；手势不压 y 0.86–0.93 字幕带 | 让用户在工具里调景别/缩放/位置重新导出；小偏差由我们在 PIP 取景处补偿，大偏差必须重导 |
| 背景 | 暗色单色或干净场景（亮度 Y 约 42–62），不是原博主的房间；不闪 | 换暗色背景重导；若是绿幕/透明底，告知**目前渲染器没有换背景实现**，需在工具里烧入暗色背景 |
| 口型与表情 | 抽 3 个说话帧，嘴型清晰、无糊脸/掉帧/手变形 | 指出具体时间点，请用户换形象/换工具设置重生成该条 |
| 服装灯光 | 纯色深色上衣，无细条纹；脸亮背景暗 | 同上，重导 |
| 音频 | 视频自带音轨；最好另导出无 BGM 的 wav | 没有 wav 我们从视频里提取（见下）；有 BGM 烧在里面要请用户导出无配乐版 |
| 字幕/文字 | 最好附 SRT 或口播稿原文 | 没有则走下面的转写 |
验收结论用 ✓/✗ 表交给用户，不合格项逐条写"重导时怎么设"。

**取音频与文字（哪些已有、哪些待搭建）**
- ✓ 已有（本机 ffmpeg/ffprobe）：转码 30fps、提取音频 `ffmpeg -i in.mp4 -vn -ar 48000 -ac 1 host.wav`、做 480p PIP 代理——命令全在 digital-human.md §8。
- ✓ 已有 · 用户有口播稿（方案 B 或用户自己提供）：句级文字直接用稿子；时间用 wav 时长 + 字数比例估算，confidence=0.5，贴字偏移 +4 帧（digital-human.md §9-3）。
- ✗ **待搭建 · 语音转写 + 中文词级强制对齐**：本机未安装 whisper / WhisperX / stable-ts / FunASR（已查），Python 里也没有；工程里的 `@remotion/openai-whisper` 只是解析 OpenAI Whisper API 返回结果的工具包，需要用户的 API Key，我们没有接入。在搭建并在样例上验证中文对齐误差之前，**不能声称已有词级时间戳**。可选替代：(1) 数字人工具导出的 SRT（句级）；(2) 用户在剪映里"识别字幕"导出 SRT；(3) 用户同意后由 Claude 搭建本地 ASR（需先征得同意，装依赖要说明）；(4) 先用句级估算做样张，终版前再补对齐。
- 无论哪种，把结果存成 `projects/<slug>/words.json` 并在 notes.md 记明来源与置信度；中文读错字要对比稿子（digital-human.md §10）。
交给用户：验收表 + 时间戳来源说明 + 需要重导的清单。请用户确认：视频是否就用这一条；时间戳走哪种方案。

### 第 1 轮 稿子（选题 → 口播稿 → 句子角色表）
做：选题 5 问（thinking.md §2）、模板类型、一句主张 + ≤3 条证据 + 一个反差（thinking.md §4–§7）、钩子（hooks-and-copy.md §1–§2）、段落时间表（templates.md；字数 = 时长 × 4.8 左右，教程型 `N = round((T−42)/25)`）、逐句口播并打 role/intent/marks（hooks-and-copy.md §3–§5；每句 ≤20 字、数字单独成句、CTA 只在结尾一次、不写原博主句子，forbidden.md）。若用户已有视频，则以视频里的实际台词为准，只做"角色表 + 修改建议"，不擅自改稿。
交给用户：2–3 个标题/钩子备选 + 口播稿全文（可粘贴版）+ 句子角色表（精简列：句号｜原句｜role｜谁出镜）。
请用户确认：钩子选哪个；哪些句子要删改；数字/事实是否属实；字数与时长是否合适。
反馈后：改稿 → 重算字数/语速 → 如已有视频需重新对齐时间。

### 第 2 轮 分镜（分镜表 + 素材清单）
做：判断句→主播、证明句→动效，连续 2–3 句合一个主画面，选 PIP 预设（visual-mapping.md、motion-and-camera.md、comfort-rules.md）；开头 20–30s 最密，之后"15s 紧 + 15–20s 松"，大景每 15–20s 回归，无脸段 ≤10s，punch ≤2/分，录屏每 3–5s 一次推拉或标注。证据素材不够就降级为关键词卡 + 主播，不硬凑。
交给用户：分镜表（时间｜口播｜画面｜PIP｜字幕与强调词｜动效/运镜）+ **素材清单**（每项：id、用在第几镜、要什么内容、怎么录/怎么导、没有的话的降级方案，如"screen_render：渲染命令运行的录屏，≥1080p，5–10s，光标可见；没有则改关键词卡"）。
请用户确认：分镜节奏；每个素材能不能提供；缺的素材是补还是降级。
反馈后：改分镜、更新素材清单；素材到了放 `input/`，检查分辨率/内容/隐私信息（账号、Key、人脸）后转进 `public/projects/<slug>/assets/`。

### 第 3 轮 关键帧样张（与原片证据帧并排）
做：写 timeline.json（remotion-pipeline.md；可参考组件渲染样例 templates/timeline.example.json，但内容换成本项目），`npm run lint:timeline`，然后出 **6–10 张关键帧**——钩子帧、夹头词、关键词卡/章节卡、录屏推镜中点、大数字/对比卡、PIP 画面、字幕帧、片尾帧各选代表：
```bash
cd <工程目录>
# 用法: node <脚本> <timelineSrc> <outDir> <帧号,帧号,…>；打包一次出多张，约 10 秒，输出 f<帧号5位>.png
node talking-video-oneshot/scripts/stills_timeline.mjs projects/<slug>/timeline.json out/<slug>/stills 45,300,620
# 单张也可：npx remotion still Main out/<slug>/x.png --props='{"timelineSrc":"projects/<slug>/timeline.json"}' --frame=300
# 并排（左原片 右我们，均缩到 960×540）
scripts/compare.sh projects/<slug>/review/r3_cmp_01.png <原片证据帧> out/<slug>/stills/f00045.png   # 左原片 右我们，均缩到 960×540
```
- 原片证据帧在 `<素材目录>` 的 `v03|v04|ex04–ex06/evidence/`、`ex01–ex03/ev/`、`v01|v08|v09|ex07|ex08/frames|bursts|scenes/`；对应 `analysis.md`/`motion_catalog.md`/`transcript.md` 可查某镜头在原片里的做法。工程 `compare/` 下还有各组件的既有对照图。**只读，不要改动原片目录**。
- 找不到同类证据帧时，如实标"无对应原片帧"，改用 packaging.md 的参数核对。
- 每张并排图下写一行：这是哪一镜、对标原片哪一帧、我看到的差距（字体/阴影/间距/位置/色值）。
交给用户：6–10 张并排图（一次最多发 4 张，分批）+ 我自己看出的差距清单。
请用户确认：每张"像 / 不像 / 哪里不像"；哪几处优先修。
反馈后：按 collaboration.md 对照表改 timeline 或（若是组件级缺陷）记录为"工程问题"告诉用户，需要时可以直接改 src/（改完建议跑回归）；改完只重出被点名的那几张。

### 第 4 轮 低清整片预览
做：整片低清渲染，供看节奏和时间点（高 CRF、可半分辨率；首次渲染前告诉用户预计耗时，60s 约 4 分钟量级）：
```bash
cd <工程目录>
npx remotion render Main out/<slug>/preview_v1.mp4 --props='{"timelineSrc":"projects/<slug>/timeline.json"}' --crf=32 --scale=0.5 --codec=h264
```
（只改局部时先用 `--frames=a-b` 渲染区间。）预览若用占位素材/时间戳是估算的，必须告诉用户。
交给用户：preview_vN.mp4 + 我标出的 5–8 个"请重点看"的时间点（mm:ss）。
请用户确认：逐时间点反馈（格式："0:23 贴字晚了""1:05 录屏推太猛"）；整体节奏是否像原片。
反馈后：把每条反馈翻译成参数改动（对照表），改完说明"改了哪些镜头的哪个参数"，再出 v2（尽量只重渲受影响区间）。可多次循环。

### 第 5 轮 精修与终版渲染 + 自检
做：处理预览遗留项；时间戳升级为真实对齐（若第 0 轮用的是估算）；lint 15/15；终版渲染：
```bash
npx remotion render Main out/<slug>/final.mp4 --props='{"timelineSrc":"projects/<slug>/timeline.json"}' --crf=18 --codec=h264
```
再抽 5–8 帧核对（无红底 "P2 scene not implemented"、字幕不跳、贴字不早于口播、运镜不过猛、hostAudio 有声）。按下方"交付前自检清单"逐条写 ✓/✗/数值，不确定的列入"待用户确认"，整理成 templates/output-template.md 交付。
交给用户：final.mp4 + 自检表 + 与原片的最后一轮并排帧。用户不满意 → 回到对应轮次，不要硬交。

### 路径 A（剪映手工）
用户要在剪映里自己剪时，第 3–5 轮改为：按分镜写 references/jianying-guide.md 的逐项操作说明（字幕样式、关键帧推镜、圆形 PIP、动画时长、转场、音效、配乐），用户剪出一版后截图/导出片段交回，Claude 对照原片和 comfort-rules 手查后给修改意见。

## 两条执行路径对照
| 项 | 路径 A：剪映手工 | 路径 B：Remotion 自动 |
|---|---|---|
| 适合 | 不写代码、素材少、要快 | 要批量、要像素级一致、要自动检查 |
| 输入 | 数字人视频 + 分镜表 + 剪辑说明 | 数字人视频 + host.wav + 时间戳 + timeline.json |
| 字幕 | 识别字幕 → 一个样式批量套用，y≈0.90H | `subtitles[]`，box 46px，y 0.905H（stroke 56px，y 0.885H） |
| 推镜 | 缩放关键帧 100→112%，28 帧，缓入缓出 | `camera:[{kind:'push',dur:28,scale:[1,1.12],ease:'inOutCubic'}]` |
| PIP | 画中画 + 圆形蒙版，直径 0.14W，圆心 (0.08,0.85) | `pip:{preset:'bl_circle'}`，连续镜头自动合并 |
| 检查 | 手查（comfort-rules.md 的"手查"项） | lint 15 条 + 抽帧 |
| 局限 | 剪映菜单/数值需按版本确认；标注随推镜需复合片段 | 图表/成片全屏/片尾卡/毛笔字/音效未实现（有替代方案） |

## 最终交付格式（templates/output-template.md；各轮产物拼成）
0. 基本信息 1. 标题与封面 2. 口播稿 + 角色表 3. 数字人设置 4. 分镜表 5. 剪辑说明（5A 剪映 / 5B Remotion） 6. timeline 摘要 7. 自检 + 待确认项。协作过程示例见 examples/demo-script.md。

## 交付前自检清单
- [ ] 3 秒内出现钩子（问句/反差/承诺）且有第一次画面变化；开头没有寒暄、自我介绍、Logo
- [ ] 语速 4.5–5.5 字/秒（总字数 ÷ 时长）；每句 ≤20 字；字幕行 ≤14 字（8–10 最佳）
- [ ] 英文版：语速 2.2–2.6 词/秒；每句 ≤16 词；字幕 ≤7 词/38 字符；**全片抽帧无汉字**（english.md §4：timeline 静态 grep + `tools/ocr` 对抽帧 OCR，结果 NO_CJK）
- [ ] 每句都有 role 与 intent；论点在主播、证据在动效；证据不足已降级为关键词卡
- [ ] 切点落在句首（±3 帧）≥60%；2–3 句一个主画面；刀/分 12–20（数据型 ≤24）
- [ ] 镜头时长：主播 3–6s；B-roll 1.5–3s；卡片 1.5–4s；录屏 5–10s（中间有运镜/标注）
- [ ] 大景每 15–20s 回归；最长无脸段 ≤10s；punch-in ≤2/分；叠化 ≤2/分
- [ ] 贴字在关键词开始 −2~+4 帧出现、停留 ≥40 帧；同屏文字块 ≤4
- [ ] 动效时长落在 0/6/12（18）帧；运镜幅度 ≤1.12，只作用于内容层；静态素材全部慢推
- [ ] 字幕全片一种样式、位置不变；强调色 ≤3；只用两种底
- [ ] 没有原博主的原句、口头禅、口号、Logo、形象、标志性标题与片尾（forbidden.md）
- [ ] 内容是用户自己的主题与素材；示例数据已标"示例"；素材缺口已列出
- [ ] 路径 B：lint 15/15 PASS；抽帧无红底占位；hostAudio 已设置（否则无声）
- [ ] 终版：响度 -16 LUFS（人声+SFX，peak < -1 dBFS）；视频/音频时长一致（±0.05s）；OCR 每 1.5s 抽帧严格档零汉字；`assets.bgm` 未设置；成片已拷到桌面，大小与时长写进交付说明

## 禁区（详见 references/forbidden.md）
账号片尾卡与吉祥物、原博主的口号/问候/口头禅/固定标题与过场句、原博主形象与演播室（服装、霓虹房间、灯牌、书房沙发）、他们的 3D 卡通角色、国旗纹理角标、火焰转场、口播广告、综艺化梗（VHS、恶搞卡、梗图）、原片的素材与数据。可以沿用的只有视觉母题（黑底网格、荧光绿标签、圆角药丸、圆形 PIP 等），主色可换成自己的。

## 已知限制（如实告诉用户）
- **样本**：13 集（博主A 9、博主B 4），均为 540P、2 倍速录屏；<0.13s 的入场记为硬切；缓动/spring 多为估计；原片录屏无声，**配乐与音效全部是推测**。
- **Remotion 未实现（P2）**：图表（饼/条形/折线/气泡/3D 时间轴/翻牌）、clip_full 成片全屏、ClosingCard、BrushWord 毛笔字、TitleCard、Badge 章节角标、sticker_words/name_tag/checklist 贴字、换背景、主题切换（`meta.theme` 不被读取，PIP 紫环不随主题关闭）。用了会出红底占位或被静默忽略——替代方案见 remotion-pipeline.md §4。
- **没有语音转写/词级对齐工具**：本机未装 whisper 类工具，第 0 轮的词级时间戳目前只能用数字人工具的 SRT / 用户剪映识别字幕 / 字数估算（待搭建，见第 0 轮）。
- **没有自动 planner**：timeline 目前由 Claude 手写或用工程里的 builder（按字数均分时间）生成；接入真实数字人后需用真实词级时间戳重排（数字人工具未定，第 2 步流水线未验证）。中文强制对齐误差未验证。
- **字体差距**：窄体（ZCOOL QingKe HuangYou）偏重、数字（Barlow Condensed）偏宽；毛笔体需自查授权。字体经 google-fonts 在线加载。
- **剪映路径**：菜单名、字号数值、坐标正负号随版本变化，手册中标"需按版本确认"的需第一次实操核对。
- **lint 通过 ≠ 像他们**：lint 只保证不违反舒适规律；气质要靠 10–15s 主观 A/B 盲看。
- 数字人手势通常少于真人，用 punch-in 和夹头词补偿，效果需实测。
