# 全息投影

编号：192  |  分类：科幻、能量与魔法
实现标签：三维材质

## 查看

- 图鉴入口：打开 project.godot，按 F5，搜索“全息投影”或“hologram”。
- 单独查看：打开本目录 demo.tscn，按 F6。
- 临时试效果：可编辑本目录 effect.gdshader；要长期保存，请把改动合回 tools/build_library.py 对应公式后再重建。
- 重建前检查：python tools/build_library.py --check。检测到手改文件时会停止覆盖，先确认并保留改动。
- 每个效果的代码保存在本目录 effect.gdshader；展示场景共用 shared/ 里的脚本。
- 先关掉“启用效果”看原样，再打开比较；想看清静止画面时点“暂停动画”。

## 原理

模型像由半透明扫描线投影出来。

## 它是怎么做到的？

弱化正面、提亮边缘，再叠不断移动的横向亮条。

## 这一类效果的共同思路

先画圆环、线条或不规则花纹，再让它们移动和发亮。有些效果还能把点击位置当作命中点或扩散中心。

## 右侧参数怎么理解？

- 扫描线密度（u_line_density）：4–120，步长 1 条/模型单位；默认 40。
- 线亮度（u_intensity）：0–3，步长 0.01 ；默认 1。
- 基础透明度（u_opacity）：0–1，步长 0.01 ；默认 0.25。
- 边缘亮度（u_rim_strength）：0–3，步长 0.01 ；默认 1。
- 全息颜色（u_color）：color ；默认 #55e8bb。

条纹使用模型局部坐标；这是表面着色，不是体积全息。
播放区：速度 0–3，默认 1；暂停、调速保持当前时刻。
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
