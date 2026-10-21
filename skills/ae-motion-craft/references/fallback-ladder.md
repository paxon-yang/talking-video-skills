# 降级阶梯：Remotion 直接做不到时怎么办

原则：从低档往高档试，能在低档做到 7 成以上就不升档；升到第③档要用户提供素材，升档前先告诉用户「要什么、什么格式、能到几成」。

| 档 | 手段 | 什么时候用 | 代价 |
|---|---|---|---|
| ① | CSS / SVG / canvas 2D（DOM 文字清晰；SVG mask、feGaussianBlur；canvas 逐像素） | 绝大多数 UI、文字、路径、点阵、马赛克、透视网格（自己做投影） | 零依赖；canvas 要按帧确定性重画 |
| ② | `@remotion/three` + three.js（ThreeCanvas，透射/虹彩材质、挤出几何、GLB） | 真 3D 物体、玻璃材质、物体遮挡文字 | 渲染**必须加 `--gl=angle`**（本机默认 GL 拿不到 WebGL 上下文，直接报错，已实测）；包体 +40MB；只有 import 了 three 的入口才打进 bundle |
| ③ | 预渲染素材接 `PrerenderedClip`：AI 生成视频（用户用 Gemini 生成，见 combo-style `references/gemini-asset-prompts.md`）、Blender/C4D 渲染、实拍底片 | 有机形变、厚玻璃折射、GI/景深的产品场景、真实拍摄感 | 要用户出素材；Blender 本机**没有**，装之前要用户同意 |
| ④ | ffmpeg 后期 | 本项目只用在音频（loudnorm -16 LUFS、混音检查）、转码、并排对照；**还没用 ffmpeg 做过画面特效**，别承诺 | - |

## 本批每个难项走了哪一档、像几成、缺什么
「约像」是 3B 批对着并排图的主观评分（动势 / 质感 → 综合），来自 `out/motionlab/batch3b/NOTES.md`；其它批没有评分。

| 难项（原片） | 档 | 约像 | 主要差距 | 想更像需要用户提供 |
|---|---|---|---|---|
| WireCube 线框立方体（D 138.55s） | ① SVG + 自写透视投影 | 6.5（8 / 5） | 线更粗更亮，侧面没有玻璃感 | - |
| PerspectiveGrid + BallLeadText（D 145.6s） | ① | 6.5（8 / 5.5） | 格子没有玻璃厚度 | - |
| PerspectiveGrid + ScrambleText（D 795.7s） | ① | 6（8.5 / 4） | 同上 | - |
| GridTunnel（D 796.2s，原片是 AI 视频） | ① SVG 3D 线框 | 5（6 / 4） | 原片是带反光地面、光柱的房间 | AI 生成片段 |
| GlassCapsule 玻璃胶囊（D 794.6s，原片是 AI 视频） | ② 透射 + 虹彩 | 5（目标 6–7 没达到；本体 6，融化形变 2–3） | 彩虹带像实心涂料，没有厚玻璃折射 | **AI 生成的胶囊形变片段，约 3 秒，16:9，最好带 alpha，否则纯色影棚底；接 `PrerenderedClip`** |
| StarFlare / GlassBall（D 997–998s） | ① | 7 / 6 | - | - |
| TumbleObject 物件翻滚压字（D 1107.3s，原片离线渲染） | ② 挤出几何 + DOM 字带 | 6（7 / 5，只算物件 + 字） | 没有 GI、景深、哑光材质、笔记本场景 | 产品 GLB，或 Blender/C4D 出的 PNG 序列 / ProRes 4444 |
| ScreenComposite 屏幕合成（D 811–832.7s，原片是真机实拍） | ① matrix3d 单应矩阵 | 几何 10；有实拍底片约 8.5，程序化暗房约 4.5 | 键盘反光、边框、手机噪点只有底片能给 | **① 黑屏（或绿屏）实拍底片 mp4/ProRes；② 逐帧屏幕四角 JSON `[{frame, quad:[[x,y]×4]}]`（Mocha/AE 跟踪，慢镜头 6–10 帧一个关键帧即可；本机 `scripts/screen_quad.py` 只能给粗初值）；③ 屏幕变亮的帧号（填 `exposure.events`）** |
| HalftoneLens 半调放大镜（D 1051.2s） | ① canvas 点阵 | 7（7.5 / 7） | 切换后不是烟雾辉光 | - |
| BevelPanel 斜面玻璃面板（D 250.7s） | ① CSS 3D（方案 A；没选 Three 贴图的方案 B：要先把 DOM 栅格化，字更糊） | 5.5（6 / 5.5） | 面板更长更斜、条目更多 | - |
| FluidBackground 流体（D 998.3s） | ① canvas 径向渐变（没做 WebGL fbm 方案） | 未评分 | 速度对，形状不像（原片色团大而浑、会变形） | - |
| GlyphCloud 字形云（B 9.75–14.6s） | ① canvas，约 1.9k 字形 | 未评分 | 原片浓密暗团 + 半调底层，墨量少约 31% | - |
| DotMap 点阵地图（D 31.07s） | ① canvas + 生成的陆地掩膜（Natural Earth 110m，公有领域） | 未评分 | 热点分布、HUD 态 | - |
| designer throughObject 字穿过 3D 环 | ② 两层 WebGL | 未评分 | 只有程序化环/立方体 | GLB |
| D W3 卡 10 的 3D 玻璃 UI（BOUNCE） | ③ | 动效可 100%，质感 50–60%（W3 可行性表，预估未做） | - | 3D 玻璃 UI 场景素材 |

`PrerenderedClip` 的接口：`videoSrc`（OffthreadVideo，`transparent` 可带 alpha）或 `sequence {prefix, digits, ext, first, count, hold}`；`trimBefore, playbackRate, pushPerSec, panX/panY`；`children` 叠标题/logo；`fallback` 没素材时先放近似版。**只做过 typecheck，还没用真素材渲染过**——第一次接素材时要先单独渲几帧验证。

## 本机环境事实（2026-10-19 查）
- 有：ffmpeg / ffprobe（Homebrew；**没有 drawtext 滤镜**；有 hstack、tile、select、scdet）、node v24、python3 3.9.6（numpy 2.0.2、scipy 1.13.1、Pillow 11.3）。
- 没有：Blender、After Effects、DaVinci、opencv（`import cv2` 失败）。要装任何一个都先问用户。
- 语音对齐：mlx-whisper 在 venv `~/.cache/combo-whisper-venv`（Python 3.12），`scripts/align_words.py` 会自动切过去；默认 small 模型，8GB 上**永远不用 large**。
- 机器：Apple M2，**8GB 内存**。渲染一次只跑一个；预览用 `--scale=0.5`；子代理同时 ≤3 个；构建/渲染被系统杀掉 ≠ 代码失败，先看内存再重跑。
- WebGL：`--gl=angle`（走 Metal）可用；`--gl=swangle`（纯软件）也能出图但像素与 angle 有细微差别；同一种 GL 下同一帧两次渲染 md5 一致。
