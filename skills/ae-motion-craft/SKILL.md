---
name: ae-motion-craft
description: 高级动效的拆解与复刻（AE 精品产品宣传片风格）。用户给一条精美动效参考视频/录屏、说「学这个动效」「拆一下这个视频的动效」「照这个做」，或要「做宣传片 / 产品动效片 / 纯动效视频」「口播（数字人）视频里加高级动效」「这个动效不够高级」时使用。三层：规律层（四条精品片反复印证、带数值和置信度的规则，含逐镜头复刻得出的「设计与镜头」一节）、积木层（你的Remotion工程 工程里 70 多个已校准的 Remotion 动效积木 + 场景速查 + 升级待办）、方法层（拆新视频的步骤、测量脚本、独立像素检验、并排校准、逐镜头复刻法）。口播视频的融合口径见 hosted-video-fusion.md。与 combo-style 配合：口播片整体流程按 combo-style，动效部分按本 Skill。
---

# 高级动效：拆解 → 入库 → 复刻

## 三层
| 层 | 文件 | 什么时候读 |
|---|---|---|
| 规律层 | `references/principles.md` | 做任何动效前先过一遍（缓动两档、0 帧硬切、错峰表、点击反馈、打字、转场、后期克制、音效卡操作）；**第 15 节「设计与镜头」**（设计/镜头/光效/排版四层规则，逐镜头复刻得出）做片前必读；**第 16 节「图表与数据可视化」、第 17 节「图标」**（做图表/图标前读，各条标了置信度，柱状最薄）；**第 19 节「AE 表达式等价与多卡片编排」**（多元素丝滑：重叠错峰、永不停稳、弹簧是风格选项；AE 表达式→函数见 `references/ae-expressions-map.md`）；第 14 节「被推翻的结论」是测量教训 |
| 方法层 | `references/method-dissect.md` | 拆新参考视频：素材 → 通览 → 编目 → 密集抽帧 → 测量 → 技法卡 → 积木 → 独立检验 → 并排图 |
| 复刻 | `references/method-replicate.md` | 学新风格 / 验证 Remotion 能否做到 / 校准积木：逐镜头复刻 + 打分迭代；脚本 `replicate_score.py`、`plane_track.py` 等 |
| 口播融合 | `references/hosted-video-fusion.md` | 做口播片前必读：沿用 示例项目 骨架，融合 = 升级每个元素的动效与设计，不是放大主播叠特效 |
| 降级 | `references/fallback-ladder.md` | Remotion 做不到时（3D、玻璃、实拍合成）走哪一档、要用户给什么素材；本机环境事实 |
| 做片 | `references/promo-and-hosted-pipeline.md` | 宣传片 timeline 格式、口播片 fx overlay、渲染命令、SFX 接入、字幕对齐闸门、回归、竖屏 |
| 脚本 | `scripts/README.md` | 抽帧、测量、拟合、音频节拍、并排图、回归、生成积木目录 |

（说明：本分享版**不含积木源码**。积木 = 你自己工程里一个个带参数的 Remotion 组件；按 `method-dissect.md` 第 7 节的规范和 `principles.md` 的数值自建即可，目录文件 block-catalog / backlog 已略去，文中出现处当作「你自己的积木目录」。）

工程：`<工程目录>/`（积木在 `src/motion/**`，登记在 `registryMeta.ts` + `registry.ts`；工程说明 `src/motion/README.md`）。代码是参数的唯一事实来源，文档与代码冲突以代码为准。

## 工作流 A：用户给了新的参考视频（「学这个动效」）
1. **拿素材**：`ffprobe` 看规格；录屏/可变帧率/超长合集先 `scripts/make_proxy.sh` 做恒定帧率代理。原片只读。
2. **拆解**：`overview_sheet.sh` 通览定位（拼图时间有误差，必须 `-ss` 复核；编目时间可能偏几十秒）→ 长素材先编目、按技法分组（子代理同时 ≤3 个）→ 每个事件 `dense_sheet.sh` 12–30fps 密集抽帧 + `measure.py` 量位移/缩放/模糊/亮度 → `fit_decay.py` / `fit_bezier.js` 判断缓动 → 写技法卡（模板在 method-dissect.md 第 6 节），每个数值带「测/≈」和置信度。
3. **入库**：先查 block-catalog 有没有现成积木能调参或用 `Compose` 组合；没有才新做积木（规则见 method-dissect.md 第 7 节）。新规律写进 principles.md（规则→数值→来源→置信度）。
4. **复刻**：做校准小合成，先用卡片参数渲一次、量一次存 `_verify_firstpass.md`，再写 VERIFY.md（每行标 IND/FIT/SEMI/T/CARD），偏差 ±15% 为通过，只有 IND 行能证明原片数值对。
5. **并排校准**：`side_by_side.sh` 出左原片右我们的对照图，写差距与「约像几成」；交给用户看，按反馈改。
6. **回写**：`node scripts/gen_catalog.mjs --project <工程目录>` 重新生成积木目录（新积木先在 `scripts/catalog_notes.json` 补来源/差距）；被推翻的卡片数值记进 principles.md 第 14 节。

## 工作流 A2：逐镜头复刻（学新风格 / 验证 / 校准积木）
入口 `references/method-replicate.md`：抽全帧 → 镜头表（`shots.json`）→ `src/study/<name>/` 独立复刻 → 渲染 → `scripts/replicate_score.py` 打分（整帧 + 内容 SSIM + PSNR）→ 每轮修最差镜头并记「改了什么→分数多少到多少」→ 写 LESSONS → 规则并入 principles、积木差距并入 backlog。**复刻只作内部学习，不进用户成片。**

## 工作流 B：要做片（宣传片 / 口播片加动效）
0. **做片前必读**：`principles.md` 第 15 节（设计与镜头）；口播片还要读 `hosted-video-fusion.md`（示例项目 骨架，主播多数时间小窗/不出现）；要用的积木在 `block-upgrade-backlog.md` 里有没有已知差距。
   - **图标**：默认用精美图标 `PremiumIcon`（图标名 `pm:<id>`，`recommendIcon('<概念>')` 直接给出 id + 推荐预设），**不再用 Lucide 线性图标当默认**；旧预设套在精美图标上要按 principles 第 17 节 I3 适配（下落减半、不画光弧/角标徽章）；清单与语义在 block-catalog 第 6 节。
   - **图表**：用 Chart 系列（`ChartLine / ChartBar / KpiStat / ChartRing / ChartStage`），规律见 principles 第 16 节；折线/环有复刻证据，**柱状证据最薄，默认走描边 + 辉光风格（`outline`、低 `fillAlpha`、`glow`），不要用实心渐变柱**，直到有 AE 柱状参考片复刻；不要再拿旧 Counter/CurveChart 当图表交付。
1. **定叙事再选积木**：每个画面问「这一句要表现什么」，查 block-catalog 第 1 节场景速查（数据增长/占比/趋势/KPI → Chart 系列；要图标 → `PremiumIcon pm:<id>` + 推荐预设）；按 principles 选节奏（每段 2–3s、动作后留白 0.5–1.2s、同级元素错峰、一个镜头一个相机、光影只给一个主角时刻）。
2. **拼**：纯动效片写 `public/projects/<slug>/promo.timeline.json`（clips + transitionIn + camera）；口播片在 combo-style 的 timeline 里加 `kind:"fx"` overlay（层选 fixed/content，避开字幕带和脸，贴字时间来自词级对齐）。
3. **SFX**：默认取 `public/sfx/block_sfx_map.json`；中间事件用 `sfxAt` 指定帧；音效贴操作帧，不卡拍。
4. **字幕**：有配音就 `align_words.py` 逐词对齐 → 写字幕 → 预览后 `check_sub_sync.py` 过 G5.5 闸门（起 ≤3 帧、止 ≤6 帧）。
5. **出图与预览**：lint（`npm run lint:promo` / `npm run lint:timeline -- <路径>`）→ 关键帧静帧 → 低清预览（`--scale=0.5`）→ 给用户看 → 终版。
6. **回归（建议，非门槛）**：改过 `src/` 共享文件（types / Player / SceneRenderer / lint / Root）就跑 `scripts/regress_md5.sh`（示例项目 8 帧 md5，不加 `--gl=angle`）+ lint + `npx tsc --noEmit`。
命令全文见 `references/promo-and-hosted-pipeline.md`。

## 禁区与长期口径（来源：combo-style、工程 README、用户记忆，已查证）
- **不做 BGM**：只交「人声 + SFX」，音乐由用户在剪映加；`bgm` 字段不写。（combo-style、`scripts/sfx_rules.md` §8）
- **英文片画面零汉字**：含字幕、积木文案、示例数据；lint 查文本，成片按 combo-style `references/english.md` §4 OCR 抽检。积木示例文案一律英文。
- **字幕必须逐词对齐并过同步闸门 G5.5**，不得按字数估算（combo-style `references/subtitle-sync.md`）。
- **3D 积木渲染要 `--gl=angle`**（GlassCapsule、TumbleObject、标题预设 throughObject；不加会报 WebGL 上下文错误）；宣传片命令一律带上。**做 示例项目 回归不要加**（基线是默认 GL 渲的，换 GL 像素会变，md5 不可比；2026-10-19 不加 angle 实测 8/8 相同）。
- **不加说明性小字**：画面上不放解释机制的注释、标签说明、安抚性文字（用户跨项目铁律；积木各批也按此做）。
- **确定性**：积木里不用 `Math.random` / `Date` / 墙钟，随机一律 `mulberry32(seed)`；时间由帧推出。
- **一个镜头一个相机**；content 层 fx 不跨场景切点（lint 拦）。
- **积木按 1920×1080 像素写**；竖屏要逐个手调 props。
- **`src/` 不是只读，按需求需要就改**（新增/扩展积木、改共享文件都可以，用户 2026-10-19 明确认可）；改完建议跑回归确认没弄坏旧流程；**不要 git commit**，除非用户要求。
- **不编数**：看不清写「看不清」；「约像几成」没评过就写「未评分」；单次目视读数不当结论，入库前独立像素复测（principles.md 第 14 节 26 条反例）。
- 8GB 内存：渲染一次一个，子代理同时 ≤3 个；装 Blender/opencv 等新软件先问用户。
- 与用户沟通用中文；需要用户拍板的事出选择题；没完全理解就先问。
