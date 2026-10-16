# 雪地压痕

编号：166  |  分类：地表与表面变化
实现标签：演示近似

## 查看

- 图鉴入口：打开 project.godot，按 F5，搜索“雪地压痕”或“snow_track”。
- 单独查看：打开本目录 demo.tscn，按 F6。
- 修改效果：编辑本目录 effect.gdshader。
- 每个效果的代码保存在本目录 effect.gdshader；展示场景共用 shared/ 里的脚本。
- 先关掉“启用效果”看原样，再打开比较；想看清静止画面时点“暂停动画”。

## 原理

雪面上出现颜色较深的压痕。

## 它是怎么做到的？

先重复画椭圆形区域，再把这些区域染成偏暗的雪色。

## 这一类效果的共同思路

先决定哪里覆盖哪种东西，再分别改颜色和反光。积雪、锈斑、潮湿等外观，很多都能从这个共同做法变化出来。

## 右侧参数怎么理解？

- 强度 / 进度（u_amount）：从 0 到 1，表示效果有多强或走到哪一步；具体含义看上面的解释。
- 动画速度（u_speed）：控制随时间变化的快慢；0 会停下这类变化。
- 纹理 / 图案尺度（u_scale）：调图案的疏密或大小；本效果用到它时才会变化。
- 强调色（u_color）：调亮边、花纹等使用的颜色；本效果用到它时才会变化。
- 启用效果（u_enabled）：开关效果，方便和原样比较。
- 点击位置（u_mouse）：支持交互的案例会把点击处当作中心、命中点或光源位置。
- 播放时间（u_time）：告诉效果现在播放到几秒，暂停动画时这个数字也停下。

## 这个演示做到哪一步？

压痕只改变颜色，雪面没有真的被踩凹，也不会记录新的踩踏。





项目默认使用 Forward+ 渲染器。切换到 Compatibility 等其他模式时，部分反射、雾和环境光功能会有差别，需要重新检查。

## 接入配置

效果公式保存在本目录的 effect.gdshader。

## 相关官方文档

- https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/spatial_shader.html
- https://docs.godotengine.org/en/stable/tutorials/shaders/screen-reading_shaders.html
- https://docs.godotengine.org/en/stable/tutorials/3d/environment_and_post_processing.html
