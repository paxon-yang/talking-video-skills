# 音效用法指南：什么时候用哪个音效

> 这份是做片时**选音效的唯一依据**。不要翻着音效库凭感觉挑：先看画面里发生了什么事件，在下面的对照表里找到那一行，用「首选」；同一支片里同类事件已经用过首选、需要变化时才用「备选」。表里没有的事件，先在音效库里按标签找，再去 Freesound 找 CC0，最后才自己合成，并在选型单里写明为什么。

**音效库**：329 个 CC0 短音效（可商用、不用署名），20 类。表里写的 `分类/id` 就是文件位置：
- 网站：`https://www.paxonblocks.com/sfx/audio/<分类>/<id>.mp3`（也可以在 paxonblocks.com「素材 › 音效」里试听、整包下载）
- 积木库（combo-remotion）：`public/sfx/cc0/<分类>/<id>.mp3`，清单 `public/sfx/cc0/sfx.json`（含时长、轻重、标签、原作者）

## 一、六条规矩

1. **有画面动作才有声音**：声音跟着「画面里有东西动了、出现了、被确定了」走，不跟着话走。没有动作的地方不要为了热闹补音。
2. **少而准**：口播片平均每 2 秒最多 1 个音效（≤ 0.5 个/秒）；相邻两个音效间隔 ≥ 0.2 秒，同一个音效相邻 ≥ 0.5 秒；同一时刻只响一个。
3. **重音要省着用**：冲击、蓄力、电影感这些「重」音，一支片 2–4 次，只给开头钩子、章节、大数字、金句。玩梗音效每支片 ≤ 1 次。
4. **永远在人声下面**：音效比人声低 10 dB 以上；成片人声 + 音效 −16 LUFS。过渡页配音暂停时只留一个音效。
5. **卡在命中帧**：点击、弹出、冲击落在画面命中那一帧；呼啸提前 2–3 帧；蓄力的结束点对准揭示帧。不要早于画面，也不要晚于画面。
6. **同一件事用同一个音**：一支片里同类事件用同一个音效（比如所有按钮都是 mouse-click），观众会形成条件反射；只有连续多下才轮换变体。

## 二、场景 → 音效对照表

### 界面操作（录屏、手机、App 演示）

| 画面里发生了什么 | 首选 | 备选 | 卡在哪一帧 | 注意 |
|---|---|---|---|---|
| 按钮按下、勾选、选中、列表逐条点亮、标签落位、图标点亮 | `click/mouse-click`（鼠标点击） | `click/mouse-click-up`、`click/mouse-click-down`、`click/button-simple` | 命中那一帧 | 连续多下用 mouse-click / -up / -down 三个轮换，间隔 ≥ 4 帧，音量逐个递减 8% |
| 打开菜单、切换选项、Tab 切换 | `click/menu-tick`（菜单切换） | `click/menu-scroll`、`click/menu-click` | 切换那一帧 | 滚动列表时不要每格都响，只在停住时响一下 |
| 开关拨开 / 关掉 | `click/mouse-click-up`（鼠标点击（升调）） | `click/tv-switch-off`、`glitch/zap` | 拨动那一帧 | 开用 mouse-click-up，关用 tv-switch-off；「通电亮起」才用 zap |
| 输入框打字、逐字出标题（短句） | `typing/typewriter-short`（打字机短句） | `typing/digital-typing`、`typing/typewriter-key` | 第一个字出现 | 超过 1.5 秒的长句改用 keyboard-typing 按字数裁短，别从头放到尾 |
| 长段打字、写 Prompt | `typing/keyboard-typing`（键盘打字） | `typing/keyboard-mech`、`typing/typing-sending` | 第一个字出现 | 按画面打字时长裁剪，结尾淡出 3 帧 |
| 回车发送、提交 | `typing/key-enter`（回车键） | `typing/typewriter-bell-return`、`notify/message-sent` | 按下回车那一帧 | 发出去后如果画面有气泡飞走，再接 whoosh-short |
| 聊天消息到达、AI 回复弹出 | `notify/message-receive`（收到消息） | `notify/chime-notification`、`notify/text-message` | 气泡出现那一帧 | 一屏连续好几条消息，只给第一条和最后一条 |
| 手机通知、来消息 | `notify/chime-notification`（清脆通知） | `notify/text-message`、`notify/notify-pluck` | 通知横幅落下那一帧 | 手机振动画面用 phone-buzz-short |
| 截图、定格一张画面 | `shutter/shutter-phone`（手机快门） | `shutter/iphone-capture`、`shutter/shutter-short` | 白闪那一帧 | 照片从画面里翻出来用 shutter-film；连续展示多张图用 shutter-burst |
| 数据加载、AI 正在生成、扫描 | `typing/data-reveal`（数据显现） | `typing/digital-typing`、`riser/sweep` | 进度开始那一帧 | 只放一次，生成很久的画面不要循环铺满 |

### 元素出现与移动

| 画面里发生了什么 | 首选 | 备选 | 卡在哪一帧 | 注意 |
|---|---|---|---|---|
| 关键词牌、标签、图标弹出 | `pop/ui-pop-a`（界面弹出 A） | `pop/pop-short-a`、`pop/pop-short-b` | 元素最大那一帧（弹簧顶点） | 同一屏多个依次弹出：pop-short-a / -b 轮换，或直接用 toony-pops 一条 |
| 气泡、药丸、小圆点出现（更软） | `pop/pop-hollow`（空心弹出） | `pop/bubble`、`pop/pop-02` | 出现那一帧 | 比 ui-pop-a 更轻，适合背景里的小元素 |
| 弹窗、提示框出现 | `pop/popup-notify`（弹窗出现） | `pop/ui-pop-b`、`pop/pop-classic` | 弹窗出现那一帧 | 报错弹窗换成 error-tone |
| 卡片、截图、窗口飞入 | `whoosh/whoosh-short`（短呼啸） | `whoosh/swoosh-tiny`、`whoosh/swoosh-1` | 提前 2–3 帧开始 | 飞出不用再配，下一个镜头的声音会盖住 |
| 卡片甩入 / 甩出、卡牌左右滑 | `slide/swipe-quick`（快甩） | `slide/card-slide-right`、`slide/card-slide-left` | 开始移动那一帧 | 左右成对出现时用 card-slide-right / -left |
| 文档、纸张、长页面滑入 | `slide/paper-swipe`（纸张长滑） | `slide/envelope-slide`、`slide/paper-slide` | 开始移动那一帧 | 长页面斜视角从头滑到尾时，只配开头一下 |
| 翻页、下一页 | `paper/page-turn`（翻页） | `paper/page-turn-b`、`paper/page-turn-c` | 纸张翻过中线那一帧 | 翻很多页只配第一页 |
| 画圈、划重点、下划线 | `writing/marker-circle`（马克笔画圈） | `writing/scribble-short`、`writing/sharpie-paper` | 笔画开始那一帧 | 声音长度跟笔画动画对齐，裁掉多余部分 |
| 打勾、确认一项完成 | `writing/pencil-check-2`（铅笔打勾） | `writing/pencil-check-1`、`click/mouse-click` | 勾画完那一帧 | 清单最后一项再加 correct |
| 签名、签字确认 | `writing/pen-signature`（签名） | `writing/signing-pen` | 笔开始动那一帧 | — |
| 白板、黑板讲解写字 | `writing/whiteboard-marker`（白板笔） | `writing/chalk-board`、`writing/pencil-writing` | 笔开始动那一帧 | — |
| 盖章、下定论 | `paper/stamp`（盖章） | `paper/stamp-b`、`impact/impact-hit` | 章落下那一帧 | 一支片最多一次 |

### 镜头与转场

| 画面里发生了什么 | 首选 | 备选 | 卡在哪一帧 | 注意 |
|---|---|---|---|---|
| 普通镜头切换 | `whoosh/swoosh-clean`（干净转场） | `whoosh/whoosh-short`、`whoosh/swish-wipe` | 提前 2 帧 | 不是每一刀都配：隔一刀配一个，同类镜头硬切可以不配 |
| 章节过渡页（第 N 步） | `whoosh/whoosh-deep`（低沉呼啸） | `riser/cinematic-woosh-15`、`whoosh/swoosh-long` | 过渡页开始那一帧 | 过渡页期间配音暂停，只留这一个音效 |
| 推近、拉远到重点 | `riser/zoom-up`（极速拉升） | `whoosh/whoosh-mid`、`whoosh/swish-up` | 推近开始那一帧 | 只给讲解点的那一次推近，慢推慢摇不配 |
| 从屏幕回到主播、换场景 | `whoosh/whoosh-mid`（中速呼啸） | `whoosh/metallic-whoosh`、`whoosh/double-swoosh` | 提前 3 帧 | — |
| 回到过去、倒回去重来 | `cartoon/vinyl-rewind`（倒带） | `glitch/glitch-tape` | 倒放开始那一帧 | 一支片最多一次 |
| 故障转场、画面撕裂 | `glitch/glitch`（故障音） | `glitch/glitch-static`、`glitch/glitch-01` | 故障第一帧 | 科技 / AI 主题才用 |

### 强调（重音，一支片 2–4 次）

| 画面里发生了什么 | 首选 | 备选 | 卡在哪一帧 | 注意 |
|---|---|---|---|---|
| 大数字揭示 | `riser/riser-short`（短蓄力） | `riser/bass-rise`、`riser/riser` | 蓄力结束点 = 数字出现那一帧 | 数字落地那一帧再接 impact-hit；数字滚动过程中不加连续音 |
| 大字砸下、定性词落地 | `impact/impact-hit`（硬切重击） | `impact/punch`、`impact/major-punch` | 字落地那一帧 | 比 impact-bass 轻，口播里更常用 |
| 章节标题、开头钩子大标题 | `impact/impact-bass`（低音冲击） | `impact/sub-bass-drop`、`impact/impact-cinematic` | 标题落地那一帧 | 最重的一档，一支片 ≤ 2 次 |
| 金句、核心结论前的铺垫 | `riser/riser-glass`（玻璃反向镲） | `riser/reverse-cymbal`、`riser/cinematic-woosh-09` | 结束点 = 金句第一个字 | 后面接 chime-crystal 或 impact-hit，二选一 |
| 金句落定、重点高亮 | `ding/chime-crystal`（答对提示 A） | `sparkle/item-sparkle`、`ding/ding-clean` | 高亮出现那一帧 | 金色高亮可以再叠 item-sparkle（+5 帧，音量减半） |

### 结果与情绪

| 画面里发生了什么 | 首选 | 备选 | 卡在哪一帧 | 注意 |
|---|---|---|---|---|
| 答对、做成了、搞定 | `ding/correct`（答对了） | `ding/chime-crystal`、`success/correct-choice` | 结果出现那一帧 | — |
| 成果揭晓、最终效果亮相 | `success/tada-a`（Tada 号角） | `success/achievement-sparkle`、`success/glockenspiel-treasure` | 成品出现那一帧 | 一支片最多一次，留给最后的「看，做出来了」 |
| 解锁新技能、升级 | `success/level-up`（升级） | `success/powerup`、`ding/unlocked` | 图标亮起那一帧 | — |
| 答错、踩坑、这样不行 | `error/wrong-answer`（答错了） | `error/wrong-choice`、`error/negative-beeps` | 红叉出现那一帧 | 知识片里用轻的 wrong-choice 更多；buzzer 太综艺，慎用 |
| 报错、AI 出错、系统崩了 | `error/computer-error`（电脑报错） | `error/error-tone`、`glitch/glitch` | 报错弹窗那一帧 | 画面有故障效果时用 glitch |
| 警告、注意、风险 | `error/beep-warning`（警告哔声） | `error/error-signal`、`ding/alert` | 警告图标出现那一帧 | — |
| 钱：赚钱、省钱、价格、成本 | `coin/cash-register`（收银机） | `coin/coin-pickup`、`coin/coins` | 价格数字出现那一帧 | 小金额、多次出现用 coin-pickup；一屏只响一次 |
| 时间紧、倒计时、等待 | `tick/tick-tock`（滴答钟） | `tick/countdown-fast`、`tick/clock-tick` | 倒计时开始那一帧 | 倒计时归零用 oven-timer-done |
| 一键变出来、AI 魔法般完成 | `sparkle/magic`（魔法） | `sparkle/poof-cloud`、`sparkle/magic-burst` | 东西变出来那一帧 | 用在「AI 自动做完」，别每个生成都配 |

### 玩梗与观众反应（每支片 ≤ 1 次，只在真有梗的地方）

| 画面里发生了什么 | 首选 | 备选 | 卡在哪一帧 | 注意 |
|---|---|---|---|---|
| 反转、尴尬、急刹车 | `cartoon/record-scratch`（唱片急停） | `cartoon/slide-whistle` | 反转那句话的第一个字 | — |
| 搞笑、蹦出来、弹一下 | `cartoon/cartoon-boing`（卡通弹簧） | `cartoon/bounce`、`cartoon/cartoon-pop-dist` | 动作那一帧 | 严肃话题不用 |
| 惊讶、没想到 | `crowd/gasp`（倒吸一口气） | `crowd/crowd-shock`、`crowd/kids-woah` | 惊讶点后 2 帧 | — |
| 被逗笑、自嘲 | `crowd/crowd-laugh`（观众大笑） | `crowd/woman-laugh` | 梗说完之后 | — |
| 认可、鼓掌、值得表扬 | `crowd/small-applause`（小掌声） | `crowd/cheer`、`crowd/yay` | 结论说完之后 | 音量压到人声以下 14 dB |

## 三、口播知识片默认配方（60–90 秒）

| 段落 | 音效 |
|---|---|
| 开头钩子（0–3 秒） | 1 个：impact-hit 或 riser-short→impact-hit |
| 每个章节过渡页 | 1 个：whoosh-deep（配音暂停） |
| 实操录屏段 | 点击 mouse-click、打字 typewriter-short/keyboard-typing、发送 key-enter、消息 message-receive，跟着画面操作走 |
| 关键词、卡片 | ui-pop-a / whoosh-short，隔一个配一个 |
| 大数字、金句 | riser-short→impact-hit；chime-crystal |
| 成果亮相 | tada-a 或 correct，全片一次 |
| 结尾 | chime-crystal 一个 |

全片合计通常 20–40 个音效。做完数一下：超过「时长秒数 ÷ 2」就删，先删没有画面动作对应的。

## 四、音量（Remotion `volume`，人声 = 1.0）

| 类别 | volume |
|---|---|
| 点击、弹出、打字 | 0.22–0.30 |
| 呼啸、滑动、翻页 | 0.28–0.32 |
| 提示铃、通知、成功 | 0.30–0.34 |
| 冲击、蓄力 | 0.26–0.40 |
| 观众反应、玩梗 | 0.25–0.30 |

## 五、别这样做

- 每句字幕、每个字都配音
- 整片铺满呼啸，每一刀都「嗖」
- 两个音效同一帧叠在一起
- 严肃、走心的段落里放搞笑音和观众笑声
- 数字滚动、长时间生成时放循环音
- 音效比人声还响，或者为了「听得见」把音量拉高
- 库里有合适的还自己合成（顺序：先库，再 Freesound CC0，最后才合成）

## 六、选型单怎么写

音效和积木一样进选型单，一行一个：

```
时间    | 画面事件            | 音效                 | 为什么
00:03.2 | 大标题「7 小时」落地 | impact/impact-hit    | 定性词砸下，开头钩子
00:12.5 | 点击「生成」按钮     | click/mouse-click    | 界面操作，命中帧
```

交付时报一句：本片共几个音效、平均几秒一个、重音几次。
