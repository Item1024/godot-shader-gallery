# M4 可复用资产实施与验证记录

日期：2026-10-20。实施基线：`056e99e`。环境：Windows、Godot 4.7.2.stable.official.ed1daf0bf、Forward+ / Vulkan、RTX 5060。

**当前状态：实现及空工程专项已完成，最终验收未完成。** 用户反馈机器卡顿后停止重测试；本次按要求提交当前实现和验证记录，不能将本记录视作 M4 最终通过。

## 已实现

- 首批 20 项各有 `material.tres`、`usage.tscn`、`dependencies.json`；高斯另有 `material_vertical.tres`。原目录、编号、标签、Shader 与 demo 入口保留。
- 源文件 `tools/usage_assets.py` 从 `tools/build_library.py` 调用，全部资产及逐项中文说明受现有生成清单保护；未删除清单或强制覆盖。
- 原生 Sprite2D、Control/ColorRect、MeshInstance3D 接入场景，不依赖图库 UI、catalog 或 stage.gd。玻璃含背景与相机，水面含深度参考物，LUT 同时列入暖色和中性表。
- 动态场景由 `shared/usage_player.gd` 适配已有连续时间播放器；水面与球面求交提取到 `shared/surface_hit.gd`，图库和独立场景共用。材质使用 `resource_local_to_scene`，避免场景实例互相修改参数或时间。
- 每项中文说明列出复制方法、材质位置、代码改值、动态播放/暂停/重置、交互规则和平台限制。

## 实际通过

| 检查 | 结果 |
|---|---|
| 20 项分别复制到独立空工程 | 335 项断言通过，失败 0；76 个参数低/高值实际像素变化、默认值及固定状态重置通过 |
| 实例隔离 | 20 项材质对象/参数隔离；8 项动态时钟隔离 |
| 单次事件与输入 | 闪白、涟漪与护盾触发/过期不重复；拖动不触发；移动和旋转接入场景后命中投影误差小于 3 像素 |
| 双遍高斯 | 横竖材质、两遍之间的 BackBufferCopy；独立 CPU 分离核误差小于 2/255，对角像素有能量；三档纯色归一化 |
| 其他画面约束 | 溶解 0/1、描边零宽、换色零强度、进度空满、零波高、CRT 全零、中性 LUT 通过；20 项总览已查看 |
| M2 回归 | 344 项逻辑和 445 项真实显卡断言通过 |
| M3 回归 | 串行复查通过：832 项断言、182 张实际渲染图 |
| 资源验证 | 421 项、23 类、失败 0，含新增材质、usage、依赖和默认值 |
| 生成保护 | 21 项通过，保留原 19 项，新增材质手改保护和 CRLF 只读检查 |
| 生成一致性 | `CHECK OK files=1771`；新增材质固定 LF，再纳入文本换行哈希规则，安全生成器正常通过 |

复制检查由 `tools/test_m4.py` 逐项按清单创建全新工程，并以 `tools/test_m4.gd` 作为单独的测试脚手架运行真实 GPU 检查。原项目的 stage、catalog、metadata 不作为接入运行依赖；case.json 仅供测试读取期望参数。

## 失败与待补

- 最终全库 GPU 审查未出现 `AUDIT_COMPLETE 421`，在读取图像时发生内存分配失败并崩溃，因此**421 项本轮真实运行回归未通过完整验收**。不能沿用 M3 的历史全库结果替代。
- 高斯新增专项曾发生一次图像读取分配失败；同一代码专项及随后完整 20 项重跑通过。M3 首次复查也遇到分配失败，随后串行复查通过。检查时系统可用提交内存约 1 GB；这些失败与当前内存压力相关，但未证明唯一根因。
- 原有 7 个 Texture RID 退出警告尚未定位，本轮完整退出状态未确认。
- 空工程最终通过报告的材质源哈希来自 LF 固定前的版本；随后材质仅通过生成器改变了 CRLF/LF 字节，未改值或逻辑。提交前逐项核对了 20 个空工程共 99 个运行依赖条目：保存的源哈希有效，当前文件与通过版本除 CRLF/LF 外完全一致；生成检查及 M1 基线差异检查通过。
- 仍需：空闲时补齐最终全库显卡审查并更新最终验收结论。本次先保存可复查的实现和已完成检查，当前不再自动启动重测试。
- 其他显卡、系统、Mobile / Compatibility / Web 未验证；其余 401 项未新增可复制资产。M5 140 状态参考图与 M6 性能/浏览优化未实施。

## 证据与复查

证据在忽略目录 `artifacts/`：`m4/report.json`、对应 `m4/copies-*/` 独立工程与图像/导入日志、`m4/overview.png`、`m4-m2-gpu.log`、`m4-m3-final.log`、`m4-generator-tests.log`、未完成的 `m4-audit.log`。这些不是 M5 人工确认参考图。

在有足够资源余量时复查，以下重测试应串行执行：

```powershell
python tools/build_library.py --check
python tools/test_m4.py
& 'E:\Godot\Godot_v4.7.2-stable_win64_console.exe' --headless --path . --script res://tools/validate.gd
& 'E:\Godot\Godot_v4.7.2-stable_win64_console.exe' --path . -- --audit --quit-after-audit
```

Godot 打开任一首批效果的 `usage.tscn`，按 F6 查看独立接入场景；按 dependencies.json 复制相对路径文件即可在目标工程导入。图鉴继续使用 F5，原 demo.tscn 继续使用 F6。
