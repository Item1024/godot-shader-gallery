"""M3's twenty parameter contracts. Values here drive metadata, UI and reset."""


def number(key, label, low, high, default, step=0.01, unit="", help="", advanced=False):
    return dict(key=key, label=label, type="float", target="material", min=low,
                max=high, step=step, default=default, unit=unit, help=help, advanced=advanced)


def color(label, default="#55e8bb", key="u_color"):
    return dict(key=key, label=label, type="color", target="material", default=default,
                unit="", help="", advanced=False)


def choice(key, label, values, default, type="enum"):
    return dict(key=key, label=label, type=type, target="material", options=values,
                default=default, unit="", help="", advanced=False)


def profile(parameters, animated=False, action="", note=""):
    return dict(parameters=parameters, animated=animated, action=action, profile_note=note)


def progress(default=0.32, label="消失进度"):
    return number("u_amount", label, 0, 1, default, help="0 为起点，1 为终点；端点不受其他参数影响。")


def edge(default=0.04, label="亮边宽度"):
    return number("u_edge_width", label, 0, 0.15, default, 0.001, "UV 比例", "只扩宽保留侧的交界，不改变消失区域。")


def density():
    return number("u_noise_scale", "花纹密度", 2, 32, 8, 0.1)


def angle(key="u_start_deg", label="起点角度", high=360, default=0):
    return number(key, label, 0, high, default, 1, "°", "起点 0° 在顶部，正角度沿顺时针。")


def clockwise():
    return dict(key="u_clockwise", label="顺时针", type="bool", target="material",
                default=True, unit="", help="关闭后沿逆时针填充。", advanced=False)


WAVE = number("u_wave_height", "波高", 0, 0.25, 0.04, 0.001, "场景单位", "0 为平面；波形幅度上界为此值。")
PROFILES = {
    "dissolve/noise": profile([progress(), density(), edge(), color("亮边颜色")]),
    "dissolve/direction": profile([progress(), angle("u_direction_deg", "方向"), edge(), color("亮边颜色")]),
    "dissolve/burn": profile([progress(), density(), edge(0.05, "焦边宽度"), color("火边颜色", "#ff5206")]),
    "outline/outer": profile([number("u_width_px", "宽度", 0, 16, 3, 0.5, "贴图像素"), number("u_softness", "柔和程度", 0, 1, 0.15), color("描边颜色")]),
    "outline/inner": profile([number("u_width_px", "宽度", 0, 16, 3, 0.5, "贴图像素"), number("u_softness", "柔和程度", 0, 1, 0.15), color("描边颜色")]),
    "emission/breathing": profile([number("u_intensity", "发光强度", 0, 5, 1.5), number("u_frequency", "频率", 0.1, 3, 0.5, 0.01, "次/秒"), number("u_min_brightness", "最低亮度", 0, 1, 0.2), color("发光颜色")], True),
    "emission/diagonal": profile([number("u_intensity", "强度", 0, 5, 2), number("u_band_width", "光带宽度", 0.01, 0.5, 0.12, 0.001, "UV 比例"), angle("u_angle_deg", "角度", 180, 45), number("u_period", "周期", 0.2, 5, 1.5, 0.01, "秒")], True),
    "sprite/flash": profile([number("u_strength", "强度", 0, 1, 1), number("u_duration", "持续时间", 0.05, 1, 0.15, 0.01, "秒"), color("闪光颜色", "#ffffff")], True, "播放一次", "播放一次或点击图案触发；新事件替换旧事件，暂停时事件也暂停。"),
    "sprite/recolor": profile([color("源颜色", "#a2f6da", "u_source_color"), color("目标色"), number("u_tolerance", "容差", 0, 1, 0.2, help="按 RGB 距离选择颜色；0 只选择完全相同的颜色。"), progress(1, "混合强度")]),
    "ui/ring": profile([progress(0.55, "进度"), number("u_ring_width", "环宽", 0.01, 0.3, 0.07, 0.001, "UV 比例"), angle(), clockwise(), color("进度颜色")]),
    "ui/cooldown": profile([progress(0.55, "进度"), angle(), clockwise(), color("扇区颜色")]),
    "ui/liquid": profile([progress(0.55, "液位"), number("u_wave_height", "波高", 0, 0.08, 0.025, 0.001, "区域高度比例"), number("u_wave_frequency", "波频", 1, 8, 3, 0.1), color("液体颜色")], True),
    "water/calm": profile([WAVE, number("u_wave_length", "波长", 0.25, 4, 1, 0.001, "场景单位"), color("浅水色", "#1a9e9c", "u_shallow_color"), color("深水色", "#041f45", "u_deep_color"), number("u_depth_distance", "变深距离", 0.2, 5, 2, 0.001, "场景单位")], True, note="深度来自当前屏幕的不透明物体；不包含水下体积散射。"),
    "water/interactive": profile([number("u_ripple_speed", "扩散速度", 0.1, 2, 0.6, 0.01, "场景单位/秒"), number("u_ripple_width", "波纹宽度", 0.01, 0.2, 0.04, 0.001, "场景单位"), number("u_duration", "持续时间", 0.2, 3, 1, 0.01, "秒"), number("u_strength", "强度", 0, 1, 0.6), WAVE], True, note="点击起伏水面触发一次；最新点击替换旧圈。继承平静水面默认波长 1。"),
    "magic/hologram": profile([number("u_line_density", "扫描线密度", 4, 120, 40, 1, "条/模型单位"), number("u_intensity", "线亮度", 0, 3, 1), number("u_opacity", "基础透明度", 0, 1, 0.25), number("u_rim_strength", "边缘亮度", 0, 3, 1), color("全息颜色")], True, note="条纹使用模型局部坐标；这是表面着色，不是体积全息。"),
    "magic/shield_hit": profile([number("u_duration", "持续时间", 0.2, 2, 1, 0.01, "秒"), number("u_ring_width", "环宽", 0.01, 0.3, 0.08, 0.001, "场景单位"), number("u_intensity", "亮度", 0, 5, 1.8), color("波纹颜色")], True, note="点击球面触发，亮圈沿球面弧长扩散，结束不重复。只支持本例球形命中。"),
    "glass/clear": profile([number("u_distortion", "折弯强度", 0, 0.08, 0.025, 0.001, "屏幕比例"), color("染色", "#b3e6f2"), number("u_opacity", "不透明度", 0, 1, 0.85)], note="屏幕折射只能读取已画出的背景；镜头外内容和完整物理玻璃未实现。"),
    "lens/gaussian": profile([number("u_radius_px", "半径", 0, 16, 4, 0.25, "屏幕像素", "每方向的采样支撑半径；横向后复制屏幕，再做纵向。"), choice("u_quality", "质量", [dict(label="低 · 每方向 5 次", value=0), dict(label="中 · 每方向 9 次", value=1), dict(label="高 · 每方向 13 次", value=2)], 1)], note="两遍归一化高斯权重；低质量大半径可能出现稀疏采样。"),
    "color/lut": profile([progress(1, "混合强度"), choice("lut_texture", "颜色表", [dict(label="暖色 LUT", value="res://assets/warm_lut.png"), dict(label="中性 LUT", value="res://assets/neutral_lut.png")], "res://assets/warm_lut.png", "texture")], note="16³ 颜色表横排 16 个蓝色切片；红绿双线性、蓝色两片插值，采样限制在各片中心。PNG 按原始 RGB 数据读取。"),
    "retro/crt": profile([number("u_curvature", "屏幕弯曲", 0, 0.2, 0.04, 0.001), number("u_scanline_strength", "扫描线强度", 0, 1, 0.25), number("u_vignette", "暗角", 0, 1, 0.3), number("u_rgb_mask", "三色条纹强度", 0, 1, 0.15)]),
}


def parameter_notes(parameters):
    lines = []
    for p in parameters:
        bounds = f"{p['min']}–{p['max']}，步长 {p['step']}" if p["type"] == "float" else p["type"]
        lines.append(f"- {p['label']}（{p['key']}）：{bounds} {p['unit']}；默认 {p['default']}。{p['help']}")
    return "\n".join(lines)
