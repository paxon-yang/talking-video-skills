# 素材提示词包：用户用 Gemini 生成全部视频/图片素材（S2.5）

> 何时读：分镜/口播稿确认之后、动手搭 timeline 之前；以及用户反馈"素材不对"需要重新出提示词时。
> 决定（2026-10-18，用户）："图片都是到网页找的，有些不符合……以后视频素材、图片素材我都用 Gemini 生成，你给我所有提示词；小短视频要告诉我几秒，具体点，风格明确。"
> 所以：**从现在起，B-roll 与静图一律由用户用 Gemini（视频 = Veo，图片 = Nano Banana / Imagen 类）生成，Claude 负责写每一条提示词、定时长、入库质检、改错重出。** Pexels 等素材站只作兜底（用户明确说"这条先用库存"时才用，仍要记 LICENSES.md）。图标是矢量（src/components/icons），**不需要生成**。
> 工具：`scripts/make_prompt_pack.py`（出提示词包）、`scripts/ingest_gen_assets.py`（入库质检）。示例项目 示例：`projects/bee-level8/gen_plan/`（38 条）。

## 1. 流程位置与闸门（S2.5）
`分镜/口播稿 gate 通过 → [S2.5-a Claude 写镜头清单 shotlist.json + style_bible.md → 出 prompt_pack.md/html] → [S2.5-b 用户在 Gemini 生成，存进 projects/<slug>/gen/] → [S2.5-c Claude 入库质检 → gen30/ + 报告] → 闸门 G2.5 → S6 timeline`
| 步骤 | Owner | 内容 |
|---|---|---|
| a | C | 从分镜逐句列出所有需要的视频/图片素材（每条一个 id），写 style bible，跑 make_prompt_pack |
| b | U | 打开 prompt_pack.html，点 COPY，贴进 Gemini，每条出 2–3 个变体、选一个，按文件名存 |
| c | C | 跑 ingest_gen_assets，看联系表 + OCR，必要时给"重出提示词" |
| **G2.5** | U | 看联系表/预览：哪些要重出、哪些可降级（用库存或改成卡片）。**全部通过或明确降级后才搭 timeline** |
时间线预估：先交一小批（5–8 条最关键镜头）让用户试一次，确认风格对再出全套——风格不对重出全套代价大。

## 2. STYLE BIBLE（每条视频写一次，前置到每条提示词）
Claude 为每条视频写**一段固定文字**（`projects/<slug>/gen_plan/style_bible.md` 的 `## STYLE`），脚本把它原样放在每条提示词最前面。必须包含：
1. **影像质感**：cinematic, photorealistic documentary footage；相机/镜头语言（full-frame cinema camera，35/50mm 定焦，航拍 24mm），轻微胶片颗粒，无 CGI/卡通/插画感。
2. **调色**：与本片 `hostLook` / `brollLook` 对齐——示例项目 是冷蓝暗调：深海军蓝阴影 #0b1626、钢蓝中间调 #2a5cc8（低强度）、冷灰白高光 #dfe8f5，**只在真实光源处**给一个暖色点缀（琥珀 #e8a33d：日落/钠灯/台灯）。略低调曝光、中等对比、轻暗角。**写 hex 是给 Gemini 的色彩倾向，不是精确调色**；最终色靠 `meta.brollLook` 后期统一（生成素材通常更干净更亮，brollLook 的 dim/饱和度要重新对）。
3. **光线**：软自然光/低调实用光，禁止平光明亮的图库感。
4. **写实度 + 语境**：documentary realism；地点/人群/服装（示例项目：南非高原与布什维尔德、约堡/桑顿、橙色反光背心、白安全帽、玻璃塔楼；人物以南非黑人为主、混合背景、自然表情、无摆拍笑容）。
5. **运镜总则**：慢、稳、云台或无人机，禁手持抖动与急摇。
6. **一致性规则**（跨镜头同一个人/地点）：把"重复出现的元素"写死在 STYLE 里——如"矿 = 同一座阶梯状红棕灰露天矿坑""董事会 = 一张长胡桃木桌 + 玻璃墙 + 柔和城景"；服装/车辆**无公司名、无 logo**。重复人物/地点先出一张**锚定静图**（s 系列），再用它做视频首帧（见 §7）。
7. 另有 `## VIDEO_SPEC` / `## IMAGE_SPEC` / `## NEGATIVE` 三节（可省略，有默认值）。
格式示范见 `projects/bee-level8/gen_plan/style_bible.md`。

## 3. shotlist.json 字段（make_prompt_pack 的输入）
顶层 `{"slug","title","assets":[...]}`；每个 asset：
| 字段 | 说明 |
|---|---|
| `id` | 镜头 id：视频 `bNN`（沿用 broll shotlist 的编号，alt 加 `alt`），静图 `sNN`。**唯一** |
| `type` | `video` 或 `image` |
| `slug` | 文件名里的短名，文件 = `<id>_<slug>.mp4` / `.png` |
| `purpose` | 对应哪句口播/哪个场景（英文，一行） |
| `gloss_zh` | 给用户看的中文一句话说明（html 里黄字） |
| `seconds` | **视频：要生成的秒数**，只用 4 / 6 / 8（见 §6）。图片省略 |
| `use_seconds` | 视频：时间线实际需要的秒数；入库时裁到这个长度（≤ seconds）。一镜头被引用多次且取不同时段时，设成整段 |
| `subject` / `setting` / `action` / `camera` / `lighting` / `mood` | 提示词主体（英文；action 视频写**时间进程**，如 "0-4s ...; 4-8s ..."） |
| `text_safe_area` | `none/left/right/upper_third/lower_third/center`：后期要压字的位置，会加 "clean negative space" 句 |
| `depth_for_type_behind` | true = 要做"文字藏在主体后面"的遮挡效果，会加"强前景主体、与背景分离"句 |
| `loop` | true = 无缝循环（首尾帧一致），入库时只从头裁 |
| `image_kind` | 图片：`still`（默认）/ `plate`（虚化房间底图）/ `cutout`（纯色底元素图） |
| `ref` | 参考锚定图 id（如 `s05`），提示用户用它做首帧/参考图 |
| `avoid` | 本条额外负面词 |
| `notes` | 给用户的备注（风险、后期处理） |
| `trim` | 入库裁剪 `center`（默认）或 `head` |
| `allow_text` | 画面里允许出现文字（OCR 只记 INFO） |
也可以写 YAML（需 PyYAML）。

## 4. 视频提示词结构（Veo）
顺序固定（脚本按此拼接）：
`STYLE 段` → `SHOT (video, exactly N seconds, 16:9)` → **Subject**（主体，具体到数量/服装/材质）→ **Setting** → **Action**（谁在动、怎么动；时间进程）→ **Camera**（运镜 + 镜头焦段）→ **Lighting** → **Mood** → **Composition**（留白/遮挡/循环）→ **Technical** → **Negative**。
- **Technical 固定句**：`Duration: exactly N seconds. Aspect ratio 16:9 landscape, 1080p, 24 fps ... Silent footage: no dialogue, no music, no voice-over. No text, no captions, no logos, no watermarks, no subtitles.`（Veo 3 会自带音频，入库时统一去掉。）
- **负面清单**：text, letters, numbers, logos, brand names, watermarks, real people or celebrities, distorted hands, extra fingers, warped faces, flicker, jump cuts, camera shake。
- **写法原则**：
  - 不出现品牌名、真实人物（Gemini 会拒绝或出怪脸）；政府楼/银行写"风格"，不写真实建筑/公司。
  - **优先慢运镜、稳主体**：dolly / 慢推 / 云台横移 / 无人机缓降；避免快摇、快速动作、人群密集运动（易变形）。
  - **避免手与脸的特写**：手只给"翻页""签字"这类简单动作且不近距；人脸给中景/背影/虚化；需要特写写"face out of focus / not in frame"。
  - **画面里有文字的物件**（警示牌、文件、屏幕、箱子标签）：Gemini 文字易乱码——改成"只有图形标志、无字母"（pictogram only），文件写"纸面抽象线条不可读/虚焦"，屏幕写"abstract charts, no readable labels"。
  - **要压字时**：写 `Keep the left third of the frame as clean negative space (low detail...)`（`text_safe_area`）。字幕带在底部 ~10%，**主体尽量放在画面中上部**。
  - **要做"文字在主体后面"**：写 `Strong foreground subject, sharply separated from the background ... so text can be placed behind the subject`（`depth_for_type_behind`），主体要有干净轮廓、与背景明暗/景深分离；先在 Remotion 侧用抠像/遮罩，所以背景别太杂。
  - 航拍：写 drone 高度、方向、速度（slow, constant speed）。
- 示例（b02 节选）：`SHOT (video, exactly 6 seconds, 16:9): Subject: Three large yellow-and-grey rigid haul trucks (no company markings) driving in a line ... Camera: High drone shot, slow lateral glide at constant speed, 24mm lens, stable ...`

## 5. 图片提示词结构
`STYLE 段` → `IMAGE (still frame | background plate | isolated element, 16:9)` → Subject / Setting / Lighting / Mood → Composition → `Technical: Single still image, aspect ratio 16:9 landscape, 2K resolution (2048x1152 or larger) ...` → Negative。
- **背景图**（卡片底、模糊房间）：`image_kind: plate`，写 `Out-of-focus room plate: very heavy lens blur, no sharp detail, soft bokeh shapes only, no people, nothing readable`；亮度要低（示例项目 卡片底 mean Y 30–41，Remotion 里还会再压暗）。
- **抠图/元素图**（要放到卡片里的物体）：`image_kind: cutout`，纯色平底（脚本写 #808080 中灰），**Gemini 一般不能输出真透明**，所以写"plain flat solid background, no cast shadow, whole object visible with margin, clean sharp edges"，之后 Claude 用抠像/色键去底。要透明 PNG 的话请用户告诉我他看到的实际能力。
- **锚定静图**（地点/人物参考）：`still`，写同一套 STYLE，用来保证后续视频一致。
- **图标不生成**：全是矢量，见 src/components/icons。

## 6. 时长规则（重要假设，请用户核对）
- **假设**：Gemini 应用里的 Veo 视频**每条很短，通常最长约 8 秒**，可选时长大致是 4 / 6 / 8 秒（可能随版本/套餐变）；输出常为 720p 或 1080p、24fps、带音频。**请用户把实际看到的上限、可选时长、分辨率、每日次数告诉我**，我据此改 `seconds` 取值。
- **我们的镜头长度**：成片里大多数 B-roll 镜头 **2–3.5 秒**（示例项目 26 个 B-roll 镜头 1.6–4.1s）。所以：
  - 普通镜头：**生成 4–6 秒，入库裁到 use_seconds**（多出的 0.5–2s 是修剪余量，也给 Remotion 的 1→1.08 慢推留头尾）。
  - 推进/航拍/日落类：**6–8 秒**（动作要慢慢展开，AI 视频前 1s 常常静止/不稳，裁中段）。
  - 同一素材在片中用两次且取不同时段：生成 8 秒，use_seconds 设成整段，timeline 里用不同 `startFrom`。
  - **循环镜头**：`loop: true`，提示词要求首尾帧一致，入库只从头裁；否则做成淡入淡出。
  - **需要变速的镜头**（想要"冲击/加速"）：让 Gemini 生成 `slow motion`（慢动作），后期在 Remotion/ffmpeg 里加速到 2–4×；不要直接要快动作（AI 快动作易糊/变形）。
- 秒数永远写进提示词 `exactly N seconds`，**并在 html 的徽章上大字显示**。

## 7. 给用户的生成技巧（写进交付说明）
1. 每条提示词先生成 **2–3 个变体**，挑最稳的（主体不变形、无字、运镜慢）；不要"凑合用"。
2. **一致性**：先出锚定静图（s 系列），视频用"图生视频"（image-to-video）把静图当首帧；同一人物/房间的所有镜头都从同一张锚定图出发。支持**首帧/尾帧**的话，循环镜头用同一张图做首尾。
3. 同一批镜头尽量在**同一个对话/同一个参考设置**里生成；能固定 seed/角色参考就固定。
4. 画面出现乱码文字/怪手/怪脸：**直接重出**，别靠后期修（用 §9 模板，把问题写进去）。
5. 先试 1 条最难的（人物+动作）与 1 条最简单的（航拍），看效果与限制，再批量出。
6. 下载用 Gemini 页面的下载按钮，保留原分辨率，不要截屏录屏。

## 8. 文件命名与交付
- 文件夹：`projects/<slug>/gen/`（原件，不进 public/）。
- 视频：`bNN_<slug>.mp4`；静图：`sNN_<slug>.png`；文件名**必须以 id + 下划线开头**（html 卡片上有"Save as"，可点复制）。同一 id 多个变体：存成 `b02_x_v2.mp4`，我取最新的一个；想用哪个就删掉/不要放别的。
- 交付清单（用户存完告诉我）：☐ 每条文件名对得上 ☐ 视频 ≥1080p、≥ `seconds` 秒（至少 ≥ use_seconds）☐ 没有可读文字/乱码 ☐ 没有水印（Gemini 的可见水印会被入库报告当文字或边角提示，若有请告诉我）☐ 点了 html 里的"已生成"。
- html 的勾选和"重出备注"存在浏览器 localStorage（同一台电脑同一浏览器），不要清缓存。

## 9. Claude 入库与质检（S2.5-c）
```bash
python3 scripts/ingest_gen_assets.py <slug> [--mci b04,b18] [--trim center|head] [--no-ocr]
```
做什么：①对照 shotlist 报**缺文件/多余文件/重复**；②ffprobe 报分辨率、fps、时长、有无音轨；③转成 **1920×1080、30fps CFR、H.264 yuv420p、去音轨**，按 use_seconds 裁（center 或 head；loop 用 head），写 `public/projects/<slug>/gen30/`；④每条取 3 帧做**联系表**（`projects/<slug>/gen_plan/qa/contact_sheet_NN.png`）；⑤对这 3 帧跑 `tools/ocr`：出现汉字 = ERROR，出现其他文字类检测 = WARN "unexpected text"；⑥写 `qa/qa_report.md`。
后续处理：
- **看联系表**（人眼必看）：主体是否对、手/脸变形、物体融化、画面里有没有 Gemini 水印。OCR 假阳性见 production-playbook（全角 `！` 之类）。
- **帧率**：24→30 默认帧复制；**只有航拍/延时、无人无手**的镜头才用 `--mci <id>` 插帧；有人有手的镜头不插。
- **调色**：生成素材比库存更干净，`meta.brollLook` 与逐条 `look` / `dim` 要重新对一遍（先全局再逐条，见 playbook S5）。
- 太短（< use_seconds）：ERROR，要重出或降低 use_seconds；分辨率不足 1080p：WARN，会放大变软，重要镜头重出。
- 完成后把 timeline 的 `assets.files` 指向 `gen30/`，并更新 notes.md（哪些条重出过、哪些降级）。

## 10. 修订循环：重出提示词模板
某条不对时，Claude 不重写整条，而是给**"在原提示词上只改这一点"**的版本，并保持同一个 STYLE：
```
Regenerate the previous <video|image> with the SAME style, composition and settings, but change ONLY this:
<具体改动，英文，一两句。例：The trucks are too small - make them fill about one third of the frame width. Remove all letters from the sign; show only a red triangle pictogram.>
Keep: <要保留的>（如 "the pit, camera move and duration (exactly 6 seconds)"）
Also avoid: <新增负面词>
```
- html 每张卡片有 "Copy REGENERATE prompt" 按钮：把"重出备注"框里的话 + 原提示词拼好复制。
- 常见问题 → 改法：文字乱码 → 改"pictogram only / out of focus / abstract"；手变形 → 改成远景/背影/虚化；人物不一致 → 用锚定图做首帧；动得太快 → 加 "very slow, almost static camera"，把 `slow motion` 写进去；主体太小 → 写占画面比例；偏暖/偏亮 → 重申 STYLE 里的冷蓝暗调并写 "underexposed by one stop"。
- 重出的文件覆盖原名（或 `_v2`），重新跑 ingest；联系表里 OK 即可。每次改动写进 notes.md。

## 11. 与既有规则的关系
- 镜头节奏、PIP 禁入区、字幕带不变（comfort-rules / visual-mapping）；素材只是换来源。
- 版权：Gemini 生成物的使用条款由用户自己确认；不再需要 LICENSES.md 的逐文件来源页，但在 notes.md 记录"生成于 Gemini（Veo/Imagen）+ 日期"。库存兜底仍记 LICENSES.md。
- 生成素材里**不要出现真实品牌/真实人物**（也是 forbidden.md 的精神）。
