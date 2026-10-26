# Windows x64 便携包

日期：2026-10-26。按优化方案第 8 节继续 Windows 分发，不精修其余效果、不改 Shader 算法，也不开始跨平台适配。

M5/M6 的三个本地提交已推送，远程 main 经核对为 `8ac2bc1fcb8f7d97b3bd69a2683efc7b43912cbd`。随后在此基线上增加导出配置、构建验证工具及审查报告的原始文件哈希；普通浏览/播放路径没有改动。

## 本机交付

ZIP：`artifacts/windows/shader-atlas-windows-x64-20261026-r2.zip`。

- 大小：43,902,111 字节（约 41.87 MiB）。
- ZIP SHA-256：`fc0a79e2764f48f486a6eaf49acc828fcb7fcdc2417e287ade3c11c969bc61a8`。
- EXE：109,268,480 字节，PE 架构为 Windows x64。
- PCK：5,386,260 字节。
- 原始构建和验证目录：`artifacts/windows/shader-atlas-windows-x64-20261026-r2/`。
- 完整构建报告 SHA-256：`4d3588d3380de1893e9816b721fe2d0d8ece6ff33f4465f78793da9100bd1b6e`；报告在上述目录的 `build-report.json`，保存包内所有文件哈希。

解压整个 ZIP 后，双击 `ShaderAtlas/ShaderAtlas.exe`；不需要 Godot 编辑器。保留同目录的 PCK 和附带目录。`effects/`、`shared/`、`assets/` 提供可阅读和复制的源文件，支持现有“打开效果目录”和独立示例接入流程。引擎及第三方许可声明随包附带，未另行指定本项目源码许可证。

ZIP、模板、导入缓存和运行证据位于已忽略的 `artifacts/`，不提交二进制，也未创建 GitHub Release 或公开下载地址。代码仓库中的相对路径仅指本机输出。

## 构建方案

采用 Godot 原生 `Windows Desktop`、x86_64 release 导出，EXE 与 PCK 分开，不携带编辑器。沿用 Forward+ / Vulkan，不修改图标资源，不启用代码签名。配置在 `export_presets.cfg`；无第三方打包依赖。

运行时通过 FileAccess 读取 JSON、Shader 源码及说明，因此显式保留 `*.json,*.md,*.gdshader`；排除测试参考图、测试工具、历史 artifacts 和开发文档。构建工具先从版本控制中的运行文件建立独立工程，避免将大型历史输出导入或打包。导出后才附加可复制源文件，确保裸 EXE/PCK 的验证不被外部源码掩盖。

引擎：`4.7.2.stable.official.ed1daf0bf`。匹配模板从 [Godot 官方 4.7.2 构建](https://github.com/godotengine/godot-builds/releases/tag/4.7.2-stable) 的标准版模板归档中提取 `templates/windows_release_x86_64.exe`，本机保存于 `artifacts/windows/templates/windows_release_x86_64.exe`。模板 SHA-256：`d34d36f3be1a6c49c56525ae86469b92e4f417ddf0b43cf00dd80c385c4b0562`。本次使用明确字节范围读取并由 ZIP 校验解压该成员，没有下载或宣称验证整个 1.19 GB 归档的 SHA-256。没有安装全局模板或改变代理设置。

```powershell
python tools/build_windows.py --template artifacts/windows/templates/windows_release_x86_64.exe --output artifacts/windows/new-windows-build
```

输出目录及其同名 ZIP 必须不存在。模板需自行从官方同版本归档取得；引擎路径可用 `--godot` 指定。脚本使用 Python 标准库，检查已有输出后拒绝覆盖；任何步骤失败会保留日志，不创建“通过”归档。

## 实际验证

| 检查 | 结果与证据 |
|---|---|
| 独立导入/原生 release 导出 | `project/`、`import.log`、`export.log`；实际生成 EXE/PCK |
| PCK 内容 | 编辑器通过 `--main-pack` 挂载实际 PCK，在空工作目录运行验证脚本：421 项、1300 个原始 JSON/Shader/说明文件 SHA-256 匹配；Shader 与 demo 资源均存在；参考图和开发工具未混入。见 `validation/resources.json` |
| 实际 EXE GPU 运行 | 在空工作目录启动真实 release EXE，23 个分类分别使用独立进程，覆盖 421 个唯一编号；图像非空、uniform 可读取、无脚本/Shader/资源缺失错误。见 `validation/category-*/runtime_followup.json` 和对应日志/截图 |
| 实际 EXE 文件读取 | 上述 421 项审查记录的 Shader、README 哈希逐项与源文件匹配，共 842 项；验证不依赖编辑器对内容的解释 |
| 分发完整性 | ZIP CRC 及 2211 个包内文件 SHA-256 全部匹配 `build-report.json`；EXE 的 PE machine 为 `0x8664` |
| 许可声明 | 从 Godot 的 Engine API 导出引擎许可证、第三方 copyright 与完整许可证文本，并随包附带 |
| 画面检查 | 查看导出程序产生的图库截图，中文、列表、参数和效果可见；没有将冒烟检查当作全部 421 项的像素正确性认证 |

首轮目录 `shader-atlas-windows-x64-20261026/` 中的外部脚本验证未执行：官方 release 模板默认禁用路径覆盖，忽略 `--script`；进程等待到超时，没有生成通过记录。按[命令行选项适用范围](https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html)修正流程后，使用全新的 `-r2` 输出目录：PCK 结构检查由编辑器执行，实际渲染与读取验证由真实 EXE 的既有 `--audit` 路径执行。首轮输出未覆盖，也未计为通过。

此次没有改日常运行逻辑或 Shader，不重复 M6 的性能/140 状态采集；M1、已批准 M5 参考图及阈值均保持。M4/M5 取消的全库验收未补跑；本次 421 项属于 Windows 导出包本身的完整性及 GPU 冒烟验证。

## 保留的限制

验证环境为本机 Windows、RTX 5060、Forward+ / Vulkan。第 21 类退出仍有 `7 RIDs of type Texture were leaked` 警告，见 `validation/category-21.log`，没有标为解决。M4 历史内存分配失败、M6 的整帧 CPU/预览独占内存等未测项继续保留。分进程审查不证明单进程连续浏览全部效果的内存稳定性。

其他显卡、系统、Mobile / Compatibility / Web 未验证；未重新认证其余 401 项的画面正确性，59 项“演示近似”说明仍在。

原生导出与许可证资料：[Windows 导出](https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_windows.html)、[项目导出与资源过滤](https://docs.godotengine.org/en/stable/tutorials/export/exporting_projects.html)、[Engine 许可信息 API](https://docs.godotengine.org/en/stable/classes/class_engine.html#class-engine-method-get-license-info)。
