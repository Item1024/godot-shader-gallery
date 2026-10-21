# M5 参考图与人工确认

目前没有已批准的参考图库。140 张候选图已采集、自动行为及默认图重复性检查通过，仍需用户确认。实际结果见 [M5 验证记录](../../docs/M5_VERIFICATION.md)。

状态清单维护在 [visual_cases.json](../visual_cases.json)。`off / default / min / max / secondary / early / late` 分别表示关闭、默认、主参数最小、主参数最大、次参数变化、较早时间、较晚时间。每项明确区域、参数值、事件、预期时间变化和行为阈值。6 张额外对照图不计入 140 个正式状态。

候选采集目录为 `artifacts/m5/capture-final/`，独立默认图复查为 `artifacts/m5/repeat-final/`。人工审阅入口为 `artifacts/m5/review-final/REVIEW.md`，含四页 140 状态总览及四页 M1 历史样本对照；原尺寸图片在采集目录。M1 对照只用于观察预期变化，不做异尺寸图片的像素通过判断。

用户确认全部状态及预期变化后，才将完整候选采集目录复制到本目录的 `reference/`；保留其中原始 `capture.json` 和 6 张专项图，不修改采集记录。再新增 `reference/approval.json`，记录实际确认者、确认日期和该 `capture.json` 的 SHA-256：

```json
{
  "status": "approved",
  "reviewer": "实际确认者",
  "reviewed_at": "实际确认日期",
  "capture_sha256": "经确认的 capture.json 的 SHA-256"
}
```

上面的字段只是格式说明，不是批准记录。确认前不创建批准文件。比较器的 `--reference tests/visual/reference` 仅接受有有效批准记录、图片哈希匹配且 GPU/驱动/引擎/采集设置一致的完整图库。基线文字清单或图片缺失、被改动、未批准、环境不同均停止比较，不自动更新参考图。

生成器不管理本目录；参考图不能随 `build_library.py` 自动重建或通过删清单覆盖。新输出使用新的 `artifacts/` 目录；不要覆盖已有输出、M1 样本或已批准参考图。
