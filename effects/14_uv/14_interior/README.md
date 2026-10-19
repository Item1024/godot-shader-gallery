# 窗内假房间

编号：258  |  分类：UV、视差与程序纹理
实现标签：演示近似

## 查看

- 图鉴入口：打开 project.godot，按 F5，搜索“窗内假房间”或“interior”。
- 单独查看：打开本目录 demo.tscn，按 F6。
- 临时试效果：可编辑本目录 effect.gdshader；要长期保存，请把改动合回 tools/build_library.py 对应公式后再重建。
- 重建前检查：python tools/build_library.py --check。检测到手改文件时会停止覆盖，先确认并保留改动。
- 每个效果的代码保存在本目录 effect.gdshader；展示场景共用 shared/ 里的脚本。
- 先关掉“启用效果”看原样，再打开比较；想看清静止画面时点“暂停动画”。

## 原理

窗口像能看到里面的小房间。

## 它是怎么做到的？

反复画窗框和缩进去的色块，形成前后层次的二维假象。

## 这一类效果的共同思路

贴图位置就像图片上的地址。改地址能让图案平移、旋转或扭曲；也可以不用图片，直接用公式算出花纹。

## 右侧参数怎么理解？

- 强度 / 进度（u_amount）：从 0 到 1，表示效果有多强或走到哪一步；具体含义看上面的解释。
- 动画速度（u_speed）：控制随时间变化的快慢；0 会停下这类变化。
- 纹理 / 图案尺度（u_scale）：调图案的疏密或大小；本效果用到它时才会变化。
- 强调色（u_color）：调亮边、花纹等使用的颜色；本效果用到它时才会变化。
- 启用效果（u_enabled）：开关效果，方便和原样比较。
- 点击位置（u_mouse）：支持交互的案例会把点击处当作中心、命中点或光源位置。
- 播放时间（u_time）：告诉效果现在播放到几秒，暂停动画时这个数字也停下。

## 这个演示做到哪一步？

只用二维色块暗示房间深度，没有计算视线进入真实房间后会碰到哪面墙。





项目默认使用 Forward+ 渲染器。切换到 Compatibility 等其他模式时，部分反射、雾和环境光功能会有差别，需要重新检查。

## 接入配置

效果公式保存在本目录的 effect.gdshader。

## 相关官方文档

- https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/spatial_shader.html
- https://docs.godotengine.org/en/stable/tutorials/shaders/screen-reading_shaders.html
- https://docs.godotengine.org/en/stable/tutorials/3d/environment_and_post_processing.html
