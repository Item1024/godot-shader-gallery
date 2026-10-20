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

- 持续时间（u_duration）：0.2–2，步长 0.01 秒；默认 1。
- 环宽（u_ring_width）：0.01–0.3，步长 0.001 场景单位；默认 0.08。
- 亮度（u_intensity）：0–5，步长 0.01 ；默认 1.8。
- 波纹颜色（u_color）：color ；默认 #55e8bb。

点击球面触发，亮圈沿球面弧长扩散，结束不重复。只支持本例球形命中。
播放区：速度 0–3，默认 1；暂停、调速保持当前时刻。
重置恢复以上元数据默认值、播放时刻和效果开关，并清除事件。

## 这个演示做到哪一步？

点击本例球形护盾触发一次沿球面扩散的亮圈，结束后不自动重播。新点击替换上一圈；其他形状需要另外实现命中方法。





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
$Player.set_parameter("u_duration", 1)
```

动态效果必须复制 `shared/effect_player.gd`、`shared/usage_player.gd` 和 `shared/surface_hit.gd`；`Player` 节点驱动同一套连续时间。只拖入材质时得到的是时间 0 的静态状态。代码挂在 usage 根节点时：

```gdscript
$Player.player.playback_speed = 0.25 # 改速度不改变当前时刻
$Player.player.paused = true        # 暂停事件和动画
$Player.player.paused = false
$Player.reset()                     # 恢复材质默认值、时间和事件
```

运行后点击表面触发，左键拖动旋转，滚轮缩放；移动超过 4 个界面像素不触发点击。游戏也可调用 `$Player.trigger_at(viewport_pixel)`。命中只支持本例平面波面或球体；其他模型需提供相应求交。将示例放入子视口时，输入必须使用该视口的像素坐标。

已验证平台：Windows、Godot 4.7.2 标准版、Forward+、RTX 5060。其他系统/显卡及 Mobile、Compatibility、Web 未验证，不宣称支持。屏幕/深度效果要在包含背景和相机的目标视口中使用，不能脱离渲染顺序随意搬动。
