"""Summarize three independent M6 runs without treating frame intervals as CPU time."""
from pathlib import Path
import hashlib
import json
import math
import statistics

ROOT = Path(__file__).resolve().parents[1]


def stats(values):
    values = sorted(values)
    return {"median": statistics.median(values), "p95": values[math.ceil(len(values) * .95) - 1]}


def main():
    groups = {}
    hashes = {}
    for phase in ["baseline", "after"]:
        runs = []
        for run in range(1, 4):
            file_phase = "after-final" if phase == "after" else phase
            path = ROOT / f"artifacts/m6/{file_phase}-{run}.json"
            data = json.loads(path.read_text())
            assert data["complete"] and len(data["effects"]) == 20
            assert data["warmup_frames"] == 120 and data["sample_frames"] == 600
            assert data["window_size"] == "(1440, 900)" and data["preview_size"] == "(900, 660)"
            assert data["vsync"] == 0 and data["max_fps"] == 0
            hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
            rows = []
            for effect in data["effects"]:
                assert len(effect["samples"]) == 600
                rows.append({"number": int(effect["number"]), "animated": effect["animated"],
                             "warm_switch_ms": effect["warm_switch_ms"],
                             "drawn_sample_frames": sum(s["preview_drawing"] for s in effect["samples"]),
                             **{key: stats([s[key] for s in effect["samples"]]) for key in
                                ["frame_interval_ms", "render_cpu_ms", "render_gpu_ms", "global_video_memory_bytes"]}})
            runs.append(rows)
        groups[phase] = runs
    sources = [json.loads((ROOT / f"artifacts/m6/{phase}-{run}.json").read_text())
               for phase in ["baseline", "after-final"] for run in range(1, 4)]
    for key in ["engine", "gpu", "driver", "method"]:
        assert all(d[key] == sources[0][key] for d in sources)
    assert len({d["source_sha256"]["benchmark"] for d in sources}) == 1
    assert len({d["source_sha256"]["stage"] for d in sources[:3]}) == 1
    assert len({d["source_sha256"]["stage"] for d in sources[3:]}) == 1
    summary = {"environment": {k: sources[0][k] for k in ["engine", "gpu", "driver", "method"]},
               "source_sha256": {"baseline": sources[0]["source_sha256"], "after": sources[3]["source_sha256"]},
               "raw_sha256": hashes, "runs": groups, "whole_frame_cpu_ms": None, "preview_memory_bytes": None}
    lines = ["# M6 性能实测", "", "日期：2026-10-23。Windows、Godot 4.7.2、RTX 5060、Forward+ / Vulkan，驱动 32.0.15.8097。",
             "", "修改前后各独立启动 3 次；每次首批 20 项，每项预热 120 帧、采样 600 帧（每阶段共 36000 个样本帧）。实际窗口 1440×900，独立预览 900×660，VSync 关闭，帧率不限制；画质使用同一工程默认值。以默认参数播放（单次事件未触发）采集，未测开关差或纯 Shader 内核开销。", "",
             "CPU 渲染耗时为主窗口与实际绘制的预览视口 CPU 时间加 frame setup 时间；GPU 渲染耗时为两者 GPU 时间之和，均来自 RenderingServer 测量。静态预览停画后排除其陈旧的最后一帧时间，只计主窗口合成；这不是把 GPU 未测值填成零。", "",
             "整帧 CPU 耗时：未测。原始 process_cpu_ms 来自低频缓存的 Performance.TIME_PROCESS，受场景配置与报告写盘影响，不能代表这 600 帧的逐帧 CPU，故不用于结论。frame_interval_ms 只是两次绘制完成之间的墙钟间隔，包含调度/等待，不冒充 CPU 或 GPU 耗时。预览独占内存：未测；原始数据仅含全局视频内存，无法可靠归因到预览。", "",
             "下表每格为三次独立运行中位数的中位数 / 三次 P95 的中位数，单位 ms；每次运行的统计及原始文件哈希见 M6_PERFORMANCE.json。", "",
             "| 编号 | 动态 | CPU 渲染：前→后（中位/P95） | GPU 渲染：前→后（中位/P95） | 后三次预览绘制帧数 |",
             "|---|---|---|---|---|"]
    regressions = []
    for index in range(20):
        before = [r[index] for r in groups["baseline"]]
        after = [r[index] for r in groups["after"]]
        def cell(rows, key):
            return "/".join(f"{statistics.median(r[key][s] for r in rows):.3f}" for s in ["median", "p95"])
        b = statistics.median(r["render_gpu_ms"]["median"] for r in before)
        a = statistics.median(r["render_gpu_ms"]["median"] for r in after)
        if a - b > max(b * .1, .2):
            regressions.append(before[0]["number"])
        draws = "/".join(str(r["drawn_sample_frames"]) for r in after)
        lines.append(f'| {before[0]["number"]:03d} | {"是" if before[0]["animated"] else "否"} | '
                     f'{cell(before,"render_cpu_ms")} → {cell(after,"render_cpu_ms")} | '
                     f'{cell(before,"render_gpu_ms")} → {cell(after,"render_gpu_ms")} | {draws} |')
    summary["gpu_regressions_over_budget"] = regressions
    lines += ["", f"GPU 中位耗时上升超过 max(基线×10%, 0.2 ms) 的项目：{regressions or '无'}。"]
    for phase in ["baseline", "after"]:
        switch = stats([r["warm_switch_ms"] for run in groups[phase] for r in run])
        summary[phase + "_warm_switch_ms"] = switch
        lines += [f"{phase} 的 60 次预热后配置至首帧绘制切换：中位 {switch['median']:.3f} ms，P95 {switch['p95']:.3f} ms。"]
    lines += ["", "上述切换为同效果重建。另用同一脚本在原始 stage（从提交 45ab0f0 提取）与最终 stage 上各独立运行 3 次：每次先将全部 20 项各预热 120 帧，再依清单循环测量 20 次不同效果间的配置至首帧绘制。"]
    for phase in ["baseline", "after"]:
        samples = []
        for run in range(1, 4):
            path = ROOT / f"artifacts/m6/switch-{phase}-{run}.json"
            data = json.loads(path.read_text())
            assert data["complete"] and len(data["switches"]) == 20
            assert data["window_size"] == "(1440, 900)" and data["preview_size"] == "(900, 660)"
            assert data["vsync"] == 0 and data["max_fps"] == 0
            assert all(row["from"] != row["to"] for row in data["switches"])
            hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
            samples += [row["ms"] for row in data["switches"]]
        result = stats(samples)
        summary[phase + "_different_effect_switch_ms"] = result
        lines += [f"{phase} 的 60 次不同效果切换：中位 {result['median']:.3f} ms，P95 {result['p95']:.3f} ms。"]
    lines += ["", "切换时间包含配置及首帧绘制等待，不等同于纯脚本时间。冷启动、首批清单之外的切换和真实图库完整 UI 的切换延迟未测。未使用 FPS 或提升百分比填充结论。", "",
              "首轮 after-1/2/3 把 SubViewport 节点保留的 UPDATE_ONCE 当成仍在绘制，误将玻璃/高斯的陈旧计时累加为回退。最终在 frame_post_draw 后将节点状态同步为 DISABLED，再独立重采 after-final-1/2/3；旧数据保留供诊断，不纳入上表。门槛未放宽，算法未改。", "",
              "方法依据：[RenderingServer 视口 CPU/GPU 时间](https://docs.godotengine.org/en/stable/classes/class_renderingserver.html#class-renderingserver-method-viewport-set-measure-render-time)。CPU 渲染计时不包括脚本、物理等其他引擎子系统。以上结果仅适用于本机，Mobile / Compatibility / Web 未测。"]
    (ROOT / "docs/M6_PERFORMANCE.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "docs/M6_PERFORMANCE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("M6_PERFORMANCE runs=6 samples=72000 gpu_regressions=" + str(regressions))


if __name__ == "__main__":
    main()
