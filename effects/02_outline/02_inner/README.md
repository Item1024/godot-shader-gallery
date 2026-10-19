# 内描边

编号：018  |  分类：描边、轮廓与遮挡
实现标签：二维 Shader

## 查看

- 图鉴入口：打开 project.godot，按 F5，搜索“内描边”或“inner”。
- 单独查看：打开本目录 demo.tscn，按 F6。
- 临时试效果：可编辑本目录 effect.gdshader；要长期保存，请把改动合回 tools/build_library.py 对应公式后再重建。
- 重建前检查：python tools/build_library.py --check。检测到手改文件时会停止覆盖，先确认并保留改动。
- 每个效果的代码保存在本目录 effect.gdshader；展示场景共用 shared/ 里的脚本。
- 先关掉“启用效果”看原样，再打开比较；想看清静止画面时点“暂停动画”。

## 原理

描边画在图案里面。

## 它是怎么做到的？

当前点属于图案，但旁边已经透明，就把这个靠边的位置换成描边色。

## 这一类效果的共同思路

图片描边主要靠检查旁边有没有图案；模型亮边主要看表面朝向。轮廓附近加线、加亮或变透明，就有了不同外观。

## 右侧参数怎么理解？

- 宽度（u_width_px）：0–16，步长 0.5 贴图像素；默认 3。
- 柔和程度（u_softness）：0–1，步长 0.01 ；默认 0.15。
- 描边颜色（u_color）：color ；默认 #55e8bb。


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
