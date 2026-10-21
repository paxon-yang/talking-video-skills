# 方法层第二支柱：逐镜头复刻法

`method-dissect.md` 管「怎么拆一条视频、把规律和积木沉淀下来」；本文管「把原片的一段逐帧重做出来，用分数逼出差距」。
实际走过三遍：**A**（求职工具宣传片 0–17 s，1920×1080，29.97fps，510 帧）、**C**（Claude MCP 连接器片 0–14 s，24fps，336 帧）、**D**（AutoClaw 光效段，抖音录屏代理 723.0–741.5 s，1280×722@30，499 帧）。
每段的 LESSONS（带证据图）：工程 `out/study/A|C|D/LESSONS.md`；云盘 `视频/douyin/动效积木成果/4_复刻对照/`。规则已合并进 `principles.md` 第 15 节。

## 0. 复刻只作内部学习，不进用户成片
- 复刻件里有原片的品牌名、UI 文案、图标，只为了和原片比分才抄；**不得用于成片、不得对外发布**。代码放 `src/study/<name>/`，每个入口文件和 NOTES.md 头部标 `STUDY ONLY`。
- 学到的东西以「规则（principles.md）+ 积木升级（block-upgrade-backlog.md）」的形式带走，成片用积木拼，不拷贝复刻件。

## 1. 什么时候用
| 场景 | 为什么用复刻 |
|---|---|
| 学一种新风格 | 拆解（method-dissect）只能量到单个元素；复刻要把整个镜头的设计、相机、光效一起做对，才暴露「积木学到了运动、没学到设计和镜头」。用户评我们的宣传片「没学到位」，就是这个差距 |
| 验证 Remotion 能不能做到 AE 的效果 | A 整片 SSIM 0.931、12 个镜头里 9 个整帧 ≥0.90；C 7 个镜头整帧全部 ≥0.95；D 平均 0.68→0.79。结论：DOM/SVG/canvas + 逐帧表驱动够用，C 没用 three.js，D 的 3D 面板也只靠 CSS perspective |
| 校准积木 | 复刻时每一处「积木不够」都写进 NOTES.md 的「为什么不能复用」表，直接变成 `block-upgrade-backlog.md` |
不适合：要的只是某个缓动/间隔数值（用 `measure.py` + `fit_decay.py` 即可）；整段超过 20 秒（成本按镜头线性增长，A 17 s 整片 r0–r4 五次打分，另有 a1–a6、b1–b13、c1–c8 共 27 次单镜头小轮）。

## 2. 步骤与命令
`$S` = `video-asset-prep/scripts`，`$P` = `<工程目录>`，`<name>` = 研究名（A / C / D …）。

### 2.1 抽全帧
```bash
mkdir -p $P/analysis/replicate/<name>/frames
ffmpeg -ss <起点秒> -t <时长> -i src.mp4 -vf fps=<原片帧率> $P/analysis/replicate/<name>/frames/f_%04d.png   # C：336 帧；A 用 jpg 够
```
先 `ffprobe` 记原片帧率；可变帧率/录屏先 `$S/make_proxy.sh`。帧号写 0 基；注意文件名 `f_0001` = 第 0 帧。拼图 `$S/dense_sheet.sh` 目视通览。

### 2.2 镜头表（先于任何代码）
`analysis/replicate/<name>/SHOT_TABLE.md`（C 用 SHOTS.md），一行一个镜头：
`镜头 | 起止帧 | 元素与坐标（1080p 像素或代理像素） | 字号/字体 | 取色（逐个大面积取像素值） | 光 | 运动曲线（每帧数值表）`。
每个数字注明用哪个脚本量的（A 的 NOTES、C 的 tables.ts 都这样做）。镜头边界用硬切点：`ffmpeg ... select='gt(scene,0.3)'`，再逐帧确认（见 principles 15 节 M5：切点差一帧，S7 最小 SSIM 0.193→0.831）。
同时写一份机器可读的 `shots.json`（供打分脚本）：`[{"id":"A1","from":0,"to":40,"name":"…"}]`；录屏里不复刻的段加 `"scored": false`。

### 2.3 代码组织
```
src/study/<name>/entry.tsx          独立入口 + 自己的 compositions.tsx（不碰 src/Root.tsx）；文件头写 STUDY ONLY
src/study/<name>/NOTES.md           运行命令、镜头表摘要、「为什么不复用积木」表、已知差异
src/study/<name>/tracks/ data.ts    逐帧跟踪/配准结果（脚本生成，注明生成脚本）
src/study/<name>/shots.json         镜头表
public/study/<name>/fonts/          替代字体（FontFace 加载，不动共享的 vendor_fonts）
```
合成帧号 = 原片帧号（A：原片 29.97 对合成 30fps，17 s 内差 0.1%，可忽略；C 直接 24fps）。每个元素用测量表驱动，不用手感关键帧。

### 2.4 渲染
```bash
cd $P
npx remotion render src/study/<name>/entry.tsx <Comp> out/study/<name>/render_rN --sequence --image-format=png --concurrency=2 --gl=angle
# 或用工程里的 scripts/study_render_C.mjs / study_render_D.mjs（并发 2、渲完删临时 bundle）
```
- 8GB 机器：`--concurrency=2`，一次只渲一个；渲完清 remotion 的临时 bundle 目录。用 `--gl=angle`（含 WebGL/canvas 光效时）。
- 实测耗时：C 336 帧约 30 s；D 499 帧约 22 s（GlowField canvas 640×361）。
- 渲完先 `tail` 渲染输出确认没报错再打分。D 出现过一次「渲染崩溃」，原因是自己字符串拼接写坏了语法，不是内存；拿旧产物打分会得出假分数。

### 2.5 打分（`replicate_score.py`，三段口径的并集）
```bash
# A：灰度 960 宽、7x7 均值窗
python3 $S/replicate_score.py --ref src.mp4 --ours out/study/A/render_rN --frames 510 --shots src/study/replicateA/shots.json --out out/study/A --tag rN
# C：内容窗口方差>9 并膨胀 6，另算 ffmpeg YUV SSIM
python3 $S/replicate_score.py --ref src.mp4 --ours out/study/C/frames --fps 24 --frames 336 --shots 'S1:0-57,S2:58-81,…' --content-var 9 --content-dilate 6 --ffmpeg-ssim --out out/study/C --tag rN
# D：压缩录屏，高斯 11x11、原始分辨率、屏蔽录屏 UI、先把我们的帧过 x264 crf24
python3 $S/replicate_score.py --ref proxy.mp4 --start 723 --ours out/study/D/ours.mp4 --shots src/study/replicateD/shots.json --width 0 --win gauss11 --recompress 24 --mask '0,30,335,70;0,610,300,112;0,712,1280,10' --worst-by ssim --out out/study/D --tag rN
```
输出：整帧 SSIM、内容 SSIM、PSNR 按镜头汇总的表（`report_<tag>.md/json`）、逐帧 csv、曲线图（红 = 整帧、蓝 = 内容）、最差 10 帧「原片 | 我们 | 3 倍差异」并排图、并排视频（左原片右我们，每半边 1280×720、hstack、2px 白分隔线，无字幕条）。参数全表见脚本头注释与 `scripts/README.md`。
指标含义：
- **整帧 SSIM**：给总体进度。留白/暗场多的画面「什么都不做」也很高（C 第 0 轮就 >0.93，A 暗底 >0.95），**不能用来挑镜头**。
- **内容 SSIM**：只统计有纹理的窗口（A：局部标准差 >6 灰阶；C：方差 >9 且膨胀 6px），C 全程靠它指导修改。
- **PSNR**：看亮度/色阶整体偏差（暗角、背景色对不对）。
- 同一个镜头在不同口径下数不同（见 `scripts/README.md` 的对照表），**一个研究内口径固定**，不要中途换。

### 2.6 迭代：每轮只修最差镜头，并记账
1. 看曲线 + 最差帧并排图 + 差异图（SSIM 热图），挑内容 SSIM 或整帧 SSIM 最低的镜头。
2. 先做廉价诊断再动手（D、C 的经验：诊断工具每个的收益都大于目视调参）：区域平移搜索（`tools/shift.py`）、分区域 SSIM（`regssim.py`）、射线取边缘（D `rays.py`）、径向剖面、辉光拟合、SSIM 热图。1–4 px 的错位（基线、列距、旋钮位置）往往比「风格」更伤分。
3. 改一类问题，整片重渲，重新打分。
4. 在 `ITERATIONS.md` / LESSONS 里记「改了什么 → 分数从多少到多少」（C 的 6 轮表、A 的 r0→r4、D 的 round log 都是这个格式）。没涨的也记（C：字重 560/640/680 无效、旋钮内缩 2.5px −0.005 已还原、重叠笔迹窗口重拟合无效），避免重复试。
5. 同一个错误反复出现、或整体卡住时，停下来问一次「是测量错了还是做法错了」。

### 2.7 通过标准
- 整帧 SSIM ≥0.90（逐镜头平均）；内容 SSIM 只作挑镜头的依据，不设硬门槛（A 全片内容 SSIM 仅 0.50，原因是替代字体，见 4.4）。
- 压缩录屏（D）阈值放到 0.85，**并且先对我们的帧做同等压缩**（`--recompress 24`），否则编码噪声会被算成我们的差距。D 做到 4/12 镜头 ≥0.85，剩余镜头的失分原因逐条写在 LESSONS 末尾。
- 没到标准的镜头必须写明原因（字体拿不到、视差分层、星空闪烁等），不能含糊过去。

### 2.8 写 LESSONS
结构（三份都按这个）：材料与指标说明 → 最终分数表 → 迭代记录 → 设计层 / 动效层 / 光效层 / 技术层，**每条带证据（证据图路径或分数变化）** → 需要升级的积木 → 做不到的地方与原因。证据图放 `out/study/<name>/evidence/`，命名 `before_|after_<镜头>_f<帧>_<说明>.png`。完成后把并排视频拷到云盘 `视频/douyin/动效积木成果/4_复刻对照/`，LESSONS 合并进 principles。

## 3. 关键技巧
| 技巧 | 做法 | 收益证据 |
|---|---|---|
| 图像配准量相机曲线，别猜关键帧 | 以参考帧为模板，相似变换（缩放+平移）Nelder-Mead 优化，逐帧取相机参数（C `reg_panel.py`）；缩放用「每列圆心最小二乘」而不是物体宽度（抗锯齿和阴影会把宽度带偏约 2%） | C S2 0.689→0.799（一步）；S7 0.827→0.874 |
| 平面跟踪 → 单应矩阵 → CSS `matrix3d` | SIFT 初值 → ECC 精修 → `matrix3d(h00,h10,0,h20, h01,h11,0,h21, 0,0,1,0, h02,h12,0,h22)`；`scripts/plane_track.py` + `hom_to_css.py`，流程见 `scripts/PLANE_TRACK_PIPELINE.md` | A：去平滑 B3 0.833→0.863；ECC 单应 B6 0.828→0.872；入场 8 自由度 B1 0.941→0.956 |
| 墨迹框 + 基线排字 | 量每个词墨迹左右边界、基线取无下伸字母最底行；逐词按墨迹宽度定字号和位置（`ink.tsx`） | C 基线低 4px：S3 0.806→0.852，比任何换字体都大 |
| 字体按像素误差搜索 | 候选字族 × 字重 × 字距渲同一段文字，按与原片墨迹的像素误差排名 | C：12 无衬线 + 20 衬线，Petrona 600 / −0.035em 比 Source Serif 误差低 17%，S4 0.842→0.870 |
| 切点卡到帧 | 逐帧确认硬切帧；出场场景在切点前几帧塌缩（缩小+模糊） | D：S7 最小 SSIM 0.193→0.831 |
| Shutter 时间超采样运动模糊 | 180° 快门内对整层渲 N 次等权平均（`src/study/replicateA/Shutter.tsx`，待升级为积木，见 backlog）；`filter:blur` 只能做单轴 | A：f40 缩放模糊形态对上；只给文字层，面板加了反而掉分 |
| 笔迹/路径反求 | 红像素并集 → 骨架 → 航点最短路 → 逐帧可见区间 [尾,头]（C `pen_path.py`） | C：5272 px 路径 |
| 辉光拟合 | 每侧 2 个高斯 + 底部 wash，色带按采样映射，关键帧最小二乘（D `fitglow*.py`、`GlowField`） | D S5 0.798→0.865 |

## 4. 常见坑
1. **整帧 SSIM 在留白/暗场里虚高**：A 暗底、C 米色留白第 0 轮就 >0.93。挑镜头看内容 SSIM 和并排图；肉眼觉得差得多时信眼睛。
2. **暗部像素决定分数**：近黑区域 5 个灰阶的误差比 20 px 的图标错位更伤 SSIM（D 隧道环间隙）。先把背景色、暗部、辉光量准。
3. **多代理共享脚本互相覆盖**：A 的打分脚本被 C 的代理改成了另一个口径（`study_compare.py`），三份脚本各自为政，口径不可比。现在统一用参数化的 `replicate_score.py`；多代理并行时每段独立 `--out/--tag`，不要改共享脚本，要改就加参数。
4. **替代字体拉低内容 SSIM**：C 标题区无论字重 560–680 都卡 0.66–0.68；A1 笔画比原片粗约 7%；D 每行文字宽度差 5–10%。拿不到原字体就接受这个天花板，并在 LESSONS 里写明。
5. **原片比 Chrome 渲染更软**：压缩录屏边缘比我们软 0.5–1 px，全屏 0.8px 模糊让 A 的 B 段 0.904→0.907。**只在复刻比对时用，成片不加。**
6. **随机/闪烁内容有分数天花板**：D 的星空每 5 帧只有 35% 的星对得上，S8–S10、S12 因此封顶；平滑内容复刻平滑帧能到 0.95–0.99（模糊天花板测试），所以失分在几何/色阶而不是编码噪声。
7. **在倾斜帧上量 UI 尺寸会量错**：先拉正（A 结果页 804→768）。
8. **6 参数位姿在面板大半出画时符号歧义**（A f151–153 rotateX −0.27/+0.28 翻转）→ 直接用 8 自由度单应矩阵。
9. **视差**：A 的 B5 面板背景和内容有 10–14px 视差（不同 z 层），单平面跟踪对不上；需要拆两层各自跟踪。
10. **量错对象**：中心点别用帧中心（D 环中心是 (639,354)，不是 (640,361)）；文字宽度先拿尺子量再反推字号（D 一处 348 px 对 470 px）。
11. **复刻的「像」不等于「好看」**：全程只比像素，设计判断（为什么这样留白、为什么这个字号比例）要回头写进 principles，不能只留在分数里。
