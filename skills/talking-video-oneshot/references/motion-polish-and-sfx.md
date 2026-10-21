# 动效精修、音效、创意图形（示例项目 实装；全部在 `meta.motionPolish: true` 之后才生效）

> 源码事实：`<工程目录>/src/lib/polish.tsx`、`src/components/mg/*`、`src/components/SfxLayer.tsx`、`src/types.ts`。冲突以代码为准。旧样片不受影响（开关缺省关）。
> 用户要的是"丝滑、精美"：弹簧/缓动、遮罩+模糊的文字出现、快速移动带运动模糊、亚像素运镜、全视频走 OffthreadVideo、叠化 ≤2/分，且**逐帧自查**。

## 管线顺序（每步幂等，可反复跑）
```
make_bee_full.py (+make_en_timeline)  →  apply_transitions_bee.py  →  apply_creative_bee.py  →  make_sfx_cues.py [--rebase]
```
- `make_sfx_cues.py` 总是从 `full.timeline.pre_sfx.json` 干净备份重新推导；timeline 内容变了（如新增创意层）用 `--rebase`。
- **默认不加 BGM（2026-10-18 用户决定）**：`assets.bgm` 不写、已有的会被移除；交付 = 人声 + SFX，音乐由用户在剪映里加。`--with-bgm` 才恢复旧行为（不推荐）。`make_bgm.py` 保留但标注"可选，默认不用"。
- 项目里的 `scripts/make_sfx_cues.py` 仍是旧版（会设 bgm）；用 Skill `scripts/` 里的版本覆盖过去（见 scripts/README.md）。

## 1. 退场编排（exit choreography）
- 原则：入场镜像出场，easeInCubic，**`exitT(f, dur, n)` 在图层最后一帧（dur-1）正好到 1**，不早消失也不多留一帧。
- 短图层用 `fitN(dur)`：退场长度 ≤ 生命的 35%（最短 3 帧）。
- 词出场：`wordOutStyle`（上滑 110% + 模糊 0→6 + 淡出，各词按自己的末帧结束）。卡片出场：`exitStyle`（translateY + scale + blur + fade）。
- 按镜头类型的预设（`SCENE_EXIT`，ty px / scale / blur px / 帧数）：
| kind | ty | scale | blur | n |
|---|---|---|---|---|
| chapter_card | -70 | .98 | 8 | 10 |
| big_number | -36 | 1.04 | 8 | 10 |
| compare / step_list / pill_stack / image_cards | +56 / +44 / +44 / +44 | .97 | 5 | 11 / 11 / 10 / 10 |
| summary_card | -28 | .97 | 6 | 11 |
| keyword_card / question_card | -30 / -28 | .97 | 6 | 10 |
| news_collage | -28 | .96 | 6 | 10 |
| phone_mockup | +36 | .97 | 5 | 10 |
- host / broll / screen_demo 不做卡片退场（硬切或由转场处理）。下一镜头与本镜头重叠时（有转场）退场自动关闭（`SceneExit active=false`）。
- 创意图形里用 `gx(f, dur, i)` 给第 i 个元素错开 2 帧退场。

## 2. 新转场（`transitionIn`，只对 motionPolish 片子有意义）
| 类型 | 帧数 | 观感 | 示例项目 用法 |
|---|---|---|---|
| push_blur | 8 | 章节卡推入+模糊 | 4 个章节卡（≈1.6/分） |
| slide_push | 12 | 上一镜头被推出 | B-roll→host 交替 |
| zoom_through | 10 | 穿过画面放大进入 | B-roll→host 交替 |
| flash_cut | 4 | 切点叠白闪（上一镜头不保持挂载） | 卡片→B-roll 仅 1 处 |
| wipe | 12 | 擦除 | 卡片→B-roll 仅 1 处 |
- **约束：特殊转场（含章节 push_blur）≈ 三刀一个**，其余保持干净硬切（+退场编排）；叠化 ≤2/分。
- `apply_transitions_bee.py` 的模式：B-roll→host 交替 zoom_through / slide_push；卡片→B-roll 只挑两处（写死 id）给 wipe/flash_cut；断言 `cur.dur ≥ 转场帧数+4` 且 `prev.dur ≥ 转场帧数`；先删旧转场再写（幂等）；保留章节卡自带的 push_blur。换片子时改 `CARD_TO_BROLL` 与镜头类型判断即可。
- **已知瑕疵**：zoom_through 在窗口边缘有伪影（待修）。

## 3. SFX 音效库（`scripts/make_sfx_lib.py` 纯 numpy/scipy 合成，48k 立体声，峰值 -14 dBFS → `public/sfx/*.wav` + `manifest.json`）
| 名称 | 时长 | 用途 |
|---|---|---|
| whoosh_short | 0.35s | 普通切点（B-roll/host），提前 2 帧 |
| whoosh_long | 0.7s | 章节转场/大镜头 |
| whoosh_down | 0.5s | 下沉收束 |
| pop | 0.08s | 卡片/标注/药丸/关键词出现 |
| tick | 0.03s | 夹头词、列表项、图标描线、下划线 |
| swipe | 0.25s | 卡片滑入 |
| ding | 1.2s | 结尾、清单最后一项落定 |
| impact_low | 1.0s | 章节卡、大数字揭示的低频重击 |
| riser | 2.0s | 铺垫（结束点 = 揭示帧；cue 里 `rate:1.5` 压成 40 帧，起点 = 揭示 − 40 帧） |
| shimmer | 1.0s | 金句高亮/金色强调 |
| flash | 0.12s | flash_cut 亮闪 |
新增音效：在 `make_sfx_lib.py` 加一条 `lib[...]`，并在 `SfxLayer.tsx` 的 `SFX_FRAMES` 与 `types.ts` 的 SfxCue 联合类型里同步名字。

## 4. Cue 规则（`make_sfx_cues.py`）
- 来源：普通切点隔一个给 whoosh_short（≥36 帧间隔）；章节 → whoosh_long(-4f) + impact_low；大数字 → riser(-40f，rate 1.5) + impact_low；compare/summary → swipe + 各列/条目 pop/tick；夹头词 tick；pill/keyword/callout pop；mg 叠层用自带 `props.sfx` 的 `{t, type, why}`（t 相对叠层起点）；最后一句字幕 ding。
- 所有时间取自 timeline 里的词时间，**不早于词**。
- 抽稀：同类型 ≥15 帧；tick/pop/swipe 之间 ≥6 帧；**总密度 ≤ 0.8 条/秒**（优先级 impact/riser/ding 9 > whoosh_long/shimmer 8 > swipe/pop 6 > whoosh_short 5 > tick 3）。示例项目 实得 84 条 = 0.55/s。
- 音量（timeline `volume`）：whoosh_short .30 / whoosh_long .34 / pop .32 / tick .22 / ding .34 / impact_low .40 / riser .26 / shimmer .26 / swipe .28 / whoosh_down .28 / flash .20。
- `review/sfx_cues.md` 自动写出人可读的 cue 表；`check_audio_mix.py` 离线模拟混音，看 mix − voice ≤ +1.5 LU、最响 SFX 相对人声。
- **SFX 要保持安静**：用户之后会在剪映里叠音乐，SFX 太响会和音乐打架、盖人声。别为了"听得见"调大 volume。

## 5. 背景音乐（默认：无）
- **默认流程不生成、不嵌入 BGM。交付人声 + SFX；用户在剪映里自己加音乐。** timeline 里省略 `assets.bgm`。最终响度 **-16 LUFS 是"人声 + SFX"版本**的。
- 历史：示例项目 用过合成占位铺底（`make_bgm.py`：A 小调 Am-F-C-G @84bpm，无旋律，1–4kHz 人声频段 -9dB 凹槽，目标 -28 LUFS，timeline volume 0.4，`BgmLayer` 1s 淡入/2.5s 淡出）。现已不再使用，仅作参考。
- 若用户将来明确要我们加音乐：用 `--with-bgm`，铺底做人声频段凹槽，再用 check_audio_mix 验证。

## 6. 响度
- 目标 -16 LUFS integrated（两遍 loudnorm，`-c:v copy` 只重编音频），true peak < -1 dBFS。
- 内部混音检查：人声 vs 人声+SFX 的 integrated 差 ≤ +1.5 LU。

## 7. 创意图形套件 `src/components/mg/`（opt-in，经 timeline `mg` 属性与 `kind:'mg'` 叠层调用）
| 文件 | 内容 |
|---|---|
| kit.tsx | 调色板 `C`、缓动 `T/L/SP/POP`、`gx` 错开退场、`Canvas/G/Draw(描线动画)/Scrim/Txt/rrect/rnd` |
| icons.tsx | `LineIcon`（描线图标，`ICONS` 表：warning chain eye checklist boardroom orgchart cart boxes tick calendar…）、`Digit`（线条数字）、`iconFrames` |
| ChapterMg.tsx | 章节卡：图标 + 序号 + 进度条 |
| LevelLadder.tsx | 大数字 8 的 1–8 级阶梯（最低一级亮红） |
| SummaryMg.tsx | 总结卡左侧 rail+勾；金句卡 embers + 扫光 |
| graphics.tsx | 叠层图：`TieLifecycle`（授予/续期/转让生命周期链）、`RiskStairs`（风险阶梯）、`Gate`（闸门：标签穿过门亮起）、`KwBrackets/KwBar/KwUnderline/KwIcon`（关键词强调）、`MgOverlay` 分发 |
- `apply_creative_bee.py` 的做法：按 id 给章节卡/大数字/三栏卡/总结卡/金句卡写 `props.mg`；新增 `kind:'mg'` 叠层（`graphic` 为 types.ts 的 `MgGraphic`）；删掉被图形取代的纯文字 pills/keywords；约一半孤立的 keyword 叠层换成 `kw_*` 强调；所有时间 = 词起点 + 小延迟（绝不早于词）；先清旧 `mg_*` 再重写（幂等）。

### 何时用图形而不是文字
| 句子在说 | 用 | 不用 |
|---|---|---|
| 流程/生命周期（授予→续期→转让，每步要证明） | chain 图（TieLifecycle） | 三个 pill 排排站 |
| 层级/等级/严重程度递增（罚款→审计→监管行动） | stairs（RiskStairs）/ ladder | 关键词卡 |
| 门槛/准入/"没有它进不去"（采购、银行尽调） | gate（Gate） | 一句话字幕 |
| 单个关键词落在 B-roll 上 | kw_underline / kw_bar / kw_brackets / kw_icon | 大字全屏卡 |
| 结构点（章节开头、总结、金句） | 带图标/rail/embers 的卡 | 纯文字卡 |
- 反过来：没有可画的结构（只是一个事实、一个情绪）就用 B-roll + 少量关键词，不硬画图。图形少而准，不要每句都有。

### 用户在意的设计规则
- 数字用**粗 Anton**，大、实心；条/箭头/框用**粗线**；不要细而淡的蓝色小数字（看着廉价）；图标描边 **≥6px**（1080p）。
- 饱和实色（荧光绿 #9BF900、警示红 #FF4A3D、浅蓝 #BFD6FF 只做辅助），不要灰蓝细线。
- 文字用遮罩上升+模糊，图形用描线绘制（stroke-dash）；弹簧 POP 不过冲。
- 已知瑕疵：BOARD 图标看着怪；zoom_through 窗口边缘伪影。

## 8. 自查
每个动效用 `scripts/stills_tl.mjs` 出连续 12 帧，`contact_strip.py` 拼接（文件名 `<组>_<帧>.png`），逐条查：首帧是否闪现、有无过冲/跳变、是否在最后一帧正好退干净、文字是否出界。
