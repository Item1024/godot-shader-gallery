# 护盾受击波纹

编号：190  |  分类：科幻、能量与魔法
实现标签：三维材质

## 查看

- 图鉴入口：打开 project.godot，按 F5，搜索“护盾受击波纹”或“shield_hit”。
- 单独查看：打开本目录 demo.tscn，按 F6。
- 临时试效果：可编辑本目录 effect.gdshader；要长期保存，请把改动合回 tools/build_library.py 对应公式后再重建。
- 重建前检查：python tools/build_library.py --check。检测到手改文件时会停止覆盖，先确认并保留改动。
- 每个效果的代码保存在本目录 effect.gdshader；展示场景共用 shared/ 里的脚本。
- 先关掉“启用效果”看原样，再打开比较；想看清静止画面时点“暂停动画”。

## 原理

护盾上有一圈从命中处扩散的亮纹。

## 它是怎么做到的？

先找到点击射线与球形护盾的交点，再按沿球面走过的距离画出扩散亮圈；一秒后结束，下一次点击才重新出现。

## 这一类效果的共同思路

先画圆环、线条或不规则花纹，再让它们移动和发亮。有些效果还能把点击位置当作命中点或扩散中心。

## 右侧参数怎么理解？

- 强度 / 进度（u_amount）：从 0 到 1，表示效果有多强或走到哪一步；具体含义看上面的解释。
- 动画速度：控制播放时间前进的快慢；0 会停下。改速度不会跳到另一个时刻，材质的 u_speed 固定为 1，避免重复乘速度。
- 纹理 / 图案尺度（u_scale）：调图案的疏密或大小；本效果用到它时才会变化。
- 强调色（u_color）：调亮边、花纹等使用的颜色；本效果用到它时才会变化。
- 启用效果（u_enabled）：开关效果，方便和原样比较。
- 点击位置：使用三维表面命中点 u_hit_position；u_event_time 记录点击时刻，u_duration 默认为 1 秒。按下并释放才触发，拖动不触发。
- 播放时间（u_time）：告诉效果现在播放到几秒，暂停动画时这个数字也停下。

## 这个演示做到哪一步？

点击本例球形护盾触发一次沿球面扩散的亮圈，结束后不自动重播。新点击替换上一圈；其他形状需要另外实现命中方法。





项目默认使用 Forward+ 渲染器。切换到 Compatibility 等其他模式时，部分反射、雾和环境光功能会有差别，需要重新检查。

## 接入配置

效果公式保存在本目录的 effect.gdshader。

## 相关官方文档

- https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/spatial_shader.html
- https://docs.godotengine.org/en/stable/tutorials/shaders/screen-reading_shaders.html
- https://docs.godotengine.org/en/stable/tutorials/3d/environment_and_post_processing.html
