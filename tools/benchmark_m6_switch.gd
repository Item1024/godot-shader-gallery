extends SceneTree


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var output := ""
	var stage_script := "res://shared/stage.gd"
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--output="): output = argument.trim_prefix("--output=")
		elif argument.begins_with("--stage-script="): stage_script = argument.trim_prefix("--stage-script=")
	if output.is_empty() or FileAccess.file_exists(output) or DisplayServer.get_name() == "headless":
		quit(2)
		return
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = 0
	root.size = Vector2i(1440,900)
	var catalog: Array = JSON.parse_string(FileAccess.get_file_as_string("res://catalog.json"))
	var cases: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://tests/visual_cases.json"))
	var stage = load(stage_script).new()
	stage.size = Vector2i(900,660)
	root.add_child(stage)
	var picture := TextureRect.new()
	picture.size = Vector2(900,660)
	picture.texture = stage.get_texture()
	root.add_child(picture)
	# Warm every target before measuring transitions between different effects.
	for effect: Dictionary in cases["effects"]:
		stage.configure(catalog[int(effect["number"]) - 1])
		for frame in range(120):
			await process_frame
			await RenderingServer.frame_post_draw
	var rows: Array = []
	for effect: Dictionary in cases["effects"]:
		var previous: int = stage.entry["number"]
		var start := Time.get_ticks_usec()
		stage.configure(catalog[int(effect["number"]) - 1])
		await process_frame
		await RenderingServer.frame_post_draw
		rows.append({"from": previous, "to": effect["number"], "ms": (Time.get_ticks_usec() - start) / 1000.0})
	var report := {"complete": true, "engine": Engine.get_version_info()["string"],
		"gpu": RenderingServer.get_video_adapter_name(), "driver": OS.get_video_adapter_driver_info(),
		"method": RenderingServer.get_current_rendering_method(), "vsync": DisplayServer.window_get_vsync_mode(), "max_fps": Engine.max_fps,
		"window_size": DisplayServer.window_get_size(), "preview_size": stage.size,
		"warmup_frames_per_effect": 120, "stage_sha256": FileAccess.get_sha256(stage_script),
		"benchmark_sha256": FileAccess.get_sha256("res://tools/benchmark_m6_switch.gd"), "switches": rows}
	DirAccess.make_dir_recursive_absolute(output.get_base_dir())
	FileAccess.open(output,FileAccess.WRITE).store_string(JSON.stringify(report) + "\n")
	print("M6_SWITCHES complete transitions=%d" % rows.size())
	stage.free()
	quit()
