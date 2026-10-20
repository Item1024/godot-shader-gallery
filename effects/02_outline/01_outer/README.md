# 外描边

编号：017  |  分类：描边、轮廓与遮挡
实现标签：二维 Shader

## 查看

- 图鉴入口：打开 project.godot，按 F5，搜索“外描边”或“outer”。
- 单独查看：打开本目录 demo.tscn，按 F6。
- 临时试效果：可编辑本目录 effect.gdshader；要长期保存，请把改动合回 tools/build_library.py 对应公式后再重建。
- 重建前检查：python tools/build_library.py --check。检测到手改文件时会停止覆盖，先确认并保留改动。
- 每个效果的代码保存在本目录 effect.gdshader；展示场景共用 shared/ 里的脚本。
- 先关掉“启用效果”看原样，再打开比较；想看清静止画面时点“暂停动画”。

## 原理

图案外面多出一圈线。

## 它是怎么做到的？

当前点是透明的，但旁边能找到图案，就把当前点涂成描边色。

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

## 复制接入游戏（M4）

- 最小入口：打开本目录 `usage.tscn`，按 F6；没有图库 UI、catalog 或 stage.gd 依赖。原 `demo.tscn` 继续作为图鉴入口。
- 复制什么：按本目录 `dependencies.json` 的 `files` 列表逐项复制到目标工程，`res://` 后的相对路径保持不变；清单与本 README 可另外一起带走。让 Godot 重新导入素材，不复制 `.godot/` 缓存。
- 拖到哪里：把 `usage.tscn` 实例拖入目标场景，或将 `material.tres` 拖到自己的Sprite2D 的 Material。材质启用 `resource_local_to_scene`，两个 usage 场景实例各有自己的参数；手动给多个物体赋同一个外部材质时，要先“设为唯一”或 `duplicate()`，再分别驱动。
- 代码改值：下例脚本挂在 usage 根节点，范围与默认值见上方参数表。

```gdscript
$Center/Effect.material.set_shader_parameter("u_width_px", 3)
```

这是静态效果，无须播放器。重新加载材质或恢复参数表中的默认值即可重置。

已验证平台：Windows、Godot 4.7.2 标准版、Forward+、RTX 5060。其他系统/显卡及 Mobile、Compatibility、Web 未验证，不宣称支持。屏幕/深度效果要在包含背景和相机的目标视口中使用，不能脱离渲染顺序随意搬动。
