# combo-style / scripts

这些是从 `<工程目录>/scripts/` 拷来的可复用脚本。**在 Remotion 工程根目录运行**（它们用 `__file__/..` 找 `public/`）；新工程里把它们拷进工程的 `scripts/`。需要 python3 + numpy + scipy + matplotlib + Pillow，ffmpeg 在 `/opt/homebrew/bin/ffmpeg`。

| 文件 | 作用 |
|---|---|
| make_sfx_lib.py | 纯合成 11 个 SFX（whoosh_short/long/down、pop、tick、ding、impact_low、riser、shimmer、swipe、flash）→ `public/sfx/*.wav` + manifest.json。与项目无关，直接可用。 |
| make_sfx_cues.py | 从 timeline 推导 `sfx` 数组（切点/章节/大数字/卡片/叠层/夹头词/末句），抽稀到 ≤0.8 条/秒，写 `sfx_cues.md`。**默认不设 `assets.bgm`**（用户在剪映加音乐），`--with-bgm` 才恢复旧行为；`--rebase` 在 timeline 内容变了时刷新备份。改 `TL` 默认路径或传路径参数。cue 来源规则里的 scene kind / mg 约定是 示例项目 的，换片子按需改。 |
| check_audio_mix.py | 离线模拟人声+SFX（+可选 BGM）混音：LUFS、mix−voice、最响 SFX 相对人声、频谱图 → `review/audio_mix_check.wav/png`。顶部改 `SLUG`。 |
| contact_strip.py | `contact_strip.py <outDir> <rawDir>`：把 `<组>_<帧>.png` 连续帧拼成 3 列联系表，做逐帧运动自查。 |
| make_prompt_pack.py | `make_prompt_pack.py <shotlist.json> <style_bible.md>` → prompt_pack.md + 自包含 prompt_pack.html（COPY 按钮、秒数徽章、勾选、重出备注）。仅标准库。见 references/gemini-asset-prompts.md。 |
| ingest_gen_assets.py | `ingest_gen_assets.py <slug>`：校验用户用 Gemini 生成存进 projects/<slug>/gen/ 的素材，转 1080p/30fps/去音轨、裁时长 → public/projects/<slug>/gen30/，联系表 + OCR（tools/ocr）+ qa_report.md。 |
| apply_transitions_pattern.py | 转场后处理的写法参考（原名 apply_transitions_bee.py）：B-roll→host 交替 zoom_through/slide_push，两处卡片→B-roll 用 wipe/flash_cut，幂等。换片子改 `CARD_TO_BROLL` 的镜头 id。 |
| stills_tl.mjs | `node scripts/stills_tl.mjs <outDir> <timelineSrc> <name:frame>...`：同一浏览器出多张 still，带重试，Google Fonts 慢时比 stills_timeline.mjs 稳。 |
| make_bgm.py | **可选，默认不用**：合成占位铺底。用户自己在剪映加音乐，不要生成/嵌入 BGM。仅作参考。 |
| stills_timeline.mjs | 旧的出图脚本（SKILL.md 第 3 轮）。 |

## 没有拷贝的 示例项目 专用脚本（在 `<工程目录>/scripts/`）
make_bee_full.py（SRT + 镜头表 → full.timeline.json，示例项目 专用）、make_en_timeline.py（英文骨架）、apply_creative_bee.py（创意图形层，按词时间写 `mg` 属性与叠层；是同类需求的写法范例）、make_keyframes_bee.py（样张 timeline）。新片子参照它们的结构另写，不要硬改 id。

## TS 组件在哪、怎么带进新工程
组件不在 Skill 里，在工程 `<工程目录>/src/`（只读，bug 记录下来告诉用户）：
- `src/lib/polish.tsx`：motionPolish 工具（`exitT/fitN/exitStyle/wordOutStyle/SceneExit/MaskWords/riseStyle/cardEnterStyle/dirBlur`）。
- `src/components/mg/`：kit / icons / ChapterMg / LevelLadder / SummaryMg / graphics（创意图形套件）。
- `src/components/SfxLayer.tsx`：`SfxLayer`（播放 `tl.sfx`）与 `BgmLayer`（仅当设了 `assets.bgm`）。
- `src/types.ts`（`SfxCue`、`MgGraphic`、`transitionIn` 类型、`meta.motionPolish/hostLook/cardBg/brollLook`）、`src/tokens.ts`、`src/lib/textWidth.ts`。
**最简单的做法是直接在 `<工程目录>/` 里新建 `projects/<slug>/` 与 `public/projects/<slug>/`**（SKILL.md 目录约定）。若真要搬到全新工程：整体拷贝 `src/`、`public/sfx/`、`package.json`、`remotion.config.ts`，`npm i`，再用上面脚本。
