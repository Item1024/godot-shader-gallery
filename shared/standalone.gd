extends Control

@export_file("*.json") var metadata_path: String


func _ready() -> void:
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(metadata_path))
	var container := SubViewportContainer.new()
	container.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	container.stretch = true
	add_child(container)
	var stage = load("res://shared/stage.gd").new()
	container.add_child(stage)
	stage.configure(data)
	container.gui_input.connect(stage.orbit_input)
	var label := Label.new()
	label.text = data["name"] + "  ·  " + data["implementation"] + "\n拖动旋转 / 滚轮缩放 3D；F5 打开完整图鉴调整参数"
	label.position = Vector2(20, 18)
	label.add_theme_color_override("font_shadow_color", Color.BLACK)
	label.add_theme_constant_override("shadow_offset_x", 1)
	label.add_theme_constant_override("shadow_offset_y", 1)
	add_child(label)
