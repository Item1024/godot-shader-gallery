# 水下焦散

编号：122  |  分类：水体与液体表面
实现标签：三维材质

## 查看

- 图鉴入口：打开 project.godot，按 F5，搜索“水下焦散”或“caustics”。
- 单独查看：打开本目录 demo.tscn，按 F6。
- 临时试效果：可编辑本目录 effect.gdshader；要长期保存，请把改动合回 tools/build_library.py 对应公式后再重建。
- 重建前检查：python tools/build_library.py --check。检测到手改文件时会停止覆盖，先确认并保留改动。
- 每个效果的代码保存在本目录 effect.gdshader；展示场景共用 shared/ 里的脚本。
- 先关掉“启用效果”看原样，再打开比较；想看清静止画面时点“暂停动画”。

## 原理

水面上出现游动的亮色网纹。

## 它是怎么做到的？

画出不规则小区域的边界，再让这些亮边缓慢移动。

## 这一类效果的共同思路

一层会起伏的表面，加上波纹、反光和深浅颜色，就能让人联想到水。水下物体离水面多远，还能帮助决定浅水色和岸边泡沫。

## 右侧参数怎么理解？

- 强度 / 进度（u_amount）：从 0 到 1，表示效果有多强或走到哪一步；具体含义看上面的解释。
- 动画速度：控制播放时间前进的快慢；0 会停下。改速度不会跳到另一个时刻，材质的 u_speed 固定为 1，避免重复乘速度。
- 纹理 / 图案尺度（u_scale）：调图案的疏密或大小；本效果用到它时才会变化。
- 强调色（u_color）：调亮边、花纹等使用的颜色；本效果用到它时才会变化。
- 启用效果（u_enabled）：开关效果，方便和原样比较。
- 点击位置：支持二维位置交互的案例使用 u_mouse；它是当前预览内的点击位置比例。
- 播放时间（u_time）：告诉效果现在播放到几秒，暂停动画时这个数字也停下。

## 这个演示做到哪一步？

这里演示画面变化的方法。放进游戏时，还要由游戏代码决定何时出现、变化多久，并按实际模型和画面大小调整。



这里还会读取远近信息，也就是每个位置离相机多远，用它判断深浅、遮挡或模糊程度。

项目默认使用 Forward+ 渲染器。切换到 Compatibility 等其他模式时，部分反射、雾和环境光功能会有差别，需要重新检查。

## 接入配置

效果公式保存在本目录的 effect.gdshader。

## 相关官方文档

- https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/spatial_shader.html
- https://docs.godotengine.org/en/stable/tutorials/shaders/screen-reading_shaders.html
- https://docs.godotengine.org/en/stable/tutorials/3d/environment_and_post_processing.html
