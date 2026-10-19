# 方向溶解

编号：002  |  分类：溶解、显隐与侵蚀
实现标签：二维 Shader

## 查看

- 图鉴入口：打开 project.godot，按 F5，搜索“方向溶解”或“direction”。
- 单独查看：打开本目录 demo.tscn，按 F6。
- 临时试效果：可编辑本目录 effect.gdshader；要长期保存，请把改动合回 tools/build_library.py 对应公式后再重建。
- 重建前检查：python tools/build_library.py --check。检测到手改文件时会停止覆盖，先确认并保留改动。
- 每个效果的代码保存在本目录 effect.gdshader；展示场景共用 shared/ 里的脚本。
- 先关掉“启用效果”看原样，再打开比较；想看清静止画面时点“暂停动画”。

## 原理

图片从指定方向逐渐消失。

## 它是怎么做到的？

沿设定角度给位置排消失顺序，进度 0 完整显示，1 完全消失。

## 这一类效果的共同思路

核心就是决定哪里还画、哪里不画。消失顺序可以按位置、距离或随机花纹来排；边缘亮色是另外涂上去的。

## 右侧参数怎么理解？

- 消失进度（u_amount）：0–1，步长 0.01 ；默认 0.32。0 为起点，1 为终点；端点不受其他参数影响。
- 方向（u_direction_deg）：0–360，步长 1 °；默认 0。起点 0° 在顶部，正角度沿顺时针。
- 亮边宽度（u_edge_width）：0–0.15，步长 0.001 UV 比例；默认 0.04。只扩宽保留侧的交界，不改变消失区域。
- 亮边颜色（u_color）：color ；默认 #55e8bb。


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
