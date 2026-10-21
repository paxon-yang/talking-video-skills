# 字幕与语音必须对齐（2026-10-18 咖啡机视频暴露；工具与闸门 G5.5 已实现，2026-10-18 第 4 批包 A）

## 已实现（用法）
工程 `<工程目录>`，本机 Apple M2 8GB，已装 **mlx-whisper 0.4.3**（venv `~/.cache/combo-whisper-venv`，Python 3.12；脚本自动切换到该 venv）。
模型：默认 `small` = `mlx-community/whisper-small.en-mlx`（459 MB fp16，缓存 `~/.cache/huggingface/hub/`，151 秒音频约 15 秒识别，峰值内存 2.5 GB）；`--model medium` = `whisper-medium.en-mlx`（1.4 GB，慢 3 倍，峰值 4.2 GB，实测精度没有更好）。8GB 机器不要选 large。以上是英文模型（`.en`，只认英文）；中文用多语种模型，见下面第 4 条。faster-whisper 只是备选（`--engine faster`，未安装未测）。
1. **逐词时间**：`python3 scripts/align_words.py <音频> [--script 稿子.txt|timeline.json] --out words.json [--host-video ..] [--host-audio ..]`
   - 输出格式 = `src/types.ts` 的 `WordsJSON`（帧 @30fps，每词 text/start/end/confidence），另附每词秒数 `t0/t1` 和 `meta`（模型、插值词清单）。
   - 不给 `--script`：文字取识别结果（独立识别，给 G5.5 用）；给 `--script`：文字取稿子、时间取识别（difflib 对齐，识别错词保留稿子拼写，对不上的词按相邻词按字符数插值并写入 `meta.interpolated`，置信度 0.3）。
   - 默认开波形边缘修正：停顿后的词首、停顿前的词尾吸附到音频能量边沿（whisper 在停顿处会偏 0.3-0.7 秒）；`--no-refine` 关闭。
   - 替代 `coffee_words.py` 的估算；`make_*_full.py` 应改读这个文件（**尚未改，属下一步**）。
2. **闸门 G5.5**：`python3 scripts/check_sub_sync.py --timeline <timeline.json> (--words words.json | --audio 预览视频音轨.wav) [--start-tol 3] [--end-tol 6] [--allow-frac 0] [--report x.md]`
   - 每条字幕的首词/末词（difflib 匹配）与字幕 from/to 比较，输出起止漂移（帧，+ = 字幕晚）的均值/最大/P95、整体偏移（中位数）与去掉整体偏移后的残差、最差 N 条、超限清单；起点 > ±3 帧（0.1s）或终点 > ±6 帧、或 > 10% 字幕匹配不上 -> FAIL（退出码 1）。
   - 验收用的识别要**独立**于对齐输入：别用 planner 自己的 words.json。**优先用纯人声轨：`--voice-only <host_full.wav|host.wav>`**（2026-10-19 起）：不给稿子（独立识别）；纯人声轨有干净的真实静音，所以默认加 `--split-pauses`（按静音切开相邻词；`--no-split-pauses` = 原始 whisper）；报告头写明输入来源。**实测（S3，38 条字幕）**：纯人声 + split-pauses 起点平均 +0.27 帧、2/38 超限；纯人声原始 whisper 起点平均 +8.9 帧、27/38 超限；渲染成片混音（`--audio`，原始 whisper）+7.7 帧、24/38 超限。后两者几乎一样，说明大头是 whisper 在停顿后把词起点提前的偏差（S2 的 +7.5），不是音效造成的；纯人声的价值是**能用 split-pauses**（混音里的音效会盖住静音，切不准）。所以：闸门只认纯人声轨，两组数字（split / 不 split）都写进交付说明，FAIL 就写 FAIL，不放宽阈值。`--audio` 保留作参考，不是闸门。
   - 噪声底：验证用识别器自身在停顿处有 ~1.7 帧均值/~5 帧 P95 的误差（示例项目 上小/中模型互比），所以干净文件也可能有个别 >3 帧；看均值、P95 和最差清单，必要时 `--allow-frac 0.1`。
3. **示例项目 实测（只读）**：起点漂移均值绝对值 **26.5 帧（0.88 秒）、最大 68.8 帧（2.29 秒）、P95 58.5 帧**；80 条里 74 条超 ±3 帧；无整体偏移（中位数 -1 帧），是逐块估算误差。完整数字：`<工程目录>/out/sound/SYNC_REPORT.md`。示例项目 不返工。
4. **中文（2026-10-19 起，用户的视频是中文版）**——实测与细节：`<工程目录>/out/zh-sync/SYNC_REPORT_ZH.md`。
   - 流程：拿到 Fish Audio 的 mp3 → `ffmpeg -i voice.mp3 -ac 1 -ar 16000 voice.wav`（ffmpeg 的 mp3 往返实测零偏移）→ `python3 scripts/align_words.py voice.wav --lang zh --script 稿子.txt --out words.json` → `python3 scripts/build_subtitles_from_words.py words.json --timeline <timeline.json> --inplace`（看到 `meta.lang=zh` 自动走中文规则，也可加 `--lang zh`）→ `python3 scripts/check_sub_sync.py --timeline <timeline.json> --voice-only voice.wav --report SYNC_REPORT.md`（字幕里有汉字就自动走中文）。
   - 模型：中文必须用多语种模型（`.en` 模型不认中文）。默认 `turbo-q4` = `mlx-community/whisper-large-v3-turbo-q4`（464 MB，60 秒音频约 12 秒，峰值约 2.4 GB，测试中没有跳段）；`--model multi-small` = `whisper-small-mlx`（481 MB，约 6–8 秒，峰值约 2.5 GB，有一次整段跳过 17 秒，已自动补回）；`turbo`（fp16，1.6 GB，峰值约 3 GB，会出繁体，不推荐）。8GB 机器：一次只跑一个识别进程，别用 large-v3 fp16；缓存里有模型时脚本离线运行（`HF_HUB_OFFLINE=1`）。
   - 对齐：一字一词（英文缩写和数字整体算一个词，数字按读音和识别结果比对：90% = 百分之九十），文字以稿子为准、时间取识别；用 Needleman-Wunsch 序列对齐，能容忍同音字和错字；对不上的字插值，记在 `meta.interpolated`；`meta.align` 给出精确匹配率和含替换的匹配率；whisper 跳过的段、被一个字吞掉的段会把那一小段重新识别（`meta.gapFills`）。标点留在前一个字上（`punct` 字段），分句时用。
   - **中文的停顿切分默认就开**（`--no-split-pauses` 关闭）：不开时字幕起点系统性提前 5–10 帧（真值核对：平均 −9.5 帧）。中文用的是另写的逐字、按标点找停顿的版本；英文的 `split_hidden_pauses` 保持原样（直接套在一字一片上会把逗号前的字挪到停顿后面）。
   - 分句：每条 ≤14 字（不算标点，和 lint 一致）；句末硬断，逗号/顿号/停顿处软断（一个小句一条）；长句按代价切：不切开词（jieba，没有就用内置词表）、不拆「第3步」「2024年」和英文缩写、不在「的了吗」前断、行尾不落在「的/和/把/一定/要」上；不到 4 字或不到 0.6 秒的条与相邻条合并；行尾 ，。 去掉，？！ 保留。jieba 是 `pip3 install --user jieba`（约 37 MB，离线可用）。
   - **英文缩写（RAG / LLM / API / GPU / MCP，2026-10-20 起）**：中文配音里缩写要「逐字母读」，字幕和屏幕只显示缩写本身（RAG）。做法：Fish Audio 的稿子里缩写写成**大写字母、空格分隔**（`R A G`、`L L M`、`A P I`），合成才会逐字母读；字幕里的 `RAG` 靠映射还原。对齐用朗读形式（每个字母占一格，和音频一致），输出时缩写合成**一个词**：`text`=`RAG`，起点=第一个字母起点，终点=最后一个字母终点；字母级时间放在 `meta.letters`（每个字母的 `c/t0/t1`，字母之间有明显静音凹陷才按凹陷分，没有就均分），备查用。两种来源，**`pron.json` 优先，其次自动规则**：
     - `pron.json`（放在稿子或音频所在目录会被自动读到；也可 `--pron 路径`；`--no-pron` 忽略）：`{"RAG": "R A G", "LLM": "L L M", "API": "A P I"}`，键=显示形式，值=朗读形式（用空格/连字符/间隔号分隔的单位；值也可以是汉字读法，如 `"5G":"五 G"`）。稿子里写 `RAG`（没拆字母）或 `R A G` 都能认出来；`_` 开头的键当注释。
     - 自动规则 `--auto-abbr`：稿子里「相邻的单个大写字母，用空格 / 连字符 / 间隔号分隔」（`R A G`、`R-A-G`、`R·A·G`，至少两个字母，前后不能紧贴字母数字）自动还原为 `RAG`。不开则行为与以前逐字节相同。
     - 字幕：`build_subtitles_from_words.py` 与 `check_sub_sync.py` 不用改——words.json 里缩写已是一个词（`RAG`，计 3 个字，不会被拆开，≤14 字照算）；闸门按显示形式读。命令：`python3 scripts/align_words.py voice.wav --lang zh --script 稿子.txt --auto-abbr --out words.json`（或放好 `pron.json`）。
     - 注意：只对 `--lang zh` 且带 `--script` 生效；英文流程不受影响。实测见 `<工程目录>/out/zh-pron/`。
   - 闸门：阈值不变（起点 ±3 帧、终点 ±6 帧）。合成语音实测：字幕起点和真值差最大 0.7 帧，和波形直测差最大 1 帧；但闸门自己的无稿识别在没有标点的句界、不停顿的顿号处会错 5–10 帧，15 次里 5 次 FAIL——FAIL 照实写，再对最差清单用波形或人耳核对，不放宽阈值。**还没在真实配音上验证**，第一条 Fish Audio 配音要复测。
下面「发生了什么」到「规则」是原始诊断与规则，仍然有效；规则 1/5 对应的工具现已存在。

## 发生了什么
咖啡机预览 v1 通过后，用户发现**字幕和语音不太匹配**。该样稿按用户要求不再返工，只沉淀。
示例项目 视频此前没被指出，但用的是同一套方法，同样有风险。

## 根因（已知 + 待证实）
已知：词级时间全是**估算**（`coffee_words.py`：音节权重 + 停顿吸附，误差 ±0.3s，置信度 0.5），字幕块、切点、关键词出现点都依赖它。playbook S6 早就写了"强制对齐工具没有（缺口）"，当时当作可接受误差，结论错了：字幕是观众最先注意到的同步点。
待证实（下次先逐条排查，别猜）：
1. HeyGen SRT 首句比音频晚约 0.2s —— 是否整条有恒定偏移。
2. 25fps 数字人视频转 30fps、`host_full.wav` 的 start_time、Remotion `<Audio>`/`OffthreadVideo` 的起点是否有偏移。
3. SRT 是 HeyGen 对音频做识别得来，文字可能与稿子有出入；字幕文本该用"实际说出的词"，不是稿子。
4. 字幕块拆分（≤7 词）后各块起止是按词数比例切的，块越长漂得越多。

## 规则（以后必须做）
1. **字幕时间来自强制对齐，不来自估算。** 对最终的 `voice_master.mp3`（HeyGen 实际用的那条）跑带词级时间戳的识别：
   - 首选 `pip install faster-whisper`（或 `mlx-whisper`，Apple 芯片更快），`word_timestamps=True`，英文用 `small`/`medium` 模型；
   - 把识别出的词序列和稿子词序列用 difflib 对齐，**时间取识别结果，文字取稿子/实际所说**（识别错词以稿子为准，对不上的词按相邻词插值并记日志）。
   - 产出 `words.json`（每词 t0/t1/conf）替代 `coffee_words.py`；`make_*_full.py` 只读这个文件。
   - 本机已装 mlx-whisper（见「已实现」）。
2. **字幕块起止 = 块内首词 t0、末词 t1**，不再按词数比例切。出现比词早 0 帧、最多晚 2 帧（≤0.07s）；字幕提前出现比滞后更难受，宁可贴着词。
3. **关键词卡/贴字/切点也读 `words.json`**，关键词在词 t0 出现。
4. **整体偏移校准**：渲染前用 ffmpeg 抽 `host_full.wav` 与 master 做互相关，量出恒定偏移，写进 timeline 的 `audioOffset`，别靠肉眼调。
5. **新增自动门槛 G5.5（预览前必跑）** `scripts/check_sub_sync.py`（已写；下面是原设计，实际实现见上方「已实现」，差异：按首词起点/末词终点比较、阈值默认起 ±3 帧/止 ±6 帧、暂无 contact strip）：
   - 对**渲染出的预览视频音轨**再做一次识别（独立于对齐输入），逐字幕块比较"块首词在音频里的开口时间"与字幕出现帧；
   - 任一块偏差 >0.15s 报警，平均偏差 >0.08s 不放行；输出偏差表和最差 5 个时间点；
   - 再抽这 5 个点前后各 0.3s 的 contact strip 给人看一眼。
6. **预览交付时写明**：字幕同步实测偏差（均值/最差），不再写"可能差几帧"这种模糊话。

## 下次改进顺序
~~装 whisper~~、~~align_words.py~~、~~check_sub_sync.py~~、~~示例项目 回测（见 SYNC_REPORT.md）~~ 已完成 -> **剩：改 `make_*_full.py` 读 words.json**（词级时间、字幕块取首末词）-> 咖啡机/新项目上回测。**`make_*_full.py` 没改之前，不要宣称字幕同步。**
