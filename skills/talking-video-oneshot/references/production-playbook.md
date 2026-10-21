# 全流程手册（示例项目 实际跑过的一遍）：从稿子到交付

> 何时读：要从零做一条完整视频（尤其数字人 = HeyGen、配音 = 用户的 Fish Audio 克隆声音、英文版）时，照这个顺序走。
> 来源：`<工程目录>/projects/bee-level8/`（notes.md、review/preview_v1_notes.md、scripts/）。2026-10-17/18 实跑，成片 2:31、1080p。
> 仍然是**协作**：每个"闸门（gate）"处停下，把一小份东西给用户看、等确认，不是一键出片。Owner：U = 用户，C = Claude。
> 与 SKILL.md 第 0–5 轮的对应：S1–S3 ≈ 第 0–1 轮，S4–S5 ≈ 第 2–3 轮，S6–S10 ≈ 第 4–5 轮。

## 阶段总表
| # | 阶段 | 输入 → 输出 | Owner | 闸门（用户确认什么） |
|---|---|---|---|---|
| S1 | 稿子 | Notion 原稿 → 压缩口播稿 → 钩子改写 → 英文改编（词数预算） | C 写，U 审 | G1 钩子选哪版、事实/数字对不对、英文稿 |
| S2 | 声音 | 英文稿 → Fish Audio 音频 → 本地变速 → 定稿时长 | U 生成，C 后处理 | G2 选哪个时长版本 |
| S2.5 | **素材提示词包 + 用户用 Gemini 生成 + 入库** | 分镜 → shotlist.json + style_bible.md → prompt_pack.html → 用户在 Gemini 生成存 gen/ → ingest 转 30fps + 质检 | C 写提示词与质检，U 生成 | **G2.5** 联系表/OCR 过关、要重出的重出、降级项确认；通过后才搭 timeline |
| S3 | 数字人样片与整条 | 音频 → HeyGen 13s 样片 → 整条渲染 → 下载 | C 驱动浏览器，U 做身份验证/付款/删除 | G3 形象(look)、背景、样片是否 OK |
| S4 | 关键帧样张 | 样片 → 样张（含调色/取景） | C | G4 像不像、卡片背景方案 |
| S5 | 素材（B-roll） | 镜头清单 → Pexels 视频 → 30fps 转码 | C | 缺口是补还是降级 |
| S6 | timeline 生成 | SRT + 素材 → full.timeline.json | C | — |
| S7 | 低清预览轮 v1..v5 | timeline → preview_vN.mp4 | C 渲染+自查，U 看 | G5 每轮逐时间点反馈 |
| S8 | 动效精修 → SFX → 创意图形 | 见 motion-polish-and-sfx.md | C | 随预览轮确认 |
| S9 | 终版渲染与响度 | timeline → 1080p crf18 → loudnorm -16 LUFS | C | — |
| S10 | 自检与交付 | 成片 → 零汉字 OCR、时长/大小核对 → 拷到桌面 | C | G6 用户验收 |

## S1 稿子
1. 来源是用户 Notion 页面（原稿是长文）。先压成口播稿：一句一个意思、数字单独成句、每句 ≤16 词（英文）。结构按 thinking.md / templates.md，示例项目 是"观点型 B"：钩子 → 误区 1 → 误区 2 → 三个要看的点 → 行动 → 金句收尾。
2. **钩子改写**：第一版钩子被用户否掉（太平），改到 v3 方向才确认。教训：钩子给 2–3 版供选（hooks-and-copy.md），用户确认后才往下。
3. **英文改编 + 词数预算**：目标时长 × 2.2–2.6 词/秒（english.md §1）。示例项目 稿 script_en.md 约 28 行；Fish 出的原始音频 3:21（≈1.75 词/秒，偏慢）说明**词数预算要按实测语速回算**，不要信理论值。
4. 缩略词读法（XYZ、DMPR 等）写成逐字母，听样音后调（english.md §5）。屏幕上仍显示原写法。

## S2 声音（永远不用 HeyGen 自带 TTS）
1. U 在 Fish Audio 用克隆声音生成整条（粘贴版去掉 `【】`，`/`→逗号）。先生成 10–15s 样音确认读音。
2. C 本地 ffmpeg 处理（慢/停顿多时）：
   - `silenceremove` 把长停顿**封顶**到 0.40–0.45s（TTS 经常在句间留 1s 以上空白，剪辑里会像死机）；
   - `atempo` 加速：1.12 → 2:45；**封顶 0.40s + atempo 1.2 → 2:31**。atempo 在 1.2 以内人声基本不失真，超过要听。
   - 输出 `voice_en_fast.mp3`（2:45）、`voice_en_faster.mp3`（2:31）并列给用户。
3. **G2：用户选最终时长**（选了 2:31 版 = voice_en_faster.mp3，成为 HeyGen 整条渲染的主音频）。选定后不再改音频，否则 HeyGen 要重渲（烧积分）。

## S3 HeyGen 数字人（浏览器驱动）
1. 工具链：Claude 用 claude-in-chrome 操作已登录标签页；形象 = 某个自建形象的一个 look（用户在 6 个 look 里选的）。AI Studio、1080p、MP4、**水印关、自带字幕关**。
2. **用户自己做**：身份验证（新形象 lin 需要真人验证，用户选择跳过）、付款确认、删除账号/形象。Claude 不碰这三类。
3. **浏览器上传限制**：上传工具只收与会话共享、**<10MB** 的文件（mp3 可以；大视频模板 62MB 要用户手动拖进去）。
4. 样片：13s，**11 积分**（≈0.85 积分/秒）。HeyGen 一次出两个变体，用户选 variant 2。检查：脸高≈0.25H、中心≈(0.50W,0.30H)，比 combo 目标小而高 → 在 Remotion 用 `hostLook.frame` 缩放/偏移补偿；背景是浅色薰衣草墙+书架（亮）→ **G3 用户选"保留 HeyGen 房间背景"**，包装里压暗/冷调，不重渲。
5. 整条：2:31 音频 → **121 积分**（≈0.8 积分/秒），单变体、无冻帧。输出 1920×1080、**25fps**（HeyGen 不是 30fps）、AAC 48k，另有 SRT（34 条，句级时间）。
6. **下载**：走页面下载对话框（有视频 / 字幕两个 tab）。HeyGen 的签名下载链接会过期，浏览器里点下载比拿链接稳。
7. 转码：25→30fps 用帧复制（`fps=30`，不插值，见 S5 帧率规则）；另出 480p PIP 代理和 48k 单声道 host.wav（digital-human.md §8）。

## S4 关键帧样张（G4）
用真实 HeyGen 样片出样张（`scripts/make_keyframes_bee.py` 生成 keyframes.timeline.json；`_raw` 无调色、`_frameonly` 只取景，用来量调色效果）。决定：
- 卡片背景：候选 1 "房间延续"（取样片 t=1s 左右各 470px 拼接去人，gblur σ50，亮度 .32 + 冷蓝 soft-light）胜出，**全片无网格**；候选 2 纹理保留未用。
- 金句卡用 `tone:'room_gold'`（房间底 + 暖金衬线）。
- 原片只是参考不是复制：布局撞 PIP/字幕就按实际改（三栏卡走 safeArea），小设计决定自己做，不逐条问用户。

## S2.5 素材提示词包（2026-10-18 起的默认路径；细节全在 `gemini-asset-prompts.md`）
用户要求**所有视频/图片素材改用 Gemini 生成，Claude 给全部提示词（含秒数、风格）**。位置：分镜/口播稿确认后、搭 timeline 前（可与 S2–S4 并行，只要分镜已定）。
1. C 写 `projects/<slug>/gen_plan/shotlist.json`（每个 B-roll/静图一条：id、秒数 4/6/8、use_seconds、主体/动作/运镜/光线、text-safe/depth 标记）+ `style_bible.md`（冷蓝暗调、镜头语言、色值、语境、一致性规则）→ `python3 scripts/make_prompt_pack.py <shotlist> <style_bible>` → `prompt_pack.html`（每条一键 COPY、时长徽章、文件名、勾选、重出备注）+ `prompt_pack.md`。
2. U 在 Gemini（Veo / 图片）逐条生成，每条 2–3 变体选一，存 `projects/<slug>/gen/bNN_<slug>.mp4`、`sNN_<slug>.png`。先试 5–8 条最关键镜头确认风格，再出全套。
3. C `python3 scripts/ingest_gen_assets.py <slug>`：缺/多/重复文件、ffprobe、转 1920×1080 30fps H.264 去音轨、裁到 use_seconds → `public/projects/<slug>/gen30/`；联系表 + OCR（汉字=ERROR，其他文字=WARN）+ `qa/qa_report.md`。
4. **G2.5（U）**：看联系表，列出重出项（C 写"重出提示词"）与降级项（改库存/改卡片）。**不过闸不搭 timeline。**
5. Pexels 库存只在用户同意降级时兜底（下面 S5 保留作兜底参考）。示例项目 示例包：`projects/bee-level8/gen_plan/`（38 条：30 视频 + 8 静图，覆盖现有 26 个 B-roll 镜头 + 背景/三栏 + 缺口：银行大楼、具体矿区、夜间矿坑、叉车仓库、董事会）。

## S5 B-roll 素材（兜底，默认改走 S2.5；用户没有素材，要求"丰富的真实镜头"，不是关键词卡）
1. 先写镜头清单 `broll/shotlist.md`：每个句子要什么画面（矿区航拍、签合同、警示牌、仓库、董事会……），每项备 alt。
2. 来源 **Pexels**（免费商用、无需署名、不得原样转售）。下载 CDN 的 mp4，**逐文件记 `broll/LICENSES.md`**（文件名、来源页 URL、作者、许可、日期）。示例项目 用 38 个文件。
3. 转码到 `broll30/`：H.264、无音轨、最宽 1920、**30fps CFR、取前 16s**。**中断的会话留下过全部 "moov atom not found" 的损坏文件**，用到前先 ffprobe 全量验证，坏了就从原件重转。原件（658MB）放项目 `broll_src/`，**不放 public/**（会被打进每次渲染）。
4. **帧率规则**：50/60fps 源只丢帧；24/25fps 源默认复制帧（`fps=30`）；**只有慢速航拍/延时（没有人手/人脸）才用 `minterpolate=mc` 的 mci 插值**（b04/b18/b18alt/b24），有人或手的素材和 **host 一律不插值**（mci 会把手扭曲，blend 会出重影手）。A/B 方法：6s 最大动作段，比相邻帧位移变异系数 CV：复制 0.97 / mci 0.81（但手变形），航拍 0.51→0.13。
5. 调色：全局 `meta.brollLook`（contrast 1.08 / saturate .90 + 冷蓝 tint + vignette），再用 `BrollProps.look` 给个别发灰的素材逐条覆盖（b02/b04/b08/b18alt/b22：饱和 1.0–1.15、对比 1.1–1.18）；偏暗的单独提亮（b24 dim 2.0）。灰是"压暗+去饱和"叠出来的，**先按全局调，再逐条补**。
6. 素材缺口（诚实写进 notes）：没有银行、具体矿井/政府机关的好镜头，用相近替代（Sandton 航拍代银行、会议室代审计），逐镜标"最弱匹配"请用户看。

## S6 timeline 生成
- `scripts/make_bee_full.py` 读 HeyGen SRT + B-roll 清单 → `full.timeline.json`；先 `make_en_timeline.py` 的英文骨架。字幕 = SRT 句子原文，拆成 ≤7 词/≤38 字符。
- **时间精度**：句子起止来自 SRT（真实，但首句比音频晚约 0.2s；句内边界可差 0.2–0.4s）；**句内的词时间、字幕块、句中切点、夹头词、关键词、卡片出现点全是按词数比例估算，误差 ±0.3s，置信度 0.5**。强制对齐工具**没有**（缺口）——**2026-10-18 咖啡机预览被用户发现字幕与语音不匹配，此缺口不可再接受，见 `subtitle-sync.md`：字幕必须用词级强制对齐（whisper word_timestamps），并过 G5.5 同步门槛。**保护措施：句末关键词提前一个词，保证停留 ≥0.7s；贴字宁晚勿早。
- 每次改完跑 `npm run lint:timeline`，示例项目 全程 15/15（46 镜头、17.8 刀/分、60% 切点在句首、最长无脸段 8.1s、punch-in 3 次）。

## S7 低清预览轮（G5，每轮 `--scale=0.5 --crf=30`，约 9 分钟/次，6 线程）
| 版本 | 解决了什么 |
|---|---|
| v1 | 首个整片：真实 SRT 时间、28 个 B-roll、motionPolish 开启（词遮罩上升+模糊、卡片 .96→1、PIP 弹簧、定向运动模糊）。自查后修：三栏卡左栏提前到句首进入、大数字垂直模糊调软、金句卡改到 "compliance" 才出现。 |
| v2 | 用户 8 条意见：三栏卡重做（三栏真实素材逐个点亮，最长卡 9.5s→5.4s）；**章节标签叠在人脸上**（是章节卡自己的标签在 push_blur 期间淡入，加 `enterDelay:8`）；**夹头词左右错位**（LOW 在右，真 bug，改 LOW 左/FINED 右）；**大数字 8 首帧糊成一团**（模糊 ≤3px、首帧不透明）；**金句卡太短 1.6s→3.6s**（加 eyebrow，金字从 compliance 起）；**B-roll 发灰**（逐条覆盖 look）；**25→30 卡顿**（做 A/B，航拍插值、host 保持复制）；字幕保持 "level eight" 拼写。 |
| v3 | 退场编排与新转场（`exitT` 精确落在最后一帧；slide_push/zoom_through/flash_cut/wipe，约三刀一个）。见 motion-polish-and-sfx.md。 |
| v4 | SFX 音效层（84 条，0.55/s）+ 创意图形层第一版（章节图标、等级阶梯、生命周期/风险阶梯/闸门图、关键词强调）；音频离线模拟（check_audio_mix）。 |
| v5 | 创意图形审后修正（推断：细淡蓝数字/图标显得廉价→改粗 Anton、描边加粗），再次全片自查。 |
（实际反馈链：v2→用户说"整体不错，但动效简单、没有出场退场、没有音效"→v3 退场+转场+SFX+占位BGM；→用户说"大多纯文字，要更有创意"→v4 创意图形；→用户说"1 2 3 太 low、不要细蓝色"→v5 粗体数字/粗柱；→"go ahead"→终版；终版后用户说"不要 BGM，我自己在剪映加"→重渲无 BGM 版。以后每轮都把"改了什么"写进 notes.md。）
每轮自查固定动作：16 帧总览图 + 6 条 12 连帧运动条（`contact_strip.py`）+ OCR + 指标表（刀/分、句首占比、最长无脸、host 占比）；交付时附 5–8 个"请重点看"的时间点。

## S8 精修 → SFX → 创意图形
管线顺序和规则全在 `motion-polish-and-sfx.md`：`make_bee_full → apply_transitions → apply_creative → make_sfx_cues`。**默认不生成 BGM**。

## S9 终版渲染与响度
```bash
npx remotion render Main out/<slug>/<Name>_final_1080p.mp4 --props='{"timelineSrc":"projects/<slug>/full.timeline.json"}' --crf=18 --codec=h264
# 响度：loudnorm 到 -16 LUFS，视频流 copy，只重编音频
ffmpeg -i final.mp4 -af loudnorm=I=-16:TP=-1.5:LRA=11 -c:v copy -c:a aac -b:a 192k final_norm.mp4
```
- **-16 LUFS 针对"人声 + SFX"版本**。音乐由用户之后在剪映里加，SFX 因此要够轻（见 motion-polish-and-sfx.md），否则加了音乐后盖过人声。
- 终版渲染耗时未记录（0.5 倍预览约 9 分钟）；先 `--frames=a-b` 渲小段验证。loudnorm 命令是推荐写法，实际用的参数以 ebur128 复测结果为准（目标 -16 LUFS，不达标就改 I/测量值做两遍）。

## S10 自检与交付
1. 时长：ffprobe 视频/音频均 ≈151.5s，start_time 0。
2. 响度：ebur128 integrated ≈ -16，true peak < -1。
3. **零汉字**：timeline 静态 grep + 每 1.5s 抽一帧 OCR（`ffmpeg -vf fps=1/1.5`，tools/ocr）。严格档（U+4E00–9FFF）必须为空；假阳性见下。
4. 大小：示例项目 成片约 130MB。
5. 交付：**拷贝到桌面** `~/Desktop/示例项目_Level8_final_1080p.mp4`，原件留在 `out/<slug>/`。**不要把 130MB 放进 Google Drive**（同步拖慢）。
6. 更新 notes.md 与云盘 PROGRESS.md。

## 成本表（示例项目，约数）
| 项 | 用量 | 费用 |
|---|---|---|
| HeyGen | 样片 11 + 整条 121 = 132 积分（≈0.8 积分/秒） | 按 ≈$0.05/积分【估算，随套餐变】≈ **$6.5** |
| Fish Audio | 克隆声音 3:21 文本 | 很便宜（用户已有订阅） |
| 素材/音效/配乐 | Pexels 免费商用；SFX 合成自生成；不做 BGM | $0 |
| Remotion | 在公司许可门槛以下免费 | $0 |
| Claude 用量 | 无法测量 | — |
HeyGen 每次重渲都烧积分：**样片（G3）和音频定稿（G2）通过前不要渲整条**。

## 坑清单（都踩过）
| 坑 | 对策 |
|---|---|
| 浏览器上传 <10MB 限制 | 大文件让用户拖；mp3 通常够小 |
| HeyGen 签名下载链接过期 | 在页面里点下载 |
| 网络中断 / 代理断线恢复 | 恢复后先核对磁盘上的文件（别信"已完成"），不完整就重做 |
| 中断留下的损坏转码（moov atom not found） | 全量 ffprobe 验证，原件重转 |
| TTS 停顿过长 | silenceremove 封顶 0.40s |
| 夹头词左右顺序错（LOW 在右） | 夹头词左右要符合句中词序，出样张看 |
| 章节标签压在人脸上 | `enterDelay` 等 push_blur 结束 |
| 大数字首帧糊 | 模糊 ≤3px、首帧不透明 |
| B-roll 压暗后发灰 | 逐条 `look` 覆盖，提高饱和/对比 |
| 金句卡太短 | ≥3s，加 eyebrow，金字按词出现 |
| 细而小的淡蓝数字看着廉价 | 用粗 Anton、厚条、饱和色；图标描边 ≥6px |
| 零汉字 OCR 误报 | Anton 模糊帧被识成符号；ASCII `, ?` 被读成全角；b11 栅栏里 "WARNING!" 的 `!` 被读成 `犯`——人眼复核，严格档才算数 |
| 旧文件/旧产物混用（stale） | 文件名带版本；渲染前确认 timeline 是最新生成的、public 里没有旧 bgm/旧 sfx；改了 public 素材要重打包 |
| 大素材放 public/ | 放 `broll_src/`，public 只放处理后的成品 |
| Google Fonts 慢导致出图超时 | 用 `scripts/stills_tl.mjs`（同一浏览器+重试） |

> 备注：示例项目 的首个桌面成片（2026-10-18 04:43）仍带合成占位 BGM；改为无 BGM 默认后需用 `full.nobgm.timeline.json` 重渲替换。新项目一开始就不设 `assets.bgm`。
