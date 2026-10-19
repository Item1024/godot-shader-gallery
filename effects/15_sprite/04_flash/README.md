# 受击闪白

编号：270  |  分类：2D精灵与像素画
实现标签：二维 Shader

## 查看

- 图鉴入口：打开 project.godot，按 F5，搜索“受击闪白”或“flash”。
- 单独查看：打开本目录 demo.tscn，按 F6。
- 临时试效果：可编辑本目录 effect.gdshader；要长期保存，请把改动合回 tools/build_library.py 对应公式后再重建。
- 重建前检查：python tools/build_library.py --check。检测到手改文件时会停止覆盖，先确认并保留改动。
- 每个效果的代码保存在本目录 effect.gdshader；展示场景共用 shared/ 里的脚本。
- 先关掉“启用效果”看原样，再打开比较；想看清静止画面时点“暂停动画”。

## 原理

图片受击后闪白一次再恢复。

## 它是怎么做到的？

点击播放一次或图案才开始，按持续时间淡回原图，透明边缘保持不变。

## 这一类效果的共同思路

先读取图片的颜色和透明部分，再决定哪些地方换色、加边或隐藏。很多效果能直接用于普通二维图片，放进大图集时还要对应好图片区域。

## 右侧参数怎么理解？

- 强度（u_strength）：0–1，步长 0.01 ；默认 1。
- 持续时间（u_duration）：0.05–1，步长 0.01 秒；默认 0.15。
- 闪光颜色（u_color）：color ；默认 #ffffff。

播放一次或点击图案触发；新事件替换旧事件，暂停时事件也暂停。
播放区：速度 0–3，默认 1；暂停、调速保持当前时刻。
操作：播放一次。
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
