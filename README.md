# talking-video-skills

一句话需求 → 口播 / 动效讲解视频成片。两个 Claude Code Skill（备料 + 制作） + 方法论 + 可复用脚本。

<p align="center"><img src="assets/frame_claude.png" width="800" alt="成片画面：数字人 + 身后大标题"></p>
<p align="center"><img src="assets/frame_four_steps.png" width="800" alt="成片画面：身后大字「四步」"></p>

上图为用本 Skill 做出的视频中的两帧：数字人出镜，大标题叠在人物身后。

## 结构：备料 + 制作
| 路径 | 内容 |
|---|---|
| `skills/video-asset-prep/` | **备料**：数字人、声音、沉淀积木 / 学动效、固定框架；带备料清单 |
| `skills/talking-video-oneshot/` | **制作**：一句话需求 → 成片，自动推进；开工先查备料 |
| `使用说明.md` | **新手先看这个**：安装、用法、常见问题 |
| `方法论-备料篇.md` / `方法论-制作篇.md` | 两部分的方法论全文 |
| `pipeline-scripts/` | 对齐、字幕、字幕同步核对、波形起音核对、抠像、看门狗渲染、音效、打字登记 |

## 安装
把 `skills/` 下两个文件夹放进 `~/.claude/skills/`，重启 Claude Code，先说「我还缺什么备料」，备齐后说「帮我做一条关于 X 的视频」。

## 注意
- 本包**不含**动效积木源码（依赖原工程的主题与字体，单独跑不起来）。文档里提到「积木目录」处，指你自己建的积木库，建法见 `skills/video-asset-prep/references/method-dissect.md`。
- 文档中的博主名、项目名、本机路径已做通用化处理，个别措辞可能残留，使用前请通读。
- 脚本里的路径（whisper 虚拟环境等）按你的机器改。
