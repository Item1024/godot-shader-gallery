extends SceneTree

const Stage = preload("res://shared/stage.gd")
const MANIFEST := "res://tests/visual_cases.json"
var output := ""
var defaults_only := false
var only := 0
var report: Dictionary = {}


func _initialize() -> void:
	call_deferred("_run")


func fail(message: String) -> void:
	push_error("M5: " + message)
	quit(2)


func write_report() -> void:
	var file := FileAccess.open(output.path_join("capture.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t") + "\n")
	file.close()


func snapshot(stage: Stage, id: String, category: String) -> bool:
	# Rendering remains enabled during these waits; this also settles screen copies.
	for frame in range(4):
		await process_frame
		await RenderingServer.frame_post_draw
	var image := stage.get_texture().get_image()
	if image == null or image.is_empty():
		fail("Empty GPU image: " + id)
		return false
	var filename := id + ".png"
	if image.save_png(output.path_join(filename)) != OK:
		fail("Cannot save " + filename)
		return false
	report["captures"].append({"id": id, "category": category, "filename": filename,
		"sha256": FileAccess.get_sha256(output.path_join(filename)),
		"time_seconds": stage.elapsed, "event_time": stage.player.event_time})
	return true


func fixture(stage: Stage, name: String) -> void:
	if name == "transparent_subject":
		stage.transparent_bg = true
		stage.canvas_root.get_child(0).hide()
	elif name in ["blur_chart", "color_chart"]:
		var image := Image.create(stage.size.x, stage.size.y, false, Image.FORMAT_RGB8)
		for y in range(stage.size.y):
			for x in range(stage.size.x):
				var value := Color(x / float(stage.size.x - 1), y / float(stage.size.y - 1), 1.0 if y >= stage.size.y / 2 else x / float(stage.size.x - 1))
				if name == "blur_chart":
					value = Color(0.3, 0.6, 0.8) if x < 160 else (Color.WHITE if (x / 16 + y / 16) % 2 == 0 else Color.BLACK)
				image.set_pixel(x, y, value)
		var picture := stage.canvas_root.get_child(1) as TextureRect
		picture.texture = ImageTexture.create_from_image(image)


func apply_state(stage: Stage, specification: Dictionary, state: Dictionary) -> bool:
	stage.reset()
	stage.paused = true
	stage.elapsed = 0.0
	for key: String in state.get("parameters", {}):
		if not stage.set_parameter(key, state["parameters"][key]):
			fail("Invalid parameter: " + key)
			return false
	if not stage.set_parameter("u_enabled", state.get("enabled", true)):
		fail("Cannot set enabled")
		return false
	if state.get("event", false):
		var pixel := Vector2(stage.size) * 0.5
		if specification.has("hit_local"):
			var point: Array = specification["hit_local"]
			pixel = stage.camera.unproject_position(stage.interaction_surface.to_global(Vector3(point[0], point[1], point[2])))
		if not stage.trigger_at(pixel):
			fail("Fixed event did not hit the surface")
			return false
	stage.elapsed = float(state["time"])
	return true


func probes(stage: Stage, specification: Dictionary) -> bool:
	var number := int(specification["number"])
	var base := "%03d_" % number
	if number == 348:
		stage.reset()
		stage.paused = true
		for p: Dictionary in stage.entry["parameters"]:
			stage.set_parameter(p["key"], 0.0)
		if not await snapshot(stage, base + "all_zero", "probe"): return false
	if number == 112:
		stage.reset()
		stage.paused = true
		stage.set_parameter("u_wave_height", 0.0)
		stage.elapsed = 2.0
		if not await snapshot(stage, base + "flat_late", "probe"): return false
	if number in [118, 190]:
		stage.reset()
		stage.paused = true
		stage.elapsed = 2.0
		if not await snapshot(stage, base + "no_event_late", "probe"): return false
	if number == 96:
		stage.reset()
		stage.paused = true
		stage.set_parameter("u_distortion", 0.0)
		stage.set_parameter("u_color", "#ffffff")
		stage.set_parameter("u_opacity", 1.0)
		if not await snapshot(stage, base + "straight", "probe"): return false
		stage.interaction_surface.hide()
		if not await snapshot(stage, base + "background", "probe"): return false
	return true


func _run() -> void:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--output="): output = argument.trim_prefix("--output=")
		elif argument == "--defaults-only": defaults_only = true
		elif argument.begins_with("--only="): only = int(argument.trim_prefix("--only="))
		else:
			fail("Unknown argument: " + argument)
			return
	if output.is_empty() or DirAccess.dir_exists_absolute(output):
		fail("Choose a new --output directory; captures are never overwritten")
		return
	if DisplayServer.get_name() == "headless":
		fail("Real GPU rendering is required; do not use --headless")
		return
	if DirAccess.make_dir_recursive_absolute(output) != OK:
		fail("Cannot create output directory")
		return
	var specification: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(MANIFEST))
	var catalog: Array = JSON.parse_string(FileAccess.get_file_as_string("res://catalog.json"))
	seed(int(specification["seed"]))
	report = {"complete": false, "defaults_only": defaults_only, "only": only,
		"approved_visual_reference": false, "manifest_sha256_lf": FileAccess.get_file_as_string(MANIFEST).replace("\r\n", "\n").sha256_text(),
		"environment": {"engine": Engine.get_version_info()["string"], "gpu": RenderingServer.get_video_adapter_name(),
			"driver": OS.get_video_adapter_driver_info(), "os": OS.get_name(),
			"method": RenderingServer.get_current_rendering_method(), "viewport_size": specification["viewport_size"],
			"seed": specification["seed"], "msaa_3d": 0, "taa": false, "screen_space_aa": 0},
		"source_sha256": {}, "captures": []}
	var sources: Array = ["res://shared/stage.gd", "res://shared/effect_player.gd", "res://shared/surface_hit.gd", "res://catalog.json",
		"res://tools/capture_visuals.gd", "res://assets/subject.svg", "res://assets/cottage.png", "res://assets/warm_lut.png", "res://assets/neutral_lut.png"]
	for effect: Dictionary in specification["effects"]:
		sources.append(catalog[int(effect["number"]) - 1]["shader"])
	for path: String in sources:
		report["source_sha256"][path] = FileAccess.get_sha256(path)
	write_report()
	var count := 0
	for effect: Dictionary in specification["effects"]:
		var number := int(effect["number"])
		if only != 0 and number != only: continue
		var stage := Stage.new()
		stage.size = Vector2i(specification["viewport_size"][0], specification["viewport_size"][1])
		root.add_child(stage)
		stage.set_process(false)
		stage.configure(catalog[number - 1])
		stage.msaa_3d = Viewport.MSAA_DISABLED
		stage.screen_space_aa = Viewport.SCREEN_SPACE_AA_DISABLED
		stage.use_taa = false
		stage.orbit = 0.0
		stage.elevation = 0.28
		stage.distance = 5.0
		stage._position_camera()
		if stage.environment != null: stage.environment.tonemap_exposure = 1.0
		fixture(stage, effect["fixture"])
		for state: Dictionary in effect["states"]:
			if defaults_only and state["id"] != "default": continue
			if not apply_state(stage, effect, state):
				stage.free()
				return
			if not await snapshot(stage, "%03d_%s" % [number, state["id"]], "state"):
				stage.free()
				return
		if not defaults_only and not await probes(stage, effect):
			stage.free()
			return
		stage.free()
		await process_frame
		count += 1
		write_report()
		print("M5_CAPTURE %03d %s" % [number, effect["name"]])
	if count == 0:
		fail("No matching effect")
		return
	report["complete"] = true
	write_report()
	print("M5_CAPTURE_COMPLETE effects=%d images=%d defaults_only=%s" % [count, report["captures"].size(), defaults_only])
	quit()
