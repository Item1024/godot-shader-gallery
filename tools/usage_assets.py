"""M4's twenty minimal, copyable scenes and explicit dependency manifests."""
import json


def color_value(hex_value):
    value = hex_value.lstrip("#")
    channels = [int(value[i:i+2], 16)/255 for i in (0, 2, 4)]
    channels.append(int(value[6:8], 16)/255 if len(value) == 8 else 1.0)
    return "Color(" + ", ".join(str(v) for v in channels) + ")"


def material_text(entry, vertical=False):
    textures = [p for p in entry["parameters"] if p["type"] == "texture"]
    lines = [f'[gd_resource type="ShaderMaterial" load_steps={2+len(textures)} format=3]', "",
             f'[ext_resource type="Shader" path="{entry["shader"]}" id="1"]']
    for i, parameter in enumerate(textures, 2):
        lines.append(f'[ext_resource type="Texture2D" path="{parameter["default"]}" id="{i}"]')
    lines += ["", "[resource]", "resource_local_to_scene = true", 'shader = ExtResource("1")',
              "shader_parameter/u_enabled = true", "shader_parameter/u_time = 0.0", "shader_parameter/u_speed = 1.0"]
    for p in entry["parameters"]:
        value = p["default"]
        if p["type"] == "color": value = color_value(value)
        elif p["type"] == "bool": value = str(value).lower()
        elif p["type"] == "texture": value = f'ExtResource("{textures.index(p)+2}")'
        elif p["type"] == "float": value = str(float(value))
        lines.append(f'shader_parameter/{p["key"]} = {value}')
    if entry["slug"] in ["flash", "interactive", "shield_hit"]:
        lines.append("shader_parameter/u_event_time = -1.0")
    if entry["slug"] in ["interactive", "shield_hit"]:
        lines.append("shader_parameter/u_hit_position = Vector3(0, 0, 0)")
    if entry["slug"] == "interactive":
        lines.append("shader_parameter/u_wave_length = 1.0")
    if entry["slug"] == "gaussian":
        lines.append("shader_parameter/u_vertical = " + str(vertical).lower())
    return "\n".join(lines) + "\n"


FULL_RECT = '''layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
mouse_filter = 2
'''


def usage_scene(entry):
    directory = entry["directory"]
    kind = entry["kind"]
    animated = entry["animated"]
    gaussian = entry["slug"] == "gaussian"
    resources = [f'[ext_resource type="Material" path="{directory}/material.tres" id="Material"]']
    assets = []
    subresources = []
    player = ""
    if animated:
        resources.append('[ext_resource type="Script" path="res://shared/usage_player.gd" id="Player"]')
        target = "../Center/Effect" if kind == "sprite" else "../Effect"
        interaction = {"flash": "flash", "interactive": "water", "shield_hit": "shield"}.get(entry["slug"], "none")
        player = f'''\n[node name="Player" type="Node" parent="."]
script = ExtResource("Player")
material_targets = Array[NodePath]([NodePath("{target}")])
interaction = "{interaction}"
'''
        if kind == "spatial": player += 'camera_path = NodePath("../Camera3D")\n'
    if kind == "spatial":
        # Keep these fixtures explicit and editable in the scene inspector.
        subresources += ['''[sub_resource type="Environment" id="Environment"]
background_mode = 1
background_color = Color(0.063, 0.11, 0.176, 1)
ambient_light_source = 3
ambient_light_color = Color(0.569, 0.671, 0.773, 1)
ambient_light_energy = 0.55
tonemap_mode = 2
''', '''[sub_resource type="StandardMaterial3D" id="FloorMaterial"]
albedo_color = Color(0.09, 0.169, 0.239, 1)
roughness = 0.5
''', '''[sub_resource type="PlaneMesh" id="FloorMesh"]
size = Vector2(20, 20)
''', '''[sub_resource type="StandardMaterial3D" id="ReferenceMaterial"]
albedo_color = Color(0.56, 0.67, 0.65, 1)
roughness = 0.65
''']
        water = entry["category_slug"] == "water"
        geometry = '''[sub_resource type="PlaneMesh" id="EffectMesh"]
size = Vector2(3.6, 3.1)
subdivide_width = 70
subdivide_depth = 70
''' if water else '''[sub_resource type="SphereMesh" id="EffectMesh"]
radius = 0.92
height = 1.84
radial_segments = 64
rings = 40
'''
        subresources.append(geometry)
        nodes = '''[node name="Usage" type="Node3D"]

[node name="WorldEnvironment" type="WorldEnvironment" parent="."]
environment = SubResource("Environment")

[node name="Sun" type="DirectionalLight3D" parent="."]
rotation_degrees = Vector3(-42, -32, 0)
light_color = Color(1, 0.898, 0.741, 1)
light_energy = 1.5
shadow_enabled = true

[node name="Fill" type="OmniLight3D" parent="."]
position = Vector3(-2, 2.5, 2)
light_color = Color(0.345, 0.71, 1, 1)
light_energy = 3.5
omni_range = 8.0

[node name="Floor" type="MeshInstance3D" parent="."]
position = Vector3(0, -1.05, 0)
mesh = SubResource("FloorMesh")
material_override = SubResource("FloorMaterial")

[node name="Effect" type="MeshInstance3D" parent="."]
mesh = SubResource("EffectMesh")
material_override = ExtResource("Material")
'''
        if not water: nodes += 'position = Vector3(0, 0.1, 0)\n'
        nodes += '''
[node name="Camera3D" type="Camera3D" parent="."]
position = Vector3(0, 2, 5)
rotation = Vector3(-0.389097, 0, 0)
current = true
fov = 43.0
near = 0.05
'''
        if water:
            subresources.append('''[sub_resource type="SphereMesh" id="RockMesh"]
radius = 0.38
height = 0.7
''')
            for i in range(4):
                nodes += f'''\n[node name="Rock{i+1}" type="MeshInstance3D" parent="."]
position = Vector3({-1.3+i*0.85:.2f}, -0.2, -0.5)
mesh = SubResource("RockMesh")
material_override = SubResource("ReferenceMaterial")
'''
        else:
            subresources.append('''[sub_resource type="BoxMesh" id="ReferenceMesh"]
size = Vector3(0.46, 2.5, 0.5)
''')
            for i in range(5):
                nodes += f'''\n[node name="Background{i+1}" type="MeshInstance3D" parent="."]
position = Vector3({-2+i}, 0.2, -1.7)
mesh = SubResource("ReferenceMesh")
material_override = SubResource("ReferenceMaterial")
'''
    else:
        nodes = '[node name="Usage" type="Control"]\n' + FULL_RECT
        if kind != "post":
            nodes += '\n[node name="Background" type="ColorRect" parent="."]\n' + FULL_RECT + 'color = Color(0.0392, 0.0706, 0.1255, 1)\n'
        if kind == "sprite":
            assets.append("res://assets/subject.svg")
            resources.append('[ext_resource type="Texture2D" path="res://assets/subject.svg" id="Picture"]')
            nodes += '''
[node name="Center" type="Control" parent="."]
layout_mode = 1
anchors_preset = 8
anchor_left = 0.5
anchor_top = 0.5
anchor_right = 0.5
anchor_bottom = 0.5
mouse_filter = 2

[node name="Effect" type="Sprite2D" parent="Center"]
texture = ExtResource("Picture")
material = ExtResource("Material")
scale = Vector2(0.74, 0.74)
'''
        else:
            if kind == "post":
                assets.append("res://assets/cottage.png")
                resources.append('[ext_resource type="Texture2D" path="res://assets/cottage.png" id="Picture"]')
                nodes += '\n[node name="Background" type="TextureRect" parent="."]\n' + FULL_RECT + 'texture = ExtResource("Picture")\nexpand_mode = 1\nstretch_mode = 6\n'
            nodes += '\n[node name="Effect" type="ColorRect" parent="."]\n' + FULL_RECT + 'material = ExtResource("Material")\n'
            if gaussian:
                resources.append(f'[ext_resource type="Material" path="{directory}/material_vertical.tres" id="Vertical"]')
                nodes += '''
[node name="BetweenPasses" type="BackBufferCopy" parent="."]
copy_mode = 2

[node name="EffectVertical" type="ColorRect" parent="."]
''' + FULL_RECT + 'material = ExtResource("Vertical")\n'
    steps = len(resources) + len(subresources) + 1
    scene = f'[gd_scene load_steps={steps} format=3]\n\n' + "\n".join(resources) + "\n\n" + "\n".join(subresources) + "\n" + nodes + player
    return scene, assets


def generate_usage(output_root, entry):
    folder = output_root / entry["directory"].removeprefix("res://")
    scene, assets = usage_scene(entry)
    (folder / "material.tres").write_text(material_text(entry), encoding="utf-8", newline="\n")
    (folder / "usage.tscn").write_text(scene, encoding="utf-8")
    files = [entry["shader"], entry["directory"] + "/material.tres", entry["directory"] + "/usage.tscn"] + assets
    if entry["slug"] == "gaussian":
        (folder / "material_vertical.tres").write_text(material_text(entry, True), encoding="utf-8", newline="\n")
        files.append(entry["directory"] + "/material_vertical.tres")
    if entry["animated"]:
        files += ["res://shared/effect_player.gd", "res://shared/usage_player.gd", "res://shared/surface_hit.gd"]
    for p in entry["parameters"]:
        if p["type"] == "texture": files += [option["value"] for option in p["options"]]
    manifest = dict(version=1, scene=entry["directory"]+"/usage.tscn", files=sorted(set(files)),
                    verified_platform="Windows / Godot 4.7.2 / Forward+ / RTX 5060",
                    unverified_platforms=["其他显卡与系统", "Mobile", "Compatibility", "Web"])
    (folder / "dependencies.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    target = "$Center/Effect.material" if entry["kind"] == "sprite" else "$Effect.material_override" if entry["kind"] == "spatial" else "$Effect.material"
    first = entry["parameters"][0]
    value = first["default"]
    if first["type"] == "color": value = 'Color("'+value+'")'
    node = "Sprite2D 的 Material" if entry["kind"] == "sprite" else "MeshInstance3D 的 Material Override" if entry["kind"] == "spatial" else "Control / ColorRect 的 Material"
    code = (f'$Player.set_parameter("{first["key"]}", {value})' if entry["animated"] else f'{target}.set_shader_parameter("{first["key"]}", {value})')
    if entry["slug"] == "gaussian":
        code = '''for node in [$Effect, $EffectVertical]:
    node.material.set_shader_parameter("u_radius_px", 4.0)'''
    dynamic = '''
动态效果必须复制 `shared/effect_player.gd`、`shared/usage_player.gd` 和 `shared/surface_hit.gd`；`Player` 节点驱动同一套连续时间。只拖入材质时得到的是时间 0 的静态状态。代码挂在 usage 根节点时：

```gdscript
$Player.player.playback_speed = 0.25 # 改速度不改变当前时刻
$Player.player.paused = true        # 暂停事件和动画
$Player.player.paused = false
$Player.reset()                     # 恢复材质默认值、时间和事件
```
''' if entry["animated"] else "\n这是静态效果，无须播放器。重新加载材质或恢复参数表中的默认值即可重置。\n"
    if entry["slug"] == "flash": dynamic += '\n运行后点击图案触发一次；也可调用 `$Player.play_once()`。拖动不触发，超时恢复原图，新事件替换旧事件。\n'
    if entry["slug"] in ["interactive", "shield_hit"]:
        dynamic += '\n运行后点击表面触发，左键拖动旋转，滚轮缩放；移动超过 4 个界面像素不触发点击。游戏也可调用 `$Player.trigger_at(viewport_pixel)`。命中只支持本例平面波面或球体；其他模型需提供相应求交。将示例放入子视口时，输入必须使用该视口的像素坐标。\n'
    if entry["slug"] == "gaussian": dynamic += '\n必须保留 `Effect → BetweenPasses (BackBufferCopy) → EffectVertical` 的顺序。同时修改两个材质的半径、质量和开关；纵向材质的 `u_vertical` 保持 true。单独拖入一个材质只完成一个方向。\n'
    if entry["slug"] == "lut": dynamic += '\n包中同时附带暖色与中性 LUT。切换示例：`$Effect.material.set_shader_parameter("lut_texture", load("res://assets/neutral_lut.png"))`。将颜色表作为原始数据读取，不能替换成普通风格图片。\n'
    return f'''
## 复制接入游戏（M4）

- 最小入口：打开本目录 `usage.tscn`，按 F6；没有图库 UI、catalog 或 stage.gd 依赖。原 `demo.tscn` 继续作为图鉴入口。
- 复制什么：按本目录 `dependencies.json` 的 `files` 列表逐项复制到目标工程，`res://` 后的相对路径保持不变；清单与本 README 可另外一起带走。让 Godot 重新导入素材，不复制 `.godot/` 缓存。
- 拖到哪里：把 `usage.tscn` 实例拖入目标场景，或将 `material.tres` 拖到自己的{node}。材质启用 `resource_local_to_scene`，两个 usage 场景实例各有自己的参数；手动给多个物体赋同一个外部材质时，要先“设为唯一”或 `duplicate()`，再分别驱动。
- 代码改值：下例脚本挂在 usage 根节点，范围与默认值见上方参数表。

```gdscript
{code}
```
{dynamic}
已验证平台：Windows、Godot 4.7.2 标准版、Forward+、RTX 5060。其他系统/显卡及 Mobile、Compatibility、Web 未验证，不宣称支持。屏幕/深度效果要在包含背景和相机的目标视口中使用，不能脱离渲染顺序随意搬动。
'''
