# M5 固定状态画面回归记录

日期：2026-10-21。实施基线：`0579ab7`。

**状态：2026-10-23 按调整后范围完成验收。** 用户在本聊天审阅候选图与 M1 对照、了解批准含义后回复“可以”，批准全部 140 个状态及预期变化。已保存参考图、原始采集记录与批准记录，并用新的独立进程采集验证参考图比较流程。

收尾证据：核对原有 166 张图像、29 个源码/素材哈希和采集/清单/比较器哈希均匹配；未重复运行已通过的 9 项比较器合成测试。`tests/visual/reference/` 保留 146 张原图和未修改的 `capture.json`，批准日期为 2026-10-23，原始记录 SHA-256 仍为 `5ef8afe48d3cb941f6db76514d93554827fda42e87526f9414d8d035cd94c186`。

新的完整 GPU 采集在 `artifacts/m5/capture-approved-check/`，比较报告在 `artifacts/m5/review-approved-check/report.json`：140 项已批准参考图比较、98 项行为断言、20 项独立默认图重复检查全部通过，失败 0。实际图来自新的独立进程，未把参考图与自身比较。M4/M5 已取消的全库检查未补跑。以下保留 2026-10-21 的采集历史；其“待确认”描述已由本段批准及收尾结果取代。M6 将另行实施和记录。

用户已明确将 M5 本轮验收限定为首批 20 项 × 7 状态、重复性及参考图验收，并取消原计划中的 421 项全库运行检查。本轮没有执行该检查，不能写成全库通过。M4 已取消的全库 GPU 验收也没有补跑。后续 M6 的独立实施与回归范围见 [M6 记录](M6_VERIFICATION.md)。

## 已实现与本机结果

| 项目 | 结果 |
|---|---|
| 固定状态清单 | `tests/visual_cases.json`：20 项 × 7 状态 = 140；逐项列出参数、区域、时间、事件和行为阈值 |
| 实际采集 | 140 张正式状态图，另有 6 张玻璃、零波高、事件过期和 CRT 全零对照图 |
| 画面行为 | 98 项断言通过，失败 0：端点、透明度、内部颜色、参数变化、时间/事件、零值恢复、高斯纯色/硬边与中性 LUT |
| 独立进程重复性 | 另采集 20 张默认图；20 项通过；最大 RGB 均差 0，差异像素比例 0，alpha 差 0 |
| 比较器合成测试 | 9 项通过，覆盖局部漂移、alpha 丢失、范围、缺图、不完整采集、图片篡改和未批准/过期批准记录 |
| 安全生成与差异 | 生成器仅更新 README 及对应清单哈希；`CHECK OK files=1771`，Git 空白检查通过 |
| 差异报告 | 98 张行为差异图和 20 张默认重复差异图；另有四页 140 状态图集及四页 M1 历史对照 |
| 已批准参考图比较 | 2026-10-23 新独立采集与已批准图库比较：140 项通过，失败 0 |
| 运行代码、Shader 与 M1 样本 | 未改动；README 通过修改生成源再安全生成 |

环境：Windows、Godot `4.7.2-stable (official)`、Forward+ / Vulkan、RTX 5060、NVIDIA 驱动 `32.0.15.8097`。预览为 640×480，随机种子 20261021，MSAA / TAA / 屏幕空间抗锯齿关闭；相机方位 0、仰角参数 0.28、距离 5、FOV 43，曝光 1。截图脚本每次只保留一个效果场景，限制到 30 FPS，完成绘制后再读取图片。Python 3.13.14、Pillow 12.3.0、NumPy 2.4.6；没有安装新依赖。

本轮 GPU 日志未出现脚本错误、Shader 错误、内存分配失败或 RID 警告。这不证明原有全库退出时的 7 个 Texture RID 释放警告已解决；其来源仍未定位，M4 的历史内存失败记录保持。结果仅适用于上述本机环境，不代表其他显卡、系统或 Mobile / Compatibility / Web。

## 固定输入、时间和阈值

- 每项恰好七个正式状态：关闭、默认、主参数最小、主参数最大、次参数变化、较早、较晚。静态效果跨时间应保持；动态效果按清单声明变化或周期关系。
- 常规时间为 1 秒，较早 0.5 秒，较晚 2 秒。闪白默认 0.075 秒，涟漪/护盾默认 0.25 秒；三项早期状态为触发前，默认/参数状态在时间 0 单次触发，晚期为 2 秒的过期状态。涟漪/护盾从固定局部表面点投影，调用实际 `trigger_at()`，未命中会失败。
- 精灵使用原透明图案、隐藏背景并保留 RGBA；高斯使用左侧纯色、右侧黑白硬边图；LUT 使用 RGB 渐变及蓝色最大值测试图；其余保留现有展示素材。这些输入和 640×480 尺寸与 M1 的 900×660 展示样本不同，M1 并排图只供观察，不宣称逐像素相等。
- 重复性门槛不变：归一化 RGB 均差 ≤ `1/255`，任一 RGB 通道差值超过 `3/255` 的像素比例 ≤ 0.1%。已批准参考图的门槛为均差 ≤ `2/255`，通道差超过 `8/255` 的像素比例 ≤ 1%。比较器还检查 alpha，不以 RGB 相同掩盖透明度丢失。
- 行为比较采用清单逐项阈值；静态同图、零宽、零强度等应恢复原图的情况严格比较。高斯纯色/中性 LUT 允许 1 个色阶；玻璃背景对照允许 2 个色阶。差异图将绝对 RGBA 差异放大 4 倍，范围与数值见 `report.json`。

## 首轮失败与定位

首次 `capture-a / capture-b` 的默认图已完全一致，但两项行为断言失败，记录保留在 `artifacts/m5/review-a/`：

1. 扫光默认周期为 1.5 秒，0.5 秒与 2 秒正好同相位，不能断言它们必须不同。清单改为验证周期回到原相位（允许浮点相位导致的 1 个色阶舍入），另验证 0.5 秒和 1 秒的不同相位确实变化；未改变全局比较阈值或 Shader。
2. 外描边 PNG 中两个边界像素的 alpha 被量化为 255，RGB 有 1 个色阶差；不能据此把滤波边界当成不透明内部。现在用 3×3 全不透明邻域定义内部，内部颜色仍严格相等；同时检查外部确实扩宽、alpha 不收缩。实际内部误差为 0；没有改变描边公式。

最终清单重新执行 140 状态及独立默认图采集，98 项行为和 20 项重复性检查全部通过；旧报告未覆盖。

## 人工审阅与待办

审阅入口：[完整图集与报告](../artifacts/m5/review-final/REVIEW.md)。

| 图集 | 效果编号 | M1 对照 |
|---|---|---|
| [第 1 页](../artifacts/m5/review-final/states_1.png) | 001、002、007、017、018 | [历史对照 1](../artifacts/m5/review-final/m1_comparison_1.png) |
| [第 2 页](../artifacts/m5/review-final/states_2.png) | 034、037、270、271、296 | [历史对照 2](../artifacts/m5/review-final/m1_comparison_2.png) |
| [第 3 页](../artifacts/m5/review-final/states_3.png) | 297、298、112、118、192 | [历史对照 3](../artifacts/m5/review-final/m1_comparison_3.png) |
| [第 4 页](../artifacts/m5/review-final/states_4.png) | 190、096、326、317、348 | [历史对照 4](../artifacts/m5/review-final/m1_comparison_4.png) |

核对 M1 时的预期变化包括：M3 的溶解/进度端点、专用参数默认值、单次事件、真实双遍高斯、中性 LUT 与边界修正；另有上述测试素材、透明背景和尺寸变化。已查看 20 项总览，未把机器检查或代理查看视为用户对参考图的批准。

待用户确认全部 140 个状态及预期变化后，按 [参考图确认流程](../tests/visual/README.md) 保存到版本控制中的 `tests/visual/reference/`，记录批准者、日期和采集哈希，再执行已批准参考图比较。确认前，所有采集记录的 `approved_visual_reference` 均为 false，报告状态为 `awaiting_human_reference_review`；禁止自动覆盖 M1 或将失败输出当成正确答案。

## 复查与证据

下列采集输出目录必须尚不存在；复查时换新目录，不覆盖本次证据。两次 GPU 命令串行执行，不加 `--headless`：

```powershell
python tools/compare_visuals.py --validate-only
python -B -m unittest discover -s tools/tests -p test_visuals.py -v
& 'E:\Godot\Godot_v4.7.2-stable_win64_console.exe' --path . --rendering-method forward_plus --rendering-driver vulkan --resolution 640x480 --max-fps 30 --script res://tools/capture_visuals.gd -- --output=res://artifacts/m5/capture-new
& 'E:\Godot\Godot_v4.7.2-stable_win64_console.exe' --path . --rendering-method forward_plus --rendering-driver vulkan --resolution 640x480 --max-fps 30 --script res://tools/capture_visuals.gd -- --output=res://artifacts/m5/repeat-new --defaults-only
python tools/compare_visuals.py artifacts/m5/capture-new --repeat artifacts/m5/repeat-new --output artifacts/m5/review-new
```

人工批准并保存参考图后，才给最后一条命令追加 `--reference tests/visual/reference`。诊断可用 `--only=编号` 采集单项；比较器拒绝将不完整或单项采集当作完整 M5 验收。

本机忽略目录证据：`artifacts/m5/capture-final/`、`repeat-final/`、`review-final/`，以及 `artifacts/m5-capture-final.log`、`artifacts/m5-repeat-final.log`。完整采集记录 SHA-256：`5ef8afe48d3cb941f6db76514d93554827fda42e87526f9414d8d035cd94c186`；清单 LF 文本 SHA-256：`2376bbe09fe6fe0e857f1cf3265f12e36e500103b38e3bc541ce463db74fd595`。采集记录保存源码、素材和每张 PNG 的哈希；比较报告另保存清单、比较器哈希及图像库版本。

方案调研：[Godot 绘制完成信号](https://docs.godotengine.org/en/stable/classes/class_renderingserver.html#class-renderingserver-signal-frame-post-draw) 用于等待真实视口绘制；[Pillow](https://pillow.readthedocs.io/en/stable/about.html) 免费、MIT-CMU 开源且本机已有，配合 NumPy 按项目原定 RGB 阈值比较。[Pixelmatch](https://github.com/mapbox/pixelmatch) 也是免费开源方案，但其感知色差和 Node 工具链不适合直接替代本项目已定的 RGB 数值门槛，因此未引入。
