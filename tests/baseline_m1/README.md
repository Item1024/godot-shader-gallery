# M1 优化前画面样本

这 20 项各保存效果开启 / 关闭两张图片，共 40 张。它们记录提交 8cff48e 的实际外观，用于之后观察改动；不是已经通过视觉正确性验收的金标准。

固定效果时间 1 秒，预览 900×660，Godot 4.7.2，Forward+ / Vulkan，RTX 5060。实际参数、输入文件哈希和图片哈希保存在 capture.json。

复现前先核对 tests/m1_cases.json 中的源文件哈希；工具遇到源码变化或已有输出记录会停止，不会拿新效果冒充旧样本。

```text
Godot_v4.7.2-stable_win64_console.exe --path . --rendering-method forward_plus --rendering-driver vulkan --resolution 900x660 --script res://tools/capture_m1.gd -- --output=res://artifacts/m1-capture-new
```

| 编号 | 效果 | 关闭 | 开启 |
|---|---|---|---|
| 001 | 噪声溶解 | [关闭](001_noise_off.png) | [开启](001_noise_on.png) |
| 002 | 方向溶解 | [关闭](002_direction_off.png) | [开启](002_direction_on.png) |
| 007 | 燃烧溶解 | [关闭](007_burn_off.png) | [开启](007_burn_on.png) |
| 017 | 外描边 | [关闭](017_outer_off.png) | [开启](017_outer_on.png) |
| 018 | 内描边 | [关闭](018_inner_off.png) | [开启](018_inner_on.png) |
| 034 | 呼吸发光 | [关闭](034_breathing_off.png) | [开启](034_breathing_on.png) |
| 037 | 斜向扫光 | [关闭](037_diagonal_off.png) | [开启](037_diagonal_on.png) |
| 270 | 受击闪白 | [关闭](270_flash_off.png) | [开启](270_flash_on.png) |
| 271 | 局部换色 | [关闭](271_recolor_off.png) | [开启](271_recolor_on.png) |
| 296 | 环形进度 | [关闭](296_ring_off.png) | [开启](296_ring_on.png) |
| 297 | 扇形冷却 | [关闭](297_cooldown_off.png) | [开启](297_cooldown_on.png) |
| 298 | 液体进度条 | [关闭](298_liquid_off.png) | [开启](298_liquid_on.png) |
| 112 | 平静水面 | [关闭](112_calm_off.png) | [开启](112_calm_on.png) |
| 118 | 交互涟漪 | [关闭](118_interactive_off.png) | [开启](118_interactive_on.png) |
| 192 | 全息投影 | [关闭](192_hologram_off.png) | [开启](192_hologram_on.png) |
| 190 | 护盾受击波纹 | [关闭](190_shield_hit_off.png) | [开启](190_shield_hit_on.png) |
| 096 | 透明玻璃 | [关闭](096_clear_off.png) | [开启](096_clear_on.png) |
| 326 | 高斯模糊 | [关闭](326_gaussian_off.png) | [开启](326_gaussian_on.png) |
| 317 | LUT调色 | [关闭](317_lut_off.png) | [开启](317_lut_on.png) |
| 348 | CRT显像管 | [关闭](348_crt_off.png) | [开启](348_crt_on.png) |
