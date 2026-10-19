# 斜向扫光

编号：037  |  分类：发光、流光与扫光
实现标签：二维 Shader

## 查看

- 图鉴入口：打开 project.godot，按 F5，搜索“斜向扫光”或“diagonal”。
- 单独查看：打开本目录 demo.tscn，按 F6。
- 临时试效果：可编辑本目录 effect.gdshader；要长期保存，请把改动合回 tools/build_library.py 对应公式后再重建。
- 重建前检查：python tools/build_library.py --check。检测到手改文件时会停止覆盖，先确认并保留改动。
- 每个效果的代码保存在本目录 effect.gdshader；展示场景共用 shared/ 里的脚本。
- 先关掉“启用效果”看原样，再打开比较；想看清静止画面时点“暂停动画”。

## 原理

亮带斜着扫过图案。

## 它是怎么做到的？

把横向位置和纵向位置相加，用这个斜向顺序移动亮带。

## 这一类效果的共同思路

把一部分颜色画得很亮，再让亮的位置或亮度变化。这些二维亮色本身不会变成能照亮周围的灯。

## 右侧参数怎么理解？

- 强度（u_intensity）：0–5，步长 0.01 ；默认 2。
- 光带宽度（u_band_width）：0.01–0.5，步长 0.001 UV 比例；默认 0.12。
- 角度（u_angle_deg）：0–180，步长 1 °；默认 45。起点 0° 在顶部，正角度沿顺时针。
- 周期（u_period）：0.2–5，步长 0.01 秒；默认 1.5。


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
