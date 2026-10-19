# M2 播放时间与表面命中验收

日期：2026-10-19。实施前基线：`27b1064`（M1 实现为 `e004adb`）。

验证环境：Windows，Godot 4.7.2.stable.official.ed1daf0bf，Forward+ / Vulkan 1.4，NVIDIA GeForce RTX 5060。

## 已完成的行为

- 新增 `shared/effect_player.gd`。播放器按 `delta × 播放速度` 累加时间，传入 Shader 的 `u_speed` 保持为 1；改速度不重新计算已经播放的时间。速度为 0、暂停与恢复都保留当前时刻，显式 `seek()` 才跳到指定时间。
- 图库和所有独立 `demo.tscn` 使用同一播放器；每个展示实例单独创建材质。一个播放器也可同步多个材质，供后续双遍效果复用。
- 交互涟漪使用相机射线与当前起伏水面的交点。先在网格局部空间求静止平面初值，再按 Shader 同一波形和导数最多修正 8 次；越界、相机后方、过于平行或未收敛的结果不触发。
- 护盾使用局部球面最近的正向交点，亮圈按沿球面走过的距离扩散，摄像机转动后仍保持在表面上。
- 水面和护盾只在有效点击释放时触发一次，默认 1 秒后淡出；新点击替换上一圈。暂停时可以设置新的命中点，事件年龄保持不变。重置参数会清除事件并恢复默认时间、速度、强度、尺度、颜色及效果开关。
- 按下到释放移动不超过 4 个界面像素才算点击；一旦超过，即使拖回起点也不触发。滚轮缩放、失去按键状态、窗口失焦和隐藏预览都会取消待触发手势。
- 点击位置根据实际容器和 SubViewport 尺寸换算，支持 `stretch_shrink`。二维图片按自己的显示区域换成 UV，图片外留边不会移动交互中心。
- 修改首先保存在生成源中，再重建两项 Shader、元数据和说明。全部 421 项的公共参数说明同步新的播放规则；其余 419 个 Shader 公式未改，目录、编号和原有 59 项近似标签保持。

## 实测结果

| 检查 | 实际结果 |
|---|---|
| 运行逻辑检查 | 344 项断言，失败 0 |
| 真实显卡行为检查 | 445 项断言，失败 0 |
| 基本命中矩阵 | 水面 30 组、护盾 30 组；各为 3 个相机方位 × 5 个表面点 × 2 个视口尺寸 |
| 测试视口尺寸 | 900×660、1280×720 |
| 实际 GPU 表面标记最大偏差 | 水面 1.336 像素；护盾 0.212 像素，均小于 3 像素目标 |
| 已知表面点的最大局部距离误差 | 0.00001425 场景单位 |
| 水面最大高度残差 | 0.00000985 场景单位，小于 0.001 目标 |
| 额外波形和网格变换检查 | 27 组：3 档强度 × 3 档尺度 × 3 个时刻，包含平移、旋转与非均匀缩放；GPU 标记最大偏差 1.105 像素 |
| 图库真实输入路径 | 1440×900、1180×720 两种窗口尺寸，各检查 `stretch_shrink=1/2`，点击经实际 `gui_input` 连接触发 |
| 独立场景 | 噪声溶解、交互涟漪、护盾受击均可加载；两种交互独立入口的真实 GUI 点击通过 |
| 动画画面对比 | 呼吸发光、黏性融合在改速度、速度为 0、暂停时逐像素一致；恢复后画面继续变化 |
| 单次事件画面对比 | 两项触发后都改变实际像素；过期画面与同一时刻未触发画面逐字节一致，无自动重播 |
| 全库实际运行 | `AUDIT_COMPLETE 421`，421 / 421 运行检查通过 |
| 结构与资源 | `VALIDATION effects=421 categories=23 failures=0` |
| 生成一致性 | `CHECK OK files=1709` |
| 生成保护回归 | 19 项 Python 测试通过，107.014 秒 |

命中检查不只把射线交点重新投影回去：测试还保留实际效果的顶点代码，用白色表面标记替换片元颜色，测量 GPU 画出的标记中心，独立核对 CPU 命中与 Shader 波面的位置。27 组额外检查中，高波可能遮住预设表面点，因此允许命中该射线上更靠近相机的水面，但 GPU 标记仍必须可见并满足误差要求。

最终显卡专项运行与资源检查未记录 Shader 编译错误或脚本错误。全库退出时终端仍报告 `7 RIDs of type "Texture" were leaked`；这是退出阶段的纹理释放警告，本轮未定位来源，不将其当作资源释放已验证通过。445 项专项检查没有出现该警告。

早期在沙箱内运行时出现系统证书读取和 Shader 缓存写入限制；真实显卡验收已在获得授权后于沙箱外完成。逻辑断言的失败数与这些环境错误分别核对。

## 复查命令与本机证据

在工程根目录运行 PowerShell：

```powershell
$godotM2 = 'E:\Godot\Godot_v4.7.2-stable_win64_console.exe'
& $godotM2 --headless --path . --script res://tools/test_runtime.gd
& $godotM2 --path . --script res://tools/test_runtime.gd -- --render-checks
& $godotM2 --headless --path . --script res://tools/validate.gd
& $godotM2 --path . -- --audit --quit-after-audit
python tools/build_library.py --check
python -B -m unittest discover -s tools/tests -v
```

`--render-checks` 需要真实渲染器；只运行 headless 检查不代表 GPU 验收完成。检查结果保存到以下已忽略的本机路径，重复运行会更新这些临时报告：

- `artifacts/m2/runtime_logic.json`、`runtime_gpu.json`：逐项断言、60 组命中、27 组波形参数、引擎/显卡与源码 SHA-256。
- `artifacts/m2/marker_*.png`：12 张实际顶点标记截图。
- `artifacts/m2/event_118_active.png`、`event_190_active.png`：两项实际触发画面。
- `artifacts/m2-logic.log`、`m2-gpu.log`、`m2-validate.log`、`m2-audit.log`：对应 Godot 日志。
- `artifacts/runtime_audit.json`：本次 421 项全库运行报告；`artifacts/m2-generator-tests.log`：19 项生成保护测试结果。

本文件保存验收摘要并随代码提交；这些临时输出不作为 M5 已确认的画面参考图。M1 的 40 张样本及源码哈希保持原样；M2 改变了展示脚本和两项公式后，旧采集工具会按设计拒绝把新画面标成 M1 基线。

## 如何查看与实现边界

用 Godot 导入 `project.godot` 并按 F5，搜索“交互涟漪”或“护盾受击波纹”。点击表面观察一次扩散，拖动检查旋转，再调整速度、设为 0、暂停/继续、重置。也可分别打开两项目录的 `demo.tscn` 按 F6。

命中求解仅用于本例的有限波面和球形护盾，不提供任意网格碰撞或场景遮挡物查询；CPU 使用解析波面，GPU 网格是细分三角形近似，因此保留像素误差验收。不能由这些测试推断所有相机角度、任意波形或其他平台都支持。多个点击不叠加，最新事件替换旧事件。

本轮没有精修专用参数或其他效果算法，也没有做跨平台、性能预算或全库视觉正确性验收。M3–M6 仍待实施，下一步见 [优化实施方案](OPTIMIZATION_PLAN.md)。

API 与坐标约定依据：[Camera3D 射线与投影](https://docs.godotengine.org/en/4.7/classes/class_camera3d.html)、[SubViewportContainer 尺寸与缩放](https://docs.godotengine.org/en/4.7/classes/class_subviewportcontainer.html)、[Spatial Shader 模型局部坐标](https://docs.godotengine.org/en/4.7/tutorials/shaders/shader_reference/spatial_shader.html)。交互技能检索未找到可直接用于本项目的拖动阈值条目，4 像素阈值按已保存的 M2 方案实施。
