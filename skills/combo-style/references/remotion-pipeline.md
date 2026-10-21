# 路径 B：Remotion 自动路径（timeline.json → lint → 渲染 → 对照）

> 工程：`<工程目录>/`（remotion 4.0.531 / react 19 / TS 7；**不在云盘**）。**`src/` 只读**，发现 bug 记下来，不要改。
> 契约事实来源：`src/types.ts`（数据契约）、`src/tokens.ts`（参数）、`src/Root.tsx`（composition）、`src/lint.ts`、`src/components/**`。本文件基于它们写成；如与工程当前代码冲突，以代码为准。

## 1. 数据流与目录

```
选题 + 素材 → Claude 写 script.json（口播句子 + role/intent/marks）
   → 数字人工具：host_full.mp4 + host.wav + 字/词级时间戳（words.json）
   → 生成 timeline.json（scenes / overlays / subtitles / chapters / sentences）
   → npm run lint:timeline（15 条，必须全过）
   → npx remotion render Main …（读 timeline）
   → out/*.mp4 → 对照验证
```

放哪里（都在 `<工程目录>/public/` 下，**路径写相对 public/、不要前导斜杠**）：

| 文件 | 位置 | timeline 里的字段 |
|---|---|---|
| timeline | `public/timeline/<name>.timeline.json`（任意文件名） | 渲染命令的 `timelineSrc` |
| 数字人大景 | `public/host/<slug>/host_full.mp4` | `assets.hostVideo = "host/<slug>/host_full.mp4"` |
| 数字人 PIP 代理（480p，可选） | `public/host/<slug>/host_pip_480.mp4` | `assets.hostPipVideo`（省略则 PIP 也用 hostVideo） |
| 数字人音频 | `public/host/<slug>/host.wav` | `assets.hostAudio`（**省略则成片无声**） |
| 配乐（可选） | `public/audio/bgm.mp3` | `assets.bgm = {src, volume: 0.12}` |
| 录屏/图/B-roll/Logo/抠像 | `public/assets/<slug>/…` | `assets.files = {素材id: 路径}`，scene.props 里引用 id |

占位素材（测试用）：`public/placeholder/`（host_full.mp4 60s、host_full_2m.mp4 120s、host*.wav、screen_*.mp4、broll_1–6.jpg、logo*.png、cutout.png、news_1–4.png、clip_orig/clip_ai.mp4、screen_phone.mp4）。

## 2. 命令（都在工程根目录执行）

```bash
cd <工程目录>

# lint（会先 tsc 编译 src/lint.ts → .lintbuild/，再跑；可同时传多个文件）
npm run lint:timeline -- public/timeline/<name>.timeline.json

# 完整渲染（h264, crf 23）
npx remotion render Main out/<name>.mp4 \
  --props='{"timelineSrc":"timeline/<name>.timeline.json"}' --crf=23 --codec=h264

# 低成本验证：只渲前 61 帧（约 13 秒，含打包）
npx remotion render Main out/<name>_0-60.mp4 \
  --props='{"timelineSrc":"timeline/<name>.timeline.json"}' --frames=0-60 --crf=28 --codec=h264

# 单帧截图
npx remotion still Main out/<name>_f1130.png \
  --props='{"timelineSrc":"timeline/<name>.timeline.json"}' --frame=1130

# 预览/调参（浏览器）：在 Props 里把 timelineSrc 改成你的文件
npm run studio

# 组件单测帧（T-* composition，见 §8）；多帧批量截图
npx remotion still T-ChapterCard out/ChapterCard.png --frame=30
node scripts/stills.mjs out/stills T-KeywordCard-grid:0,6,12,40
```
- Composition id 固定为 **`Main`**（1920×1080、30fps、时长由 `calculateMetadata` 读 `timeline.meta.durationInFrames`）。`timelineSrc` 是相对 `public/` 的路径，默认 `timeline/example.timeline.json`。
- 渲染耗时参考：60s 约 4 分钟，2 分钟样片约 8 分钟量级（估计，视 CPU；PROGRESS 记 60s 示例 3 分 44 秒）；同屏最多 2 个 OffthreadVideo（大景 + PIP）。
- 产出：`out/`（被 .gitignore 忽略）。`npm run render:example` / `render:sampleA` / `render:sampleB` 是现成的三条渲染脚本。
- 已验证可渲染的真实例子：`public/timeline/example.timeline.json`（60s，模板 A，14 镜头）、`sample_A_2min.timeline.json`（27 镜头）、`sample_B_2min.timeline.json`（31 镜头）、本 Skill 的 `templates/timeline.example.json`——**组件渲染样例（占位素材）**，90s、20 镜头，副本为 `public/timeline/skill_example.json`，只用于看组件效果和复制 JSON 结构，不是示例选题（其中 JSON 片段里的文字也只是占位）。
- **真实项目的文件位置**用 SKILL.md「每个视频项目的目录约定」：timeline 与处理后素材放 `public/projects/<slug>/`，`timelineSrc = "projects/<slug>/timeline.json"`；下表的 `host/<slug>/`、`assets/<slug>/` 是旧写法，二者都能用，新项目统一用 `projects/<slug>/`。关键帧样张用 `scripts/stills_timeline.mjs`（见 SKILL.md 第 3 轮）。

## 3. timeline.json 字段说明（基于 `src/types.ts`）

顶层：
```jsonc
{
  "version": "1",
  "meta": { "title": "…", "fps": 30, "width": 1920, "height": 1080,
            "durationInFrames": 2700,          // = 最后一个 scene 的 from+dur
            "template": "A_tool_review",       // A_tool_review | B_opinion | C_data_event
            "theme": "qiuzhi_dark" },          // qiuzhi_dark | xiaolin_data（仅标签，渲染器不读）
  "assets": { "hostVideo": "…", "hostPipVideo": "…", "hostAudio": "…",
              "bgm": {"src": "…", "volume": 0.12}, "files": { "素材id": "路径" } },
  "sentences": [ {"id":"s01","start":0,"end":78,
                  "words":[{"text":"四十分钟","start":39,"end":66,"confidence":1}]} ],
  "subtitles": [ {"id":"sub_s01_1","from":0,"to":77,"text":"开会十分钟 整理纪要四十分钟？","sentenceId":"s01",
                  "style":"box|stroke(可省)","hidden":false} ],
  "chapters": [ {"id":"ch1","index":1,"title":"转成文字","label":"STEP 1","from":996,"to":1646,
                 "cardSceneId":"sc08","hud":{"stack":["转成文字","整理纪要"],"hideInSceneIds":[]}} ],
  "scenes": [ … ], "overlays": [ … ], "sfx": [ {"at":120,"type":"pop|whoosh|ding|tick","volume":0.3} ]
}
```
- 时间全是**帧**（30fps），坐标全是**画布比例**（0..1）。
- `sentences[].words[].text` 是 `atWord.word` / overlay trigger 查找的依据（精确匹配或包含）；找不到词时退回到句首。词必须是句子文本的子串。
- `subtitles`：整句硬切，`from` = 句首，`to` = 句尾 −1（含）；≤14 字（不含标点）；句中停顿用空格；相邻不重叠。
- `sfx`：类型已定义；当前 Player **没有播放 sfx**（只播 hostAudio 与 bgm）→ 音效要在剪映/ffmpeg 里后加，或先忽略。

### Scene（主画面，互斥，首尾相接，铺满 0..duration）
公共字段：`id, from, dur, sentenceIds[], pip, camera[]?, transitionIn?, rhythm?, note?, kind, props`。
- `from` = 首句 start ±3 帧；`pip` = `"off"` 或 `{preset, diameter?, center?, shout?}`；
- `pip.preset` ∈ `bl_circle | bl_circle_big | br_circle_small | left_vertical | br_rect | right_rect_big`（几何见 visual-mapping.md §2.4）；连续 on 的镜头自动合并为一层，预设间 spring(damping 20) 过渡。
- `transitionIn`：`{type:'cut'}` | `{type:'dissolve',dur:12}` | `{type:'dip_dark',dur}` | `{type:'blur_through',dur}` | `{type:'fade_from_black',dur}`；dissolve 作用在**后一个** scene 上。
- `camera[]`（CameraMove）：`{kind: push|pull|pan|punch|kenburns|rush_in|tilt3d, at(相对 scene 起点帧), dur, scale:[起,止], translate:[dx,dy], origin:[x,y], ease, hold}`；`ease` ∈ `linear|outCubic|inOutCubic|inOutQuad|outExp|inOutSine|outBack|{spring:{damping,stiffness?,mass?}}`。
- 未写 camera 时：`host_punch` 自动补一个 punch（at 6, 20 帧, 1→1.08）；`broll` 自动一推一拉交替（线性）。

### Overlay（叠加层，可跨 scene）
公共字段：`id, from(绝对帧), dur(≥40), layer: "fixed"|"content", enter:{preset:'cut|fast|std|slow', fx?}, exit:{preset:'cut|fast'}, trigger?:{sentenceId, word, offsetFrames(−2~+4)}, accent?`。
- `enter.fx` ∈ `none|pop|blur_in|slide_up|slide_left|typewriter|wipe_lr|scale_in_blur|glow_in|spring_pop`（preset 决定帧数 0/6/12/18）。
- 已渲染的 kind：`head_flank`（fixed）、`keyword`（fixed）、`pill`（fixed）、`callout`（content）、`spotlight`（content）。
- **会被渲染器静默忽略**的 kind：`sticker_words`、`badge`、`name_tag`、`checklist`（类型里有，组件没做）。
- `layer:"content"` 的 `box` 相对该 scene 的内容盒（screen_demo 为 panel，其余为整画布）；必须在该 scene 内开始、不跨 scene；推拉时跟着界面走。`layer:"fixed"` 相对整画布。

## 4. 已实现组件与 props 速查（scene.kind → props）

| kind | props（必填 / 常用） | 要点 |
|---|---|---|
| `host_full` / `host_punch` / `host_tag` | `{background:"baked", objectPosition?}` | host_tag = 大景 + 贴字（贴字走 overlays）；`host_punch` 自动 punch |
| `screen_demo` | `{src(文件id), kind:"video"|"image", startFrom?, panel?:Box, panelRadiusPx?, dim?}` | panel 默认 x .12 y .015 w .85 h .855；>5s 必须写 camera |
| `broll` | `{src, kind, dim(0.2–0.45), widescreen?, grayscale?}` | 线性慢推；widescreen 上下 13% 黑边 |
| `keyword_card` | `{variant:"grid|on_broll|ghost_word", lines:[{text, accent?, size?:"xl|l|m"}], en?, bg?(素材id), ghostText?, enter:{preset,fx?}}` | 文字在固定层，不随运镜；on_broll 需要 bg |
| `chapter_card` | `{label?:"STEP 1", title, en?, ghostText?}` | 配合 `chapters[]`；前面接 2–4s 主播 |
| `brand_card` | `{logo(素材id), name, tagline?, variant:"white_card|dark", toCornerAt?}` | 默认配 pip 开 |
| `compare` | `{variant:"pills_vs|result_pair|three_col", left:{label,color?,items[],media?,atWord?,itemWords?[]}, right:{…}, middle?:{…}, conclusion?:{text,atWord?}, listAtWord?}` | pills_vs 用 items 与 listAtWord；result_pair 用 media |
| `step_list` | `{steps:[{no,title,thumb?,atWord?}], activeIndex}` | 1–3 张布局已校准，更多张按 pitch 外推 |
| `big_number` | `{variant?:"center|gold_card", items:[{value,unit?,prefix?,sup?,label,en?,footer?,sub?,atWord?}], bg?, frames?[], recapAtWord?, countUp?}` | 数字 1 帧硬切；gold_card 需 frames |
| `question_card` | `{title, body, ghostText?, typeFrom?, framesPerChar?(默认5)}` | 数字自动染黄 |
| `summary_card` | `{variant?:"single|double|quote", title?, items:[{no,text,atWord?}], right?:{title,items[]}, quote?:{text,highlight?[],author?}}` | 说到哪条点亮哪条 |
| `phone_mockup` | `{src(竖屏录屏), hostSide?, bullets?:[{text,atWord?}], tag?}` | 与 `pip:{preset:"left_vertical"}` 搭配 |
| `news_collage` | `{items:[{src, rotateDeg?, atWord?}]}` | 旧卡叠成堆 |
| `image_cards` | `{items:[{label,src,atWord?}], bg?}` | 三图卡，每词一张 |
| `pill_stack` | `{variant?:"gray|color", items:[{text,icon?,color?,atWord?}], side?}` | |
| `cutout_name` | `{src(透明PNG), name, en?, bg?}` | 打字机 2 帧/字 |

`atWord = {sentenceId, word}`：触发帧 = 该词 start + 2 − scene.from；缺省时在 scene 内等分。

### 未实现（P2），遇到要用替代方案
| 想要 | 状态 | 替代方案 |
|---|---|---|
| `chart`（饼/条形竞价/折线/气泡/3D 时间轴/翻牌） | scene.kind 在类型里有，**渲染出红底占位 "P2 scene not implemented"** | ① 外部做好图（Keynote/Figma/Flourish 导出 PNG 或短录屏）→ `screen_demo`（kind image/video）+ camera 线性慢推 + `callout` 标注；② 或降级 `big_number`/`step_list`/`summary_card` |
| `clip_full`（成片全屏、撤字幕） | **未实现，同样出红底占位** | `screen_demo`：`panel:{x:0,y:0,w:1,h:1}`、`panelRadiusPx:0`、`pip:"off"`，该段 `subtitles[].hidden:true` |
| `closing`（片尾账号卡）/ ClosingCard | 未实现；且属于禁区 | `host_tag` + `head_flank` 一句行动；不要账号卡 |
| BrushWord 毛笔大字 | 未实现 | `broll(widescreen)` + `keyword` overlay；或 `keyword_card(ghost_word)` |
| Timeline3D / TimelineBar / RankFlip / MapSpot / TitleCard / Badge | 未实现 | 时间线用 `step_list`（≤4 步）；盘点用 `compare(three_col)`；章节角标用 HUD |
| `sticker_words`、`badge`、`name_tag`、`checklist` overlay | 被忽略 | 用 `head_flank` / `keyword` / `pill` 代替；清单用 `step_list` |
| CircleMaskHost、DiagonalSplit、TimeTunnel | 未实现 | 不做 |
| `sfx` 播放、换背景（HostProps.background）、`theme` 切换 | 字段存在但渲染器不读 | 音效后期加；背景烧入视频；博主B 主题用零件拼（packaging.md §6） |

## 5. 怎么写一份 timeline（一步步）

1. 从 script.json 的句子出发，得到每句 `start/end`（帧）和关键词 `words[]`（真实时间戳见 digital-human.md §9；没有时用字数比例估算，confidence 0.5）。
2. 把相邻句分组成 beat（2–3 句、4–7s），每个 beat → 一个 scene：`from = 首句 start`（第一个 scene 的 from = 0），`dur` 铺到下一个 beat 的 from，最后一个铺到 `durationInFrames`。
3. 每个 scene 选 kind、写 props（§4）、定 pip（证据段开，概念/情绪/章节/总结关）。
4. 每个 level-2 mark → overlay：`from = word.start + 2`，`trigger.offsetFrames = 2`，`dur` ≥ 40（或停到 scene 末）。
5. screen_demo：每 3–5s 一个 camera（push/pull/pan），push 的 `at` = 目标词 start − 8 − scene.from。
6. 字幕：按句拆成 ≤14 字的行，`from/to` 落在句内，句中停顿换空格。
7. 章节：每个演示单元一个 chapter（`from` = 章节卡 scene.from，`to` = 下一章节卡 from 或末尾），`hud.stack` 列出全部步骤名。
8. 跑 lint → 不过按 hint 局部回退（拆 beat、插主播、开 PIP、加 camera）。
9. **可复用的生成器**：`<工程目录>/scripts/make_sample_timelines.py` 的 `build(spec)` 把"beat 列表 + 句子 + 关键词"机械地转成上述 JSON（按字数均分时间）。本 Skill 的 `templates/build_demo_timeline.py` 是用它做 90s 示例的写法，可照抄。**注意**：它用均匀字数估时间，真实数字人时间戳需要自己替换 sentences 的 start/end/words 后重算 scenes/subtitles/overlays（目前没有现成 planner，这是已知缺口）。

## 6. 数字人视频怎么接入

- `Host` 组件读 `timeline.assets.hostVideo`（相对 public/）：`<OffthreadVideo muted trimBefore={scene.from}>`，即**视频时间 = 整条时间线的绝对帧**，所以数字人视频必须是**一条**从 0 开始、长度 ≥ `durationInFrames` 的连续口播；不能每个镜头换一个文件。
- PIP 读 `assets.hostPipVideo`（缺省用 hostVideo），同样 `trimBefore = 合并后 PIP 段起点`，所以 PIP 里的口型与大景一致。
- 所有视频 `muted`；**全片声音只来自 `assets.hostAudio`**（再加可选 bgm）。忘了 hostAudio = 无声成片。
- 构图假设：脸 cx .48 / cy .38 / 脸高 .30H（PIP 靠它锚定脸；夹头词靠它留白）。构图差很多就要调 `objectPosition` 或重生成。
- 视频需 30fps 恒定、h264、1920×1080；变帧率会导致口型漂移。转码命令见 digital-human.md §8。
- 视频对 Remotion 的有效路径是 `staticFile`：必须放在 `public/` 下（云盘路径、绝对路径不行）；工程在本机 `~/Projects/`，不要把大视频放进云盘目录。

## 7. 15 条 lint（`src/lint.ts`）
见 comfort-rules.md 末尾的"lint 15 条一览"。要点：scenes 铺满且首尾相接；切点在句首 ±3 帧 ≥55%；刀/分 12–20；无脸段 ≤10s；大景间隔 ≤22s、单段 2.8–8s；10s 零切点窗口 ≤10%；punch ≤2/分；字幕 ≤14 字、不重叠；贴字偏移 −2~+4、停留 ≥40 帧、content 标注不跨镜头；运镜时长/幅度在范围；>5s 的录屏/素材有运镜。
lint 全 PASS 才进渲染；"切点落在句首 100%"只说明 timeline 按句首生成，成片要另做实测。

## 8. 对照验证（组件与成片）
- 组件级：每个组件有测试 composition `T-<Name>`（如 `T-KeywordCard-grid`、`T-HeadFlankWords`、`T-ChapterCard`、`T-HudTag`、`T-ScreenDemo`、`T-CalloutBox`、`T-BrollKenBurns`、`T-Transitions`、`T-HostPip-rect`、`T-StepList`、`T-CompareCard-pills`、`T-BigNumber-gold`、`T-SummaryCard-double`、`T-QuestionCard`、`T-PhoneMockup`、`T-BrandCard`、`T-ImageCards3`、`T-PillStack`、`T-NewsCollage`、`T-CutoutNameTag`、`T-SpotlightFocus`、`T-SubtitleBar`、`T-GridBackground`…，完整列表见 `src/tests/`）；`npx remotion still T-xxx out/x.png --frame=N` 出帧，与原片证据帧（`combo/*/evidence`、`ev` 等，ffmpeg hstack 拼图）并排；已有对照图在 `<工程目录>/compare/`。
- 验收：位置偏差 ≤±2%；取样色 ΔE ≤10 或 HEX 偏差 ≤8；入场帧数档位一致（0/6/12 ±2）；运镜缩放曲线拟合 RMSE <0.08。
- 成片级：lint + 实测（`analysis_comfort/scripts/` 同口径：切点换句、字幕 y、人脸可见、运镜、关键词同步），通过线见 comfort-rules.md；再做 10–15s 主观 A/B 盲看，重点盯字幕是否跳动、贴字是否早于口播、运镜是否过猛。
- 渲染后**必抽查**：抽 5–8 帧 still（开头、章节卡、录屏推近、PIP、大数字、总结卡、结尾），确认没有红底 "P2 scene not implemented"。

## 9. 常见坑
1. **composition id 不能有下划线**（只允许字母、数字、连字符，Remotion 规则）：主 composition 固定 `Main`，测试用 `T-Name`；**timeline 文件名可以有下划线**（它只是 props 路径）。
2. `timelineSrc` 写相对 public/ 的路径（`timeline/x.json`），不要写 `public/timeline/x.json`；props 要用单引号包 JSON。
3. scenes 必须首尾相接、从 0 开始、铺满到 durationInFrames，否则 lint 第 1 条失败且会出现黑帧。
4. 用了 `chart` / `clip_full` / `closing` → 红底占位帧；先用 §4 替代方案。
5. overlay `kind` 为 sticker_words/badge/name_tag/checklist 会被静默丢弃，看不到也不报错。
6. content 层 overlay 的 `from` 必须落在所属 scene 的区间内且不跨出 scene；callout 的 box 是相对 panel 的比例。
7. fixed 层贴字不随运镜；想跟着界面走必须是 `layer:"content"`。
8. `atWord.word` 必须在 `sentences[].words[].text` 里找得到，否则退回句首；词表要写全。
9. 夹头词：左词右对齐 x .305、右词左对齐 x .667，长词自动缩小，最长约 5–6 字；太长会换行变形，控制在 ≤5 字。
10. 数字人视频不是 30fps 恒定 / 长度不够 → 口型漂移或末尾黑屏。
11. 忘 `hostAudio` → 无声；`sfx` 字段不会被播放。
12. 字体经 `@remotion/google-fonts` 在线加载（首次渲染需要联网，离线是否可行未验证）；窄体/数字字体与原片字形略有差异（已知差距）。
13. PIP 圆形默认带紫环（博主A）；博主B 无环的主题切换未实现。
14. 同屏 blur / 3D 较慢；PIP 用 480p 代理；运镜中不要同时改 filter。
15. 章节卡 `ghostText` 字号固定 0.6H、不自动缩放：拉丁字母 ≥6 个会溢出画面被裁（如 PROMPT→"ROMP"），控制在 ≤4–5 个字母或 2 个汉字。
16. 不要改 `src/`；发现 bug 记入交付说明。工程未 git 提交（用户未要求），不要擅自 commit。
