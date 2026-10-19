extends Control

const Stage = preload("res://shared/stage.gd")
const BG := Color("#0c1423")
const PANEL := Color("#151f30")
const TEXT := Color("#eef3fa")
const MUTED := Color("#a8b7ca")
const ACCENT := Color("#55e8bb")
var catalog: Array = []
var categories: Array = []
var current: Dictionary = {}
var results: Array[int] = []
var stage
var items: ItemList
var search: LineEdit
var category: OptionButton
var count_label: Label
var heading: Label
var subtitle: Label
var badge: Label
var path_label: Label
var notes: RichTextLabel
var code: CodeEdit
var sliders: Array[HSlider] = []
var pause_button: Button
var compare_button: CheckButton
var color_button: ColorPickerButton
var screenshot_pending := false


func _style(color: Color, border: Color = Color.TRANSPARENT) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = color
	style.set_corner_radius_all(8)
	style.set_border_width_all(1)
	style.border_color = border
	style.content_margin_left = 12
	style.content_margin_right = 12
	style.content_margin_top = 9
	style.content_margin_bottom = 9
	return style


func _label(text_value: String, font_size: int = 16, color: Color = TEXT) -> Label:
	var label := Label.new()
	label.text = text_value
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	return label


func _button(title: String, callback: Callable) -> Button:
	var button := Button.new()
	button.text = title
	button.custom_minimum_size.y = 42
	button.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	button.pressed.connect(callback)
	return button


func _panel() -> PanelContainer:
	var panel := PanelContainer.new()
	panel.add_theme_stylebox_override("panel", _style(PANEL, Color("#26364d")))
	return panel


func _ready() -> void:
	catalog = JSON.parse_string(FileAccess.get_file_as_string("res://catalog.json"))
	categories = JSON.parse_string(FileAccess.get_file_as_string("res://categories.json"))
	_build_theme()
	_build_ui()
	_filter()
	if "--audit" in OS.get_cmdline_user_args():
		call_deferred("_audit")


func _build_theme() -> void:
	var visual_theme := Theme.new()
	var font := SystemFont.new()
	font.font_names = PackedStringArray(["Microsoft YaHei UI", "Microsoft YaHei", "Noto Sans CJK SC", "Segoe UI"])
	visual_theme.default_font = font
	visual_theme.default_font_size = 15
	for control in ["Label", "Button", "OptionButton", "CheckButton", "LineEdit", "ItemList", "RichTextLabel"]:
		visual_theme.set_color("font_color", control, TEXT)
	visual_theme.set_color("font_placeholder_color", "LineEdit", MUTED)
	visual_theme.set_color("font_color", "CodeEdit", TEXT)
	visual_theme.set_color("font_selected_color", "ItemList", Color("#06251c"))
	visual_theme.set_stylebox("selected", "ItemList", _style(ACCENT))
	visual_theme.set_stylebox("panel", "ItemList", _style(Color("#101a2a")))
	for control in ["Button", "OptionButton", "LineEdit"]:
		visual_theme.set_stylebox("normal", control, _style(Color("#1b2a40"), Color("#34465e")))
		visual_theme.set_stylebox("hover", control, _style(Color("#283d55"), ACCENT))
		visual_theme.set_stylebox("pressed", control, _style(Color("#305044"), ACCENT))
		visual_theme.set_stylebox("focus", control, _style(Color(0, 0, 0, 0), ACCENT))
	visual_theme.set_stylebox("normal", "CodeEdit", _style(Color("#0b1321")))
	visual_theme.set_color("font_color", "TabBar", MUTED)
	visual_theme.set_color("font_selected_color", "TabBar", TEXT)
	visual_theme.set_stylebox("tab_selected", "TabBar", _style(PANEL, Color("#34465e")))
	visual_theme.set_stylebox("tab_unselected", "TabBar", _style(BG))
	visual_theme.set_stylebox("panel", "TabContainer", _style(PANEL))
	theme = visual_theme


func _build_ui() -> void:
	var background := ColorRect.new()
	background.color = BG
	background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(background)
	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for edge in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + edge, 20)
	add_child(margin)
	var root := VBoxContainer.new()
	root.add_theme_constant_override("separation", 16)
	margin.add_child(root)
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 16)
	root.add_child(header)
	var logo := TextureRect.new()
	logo.texture = load("res://assets/icon.svg")
	logo.custom_minimum_size = Vector2(42, 42)
	logo.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	header.add_child(logo)
	var brand := VBoxContainer.new()
	brand.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(brand)
	brand.add_child(_label("SHADER ATLAS", 23))
	brand.add_child(_label("Godot 效果图鉴  /  逐项查看 · 实时调参 · 独立源码", 13, MUTED))
	header.add_child(_label("%d 个示例   /   23 类   /   Godot 4.7" % catalog.size(), 14, ACCENT))
	var body := HBoxContainer.new()
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.add_theme_constant_override("separation", 16)
	root.add_child(body)
	var sidebar := VBoxContainer.new()
	sidebar.custom_minimum_size.x = 258
	sidebar.add_theme_constant_override("separation", 12)
	body.add_child(sidebar)
	sidebar.add_child(_label("效果目录", 16))
	search = LineEdit.new()
	search.placeholder_text = "搜索名称 / 英文关键词"
	search.clear_button_enabled = true
	search.custom_minimum_size.y = 44
	search.text_changed.connect(func(_value): _filter())
	sidebar.add_child(search)
	category = OptionButton.new()
	category.custom_minimum_size.y = 44
	category.add_item("全部分类")
	for group: Dictionary in categories:
		category.add_item("%02d  %s" % [group["number"], group["name"]])
	category.item_selected.connect(func(_index): _filter())
	sidebar.add_child(category)
	items = ItemList.new()
	items.size_flags_vertical = Control.SIZE_EXPAND_FILL
	items.add_theme_constant_override("v_separation", 10)
	items.add_theme_constant_override("h_separation", 8)
	items.item_selected.connect(func(index): _show(catalog[results[index]]))
	sidebar.add_child(items)
	count_label = _label("", 13, MUTED)
	sidebar.add_child(count_label)
	var main := VBoxContainer.new()
	main.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	main.add_theme_constant_override("separation", 8)
	body.add_child(main)
	badge = _label("", 13, ACCENT)
	main.add_child(badge)
	heading = _label("", 29)
	heading.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	main.add_child(heading)
	subtitle = _label("", 14, MUTED)
	subtitle.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	subtitle.custom_minimum_size.y = 46
	main.add_child(subtitle)
	var tabs := TabContainer.new()
	tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	main.add_child(tabs)
	var preview := VBoxContainer.new()
	preview.name = "实时演示"
	tabs.add_child(preview)
	var viewport_container := SubViewportContainer.new()
	viewport_container.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	viewport_container.size_flags_vertical = Control.SIZE_EXPAND_FILL
	viewport_container.stretch = true
	preview.add_child(viewport_container)
	stage = Stage.new()
	viewport_container.add_child(stage)
	viewport_container.gui_input.connect(stage.orbit_input)
	var footer := HBoxContainer.new()
	footer.add_theme_constant_override("separation", 12)
	preview.add_child(footer)
	footer.add_child(_button("← 上一项", func(): _navigate(-1)))
	footer.add_child(_button("下一项 →", func(): _navigate(1)))
	var tip := _label("点击触发交互 · 拖动旋转 · 滚轮缩放", 12, MUTED)
	tip.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	tip.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	footer.add_child(tip)
	code = CodeEdit.new()
	code.name = "Shader 源码"
	code.editable = false
	code.gutters_draw_line_numbers = true
	code.add_theme_font_size_override("font_size", 14)
	tabs.add_child(code)
	notes = RichTextLabel.new()
	notes.name = "原理与限制"
	notes.add_theme_font_size_override("normal_font_size", 16)
	notes.selection_enabled = true
	tabs.add_child(notes)
	var inspector_panel := _panel()
	inspector_panel.custom_minimum_size.x = 248
	body.add_child(inspector_panel)
	var inspector := VBoxContainer.new()
	inspector.add_theme_constant_override("separation", 16)
	inspector_panel.add_child(inspector)
	inspector.add_child(_label("实时参数", 18))
	_add_slider(inspector, "强度 / 进度", "u_amount", 0.0, 1.0, 0.55)
	_add_slider(inspector, "动画速度", "u_speed", 0.0, 3.0, 1.0)
	_add_slider(inspector, "纹理 / 图案尺度", "u_scale", 0.4, 3.0, 1.0)
	inspector.add_child(_label("强调色", 14, MUTED))
	color_button = ColorPickerButton.new()
	color_button.color = ACCENT
	color_button.custom_minimum_size.y = 38
	color_button.edit_alpha = false
	color_button.color_changed.connect(func(value): stage.set_parameter("u_color", value))
	inspector.add_child(color_button)
	pause_button = _button("暂停动画", _toggle_pause)
	inspector.add_child(pause_button)
	compare_button = CheckButton.new()
	compare_button.text = "启用效果"
	compare_button.button_pressed = true
	compare_button.toggled.connect(func(value): stage.set_parameter("u_enabled", value))
	inspector.add_child(compare_button)
	inspector.add_child(_button("重置参数", _reset))
	var spacer := Control.new()
	spacer.size_flags_vertical = Control.SIZE_EXPAND_FILL
	inspector.add_child(spacer)
	path_label = _label("", 12, MUTED)
	path_label.autowrap_mode = TextServer.AUTOWRAP_ARBITRARY
	inspector.add_child(path_label)
	inspector.add_child(_button("打开效果目录", _open_folder))
	var helper := _label("每个目录可单独运行 demo.tscn\n近似与管线依赖见「原理与限制」", 12, MUTED)
	helper.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	inspector.add_child(helper)


func _add_slider(parent: VBoxContainer, title: String, key: String, low: float, high: float, initial: float) -> void:
	var row := HBoxContainer.new()
	parent.add_child(row)
	var label := _label(title, 14, MUTED)
	label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(label)
	var value_label := _label("%.2f" % initial, 13, ACCENT)
	row.add_child(value_label)
	var slider := HSlider.new()
	slider.min_value = low
	slider.max_value = high
	slider.step = 0.01
	slider.value = initial
	slider.custom_minimum_size.y = 26
	slider.value_changed.connect(func(value):
		value_label.text = "%.2f" % value
		if stage: stage.set_parameter(key, value)
	)
	parent.add_child(slider)
	sliders.append(slider)


func _filter() -> void:
	items.clear()
	results.clear()
	var query := search.text.strip_edges().to_lower()
	var selected_category := category.selected
	for index in range(catalog.size()):
		var entry: Dictionary = catalog[index]
		if selected_category > 0 and int(entry["category_number"]) != selected_category:
			continue
		var searchable: String = (str(entry["name"]) + " " + str(entry["slug"]) + " " + str(entry["category"]) + " " + str(entry["keywords"])).to_lower()
		if not query.is_empty() and query not in searchable:
			continue
		results.append(index)
		items.add_item("%03d  %s" % [entry["number"], entry["name"]])
	count_label.text = "%d / %d 个效果" % [results.size(), catalog.size()]
	if not results.is_empty():
		items.select(0)
		_show(catalog[results[0]])


func _show(entry: Dictionary) -> void:
	current = entry
	heading.text = entry["name"]
	badge.text = "%03d  /  %s  /  %s" % [entry["number"], entry["category"], entry["implementation"]]
	subtitle.text = entry["summary"]
	path_label.text = str(entry["directory"]).trim_prefix("res://")
	code.text = FileAccess.get_file_as_string(entry["shader"])
	notes.text = FileAccess.get_file_as_string(entry["readme"])
	stage.configure(entry)
	_reset()


func _reset() -> void:
	sliders[0].value = float(current.get("amount", 0.55))
	sliders[1].value = 1.0
	sliders[2].value = 1.0
	stage.reset()
	color_button.color = ACCENT
	pause_button.text = "暂停动画"
	compare_button.button_pressed = true


func _toggle_pause() -> void:
	stage.paused = not stage.paused
	pause_button.text = "继续动画" if stage.paused else "暂停动画"


func _navigate(direction: int) -> void:
	if results.is_empty():
		return
	var selected := items.get_selected_items()
	var index := 0 if selected.is_empty() else int(selected[0])
	index = posmod(index + direction, results.size())
	items.select(index)
	items.ensure_current_is_visible()
	_show(catalog[results[index]])


func _open_folder() -> void:
	OS.shell_open(ProjectSettings.globalize_path(current["directory"]))


func _unhandled_key_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_SPACE and not search.has_focus():
			_toggle_pause()
		elif event.keycode == KEY_F and event.ctrl_pressed:
			search.grab_focus()
		elif event.keycode == KEY_RIGHT and not search.has_focus():
			_navigate(1)
		elif event.keycode == KEY_LEFT and not search.has_focus():
			_navigate(-1)


func _audit() -> void:
	var output := ProjectSettings.globalize_path("res://artifacts")
	DirAccess.make_dir_recursive_absolute(output)
	var report: Array = []
	var selected_categories: Array[int] = []
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--audit-categories="):
			for number in argument.trim_prefix("--audit-categories=").split(","):
				selected_categories.append(int(number))
	for index in range(catalog.size()):
		var entry: Dictionary = catalog[index]
		if not selected_categories.is_empty() and int(entry["category_number"]) not in selected_categories:
			continue
		_show(entry)
		await get_tree().process_frame
		await RenderingServer.frame_post_draw
		await RenderingServer.frame_post_draw
		var uniforms: Array = stage.shader_material.shader.get_shader_uniform_list()
		var image: Image = stage.get_texture().get_image()
		var valid: bool = uniforms.size() > 0 and image != null and not image.is_empty()
		report.append({"number": entry["number"], "name": entry["name"], "valid": valid, "kind": entry["kind"], "implementation": entry["implementation"]})
		if index == 0 or (index > 0 and catalog[index - 1]["category_number"] != entry["category_number"]):
			image.save_png(output.path_join("category_%02d.png" % entry["category_number"]))
		print("AUDIT %03d/%03d %s %s" % [index + 1, catalog.size(), "PASS" if valid else "FAIL", entry["name"]])
	var report_name := "runtime_audit.json" if selected_categories.is_empty() else "runtime_followup.json"
	var file := FileAccess.open(output.path_join(report_name), FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t"))
	file.close()
	_show(catalog[0])
	await get_tree().process_frame
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(output.path_join("gallery.png"))
	print("AUDIT_COMPLETE " + str(report.size()))
	if "--quit-after-audit" in OS.get_cmdline_user_args():
		get_tree().quit()
