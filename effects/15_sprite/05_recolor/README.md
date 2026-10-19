# 局部换色

编号：271  |  分类：2D精灵与像素画
实现标签：二维 Shader

## 查看

- 图鉴入口：打开 project.godot，按 F5，搜索“局部换色”或“recolor”。
- 单独查看：打开本目录 demo.tscn，按 F6。
- 临时试效果：可编辑本目录 effect.gdshader；要长期保存，请把改动合回 tools/build_library.py 对应公式后再重建。
- 重建前检查：python tools/build_library.py --check。检测到手改文件时会停止覆盖，先确认并保留改动。
- 每个效果的代码保存在本目录 effect.gdshader；展示场景共用 shared/ 里的脚本。
- 先关掉“启用效果”看原样，再打开比较；想看清静止画面时点“暂停动画”。

## 原理

图片里某一类颜色被换掉。

## 它是怎么做到的？

先按红绿蓝的比例找出符合条件的像素，再把它们混成强调色。

## 这一类效果的共同思路

先读取图片的颜色和透明部分，再决定哪些地方换色、加边或隐藏。很多效果能直接用于普通二维图片，放进大图集时还要对应好图片区域。

## 右侧参数怎么理解？

- 源颜色（u_source_color）：color ；默认 #a2f6da。
- 目标色（u_color）：color ；默认 #55e8bb。
- 容差（u_tolerance）：0–1，步长 0.01 ；默认 0.2。按 RGB 距离选择颜色；0 只选择完全相同的颜色。
- 混合强度（u_amount）：0–1，步长 0.01 ；默认 1。0 为起点，1 为终点；端点不受其他参数影响。


静态效果不显示播放速度。
重置恢复以上元数据默认值、播放时刻和效果开关，并清除事件。

## 这个演示做到哪一步？

这里演示画面变化的方法。放进游戏时，还要由游戏代码决定何时出现、变化多久，并按实际模型和画面大小调整。





项目默认使用 Forward+ 渲染器。切换到 Compatibility 等其他模式时，部分反射、雾和环境光功能会有差别，需要重新检查。

## 接入配置

效果公式保存在本目录的 effect.gdshader。

## 相关官方文档

- https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/spatial_shader.html
- https://docs.godotengine.org/en/stable/tutorials/shaders/screen-reading_shaders.html
- https://docs.godotengine.org/en/stable/tutorials/3d/environment_and_post_processing.html
