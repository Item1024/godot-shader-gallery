extends SceneTree


func _initialize() -> void:
	call_deferred("_capture")


func _capture() -> void:
	var specification: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://tests/m1_cases.json"))
	var catalog: Array = JSON.parse_string(FileAccess.get_file_as_string("res://catalog.json"))
	for relative: String in specification["source_sha256_lf"]:
		var actual := FileAccess.get_file_as_string("res://" + relative).replace("\r\n", "\n").sha256_text()
		if actual != specification["source_sha256_lf"][relative]:
			push_error("M1 source has changed; do not relabel current output as the old baseline: " + relative)
			quit(2)
			return
	if FileAccess.get_sha256("res://assets/cottage.png") != specification["cottage_sha256"]:
		push_error("M1 input image has changed")
		quit(2)
		return
	var output := "res://artifacts/m1-capture"
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--output="):
			output = argument.trim_prefix("--output=")
	if FileAccess.file_exists(output.path_join("capture.json")):
		push_error("Capture already exists. Choose a new --output directory; recorded samples are not replaced.")
		quit(2)
		return
	if DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(output)) != OK:
		push_error("Cannot create capture output directory")
		quit(1)
		return
	var stage = load("res://shared/stage.gd").new()
	stage.size = Vector2i(specification["viewport_size"][0], specification["viewport_size"][1])
	root.add_child(stage)
	var captures: Array = []
	for number in specification["effect_numbers"]:
		var entry: Dictionary = {}
		for candidate: Dictionary in catalog:
			if int(candidate["number"]) == int(number):
				entry = candidate
				break
		if entry.is_empty():
			push_error("Missing effect: " + str(number))
			quit(1)
			return
		stage.configure(entry)
		stage.paused = true
		stage.elapsed = float(specification["time_seconds"])
		stage._set_uniforms()
		for enabled in [false, true]:
			stage.set_parameter("u_enabled", enabled)
			await process_frame
			await RenderingServer.frame_post_draw
			await RenderingServer.frame_post_draw
			var captured: Image = stage.get_texture().get_image()
			var filename := "%03d_%s_%s.png" % [number, entry["slug"], "on" if enabled else "off"]
			if captured == null or captured.is_empty() or captured.save_png(output.path_join(filename)) != OK:
				push_error("Capture failed: " + filename)
				quit(1)
				return
			captures.append({"number": number, "name": entry["name"], "effect": entry["category_slug"] + "/" + entry["slug"], "enabled": enabled, "time_seconds": stage.elapsed, "amount": stage.amount, "filename": filename, "sha256": FileAccess.get_sha256(output.path_join(filename)), "shader_sha256": FileAccess.get_file_as_string(entry["shader"]).replace("\r\n", "\n").sha256_text()})
		print("M1_CAPTURE %03d %s" % [number, entry["name"]])
	var report := {
		"purpose": specification["purpose"],
		"approved_visual_reference": false,
		"effect_source_revision": specification["effect_source_revision"],
		"source_sha256_lf": specification["source_sha256_lf"],
		"text_hash_algorithm": "sha256-lf-text",
		"engine": Engine.get_version_info()["string"],
		"gpu": RenderingServer.get_video_adapter_name(),
		"rendering_method": RenderingServer.get_current_rendering_method(),
		"viewport_size": specification["viewport_size"],
		"stage_sha256": FileAccess.get_file_as_string("res://shared/stage.gd").replace("\r\n", "\n").sha256_text(),
		"cottage_sha256": FileAccess.get_sha256("res://assets/cottage.png"),
		"captures": captures,
	}
	var file := FileAccess.open(output.path_join("capture.json"), FileAccess.WRITE)
	if file == null:
		push_error("Cannot write capture report")
		quit(1)
		return
	file.store_string(JSON.stringify(report, "\t") + "\n")
	file.close()
	stage.free()
	print("M1_CAPTURE_COMPLETE " + str(captures.size()))
	quit()
