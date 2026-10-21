# 用积木做片：宣传片（Promo）与口播片里的动效（fx overlay）

工程：`<工程目录>`（下面命令都在这个目录跑）。积木总表 `references/block-catalog.md`；工程侧权威说明 `src/motion/README.md`（与本文冲突时以代码和它为准）。口播片的整体流程（稿子、数字人、分镜、样张、预览轮）仍按 combo-style Skill 走，本文只讲「积木怎么接进去」。

## 1. 宣传片：`Promo` 合成 + PromoTimeline JSON
文件放 `public/projects/<slug>/promo.timeline.json`（lint 只认 `promo*.timeline.json`）。字段（`src/promo/types.ts`）：
```json
{ "version": "1",
  "meta": { "title": "…", "width": 1920, "height": 1080, "fps": 30, "durationInFrames": 600, "background": "#05060F", "lang": "en" },
  "clips": [
    { "id": "s1_title", "block": "Compose", "from": 0, "dur": 90, "track": 0,
      "props": { "items": [ { "kind": "fill", "background": "radial-gradient(…)" },
                            { "kind": "block", "block": "TitleReveal", "props": { "text": "AI-driven mine operations", "startFrame": 4 } } ] },
      "camera": [ { "frame": 0, "cx": 960, "cy": 540, "scale": 1 }, { "frame": 80, "cx": 960, "cy": 540, "scale": 1.08 } ] },
    { "id": "s2_map", "block": "Compose", "from": 90, "dur": 120, "transitionIn": { "type": "circle", "dur": 24 },
      "props": { "items": [ { "kind": "fill", "background": "#0C0D26" }, { "kind": "block", "block": "DotMap", "props": { "startFrame": 2 } } ] },
      "sfxAt": { "city_ping": 40 } }
  ],
  "sfx": [ { "at": 6, "type": "type_burst_a", "volume": 0.22 } ],
  "voiceover": { "src": "projects/<slug>/vo.wav", "volume": 1, "from": 0 },
  "subtitles": [ { "id": "sub1", "text": "Every site, one live view", "from": 96, "to": 200 } ] }
```
- 帧号 @30；props 里的帧（`startFrame` 等）相对 clip 自己的起点；像素是本时间线画布的像素。
- `track` 大的在上；同一轨道上 clip 不重叠。转场写在**后一个** clip 的 `transitionIn {type: circle|ribbon|pixelate|glitch|cut, dur, props, sfx}`：前一个 clip 必须正好在 `from` 结束，转场占后一个 clip 的前 `dur` 帧（默认 24/22/15/14）。参与转场的 clip 要不透明（`Compose` 第一项放 `fill`）。
- `camera`：`{frame, cx, cy, scale, ease?}`，ease 默认推近曲线 (0.25,0,0.15,1)，`'hold'` = 跳。`cameraDrift: 0.02` = 整段线性微推 2%。**一个镜头只用一个相机**：有 `clip.camera` 就别在里面再放 WorldCamera/PushIn/ScrollCamera（lint 会 FAIL）。
- 一个 clip 想放几个积木 → `Compose`；嵌套积木用 `{kind:'block', block, props, at, x, y}`（`at` = 相对 clip 的起始帧）。
- 不做 BGM：`bgm` 字段留空（用户自己在剪映加）。
- 范例：`public/projects/promo-demo/promo.timeline.json`（横屏 20s，6 镜 + 4 种转场）、`promo.portrait.timeline.json`（竖屏 18s，带字幕）。

```bash
npm run lint:promo                      # 查所有 public/projects/**/promo*.timeline.json：积木存在、层允许、无汉字、sfx 文件存在、相机规则、sfxAt 事件名
node scripts/promo_stills.mjs projects/<slug>/promo.timeline.json out/<slug> key 24,75,105     # 关键帧 PNG（打包一次）
npx remotion render Promo out/<slug>/preview.mp4 --props='{"timelineSrc":"projects/<slug>/promo.timeline.json"}' --crf=28 --scale=0.5 --gl=angle   # 低清预览
npx remotion render Promo out/<slug>/promo.mp4  --props='{"timelineSrc":"projects/<slug>/promo.timeline.json"}' --crf=23 --codec=h264 --gl=angle  # 成片
```
宣传片一律带 `--gl=angle`（用到 GlassCapsule / TumbleObject 时必须；不用时也无害）。

## 2. 口播片：overlay kind `fx`
在口播 timeline（`Main` 合成）的 `overlays[]` 里加：
```json
{ "id": "fx_ring", "kind": "fx", "block": "ProgressRing", "from": 171, "dur": 60, "layer": "fixed",
  "enter": { "preset": "cut" }, "exit": { "preset": "cut" },
  "props": { "x": 1650, "y": 300, "diameter": 220, "stroke": 18, "to": 72, "fontSize": 56 },
  "sfxAt": { "done": 58 } }
```
- `from` 是绝对帧（贴字规则同 combo-style：在关键词开始 −2~+4 帧出现，时间来自词级对齐，不估算）。`enter/exit` 必填但被忽略（积木自己管进出）。
- `layer`：`fixed` = 不跟场景镜头（主播 PIP/字幕那一层，背景必须透明）；`content` = 跟着镜头推拉，**不能跨场景切点**；整屏不透明的积木（只标 promo 的）不能进口播片。
- 位置用像素（1920×1080），要避开字幕带（y 0.86–0.93H）和主播脸，参照 combo-style 的禁入区。
- 范例：`public/projects/promo-demo/fx_demo.timeline.json`（示例项目 口播片上叠了一个 ProgressRing）。
- `npm run lint:timeline -- public/projects/<slug>/timeline.json` 会查：积木存在、层允许、无汉字、sfx 文件存在、content 层 fx 不跨切点、一个镜头一个相机、未知 overlay kind = FAIL；用到 GL 积木会多一行提示。

## 3. 音效接入
- 默认：每个积木的 SFX 来自 `public/sfx/block_sfx_map.json`（格式 `{积木: {events: {事件: {sfx:[变体], offsetFrames, volume, tier}}}}`，由 `scripts/make_block_sfx_map.py` 生成；规则与音量档在 `scripts/sfx_rules.md` §7）。
- 默认只响两类事件：第一个「开始」事件（在 `props.startFrame` 处）和所有「结束」事件（在 `dur-1`）。中间事件（点击、通知、节点亮…）默认静音，要响就写 `sfxAt: {"事件名": 相对帧}`。每个积木有哪些事件见 `block-catalog.md` 的 SFX 行。
- 覆盖：`sfx: false`（静音）/ `"音效名"`（起点放一个）/ `[{t, type, vol}]`（完全自定）。`Compose` 会把里面每个积木的默认事件按 `at` 平移后合起来。
- 原则：音效贴画面操作帧（principles.md 第 9 节），轻、短；口播片里还要服从人声优先（关键词起点 0.3s 内不放 main/hero 档，限幅规则见 `scripts/sfx_rules.md` §5）。改了 map 要重新打包才生效。

## 4. 字幕：必须逐词对齐 + 过同步闸门
有配音（口播或宣传片 voiceover）就必须：
```bash
python3 scripts/align_words.py <配音.wav> --script <稿子.txt> --out projects/<slug>/words.json    # mlx-whisper 词级时间，稿子拼写为准
#  → 字幕块的 from/to 取块内首词起点 / 末词终点（帧 @30），写进 timeline.subtitles
python3 scripts/check_sub_sync.py --timeline public/projects/<slug>/<timeline>.json --voice-only public/projects/<slug>/host.wav --report out/<slug>/SYNC_REPORT.md   # 纯人声轨（不含音效）
#  闸门 G5.5：起点偏差 ≤3 帧、终点 ≤6 帧，否则 FAIL（exit 1）；**用纯人声轨（`--voice-only`，项目里的 host.wav / host_full.wav）做独立识别**，不要拿生成字幕用的 words.json 自己验自己；混音轨（含音效）只作参考。纯人声默认加 `--split-pauses`（有真实静音才切得准），`--no-split-pauses` 看原始 whisper 偏差。S3 实测（38 条）：纯人声+split 起点均值 +0.27 帧（2/38 超限），纯人声原始 +8.9 帧（27/38），成片混音原始 +7.7 帧（24/38）——偏差主要是 whisper 停顿后起点提前，不是音效；详见 out/showcase/S3_NOTES.md
```
**中文配音（用户的视频是中文版；2026-10-19 起）**：
```bash
ffmpeg -i voice.mp3 -ac 1 -ar 16000 public/projects/<slug>/host.wav                     # Fish Audio 给的 mp3 → 16k 单声道 wav（ffmpeg 往返零偏移）
python3 scripts/align_words.py public/projects/<slug>/host.wav --lang zh --script 稿子.txt --out public/projects/<slug>/words.json
#  多语种模型（默认 turbo-q4，464 MB，60 秒约 12 秒、峰值约 2.4 GB；--model multi-small 更快）；一字一词，英文缩写/数字整体一词，标点在 punct 字段；停顿切分默认开；缩写逐字母读时加 --auto-abbr 或放 pron.json（见下）
python3 scripts/build_subtitles_from_words.py public/projects/<slug>/words.json --timeline public/projects/<slug>/<timeline>.json --inplace   # 自动走中文规则：≤14 字、按标点/词边界断、≥0.6 秒、不重叠
python3 scripts/check_sub_sync.py --timeline public/projects/<slug>/<timeline>.json --voice-only public/projects/<slug>/host.wav --report out/<slug>/SYNC_REPORT.md   # 字幕有汉字自动走中文
```
- **英文缩写（RAG/LLM/API/GPU…）**：Fish Audio 稿子里写成「大写字母 + 空格」`R A G`、`L L M`（建议；逐字母读最稳，字母间不要加标点）。对齐命令加 `--auto-abbr`（自动把 `R A G` / `R-A-G` / `R·A·G` 还原为 `RAG`），或在稿子/音频同目录放 `pron.json`：`{"RAG":"R A G","LLM":"L L M","API":"A P I"}`（稿子里直接写 `RAG` 也行，按 pron 展开对齐；优先于自动规则，`--no-pron` 忽略）。words.json 里缩写是**一个词**（`text:"RAG"`，字母级时间在 `meta.letters`），字幕直接显示 `RAG` 计 3 字、不拆开；闸门不用改。没有缩写的稿子输出不变。
- 先看对齐输出的匹配率和 `meta.interpolated` / `meta.gapFills`：插值字多的段要核对。
- 8GB：一次只跑一个识别进程；别用 large-v3 fp16。合成语音实测、模型对比和已知问题：`<工程目录>/out/zh-sync/SYNC_REPORT_ZH.md`。闸门 FAIL 照实写（中文无稿识别在不停顿的顿号/无标点句界会错 5–10 帧），对最差清单再核对，不放宽阈值。**还没在真实 Fish Audio 配音上跑过**，第一条要复测。
- 细节、噪声底（识别器自身约 1.5–2 帧平均误差）与 `--allow-frac` 用法见 combo-style `references/subtitle-sync.md`。
- 宣传片：`PromoTimeline.subtitles` 字段形状与口播片相同（id/text/from/to），`check_sub_sync.py` 能直接读；但两点要注意：Promo 播放器里 `to` 是不含的（`f < to`），闸门按含 `to` 算，终点会差 1 帧（在 6 帧容差内）；用渲染出的预览音轨时不需要偏移；若直接拿原始配音 wav 检查而 `voiceover.from = N`，加 `--audio-offset N`。**这条宣传片字幕链路还没在真实配音上跑过**，第一次用时要看一遍报告。
- 英文片画面零汉字：lint 查文本；成片按 combo-style `references/english.md` §4 做 OCR 抽检。

## 5. 回归（改了共享文件之后）
改 `src/types.ts`、`src/Player.tsx`、`src/SceneRenderer.tsx`、lint、`src/Root.tsx` 这类共享文件后，必须证明已交付的 示例项目 口播片没变：
```bash
~/.claude/skills/ae-motion-craft/scripts/regress_md5.sh <工程目录> projects/bee-level8/full.timeline.json \
    <工程目录>/out/regress4.md5 <工程目录>/out/regress_now
```
- 8 帧（60,130,900,1500,2200,3000,3700,4400）md5 逐张比；基线 `out/regress4.md5` 对应 `full.timeline.json`（2026-10-19 实测 8/8 相同，约 3 分钟）。
- **不加 `--gl=angle`**：基线是默认 GL 渲的，换 GL 像素会变，md5 不可比。
- 有不同先用 `side_by_side.sh` 并排看再下结论（用错时间线也会「不同」：拿 v6.timeline.json 跑有 4 张不同，是内容不同不是回归）。
- 再跑 `npm run lint:timeline -- public/projects/bee-level8/full.timeline.json` 和 `npm run lint:promo`，以及 `npx tsc --noEmit`。

## 6. 竖屏（1080×1920）
- 积木默认值按 1920×1080 写（坐标、字号都是横屏像素），竖屏要逐个手调 props；`TitleReveal.fitWidth` 跟画布宽走，其它积木用像素或 `useVideoConfig`。`camera` 的数学以画布尺寸为中心，竖屏可用。
- `SplitScreenVertical` 是专门的竖屏三分屏（实测比例 0.338/0.320/0.342）。
- 范例 `promo.portrait.timeline.json`；关键帧 `out/promo/key_portrait_*.png`。出图先看是否有元素出画或压字幕。

## 缩写约定（用户 2026-10-20 确认）
- 旁白里英文缩写（RAG、LLM、API、GPU、MCP…）一律逐字母读，字幕与画面直接显示缩写本身。
- Fish Audio 配音稿：缩写写成空格分隔的大写字母（`R A G`、`L L M`），字母之间不加标点；对齐时手动加 `--auto-abbr`（保持手动，不设默认，避免把“A B 两个方案”误并成 AB）；夹数字的（5G、GPT-4）用 `pron.json`。
- 拿到真实配音后复测：若 Fish 把缩写读成整词，字母级时间会不准，词级时间与字幕显示不受影响。
