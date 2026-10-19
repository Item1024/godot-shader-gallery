# LUT调色

编号：317  |  分类：屏幕调色
实现标签：屏幕后处理

## 查看

- 图鉴入口：打开 project.godot，按 F5，搜索“LUT调色”或“lut”。
- 单独查看：打开本目录 demo.tscn，按 F6。
- 临时试效果：可编辑本目录 effect.gdshader；要长期保存，请把改动合回 tools/build_library.py 对应公式后再重建。
- 重建前检查：python tools/build_library.py --check。检测到手改文件时会停止覆盖，先确认并保留改动。
- 每个效果的代码保存在本目录 effect.gdshader；展示场景共用 shared/ 里的脚本。
- 先关掉“启用效果”看原样，再打开比较；想看清静止画面时点“暂停动画”。

## 原理

整张画面像套了一款调色滤镜。

## 它是怎么做到的？

图片里存着旧颜色对应的新颜色，读取这张颜色对照表来换色。

## 这一类效果的共同思路

先拿到预览里已经画好的图，再逐点换颜色。处理范围只有中间预览，旁边的目录和参数面板不会一起变色。

## 右侧参数怎么理解？

- 混合强度（u_amount）：0–1，步长 0.01 ；默认 1。0 为起点，1 为终点；端点不受其他参数影响。
- 颜色表（lut_texture）：texture ；默认 res://assets/warm_lut.png。

16³ 颜色表横排 16 个蓝色切片；红绿双线性、蓝色两片插值，采样限制在各片中心。PNG 按原始 RGB 数据读取。
静态效果不显示播放速度。
重置恢复以上元数据默认值、播放时刻和效果开关，并清除事件。

## 这个演示做到哪一步？

这里演示画面变化的方法。放进游戏时，还要由游戏代码决定何时出现、变化多久，并按实际模型和画面大小调整。


取的是当前预览已经画出的背景颜色。镜头外没画出来的内容，单靠这张图无法补出来。


项目默认使用 Forward+ 渲染器。切换到 Compatibility 等其他模式时，部分反射、雾和环境光功能会有差别，需要重新检查。

## 接入配置

效果公式保存在本目录的 effect.gdshader。

## 相关官方文档

- https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/spatial_shader.html
- https://docs.godotengine.org/en/stable/tutorials/shaders/screen-reading_shaders.html
- https://docs.godotengine.org/en/stable/tutorials/3d/environment_and_post_processing.html
