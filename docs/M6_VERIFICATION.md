# M6 浏览与性能验收

日期：2026-10-23。实施基线：`45ab0f0`（M5 收尾与原始记录换行保护之后）。M5 参考图于本聊天获得用户批准，详情见 [M5 记录](M5_VERIFICATION.md)。

状态：M6 实施及本机规定范围验证完成。整帧 CPU、预览独占内存、冷启动与完整图库 UI 切换延迟未测，明确保留为测量缺项；资源释放仍未通过验收。不实施其他里程碑，不推送。

## 改动

- `shared/gallery.gd` 使用可重启的原生 Timer 合并搜索输入，等待 150 ms；分类立即应用最新查询并取消旧等待。当前项仍匹配时选回对应行，不再配置场景；重复选择同一项也保留材质、时间、相机、参数和暂停状态。无结果清除场景、引用及预览像素，禁用效果开关。
- `shared/stage.gd` 将用户暂停与预览页面可见状态分开。离开实时页停止时钟和预览绘制，返回从原时刻继续，不积累隐藏期间的时间，也不改变用户暂停标记。
- 首批 20 项沿用 `tools/effect_profiles.py` 生成的明确 `animated` 元数据（8 动态、12 静态）；401 项未验证时默认动态。不按 uniform 猜动画，不将反射探针、雾等未验证案例标成静态。
- 静态、暂停及零速度时停止逐帧时钟写入；参数、相机、尺寸、开关和有效输入变化请求一次绘制。`frame_post_draw` 后同步 ONCE → DISABLED，动态预览使用可见时更新。
- 所有受影响的截图等待路径显式调用 `draw_frame()` 请求实际绘制。M2/M3 测试固定时间采图前关闭自动推进，以维持原来的人工步进语义；新增输出目录参数，保留历史报告。全库审查也可指定输出目录。
- 未修改 Shader、首批参数规格或 M1 样本。生成文件先修改 `tools/build_library.py`，再安全生成 README，不绕过手改保护。

## 本机验证

环境：Windows、Godot `4.7.2.stable.official.ed1daf0bf`、RTX 5060、Forward+ / Vulkan，驱动 `32.0.15.8097`。画面比较采用原 M5 640×480、随机种子、抗锯齿和相机设置；性能采用单独的 1440×900 窗口、900×660 预览。

| 检查 | 最终结果 | 本机原始证据 |
|---|---|---|
| M6 行为 | 159 项，失败 0 | `artifacts/m6/behavior.json`、`artifacts/m6-behavior-natural.log` |
| 稳定后不重复绘制 | 20 项各 120 帧；静态保持自然状态，动态暂停；期间只有主窗口的贴图显示调用，无额外预览绘制 | 同上；每项保存全局最大 draw call 数 |
| 搜索和恢复 | 最后输入重启 150 ms 等待、保留匹配项材质/节点/时间/相机/参数、同项不重建、空结果实际清屏、切换才重建；离页停时钟、返回续播及用户暂停保留 | 同上 |
| 按需刷新 | 20 项参数改变均改变真实像素；尺寸、暂停相机和有效输入能请求绘制，无效输入保持静止；玻璃/CRT 自然一次绘制即与 M5 默认图一致 | 同上 |
| M5 已批准参考图回归 | 新独立完整采集 140 项比较通过；最大 RGB 均差、差异像素比例均为 0 | `artifacts/m6/capture-final/`、`review-final/report.json` |
| 行为/独立重复 | 98 项行为、20 项独立进程默认图重复检查通过，重复误差 0；不与自身比较 | `artifacts/m6/repeat-final/`、`review-final/report.json` |
| M2 显卡回归 | 445 项断言，60 组基本命中及 27 组额外波形，失败 0 | `artifacts/m6/m2-final/runtime_gpu.json`、`artifacts/m6-m2-final.log` |
| M3 显卡回归 | 832 项断言、182 张截图，失败 0 | `artifacts/m6/m3-final/report.json`、`artifacts/m6-m3-final.log` |
| 结构与资源 | 421 项、23 类，失败 0 | `artifacts/m6-validation.log` |
| M6 全库 GPU 冒烟 | 23 个分类分别启动进程，421 个唯一编号全部覆盖且图像非空；无新增脚本/Shader/资源缺失错误 | `artifacts/m6/audit-final/category-*/runtime_followup.json`、`artifacts/m6-audit-final-*.log` |

M4/M5 已取消的全库验收没有补跑。上表全库运行仅属于共享逻辑变化后的 M6 回归，且是分进程 GPU 冒烟，不是其余 401 项的像素质量认证，也不是一个进程连续运行 421 项的内存稳定性认证。

参考图及其原始 `capture.json`、批准记录没有更新，比较阈值未放宽：RGB 均差 ≤ 2/255，通道差超过 8/255 的像素比例 ≤ 1%，另检查 alpha。M1 保持原样。

## 性能与缺项

完整数据见 [性能记录](M6_PERFORMANCE.md) 与 [逐次统计和原始哈希](M6_PERFORMANCE.json)。修改前后三次独立正式采集，每项预热 120 帧、采样 600 帧，两阶段共 72000 个样本帧。

12 个静态项在最终每次 600 帧中均为 0 次预览绘制，8 个动态项均为 600 次。没有项目的 GPU 渲染中位耗时上升超过 `max(基线×10%, 0.2 ms)`。预热后 60 次不同效果切换 P95 为基线 47.031 ms、改动后 47.538 ms，均低于 150 ms；不声称切换变快。这是独立预览的配置至实际首帧时间，未测完整图库 UI、冷启动或 401 项其他切换。

整帧 CPU 未测：Performance.TIME_PROCESS 低频缓存值不能代替逐帧 CPU；已测的 CPU 渲染耗时不含全部脚本/物理。预览独占内存未测：只有全局视频内存计数，不能可靠归因。墙钟帧间隔不冒充 CPU/GPU；不预填 FPS、提升比例或纯 Shader 内核开销。

首轮测试曾因参数选取（颜色缺少 max、默认值已是最大值）、未设置单次事件及未实例化实际 UI 场景而失败；修正测试输入，未改画面阈值。首轮性能汇总把节点保留的 UPDATE_ONCE 误当持续绘制，累加了旧 GPU 计时；修正绘制完成状态同步后，用新进程重采三次，保留原 after-1/2/3 作为诊断记录。最终报告仅采用 after-final-1/2/3。

## 历史问题与平台限制

M4 的内存分配失败记录继续保留。原有 7 个 Texture RID 释放警告在 M6 第 21 类（光照）分进程退出时重现，记录于 `artifacts/m6-audit-final-21.log`；没有将资源释放问题标为解决，也未推断根因。其余本轮最终专项/采集日志无新增脚本、Shader 或内存分配错误。

结果仅适用于上述本机。其他显卡、系统，以及 Mobile / Compatibility / Web 均未验证。原有 59 项“演示近似”标签未改变。

## 复查入口

所有新的性能和截图输出应使用尚不存在的路径，不能覆盖既有证据或参考图。性能前后阶段必须保持同一脚本、尺寸、驱动、画质、预热和样本数；三次使用三个独立进程，原始数据汇总时核对哈希和实际环境。

```powershell
& 'E:\Godot\Godot_v4.7.2-stable_win64_console.exe' --path . --rendering-method forward_plus --rendering-driver vulkan --resolution 1440x900 --max-fps 120 --script res://tools/test_m6.gd
& 'E:\Godot\Godot_v4.7.2-stable_win64_console.exe' --path . --rendering-method forward_plus --rendering-driver vulkan --resolution 1440x900 --script res://tools/benchmark_m6.gd -- --output=res://artifacts/m6/new-run-1.json
& 'E:\Godot\Godot_v4.7.2-stable_win64_console.exe' --path . --rendering-method forward_plus --rendering-driver vulkan --resolution 1440x900 --script res://tools/benchmark_m6_switch.gd -- --output=res://artifacts/m6/new-switch-1.json
```

固定状态重采和比较沿用 [M5 流程](../tests/visual/README.md)，参考图参数使用 `--reference tests/visual/reference`。M6 本机正式数据由 `tools/summarize_m6.py` 汇总；复跑时为它指定本轮新文件名后再汇总，不能覆盖原始输出。

方案依据：[Godot Timer](https://docs.godotengine.org/en/stable/classes/class_timer.html)、[SubViewport 更新模式](https://docs.godotengine.org/en/stable/classes/class_subviewport.html)、[RenderingServer 绘制完成与 CPU/GPU 计时](https://docs.godotengine.org/en/stable/classes/class_renderingserver.html)。使用内置开源 API，无新依赖或费用；ui-ux-pro-max 的搜索 UX 查询仅用于空结果反馈和合并输入建议，保留现有布局和控件。
