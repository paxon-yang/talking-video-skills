# 平面跟踪流水线（从 A 复刻的 analysis/replicate/A/tools/ 提炼，路径全参数化）

目标：原片里有一块 UI 面板在做 3D 运镜（推近、后仰、拉回），要在 Remotion 里让我们的面板逐帧贴合到 1px 以内。

1. **搭素材平面（plate）**：用真实 DOM 按网页原生宽度（A 的面板 768 CSS px）搭出面板，渲成一张静帧。字体要和原片同一渲染引擎（Chrome），度量才一致。面板尺寸要在「拉正后的参考图」上量，不能在倾斜帧上量（A 的结果页：倾斜帧量成 804 宽，拉正后是 768，修正后 B6 0.828→0.872）。
2. **抽原片全帧**：`extract_frames.sh` 或 `ffmpeg -i src.mp4 frames/f%04d.jpg`（A 的帧从 f0001 起，所以后面用 `--frame-offset 1`）。
3. **粗位姿（可选，用来读 perspective 距离、后仰角）**：`pose_fit_css3d.py plate.png ox,oy,w,h 'frames/f%04d.jpg' 154-243 cam.txt --frame-offset 1`。先不固定 P 拟合稳定帧拿 P（A ≈ 3000），再 `--P 3000`。弧度制，对应 CSS rotateX/Y/Z + scale + translate。
4. **单应矩阵（成片用这个）**：`plane_track.py plate.png ox,oy,w,h 'frames/f%04d.jpg' 148-386 hom.txt --frame-offset 1 [--mask 局部矩形]`（SIFT+RANSAC 初值 → ECC 精修）。内容在滑动的帧用 `--mask` 屏蔽滑动区或用中间态 plate；入场段面板大半出画，SIFT 失败会沿用上一帧，必要时手工给 `--prev`。
5. **转 CSS**：`hom_to_css.py hom.txt --ts src/study/<name>/tracks/panelH.ts`，组件里 `transform: matrix3d(h00,h10,0,h20, h01,h11,0,h21, 0,0,1,0, h02,h12,0,h22)`，`transformOrigin:'0 0'`，不要再加 perspective。
6. **屏幕空间暗角**：`shade_ratio.py` 看拉正后的亮度比值表；比值随帧不变 = 暗角挂在屏幕上，做成一层裁剪到面板四边形内的固定遮罩（A：f207–222 渐入，之后保持）。
7. **卡片类平移+缩放元素**：`template_track.py`（多尺度模板匹配，虚化的邻卡加 blur）。
8. **复查**：`replicate_score.py` 按镜头打分，看 SSIM 热图/最差帧；每一步的收益见 `references/method-replicate.md` 第 6 节。

A 的实测收益：去掉位姿平滑（平滑窗会让快速镜头滞后）B3 0.833→0.863、B6 0.785→0.828；ECC 单应矩阵 B6 0.828→0.872、B5 0.813→0.844；入场段改用 8 自由度单应矩阵 B1 0.941→0.956。
A 没通过的部分：放大 1.7–2.7 倍时 UI 小字要 <1px，单平面 ECC 仍有 1–3px 残差；B5 面板背景与内容有 10–14px 视差（不同 z 层），要拆两层各自跟踪。
A 原工具里项目专用、没复制进来的：`gen_panel_tracks.py`（把几段位姿拟合平滑拼成 TS）、`hom_refine.py`（带暗角补偿的分段 ECC 精修，写死了 4 个 plate 与帧段）、`hom_fix_lift.py`、`hom_patch_entry.py`、`sheet.py`/`pair.py`/`ssimmap.py`（目视对照）；原件仍在工程 `analysis/replicate/A/tools/`。
