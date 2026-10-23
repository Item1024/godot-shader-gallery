extends SceneTree

const Stage = preload("res://shared/stage.gd")
var checks: Array = []


func _initialize() -> void:
	call_deferred("_run")


func check(passed: bool, name: String, details: Dictionary = {}) -> void:
	checks.append({"passed": passed, "name": name, "details": details})
	if not passed: push_error("M6 FAIL: " + name + " " + JSON.stringify(details))


func settle(_stage: Stage) -> void:
	for frame in range(4): await process_frame


func _run() -> void:
	if DisplayServer.get_name() == "headless":
		quit(2)
		return
	var catalog: Array = JSON.parse_string(FileAccess.get_file_as_string("res://catalog.json"))
	var cases: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://tests/visual_cases.json"))
	check(catalog.filter(func(e): return e.has("animated")).size() == 20, "only twenty verified effects declare animated")
	var stage := Stage.new()
	stage.size = Vector2i(640, 480)
	root.add_child(stage)
	var picture := TextureRect.new()
	picture.size = Vector2(640, 480)
	picture.texture = stage.get_texture()
	root.add_child(picture)
	for effect: Dictionary in cases["effects"]:
		stage.configure(catalog[int(effect["number"]) - 1])
		check(stage.is_processing() == bool(effect["animated"]), "metadata controls clock %03d" % effect["number"])
		stage.paused = bool(effect["animated"])
		stage.elapsed = 0.25
		if int(effect["number"]) == 37: stage.elapsed = 0.5
		if int(effect["number"]) in [118,190,270]:
			stage.player.event_time = 0.0
			stage.player._write_event()
			if int(effect["number"]) == 270: stage.elapsed = 0.075
		await settle(stage)
		if int(effect["number"]) in [96,348]:
			var reference := Image.load_from_file("res://tests/visual/reference/%03d_default.png" % effect["number"])
			check(stage.get_texture().get_image().get_data() == reference.get_data(), "single requested draw matches M5 default %03d" % effect["number"])
		var idle_modes := true
		var max_calls := 0.0
		for frame in range(120):
			await process_frame
			idle_modes = idle_modes and stage.render_target_update_mode == SubViewport.UPDATE_DISABLED
			max_calls = maxf(max_calls, Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME))
		check(idle_modes and max_calls <= 1.0, "120 idle frames draw only root texture %03d" % effect["number"], {"max_global_draw_calls": max_calls})
		var p: Dictionary = {}
		for parameter: Dictionary in stage.entry["parameters"]:
			if parameter["key"] == effect["primary"]: p = parameter
		var before := stage.get_texture().get_image().get_data()
		stage.set_parameter(p["key"], p["min"] if p["default"] != p["min"] else p["max"])
		check(stage.render_target_update_mode == SubViewport.UPDATE_ONCE, "parameter requests draw %03d" % effect["number"])
		await stage.draw_frame()
		check(before != stage.get_texture().get_image().get_data(), "parameter changes actual pixels %03d" % effect["number"])
		await settle(stage)
		stage.set_parameter("invalid_m6_parameter", 1.0)
		check(stage.render_target_update_mode == SubViewport.UPDATE_DISABLED, "invalid parameter leaves preview idle")
		stage.size = Vector2i(642, 482)
		check(stage.render_target_update_mode == SubViewport.UPDATE_ONCE, "size change requests draw")
		await stage.draw_frame()
		check(stage.get_texture().get_image().get_size() == stage.size, "resized capture completes")
		stage.size = Vector2i(640, 480)
	stage.configure(catalog[2])
	check(stage.entry.get("animated", true) and stage.is_processing(), "unverified effect conservatively stays dynamic")
	stage.free()
	picture.free()
	var gallery = load("res://gallery.tscn").instantiate()
	root.add_child(gallery)
	await process_frame
	gallery._show(catalog[111])
	gallery.stage.paused = true
	gallery.stage.elapsed = 3.25
	gallery.stage.orbit = 0.7
	gallery.stage.distance = 6.2
	gallery.stage.set_parameter("u_wave_height", 0.13)
	var material: ShaderMaterial = gallery.stage.shader_material
	var subject: Node3D = gallery.stage.subject
	gallery.search.text = "w"
	gallery.search.text_changed.emit("w")
	await create_timer(0.06).timeout
	gallery.search.text = "water"
	gallery.search.text_changed.emit("water")
	await create_timer(0.06).timeout
	check(gallery.search_timer.time_left > 0.0 and gallery.stage.shader_material == material, "rapid inputs restart 150 ms debounce")
	await create_timer(0.14).timeout
	check(gallery.search_timer.is_stopped() and not gallery.results.is_empty(), "search applies after final debounce")
	check(gallery.current["number"] == 112 and gallery.stage.shader_material == material and gallery.stage.subject == subject, "matching selection does not rebuild preview")
	check(gallery.stage.elapsed == 3.25 and gallery.stage.orbit == 0.7 and gallery.stage.distance == 6.2 and gallery.stage.parameter_values["u_wave_height"] == 0.13, "search preserves time camera parameters")
	gallery._show(catalog[111])
	check(gallery.stage.shader_material == material, "selecting same effect keeps state")
	gallery.tabs.current_tab = 1
	gallery.stage._process(10.0)
	check(gallery.stage.elapsed == 3.25 and gallery.stage.paused and not gallery.stage.preview_active, "hidden tab holds time and user pause")
	gallery.tabs.current_tab = 0
	check(gallery.stage.paused and not gallery.stage.is_processing(), "return preserves user pause")
	gallery.stage.paused = false
	gallery.tabs.current_tab = 1
	gallery.stage._process(10.0)
	check(gallery.stage.elapsed == 3.25 and not gallery.stage.paused, "hidden tab stops playing clock without changing pause flag")
	gallery.tabs.current_tab = 0
	gallery.stage.set_process(false)
	gallery.stage._process(0.25)
	check(absf(gallery.stage.elapsed - 3.5) < 0.00001, "return resumes continuously from previous time")
	gallery.stage.paused = true
	await settle(gallery.stage)
	gallery.stage.orbit_input(mouse_wheel())
	check(gallery.stage.render_target_update_mode == SubViewport.UPDATE_ONCE, "paused camera input requests draw")
	await settle(gallery.stage)
	gallery.stage.trigger_at(Vector2(-10, -10))
	check(gallery.stage.render_target_update_mode == SubViewport.UPDATE_DISABLED, "invalid click does not redraw")
	var pixel: Vector2 = gallery.stage.camera.unproject_position(gallery.stage.interaction_surface.to_global(Vector3.ZERO))
	check(gallery.stage.trigger_at(pixel) and gallery.stage.render_target_update_mode == SubViewport.UPDATE_ONCE, "valid paused input requests draw")
	gallery.search.text = "no-result-m6-test"
	gallery._filter()
	await gallery.stage.draw_frame()
	check(gallery.current.is_empty() and gallery.stage.get_child_count() == 0 and not gallery.stage.is_processing(), "zero results clear preview and clock")
	var empty: Image = gallery.stage.get_texture().get_image()
	check(empty.get_size() == gallery.stage.size and empty.get_pixelv(empty.get_size() / 3) == empty.get_pixelv(empty.get_size() / 2), "empty preview actually clears old pixels")
	gallery.search.text = "breathing"
	gallery._filter()
	check(gallery.current["number"] == 34 and gallery.stage.shader_material != material and gallery.stage.is_processing(), "different selection rebuilds and resumes")
	gallery.free()
	var failures := checks.filter(func(c): return not c["passed"]).size()
	DirAccess.make_dir_recursive_absolute("res://artifacts/m6")
	var file := FileAccess.open("res://artifacts/m6/behavior.json", FileAccess.WRITE)
	file.store_string(JSON.stringify({"checks": checks, "failures": failures}, "\t") + "\n")
	print("M6_CHECKS %d failures=%d" % [checks.size(), failures])
	quit(1 if failures else 0)


func mouse_wheel() -> InputEventMouseButton:
	var event := InputEventMouseButton.new()
	event.button_index = MOUSE_BUTTON_WHEEL_UP
	event.pressed = true
	return event
