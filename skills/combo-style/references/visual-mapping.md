# 内容类型 → 画面 → 组件；主播与动效的编排

> "组件"列用 Remotion 的 `scene.kind`（见 remotion-pipeline.md）。状态：✅ 已实现（P0/P1）；❌ 未实现（P2）及替代方案。
> "剪映做法"列对应 jianying-guide.md 的章节号。

## 1. 映射表

| 内容类型 | 画面 | scene.kind / overlay | 状态 | 剪映做法 |
|---|---|---|---|---|
| 钩子/反问 | 主播 + 夹头词 | host_tag + head_flank | ✅ | §6 文字模板 |
| 论点、转折、情绪 | 主播大景 | host_full | ✅ | 主轨 |
| 总结、关键观点 | 大景 + 推近 | host_punch | ✅ | §4 关键帧 |
| 产品功能、操作 | 录屏 + PIP + 标注 + HUD | screen_demo + callout + HUD | ✅ | §3、§4、§5 |
| 手机端操作 | 手机样机 + 竖版主播小窗 | phone_mockup（pip left_vertical） | ✅ | §5 |
| 产出物、成片 | 成片全屏（撤 PIP 与字幕） | clip_full | ❌ 替代：screen_demo，panel 设 {x:0,y:0,w:1,h:1}、panelRadiusPx 0，该段字幕 `hidden:true`，pip off | 主轨直接放成片、关掉字幕 |
| 以前 vs 现在 | 双药丸 + 步骤树 | compare(pills_vs) | ✅ | §6 |
| 原素材 vs 结果 | 左右卡 + 标签 | compare(result_pair) | ✅ | 两条画中画并排 |
| 三方对比 | 三列卡 + 能力标签 | compare(three_col) | ✅ | |
| 新闻事实 | 截图弹入拼贴 | news_collage | ✅ | 画中画 + 旋转 + 入场动画 |
| 历史人物 | 抠像 + 姓名条 | cutout_name | ✅（需用户给透明 PNG） | 智能抠像 |
| 概念名词 | 黑底关键词卡 / 压暗 B-roll 中英双行 | keyword_card(grid / on_broll / ghost_word) | ✅ | §6 |
| 并列要点 | 三图卡、药丸逐个点亮 | image_cards / pill_stack | ✅ | §6 |
| 流程、步骤 | 步骤卡 | step_list | ✅ | §6 |
| 比喻、故事 | B-roll 慢推 | broll | ✅（3D 卡通：可选，成本高，不做） | §4 |
| 关键数字 | 压暗 B-roll + 巨型数字 | big_number(center) | ✅ | 文字 + 压暗 |
| 金额卡（数据型） | 黑金竖卡叠白框 B-roll | big_number(gold_card) | ✅ | 难，不建议手工 |
| 占比、构成 | 饼图 | chart(pie) | ❌ 替代：外部做图 PNG → screen_demo(image) + 慢推 + callout；或 big_number | |
| 竞争、拉锯 | 条形竞价图 | chart(bar_race) | ❌ 同上 | |
| 趋势 | 折线图（倾斜白卡 + 色带） | chart(line) | ❌ 同上 | |
| 时间线、阶段 | 平面/3D 时间轴 | chart(timeline3d)、TimelineBar | ❌ 替代：step_list（≤4 步）或 summary_card | |
| 资金流向、关系 | 气泡图 | chart(bubble) | ❌ 同上 | |
| 赢家/输家盘点 | 剪影翻牌、对比表 | RankFlip / compare(three_col) | ❌ / ✅ 用 three_col | |
| 问题清单（逐字出） | 问题卡 + 打字机 | question_card | ✅ | §6 打字机动画 |
| 评分、结论 | 总结卡逐条点亮 | summary_card(single/double) | ✅ | §6 |
| 金句 | 深红底金句卡 | summary_card(quote) | ✅ | |
| 情绪、价值观 | 宽银幕 B-roll + 大字 | broll(widescreen) + overlay keyword | ✅；毛笔大字 BrushWord ❌，用 keyword overlay 或 ghost_word 替代 | |
| 聚焦一块界面 | 聚光灯（其余压暗/模糊） | spotlight overlay（layer content） | ✅ | 蒙版 + 调节 |
| 账号片尾 | 片尾卡 | closing | ❌ 不要做（见 forbidden.md）；用 host_tag + 夹头词收尾 | |
| 章节角标（数据型，左下徽章） | Badge | overlay badge | ❌ 渲染器忽略；用左上 HUD 代替 | |

## 2. 主播与动效配合编排

### 2.1 四拍序列（观点/解读型）
主播提问（3s）→ 关键词卡（1–4s，**1 帧硬切**）→ B-roll / 数字 / 步骤图举例（3–10s）→ 主播总结（3s）。
时间示意（15s）：0–3 主播 / 3–5 关键词卡 / 5–12 证据 / 12–15 主播。

### 2.2 演示序列（教程型）
章节卡 → 录屏 + PIP（5–10s/界面，每 3–5s 一次推拉或标注）→ 主播小结（≈4s，可 punch）。
单元 25s = 引出 3 + 章节卡 2 + 录屏 16 + 小结 4。

### 2.3 主播回归频率与无脸段

| 指标 | 取值 | 依据 |
|---|---|---|
| 大景回归 | 每 15–20s 一次，单次 3–6s | comfort #6（借博主B 的 4–6 次/分，1–3 分钟片取每 15–20s） |
| 大景占比 | 25–40% | 博主A 13–43%、博主B 42–52% |
| 主播可见（含 PIP） | ≥75% | 博主A 59–91% |
| 连续无脸段 | ≤10s（P90 ≤14s） | lint：最长无脸段 ≤10s |
| 纯素材段（B-roll） | ≤8–10s 必须回主播或开 PIP | |
| punch-in | ≤2 次/分，只用于关键句 | |
| 叠化 | ≤2 次/分，仅换段 | |
| "压暗再切" | 每片 ≤1 次 | |

编排算法（Claude 手排时照此检查）：
1. 从上次大景结束起，≥15s 仍无大景 → 下一个 claim/summary 句改成大景（3–6s）。
2. 连续无脸 >8s → 给其中素材镜头开 PIP；仍 >10s → 插入 3s 主播。
3. 任何 10s 窗口至少一刀或一次运镜。

### 2.4 PIP 预设与切换

| 预设 `pip.preset` | 形状 | 位置/大小（画布比例） | 用途 | 来源 |
|---|---|---|---|---|
| `bl_circle`（默认） | 圆形 | 直径 0.14W（269px），圆心 (0.08, 0.85)，环 4px #A818B0 + 18px 紫外发光（估计） | 录屏、对比、图表、数字段 | 博主A实测 |
| `bl_circle_big` | 圆形 | 直径 0.17W，圆心 (0.12, 0.80) | 图表/B-roll，落在图形主体对侧 | 博主B N1 |
| `br_circle_small` | 圆形 | 直径 0.13W，圆心 (0.92, 0.80) | 同上，另一侧 | 博主B N1 |
| `br_rect` | 竖直圆角矩形卡 | x 0.81, y 0.52, w **0.16**, h 0.43，圆角 14px | 背景/历史章节（博主B ex08） | tokens（校准） |
| `right_rect_big` | 右侧大矩形卡（同框版） | x 0.61, y 0.07, w 0.315, h 0.815，圆角 16px；左侧放地图/人物卡 | 讲背景设定 | tokens |
| `left_vertical` | 竖版小窗 | x 0.07, y 0.24, w 0.17, h 0.48，圆角 20px | 手机样机旁 | tokens |
| `shout: true` | 喊话放大 | 放大 1.35 倍，其余画面 1 帧压暗到 30% | 主播直接对观众说关键话，≤1 次/片 | 博主B N1 |

规则：
- **同框与 PIP 是同一矩形卡由大变小的连续过渡**（right_rect_big → br_rect）；预设切换用 spring(damping 20) 位移，不重新入场。
- 连续镜头里 PIP 连续存在（Remotion 自动合并连续 on 区间为一个持久图层，视频不跳）。
- 只在录屏、对比、图表、数字段出现；概念卡、情绪段、章节卡、总结卡、成片全屏时关闭（pip: "off"）。
- PIP 的数字人视频是**同一条**口播视频的再放（口型一致），Remotion 用 480p 代理 `hostPipVideo`。
- 圆形默认博主A（紫环）；博主B 风格 PIP 无紫环（**代码里尚未按主题区分**，见 remotion-pipeline.md 已知限制）。
- PIP 位置落在图形主体对侧；不得压到字幕带（y 0.86–0.93）——圆形 PIP 在 y 0.85 中心、直径 269px，字幕在其右侧居中，不重叠。

### 2.5 层级与固定位置（不要在这些区域放别的东西）

| 区域 | 坐标（画布比例） |
|---|---|
| 字幕带 | y 0.86–0.93，水平居中 |
| PIP 区 | x 0.01–0.15、y 0.78–0.92（圆形默认） |
| HUD 区 | x 0–0.29、y 0.03–0.17 |
| 夹头词区 | 左 x 0.03–0.305、右 x 0.667–0.97，y 0.07–0.35（中间留给人脸） |
| 录屏面板 | x 0.12, y 0.015, w 0.85, h 0.855，圆角 12px |
| 安全边距 | 5%（54px），角标可贴 1–3% |

## 3. 每句选画面的速查（给分镜表用）

| 想表达 | 选 | 时长 | PIP |
|---|---|---|---|
| 抛问题/钩子 | host_tag | 3–6s | 关 |
| 提观点/转折 | host_full | 3–6s | 关 |
| 强调结论 | host_punch | 3–6s | 关 |
| 点名产品 | brand_card | 3–6s | 开 |
| 前后对比 | compare | ≤6s | 关 |
| 开始一步 | chapter_card | 2–3s | 关 |
| 讲界面 | screen_demo | 5–10s | 开 |
| 报数字 | big_number | 2–4s（每个） | 开 |
| 列要点 | step_list / summary_card | 3–6s | 关/开 |
| 讲新闻 | news_collage | 6–14s | 关 |
| 打比方/抒情 | broll | 1.5–3s 一张 | 视情况 |
| 一个新词 | keyword_card | 1.5–4s | 关 |
| 成品展示 | screen_demo 全屏替代 clip_full | 1–4s | 关，撤字幕 |

没有素材的 evidence 句 → 降级为 keyword_card + 主播，**不用占位图凑**。每个 Scene 对应 ≥1 句且起点在句首，**绝不切在句中**；一个 beat 只放一个观点。
