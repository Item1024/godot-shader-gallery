extends SceneTree

const Stage = preload("res://shared/stage.gd")
var output := ""


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--output="): output = argument.trim_prefix("--output=")
	if output.is_empty() or FileAccess.file_exists(output) or DisplayServer.get_name() == "headless":
		push_error("Choose a new output file and a real GPU window")
		quit(2)
		return
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = 0
	root.size = Vector2i(1440, 900)
	var catalog: Array = JSON.parse_string(FileAccess.get_file_as_string("res://catalog.json"))
	var cases: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://tests/visual_cases.json"))
	var stage := Stage.new()
	stage.size = Vector2i(900, 660)
	root.add_child(stage)
	var picture := TextureRect.new()
	picture.size = Vector2(900, 660)
	picture.texture = stage.get_texture()
	root.add_child(picture)
	RenderingServer.viewport_set_measure_render_time(stage.get_viewport_rid(), true)
	RenderingServer.viewport_set_measure_render_time(root.get_viewport_rid(), true)
	var rows: Array = []
	var report := {"complete": false, "engine": Engine.get_version_info()["string"],
		"gpu": RenderingServer.get_video_adapter_name(), "driver": OS.get_video_adapter_driver_info(),
		"method": RenderingServer.get_current_rendering_method(), "window_size": DisplayServer.window_get_size(),
		"preview_size": stage.size, "vsync": DisplayServer.window_get_vsync_mode(), "max_fps": Engine.max_fps,
		"warmup_frames": 120, "sample_frames": 600, "preview_memory_bytes": null,
		"memory_note": "Only global video memory is exposed; not attributed to this preview.",
		"source_sha256": {"stage": FileAccess.get_sha256("res://shared/stage.gd"),
			"benchmark": FileAccess.get_sha256("res://tools/benchmark_m6.gd")}, "effects": rows}
	DirAccess.make_dir_recursive_absolute(output.get_base_dir())
	for effect: Dictionary in cases["effects"]:
		stage.configure(catalog[int(effect["number"]) - 1])
		for frame in range(120):
			await process_frame
			await RenderingServer.frame_post_draw
		var samples: Array = []
		var previous := Time.get_ticks_usec()
		for frame in range(600):
			await process_frame
			var drawing := stage.render_target_update_mode != SubViewport.UPDATE_DISABLED
			await RenderingServer.frame_post_draw
			var now := Time.get_ticks_usec()
			var preview_cpu := RenderingServer.viewport_get_measured_render_time_cpu(stage.get_viewport_rid()) if drawing else 0.0
			var preview_gpu := RenderingServer.viewport_get_measured_render_time_gpu(stage.get_viewport_rid()) if drawing else 0.0
			samples.append({"frame_interval_ms": (now - previous) / 1000.0,
				"process_cpu_ms": Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0,
				"render_cpu_ms": preview_cpu + RenderingServer.viewport_get_measured_render_time_cpu(root.get_viewport_rid()) + RenderingServer.get_frame_setup_time_cpu(),
				"render_gpu_ms": preview_gpu + RenderingServer.viewport_get_measured_render_time_gpu(root.get_viewport_rid()),
				"preview_drawing": drawing,
				"global_video_memory_bytes": Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED)})
			previous = now
		# The effect and its resources are warm; include the first actual draw.
		var start := Time.get_ticks_usec()
		stage.configure(catalog[int(effect["number"]) - 1])
		await process_frame
		await RenderingServer.frame_post_draw
		rows.append({"number": effect["number"], "animated": effect["animated"],
			"window_size": DisplayServer.window_get_size(), "preview_size": stage.size,
			"warm_switch_ms": (Time.get_ticks_usec() - start) / 1000.0, "samples": samples})
		var file := FileAccess.open(output, FileAccess.WRITE)
		file.store_string(JSON.stringify(report) + "\n")
		print("M6_BENCH %03d samples=600" % effect["number"])
	report["complete"] = true
	var file := FileAccess.open(output, FileAccess.WRITE)
	file.store_string(JSON.stringify(report) + "\n")
	stage.free()
	quit()
