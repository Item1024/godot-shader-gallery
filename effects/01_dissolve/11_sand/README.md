# 沙化消散

编号：011  |  分类：溶解、显隐与侵蚀
实现标签：演示近似

## 查看

- 图鉴入口：打开 project.godot，按 F5，搜索“沙化消散”或“sand”。
- 单独查看：打开本目录 demo.tscn，按 F6。
- 临时试效果：可编辑本目录 effect.gdshader；要长期保存，请把改动合回 tools/build_library.py 对应公式后再重建。
- 重建前检查：python tools/build_library.py --check。检测到手改文件时会停止覆盖，先确认并保留改动。
- 每个效果的代码保存在本目录 effect.gdshader；展示场景共用 shared/ 里的脚本。
- 先关掉“启用效果”看原样，再打开比较；想看清静止画面时点“暂停动画”。

## 原理

图片像细沙一样散掉。

## 它是怎么做到的？

让很细的随机纹路不断移动，再据此擦掉画面；这里没有真正飞出去的沙粒。

## 这一类效果的共同思路

核心就是决定哪里还画、哪里不画。消失顺序可以按位置、距离或随机花纹来排；边缘亮色是另外涂上去的。

## 右侧参数怎么理解？

- 强度 / 进度（u_amount）：从 0 到 1，表示效果有多强或走到哪一步；具体含义看上面的解释。
- 动画速度：控制播放时间前进的快慢；0 会停下。改速度不会跳到另一个时刻，材质的 u_speed 固定为 1，避免重复乘速度。
- 纹理 / 图案尺度（u_scale）：调图案的疏密或大小；本效果用到它时才会变化。
- 强调色（u_color）：调亮边、花纹等使用的颜色；本效果用到它时才会变化。
- 启用效果（u_enabled）：开关效果，方便和原样比较。
- 点击位置：支持二维位置交互的案例使用 u_mouse；它是当前预览内的点击位置比例。
- 播放时间（u_time）：告诉效果现在播放到几秒，暂停动画时这个数字也停下。

## 这个演示做到哪一步？

这里只画细沙般的消散花纹，没有生成一粒粒会飞动、碰撞的沙子。





项目默认使用 Forward+ 渲染器。切换到 Compatibility 等其他模式时，部分反射、雾和环境光功能会有差别，需要重新检查。

## 接入配置

效果公式保存在本目录的 effect.gdshader。

## 相关官方文档

- https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/spatial_shader.html
- https://docs.godotengine.org/en/stable/tutorials/shaders/screen-reading_shaders.html
- https://docs.godotengine.org/en/stable/tutorials/3d/environment_and_post_processing.html
