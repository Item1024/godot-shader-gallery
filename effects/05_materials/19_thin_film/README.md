# 薄膜干涉

编号：086  |  分类：真实与半真实材质
实现标签：演示近似

## 查看

- 图鉴入口：打开 project.godot，按 F5，搜索“薄膜干涉”或“thin_film”。
- 单独查看：打开本目录 demo.tscn，按 F6。
- 修改效果：编辑本目录 effect.gdshader。
- 每个效果的代码保存在本目录 effect.gdshader；展示场景共用 shared/ 里的脚本。
- 先关掉“启用效果”看原样，再打开比较；想看清静止画面时点“暂停动画”。

## 原理

模型像沾了一层会变彩色的薄膜。

## 它是怎么做到的？

把观察角度和设定厚度合起来选择彩虹色，模拟薄膜的变色外观。

## 这一类效果的共同思路

材质就是物体表面遇到光时怎么表现。底色、反光强弱、反光清晰度和细纹一起决定它更像金属、塑料还是布。

## 右侧参数怎么理解？

- 强度 / 进度（u_amount）：从 0 到 1，表示效果有多强或走到哪一步；具体含义看上面的解释。
- 动画速度（u_speed）：控制随时间变化的快慢；0 会停下这类变化。
- 纹理 / 图案尺度（u_scale）：调图案的疏密或大小；本效果用到它时才会变化。
- 强调色（u_color）：调亮边、花纹等使用的颜色；本效果用到它时才会变化。
- 启用效果（u_enabled）：开关效果，方便和原样比较。
- 点击位置（u_mouse）：支持交互的案例会把点击处当作中心、命中点或光源位置。
- 播放时间（u_time）：告诉效果现在播放到几秒，暂停动画时这个数字也停下。

## 这个演示做到哪一步？

用角度和假定厚度挑选彩虹色，没有计算不同波长的光在薄膜里如何互相影响。





项目默认使用 Forward+ 渲染器。切换到 Compatibility 等其他模式时，部分反射、雾和环境光功能会有差别，需要重新检查。

## 接入配置

效果公式保存在本目录的 effect.gdshader。

## 相关官方文档

- https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/spatial_shader.html
- https://docs.godotengine.org/en/stable/tutorials/shaders/screen-reading_shaders.html
- https://docs.godotengine.org/en/stable/tutorials/3d/environment_and_post_processing.html
