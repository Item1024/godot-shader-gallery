# M1 生成安全与基线样本验收

日期：2026-10-19。效果源码基线：`8cff48e07b712a384e7b880b7ebb8b82592f69c0`。

## 本次实现

- 重建只读取仓库内的 `assets/cottage.png`，不再查找相邻 Blender 工程；这张输入图片不会被生成器重写。
- 新增 `--check`、`--effect CATEGORY/SLUG` 及两者组合。先在系统临时目录生成，通过手改检查后只写回实际变化的内容。
- `tools/generated_manifest.json` 管理 1709 个生成文件。首次建立时逐项与基线 Git 提交核对，没有把当前手改文件自动登记成正确结果。
- 修改过、删除过的受管理文件，以及与新输出冲突的已有文件，都会阻止本次写入；不提供强制覆盖参数。缺少清单也不会自动重新信任当前目录。
- 文本内容哈希统一 LF / CRLF；二进制文件按原始字节比较。清单中的路径不能越出工程或经过链接重定向。
- 单项重建只处理该效果和确有变化的总索引，其他效果及公共素材不被重写；无变化的文件保留原字节及修改时间。
- 全部效果的 README 补充临时试改与长期维护的区别，避免下一次重建丢失修改。

## 自动检查结果

```text
python -B -m unittest discover -s tools/tests -v
Ran 19 tests
OK

python tools/build_library.py --check
CHECK OK files=1709

python tools/build_library.py --effect dissolve/noise
BUILD OK scope=dissolve/noise files=8 updated=0
```

19 项测试涵盖只读检查、源变化检测、幂等构建、Shader/说明/二进制手改保护、删除保护、新文件冲突、清单缺失与格式/路径错误、单项范围、无关手改保留、CRLF、无效效果名、输入缺失，以及从工程外启动独立副本。检查模式和无变化构建同时比较内容与修改时间。

独立 Git 检出验收通过：从基线 `8cff48e` 本地克隆，在新目录应用本次 M1 补丁；相邻目录没有 Blender 小屋工程。分别从工程外运行检查模式、全量构建、单项构建，均返回 0，得到 `CHECK OK files=1709`、`BUILD OK scope=all files=1709 updated=0`、`BUILD OK scope=dissolve/noise files=8 updated=0`。前后 2204 个工程文件的原始字节与修改时间均一致。完整报告在本机 `artifacts/m1-isolated-checkout.json`。

## 运行与画面样本

本机 Godot 4.7.2、Forward+ / Vulkan、RTX 5060 实际采集首批 20 个效果，每项开启/关闭各一张，共 40 张；固定效果时间为 1 秒，预览为 900×660。

- [样本目录及开关对照](../tests/baseline_m1/README.md)
- [固定案例与源码哈希](../tests/m1_cases.json)
- [实际采集报告](../tests/baseline_m1/capture.json)

两次独立 GPU 运行得到的 40 张图片逐张字节一致。每张 PNG 的尺寸、SHA-256，以及 20 个 Shader、展示脚本和小屋图片的来源均经过核对。再次采集时，工具会先检查输入哈希；源码改变后不能继续把新画面标为旧基线，已有采集记录也不会被覆盖。

另将采集输出指向已保存的样本目录，确认工具报出 `Capture already exists` 并停止。对应 `artifacts/m1-capture-protection.log` 中的这条错误是防覆盖负向测试的预期结果。

这些图片记录优化前的外观，不是经过视觉正确性确认的参考答案。M5 的 140 状态行为/画面验收仍待实施。

资源检查另得到：

```text
VALIDATION effects=421 categories=23 failures=0
```

本次没有修改效果公式或 `shared/` 中的运行逻辑。M2 的播放和命中修正、M3 的参数精修以及后续里程碑尚未实施。

## 日常使用

1. 临时改 Shader 可以直接观察效果。准备重建前先运行 `--check`。
2. 如果提示手改冲突，先备份并把需要保留的公式合回 `tools/build_library.py`；原理说明合回 `tools/plain_language.py`，分类名与顺序合回 `tools/effect_catalog.py`。
3. 确认改动已经保留后，只恢复对应生成文件到 Git 中的原版，再重建对应效果。工具不会替你丢弃这些手改内容。
4. 公共素材与跨案例生成规则变化后使用全量重建。删除或改名生成文件时，需明确检查旧文件和清单的移除；工具不会自动删除它们。
5. 提交时同时提交生成源、生成结果和清单。退出码 0 为成功，1 为检查发现待生成变化，2 为冲突或错误。
