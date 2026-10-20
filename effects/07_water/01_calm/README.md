# 平静水面

编号：112  |  分类：水体与液体表面
实现标签：三维材质

## 查看

- 图鉴入口：打开 project.godot，按 F5，搜索“平静水面”或“calm”。
- 单独查看：打开本目录 demo.tscn，按 F6。
- 临时试效果：可编辑本目录 effect.gdshader；要长期保存，请把改动合回 tools/build_library.py 对应公式后再重建。
- 重建前检查：python tools/build_library.py --check。检测到手改文件时会停止覆盖，先确认并保留改动。
- 每个效果的代码保存在本目录 effect.gdshader；展示场景共用 shared/ 里的脚本。
- 先关掉“启用效果”看原样，再打开比较；想看清静止画面时点“暂停动画”。

## 原理

水面轻轻起伏。

## 它是怎么做到的？

上下移动平面上的小点，再用细波纹和反光表现平静水面。

## 这一类效果的共同思路

一层会起伏的表面，加上波纹、反光和深浅颜色，就能让人联想到水。水下物体离水面多远，还能帮助决定浅水色和岸边泡沫。

## 右侧参数怎么理解？

- 波高（u_wave_height）：0–0.25，步长 0.001 场景单位；默认 0.04。0 为平面；波形幅度上界为此值。
- 波长（u_wave_length）：0.25–4，步长 0.001 场景单位；默认 1。
- 浅水色（u_shallow_color）：color ；默认 #1a9e9c。
- 深水色（u_deep_color）：color ；默认 #041f45。
- 变深距离（u_depth_distance）：0.2–5，步长 0.001 场景单位；默认 2。

深度来自当前屏幕的不透明物体；不包含水下体积散射。
播放区：速度 0–3，默认 1；暂停、调速保持当前时刻。
重置恢复以上元数据默认值、播放时刻和效果开关，并清除事件。

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

## 复制接入游戏（M4）

- 最小入口：打开本目录 `usage.tscn`，按 F6；没有图库 UI、catalog 或 stage.gd 依赖。原 `demo.tscn` 继续作为图鉴入口。
- 复制什么：按本目录 `dependencies.json` 的 `files` 列表逐项复制到目标工程，`res://` 后的相对路径保持不变；清单与本 README 可另外一起带走。让 Godot 重新导入素材，不复制 `.godot/` 缓存。
- 拖到哪里：把 `usage.tscn` 实例拖入目标场景，或将 `material.tres` 拖到自己的MeshInstance3D 的 Material Override。材质启用 `resource_local_to_scene`，两个 usage 场景实例各有自己的参数；手动给多个物体赋同一个外部材质时，要先“设为唯一”或 `duplicate()`，再分别驱动。
- 代码改值：下例脚本挂在 usage 根节点，范围与默认值见上方参数表。

```gdscript
$Player.set_parameter("u_wave_height", 0.04)
```

动态效果必须复制 `shared/effect_player.gd`、`shared/usage_player.gd` 和 `shared/surface_hit.gd`；`Player` 节点驱动同一套连续时间。只拖入材质时得到的是时间 0 的静态状态。代码挂在 usage 根节点时：

```gdscript
$Player.player.playback_speed = 0.25 # 改速度不改变当前时刻
$Player.player.paused = true        # 暂停事件和动画
$Player.player.paused = false
$Player.reset()                     # 恢复材质默认值、时间和事件
```

已验证平台：Windows、Godot 4.7.2 标准版、Forward+、RTX 5060。其他系统/显卡及 Mobile、Compatibility、Web 未验证，不宣称支持。屏幕/深度效果要在包含背景和相机的目标视口中使用，不能脱离渲染顺序随意搬动。
