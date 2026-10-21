# 脚本清单

都不写死项目路径，路径全部走参数。依赖：ffmpeg/ffprobe（本机无 drawtext 也能用）、python3 + numpy（本机 3.9 + numpy 2.0）、node ≥18。复刻类脚本（下面带 ★ 的）需要 opencv-python-headless、scipy、scikit-image、Pillow（本机已 `pip --user` 装好）；其余脚本不需要。
`.sh` 是 bash，在 macOS 自带 bash 3.2 下测过。用法都写在各文件开头注释里。

| 脚本 | 用途 | 依赖 | 2026-10-19 自测 |
|---|---|---|---|
| `make_proxy.sh <源> <out.mp4> [宽] [fps]` | 录屏/可变帧率/超长素材 → 恒定帧率代理（每秒关键帧） | ffmpeg | 跑过（C 34s → 2s） |
| `overview_sheet.sh <视频> <目录> [fps cols rows 格宽 起点 时长]` | 通览拼图 + `index.txt` 时间对照 | ffmpeg、python3 | 跑过（A 前 40s） |
| `dense_sheet.sh <视频> <out.jpg> <起> <长> <fps> [cols 格宽 crop]` | 窗口内密集抽帧拼图 | ffmpeg、python3 | 跑过（A 5.0s） |
| `extract_frames.sh <视频> <目录> <起> <长> <fps> [宽]` | 逐帧 PNG，文件名 = 毫秒时间 | ffmpeg、python3 | 跑过（A 12.9s） |
| `measure.py bbox/shift/region/sharp/color …` | 逐帧像素测量（原片和我们的渲染用同一命令） | ffmpeg、numpy | 跑过：A 标题宽 95.1%、A 滚动 34px/帧@1080、C 红笔像素序列、A 清晰度/亮度 |
| `fit_decay.py "v0,v1,…" [--final --step-fps]` | 判断缓动类型；指数衰减给 k 并换算到 30fps | python3 | 跑过（A 面板 → k 0.844，calm） |
| `fit_bezier.js "t:v,…"` | 拟合 cubic-bezier（B 片原脚本） | node | 跑过 |
| `audio_beat_check.py <音频> --events … [--highpass 3000 --period]` | 节拍估计 + 卡拍/卡操作检验 | ffmpeg、numpy | 跑过（B：不卡拍、卡操作） |
| `side_by_side.sh <out.png> <左> <左t|-> <右> <右t|->` | 左原片右我们的并排对照图 | ffmpeg | 跑过 |
| `screen_quad.py <视频> --ss --dur --thr [--crop] [--json]` | 粗测亮屏四角（给 ScreenComposite 初值） | ffmpeg、numpy | 跑过（D 815s） |
| `regress_md5.sh <工程> <timeline> <基线.md5> <输出目录>` | 共享文件改动后的 示例项目 8 帧 md5 回归（不加 --gl=angle） | node、工程依赖 | 跑过：full.timeline.json 8/8 相同 |
| ★`replicate_score.py --ref --ours --start/--frames/--dur --shots --mask --recompress --out` | 逐镜头复刻打分：整帧 SSIM + 内容 SSIM + PSNR、按镜头表、曲线图、最差 10 帧并排图、并排视频（每半边 1280x720、hstack、2px 分隔线）。合并自工程里 study_compare_A/C/D | ffmpeg、numpy、scipy、Pillow | 2026-10-19 在 A/C/D 三段产物上各跑一次，见下表 |
| ★`plane_track.py plate.png ox,oy,w,h '帧模式' 范围 out.txt` | 平面跟踪：SIFT+RANSAC → ECC 单应矩阵（plate 局部 → 屏幕） | opencv、numpy | 在 A f180/200 上跑过（cc 0.996） |
| ★`hom_to_css.py track.txt [--ts out.ts]` | 单应矩阵 → CSS matrix3d / TS 表 | numpy | 跑过 |
| ★`pose_fit_css3d.py` | 逐帧拟合 CSS 3D 位姿（perspective、后仰、缩放） | opencv、scipy | 在 A f180/200 上跑过（残差中位数约 1.6px，perspective 固定 3000） |
| ★`template_track.py` | 多尺度模板跟踪（卡片/图标平移 + 缩放） | opencv | 跑过 |
| ★`shade_ratio.py` | 拉正后与 plate 比值，量屏幕空间暗角 | opencv | 跑过 |
| ★`PLANE_TRACK_PIPELINE.md` | 平面跟踪流水线说明（八步 + 实测收益 + 没复制进来的项目专用脚本） | - | - |
| `gen_catalog.mjs --project <工程> [--out] [--check]` | 从 registry 生成 `references/block-catalog.md` | node、工程里的 esbuild | 跑过（73 条） |
| `catalog_notes.json` | gen_catalog 的人工数据（来源、约像、校准、差距、场景速查） | - | 新积木要在这里补一条 |

工程里另有不在本目录、但流程会用到的脚本（在 `<工程目录>/scripts/`）：`stills_tl.mjs`（Main 合成批量静帧）、`promo_stills.mjs`、`block_previews.mjs` + `contact_sheet.py`、`align_words.py` / `build_subtitles_from_words.py` / `check_sub_sync.py`（字幕对齐、分句与闸门；2026-10-19 起支持中文 `--lang zh`：多语种 whisper 模型默认 turbo-q4、逐字对齐、≤14 字分句（可选 jieba，`pip3 install --user jieba`）、中文闸门；英文行为不变；2026-10-20 起中文缩写逐字母读但字幕显示缩写：`align_words.py --lang zh --script 稿子 --auto-abbr` / `pron.json`（`{"RAG":"R A G"}`，缩写成一个词、字母级时间在 `meta.letters`），测试在 `out/zh-pron/`。测试集、实测与模型对比在 `<工程目录>/out/zh-sync/`（SYNC_REPORT_ZH.md，辅助脚本在其 tools/：波形起点核对 wave_onset_check.py、真值核对 truth_check.py、模型测速 bench_model.py））、`make_block_sfx_map.py`、`verify_batch*.py`（各批校准写法的范本）、`compare.sh`。

## replicate_score.py：三段实跑与旧脚本对比（2026-10-19，同一份产物）
| 段 | 命令要点 | 新脚本 ALL（SSIM / 内容 SSIM / PSNR） | 旧脚本报告 | 差异 |
|---|---|---|---|---|
| A r4（510 帧 29.97fps） | 默认（960 宽、uniform7、var>36） | 0.9315 / 0.5029 / 24.7 | 0.9308 / 0.5026 / 24.7（shots_r4.txt） | SSIM +0.0007，各镜头差 ≤0.001；原因没逐项查，疑似降采样（旧：PIL box，新：ffmpeg area）与窗口边缘处理（旧：只算有效区，新：镜像填充后裁 3px 边）不同 |
| C final（336 帧 24fps） | `--content-var 9 --content-dilate 6 --ffmpeg-ssim` | ffmpeg YUV SSIM 0.9733，内容 0.8822，PSNR 25.9 | 0.9733 / 0.8823 / 27.98（scores_final.md） | ffmpeg SSIM 逐镜头完全一致；内容 SSIM 差 ≤0.0005；PSNR 低约 2 dB：旧的 PSNR 是 ffmpeg 在 YUV 全分辨率上算的，新的是 960 宽灰度，口径不同；脚本自带的灰度 SSIM 列（0.9656）低于 ffmpeg YUV 口径，是因为 7x7 窗 + 960 降采样更严，两者不可混比 |
| D final（499 帧 30fps，原片 723 s 起） | `--width 0 --win gauss11 --recompress 24 --mask … --worst-by ssim` | 0.7865 / 内容 0.2064 / 19.2 | 0.786 / – / 19.2（report_final.md） | SSIM 与 PSNR 逐镜头一致（如 S1 0.7101、S9 0.6511）；内容 SSIM 是旧 D 脚本没有的新列，高斯窗下方差阈值 36 偏严，D 的数值（0.06–0.48）不能和 A/C 的内容 SSIM 比 |
并排视频：A 2562×720、510 帧；D 2562×720、499 帧（左半边原片、右半边我们的，2px 白线，无字幕标签——本机 ffmpeg 没有 drawtext；旧 D 脚本用 PIL 在画面上写了标签，新脚本没有）。
参数换算：A 的 `--shots` 用 JSON；C 的 `--shots 'S1:0-57,…'` 内联；D 的 JSON 里 `scored:false` 的镜头只列出不计分。
