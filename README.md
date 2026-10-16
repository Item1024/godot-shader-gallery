# Shader Atlas · Godot 效果图鉴

421 个独立效果目录，覆盖对话中的 23 类。使用 Godot 4.7.2 标准版，无外部插件、网络依赖或 .NET 依赖。

## 运行与查看

1. 用 Godot 导入本目录的 project.godot。
2. 第一次打开等待 SVG、PNG 与脚本导入完成，按 F5。
3. 左侧选择分类或输入中文/英文关键词；中间查看实时效果、源码、原理与限制；右侧调整参数。
4. 每个效果目录都有 demo.tscn，可在编辑器中打开后按 F6 单独运行。

三维预览支持左键拖动旋转和滚轮缩放。空格暂停动画，Ctrl+F 搜索，左右方向键切换过滤结果。
点击“启用效果”可比较原始画面。右侧“打开效果目录”打开当前案例所在目录。

421 项的“原理与限制”及目录 README 都采用大白话：先讲画面像什么，再讲本示例具体怎么画出来。参数和演示局限也用日常语言说明。

## 目录

- effects/01_dissolve/01_noise/ 这样的目录：每个效果一个文件夹。
- 每个文件夹：effect.gdshader、demo.tscn、metadata.json、README.md；管线案例另有 environment.json。
- shared/：通用场景、展示入口与参数控制，不放具体效果公式。
- assets/：矢量示例图、文字贴图、VAT、LUT，以及本地 Blender 小屋渲染参考图。
- docs/INDEX.md：全部目录与实现标签的完整索引。
- tools/build_library.py 与 effect_catalog.py：维护/重建库的源文件。
- tools/validate.gd：结构、资源和 Shader 语言检查。
- artifacts/：实际运行审查输出的报告与截图。

## 实现边界

完整清单中有 59 个案例明确标为“演示近似”。例如运动模糊没有运动矢量，反应扩散没有跨帧数值求解，过度绘制热力图不是实际 GPU 计数。限制同时显示在图鉴中与各目录 README 中。
SSAO、SSR、SSIL、体积雾等管线案例使用 Godot 内置渲染功能，材质文件不冒充完整算法的实现。效果按原问题分目录；相近变体共享数学原理，但各自保留独立 Shader 源文件。
这是教学展示库，不表示每个案例都能直接用于生产环境。所有公式和占位素材均随项目提供。

## 验证

结构与语言检查：

    Godot_v4.7.2-stable_win64_console.exe --headless --path . --script res://tools/validate.gd

真实渲染器逐项审查并保存各类截图：

    Godot_v4.7.2-stable_win64_console.exe --path . -- --audit --quit-after-audit

审查报告写入 artifacts/runtime_audit.json。只在审查真正完成后，才能把报告作为运行结果。

本机已完成的检查及其范围见 [验证记录](docs/VERIFICATION.md)。

## 界面与素材说明

界面采用目录—预览—参数的通用开发工具布局。设计检索返回的 FAQ 页面模式不适合本地 Godot 工具，布局采用通用可访问性原则；使用深色高对比配色、清晰焦点与动画暂停控制。
字体通过系统字体回退，不从网络下载。小屋参考图来自本工作区的 Blender 建模示例；其余图片由项目脚本生成。

官方资料：
- https://docs.godotengine.org/en/stable/tutorials/shaders/introduction_to_shaders.html
- https://docs.godotengine.org/en/stable/tutorials/shaders/screen-reading_shaders.html
- https://docs.godotengine.org/en/stable/tutorials/shaders/advanced_postprocessing.html
