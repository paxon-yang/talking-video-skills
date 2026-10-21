# AE 表达式 → Remotion 函数对照表

工具包在工程 `<工程目录>/src/motion/ae/`（`math.ts` 纯函数可在 node 里用，`index.ts` 另含 React 部分）。所有函数吃**秒**（`frame / fps`），确定性（噪声按种子，不用 `Math.random` / `Date`）。数值核对：`node scripts/verify_ae_math.mjs --md out/ae-cards/verify_ae_math.md`（95 项，全部通过，2026-10-20）。多卡片积木在 `src/motion/cards/`，规则见 principles.md 第 19 节。

## 1. 插值与关键帧
| AE | Remotion（`import … from './motion/ae'`） | 说明 |
|---|---|---|
| `linear(t, tMin, tMax, v1, v2)` | `linear(t, tMin, tMax, v1, v2)`；数组值也行 | 超出范围钳住，同 AE |
| `ease()` / `easeIn()` / `easeOut()` | `ease` / `easeIn` / `easeOut` | 曲线取 lottie-web 为对齐 AE 用的三条贝塞尔：ease (.33,0,.667,1)、easeIn (.333,0,.833,.833)、easeOut (.167,.167,.667,1)，即 33.33% Easy Ease 对 16.67% 线性；**ease 不严格对称**（ease(0.5)=0.5017） |
| 缓动预设「三次 / 五次」 | `PENNER.inCubic / outQuint / inOutQuint …`，或 `easeInCubic(t,tMin,tMax,v1,v2)` | 另有 quad、quart、sine、expo、circ、back |
| 图表编辑器：关键帧速度 + 影响 | `keyframes([{ t, v, easeOut: { speed, influence }, easeIn: {…}, interp }])` | speed 单位 = 值/秒，influence 为 %；缺省一侧 = 线性（影响 16.67%）；`interp:'hold'` 定格；数组值按直线路程走（speed = 像素/秒） |
| 速度 / 影响 ↔ CSS 贝塞尔 | `speedInfluenceToBezier(dt, dv, out, in)`、`bezierToSpeedInfluence(b, dt, dv)` | P1 = (iA, sA·iA·dt/dv)，P2 = (1−iB, 1−sB·iB·dt/dv)；Easy Ease → (0.3333, 0, 0.6667, 1) |
| `velocityAtTime(t)` | `velocityAt(fn, t)` / `velocityAtV` / `speedAtV` | 中心差分 1 ms |

```ts
// 出点 200 px/s、影响 33%；入点速度 0、影响 80%（长尾进站）
const x = keyframes([{ t: 0, v: 0, easeOut: { speed: 200, influence: 33 } }, { t: 2, v: 100, easeIn: { speed: 0, influence: 80 } }]);
const px = x(frame / fps);
```

## 2. 惯性、弹跳、弹簧、过冲、预备
| AE | Remotion | 说明 |
|---|---|---|
| 经典惯性回弹 `value + v*amp*Math.sin(freq*t*2*Math.PI)/Math.exp(decay*t)`（n 个关键帧通用） | `inertialBounce(base, keyTimes, { amp, freq, decay })`，向量用 `inertialBounceV` | v 取「关键帧前 frameDuration/10」的速度，同 AE；首个关键帧之前不加 |
| 让落点速度连续的 amp | `continuousAmp(freq)` = 1/(2π·freq) | AE 默认 amp .05 / freq 4 落地瞬间速度跳 +26%；用这个 amp 就不跳 |
| 弹跳落地（重力 + 弹性） | `bounceLand(t, { v0, e, g, nMax })` | 返回落点之上的高度 |
| 阻尼弹簧（欠阻尼 / 临界 / 过阻尼） | `spring(t, { freq, zeta, v0 })` 或 `{ stiffness, damping, mass }` | 闭式解，已与 RK4 对过；`springOvershoot(zeta)`、`springSettle(o)` |
| 过冲缓动 | `overshootEase(p, s)`、`backSForOvershoot(0.1)` → 1.70158 | Penner back |
| 预备动作（先往回拉） | `anticipation(p, { pull, ratio })` | 回拉段末速度为 0，再起步，转折处速度连续 |

```ts
const base = keyframes([{ t: 0, v: 0, easeOut: { speed: 6.5, influence: 20 } }, { t: 0.2, v: 1, easeIn: { speed: 2.5, influence: 25 } }]);
const p = inertialBounce(base, [0, 0.2], { freq: 1.25, decay: 8, amp: continuousAmp(1.25) }); // = 卡片积木的「惯性回弹」预设
```

## 3. 时间：跟随、循环、平滑
| AE | Remotion | 说明 |
|---|---|---|
| `thisComp.layer(index-1).position.valueAtTime(time - d)` | `delayed(fn, d)` | 纯延迟 |
| 跟随链（每层跟上一层，延迟 + 拖尾） | `followChain(leader, n, { delay, damping })` | 第 k 个 = 延迟 k·delay，再做 k 阶低通（时间常数 damping·delay）；damping 0 = 纯 valueAtTime |
| 单个跟随者 / 弹簧跟随 | `follow(leader, delay, damping)`、`followSpring(leader, { freq, zeta })` | followSpring 固定步长仿真，确定性，适合短镜头 |
| `loopOut("cycle" / "pingpong" / "offset" / "continue")` | `loopOut(fn, type, tA, tB)`；`loopIn` 同 | tA/tB = 参与循环的首末关键帧时间 |
| `smooth(width=.2, samples=5)` | `smooth(fn, 0.2, 5)` / `smoothV` | 窗口均值 |
| 时间重映射 / 总速度滑块 | `timeRemap(t, speed)`、`controlledTime(t, controls)` | |

## 4. 序号驱动错峰
| AE | Remotion | 说明 |
|---|---|---|
| `delay = (index-1) * d` | `staggerPlan(n, { delay })[i].start` | |
| 错峰与总时长联动 / 重叠比例 | `staggerPlan(n, { total, overlap })` | dur = total / (1 + (n−1)(1−overlap))，delay = dur·(1−overlap)，最后一个正好在 total 结束 |
| 顺序 / 反向 / 中心扩散 / 两端向内 / 随机 / 螺旋 / 波浪 / 径向 / 按行 / 按列 | `staggerRanks(n, { order: 'forward'…'cols', grid, wave, origin, seed })` | 随机按种子 |
| 错峰带缓动 | `staggerPlan(n, { ease: 'outCubic' })` | rank → 开始时间的映射 |
| 人味（间隔不等） | `staggerPlan(n, { jitter: 0.75, seed })` | 参考片间隔 CV 0.35–1.1，0.75 ≈ CV 0.4–0.6 |

## 5. 噪声
| AE | Remotion | 说明 |
|---|---|---|
| `wiggle(freq, amp, octaves, amp_mult, t)` | `wiggle(t, freq, amp, octaves, ampMult, seed)`、`wiggleV(t, dims, …)` | 1D 梯度噪声，五次 fade（加速度连续），按种子确定 |
| `seedRandom(seed, true); random()` | `mulberry32(seed)()` | |

## 6. 父子、空物体、摄像机、景深、滑块
| AE | Remotion | 说明 |
|---|---|---|
| 父子关系 / 空物体控制器 | `xform({ x,y,z,rx,ry,rz,s,ax,ay,az })`、`parentChain(nullM, childM)`、`applyM`、`toCss` | 4×4 列主序，等同 CSS matrix3d；旋转顺序按 CSS（X→Y→Z） |
| 单节点摄像机（50 mm） | `aeCamera({ mm: 50 })`：zoom = 1920·50/36 = 2666.7，z = −zoom | z = 0 的层显示为 100% |
| 层在摄像机里的位置与缩放 | `project([x,y,z], cam)` → `{ sx, sy, scale = zoom/depth, blur }` | 视差 = 不同 z 的层在同一次平移里屏幕速度之比 = scale 之比 |
| 景深（光圈 + 焦距 + 模糊级别） | `aeCamera({ aperture, focusZ, blurMax })`，`project().blur` | 简化为 aperture·|d−f|/d（薄透镜弥散圆），aperture = 无穷远处的模糊像素；不是 AE 精确公式 |
| 摄像机动画 / 焦点距离动画 | `cameraAt(base, [{ t, z, focusZ, easeOut, … }])` | 每个通道走 keyframes() |
| Expression Controls 空物体（一个滑块驱动多层） | `<AEControlsProvider value={{ speed, amp, drift, stagger, motionBlur, dof }}>` + `useAEControls()` | 卡片积木都读它 |

## 7. 运动模糊
| AE | Remotion | 说明 |
|---|---|---|
| 图层运动模糊（快门角度 / 相位 / 每帧采样） | `<MotionBlur samples={8} shutterAngle={180} shutterPhase={-90}>…</MotionBlur>`；渲染函数版 `<MotionBlurFn render={(f) => …} />` | 子树里用 `useAEFrame()` / `useAETime()` 的组件才会被采样；`mode:'add'`（plus-lighter 平均）对透明层也准，旧的 `'over'` 只对不透明整帧准 |
| 只在动的时候算 | `active={(frame) => moving(frame)}`；卡片舞台按每张卡在快门内位移 > 6 px 才超采样 3–8 次 | 成本 = 采样数 × 子树 |

**什么时候用**：快速平移、甩镜（整个世界一起动，M3）、飞入飞出、旋转木马转动、弹出。**什么时候不用**：观众要读的文字层和 UI 面板、静止元素（复刻 A：面板加模糊 B3 0.864→0.854、B6 0.872→0.859）；甩镜时外层已超采样，就关掉内层每张卡的模糊（Showcase 的做法）。


## 8. 实测曲线与「不停 / 跨切」配方（`ae/presets.ts`，数值来自 E 系列拆解 Ew1/Ew2/Ew3）
素材里没有任何字幕说明是用表达式做的；下面是「同样运动特征」的函数版。
| 现象 | Remotion | 数值 |
|---|---|---|
| 减速但不停（玻璃框急停后恒速、环旋转底速） | `coast(t, { v0, vBase, k })`、`coastVelocity`；已有落位曲线加底速 `coastSettle(settle, vBase, ramp)` | E01 玻璃框 4 帧剩余 ×0.5 后 ≈700 px/s@1920；环底速 23°/s |
| 跨硬切延续（切前缩小+旋转，切后从过大继续缩、继续转） | `continueAcrossCut(velocity, { target, k })` → `{ x0, at(t) }`；缩放在对数空间用 | 起点 = 目标 + 速度/(30·ln k)；E01 星标 ×0.74/帧（2.3×→1×），旋转 ×0.8/帧（≈120°） |
| 卡片环（整环相似变换） | `ringSpin(t)`、`ringScale(t)`；积木 `CardRing` | Ew1：0.77°/帧 + 1.88°/帧×0.928ⁿ，−ln s 0.028×0.981ⁿ；积木默认按单卡跟踪改为 4.0°/帧×0.85ⁿ、0.93 |
| 两行互换 | `CURVES.swapExpo`（1−2^(−10p)，0.3 s）、`CURVES.splitOut`（0.15 s） | 第 1 帧走 ≈60% |
| 3D 平面内滑屏 | `CURVES.pageOut` bezier(0.6,−0.1,0.95,0.9) 0.32 s、`CURVES.pageIn` bezier(0.4,0.3,0.8,1.1) 0.40 s | 靠方向模糊盖住两段速度不衔接 |
| 画面内回正 / 显示器拉远 | `CURVES.reframe` (0.55,0,0.4,1) 0.7 s、`CURVES.monitorPull` (0.25,0.1,0.7,1) 0.3 s | 对称 ease，尾巴短 |
| 过冲贝塞尔（与弹簧拟合质量相近） | `CURVES.overshoot` (0.52,2.02,0.26,0.73) 0.77 s | E06 圆→药丸 |
| 数字滚轮停靠 | `CURVES.wheelDock.k` = 0.753/帧 | τ 0.117 s，t90 0.27 s |
| E06 全局弹簧 | `spring(t, { stiffness: 155, damping: 10, mass: 1, v0: 6 })`；积木 `ShapeMorph` | ζ 0.40，T 0.55 s，满速起步 |
| 逐词上浮 / 中文逐字阶梯 / 两行拆分互换 | `LineStagger mode: 'wordRise' / 'zhStair' / 'lineSwap'` | k 0.79、词间 0.133 s；15 字/s、×0.6/帧；见 principles 第 19 节 X11 |

```ts
// 环塌缩后硬切到图标，继续同向转、继续缩（CardRing cutTo 的内部做法）
const rot = continueAcrossCut(ringDegPerSec, { target: 0, k: 0.8 });          // deg
const sc = continueAcrossCut(ringLnScalePerSec, { target: 0, k: 0.74 });      // ln(scale)
style={{ transform: `rotate(${rot.at(t)}deg) scale(${Math.exp(sc.at(t))})` }}
```
