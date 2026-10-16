# 验证记录

验证环境：Windows，Godot 4.7.2.stable.official.ed1daf0bf，NVIDIA GeForce RTX 5060，Vulkan 1.4 / Forward+。

## 已完成

- 结构与资源检查：23 类、421 个效果目录、独立 Shader、演示场景、元数据与说明文件；`artifacts/validation.log` 记录 `failures=0`。
- 显卡逐项运行：421 / 421 通过；结果在 `artifacts/runtime_audit.json`，日志在 `artifacts/runtime.log`。
- 调整后的专项显卡复查：93 项、40 项及最后第 11 类 24 项通过，对应 `runtime_followup.log`、`runtime_final.log`、`runtime_last.log`。
- 独立入口检查：噪声溶解与金属材质的 `demo.tscn` 均可独立运行，日志在 `standalone_2d.log`、`standalone_3d.log`。
- 实际窗口操作：英文搜索 `hologram` 筛选到全息投影；源码与中文说明切换；暂停按钮；强度滑块；效果开关；重置参数。
- 截图：`artifacts/gallery.png` 为图鉴入口，`category_01.png` 至 `category_23.png` 为各分类代表效果。

## 检查范围

自动渲染检查确认 Shader 可载入、有 uniform 信息、能生成非空视口图像，并结合日志排查运行与编译错误。它不包含每个效果的像素级正确性、跨显卡兼容性或性能预算验证。代表效果经过截图查看与界面操作检查。

59 项明确标注为“演示近似”；管线案例使用 Godot 内置功能。各项接入限制见对应目录 README 与图鉴的“原理与限制”。
