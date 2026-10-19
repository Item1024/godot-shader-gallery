extends SceneTree

const Stage = preload("res://shared/stage.gd")
const EffectPlayer = preload("res://shared/effect_player.gd")
const OUTPUT := "res://artifacts/m2"
var catalog: Array
var checks: Array = []
var hits: Array = []
var waves: Array = []
var render_checks := false


func _initialize() -> void:
	call_deferred("_run")


func _check(passed: bool, name: String, details: Dictionary = {}) -> void:
	checks.append({"name": name, "passed": passed, "details": details})
	if not passed:
		push_error("M2 FAIL: " + name + " " + JSON.stringify(details))


func _near(actual: float, expected: float, name: String) -> void:
	_check(absf(actual - expected) < 0.00001, name, {"actual": actual, "expected": expected})


func _entry(number: int) -> Dictionary:
	return catalog[number - 1]


func _stage(number: int) -> Stage:
	var stage := Stage.new()
	root.add_child(stage)
	stage.set_process(false)
	stage.configure(_entry(number))
	return stage


func _button(position: Vector2, pressed: bool, button: MouseButton = MOUSE_BUTTON_LEFT) -> InputEventMouseButton:
	var event := InputEventMouseButton.new()
	event.position = position
	event.global_position = position
	event.pressed = pressed
	event.button_index = button
	event.button_mask = MOUSE_BUTTON_MASK_LEFT if pressed and button == MOUSE_BUTTON_LEFT else 0
	return event


func _motion(position: Vector2, held: bool = true) -> InputEventMouseMotion:
	var event := InputEventMouseMotion.new()
	event.position = position
	event.global_position = position
	event.button_mask = MOUSE_BUTTON_MASK_LEFT if held else 0
	return event


func _click(stage: Stage, position: Vector2, offset := Vector2.ZERO) -> void:
	stage.orbit_input(_button(position, true))
	stage.orbit_input(_button(position + offset, false))


func _time_tests() -> void:
	var stage := _stage(34)
	stage.elapsed = 12.0
	stage.set_parameter("u_speed", 0.25)
	_near(stage.elapsed, 12.0, "speed change preserves current phase")
	stage._process(2.0)
	_near(stage.elapsed, 12.5, "quarter speed advances by scaled delta")
	stage.set_parameter("u_speed", 2.0)
	_near(stage.elapsed, 12.5, "second speed change preserves phase")
	stage._process(0.75)
	_near(stage.elapsed, 14.0, "double speed uses only future delta")
	_near(stage.shader_material.get_shader_parameter("u_time"), 14.0, "shader receives accumulated time")
	_near(stage.shader_material.get_shader_parameter("u_speed"), 1.0, "shader speed is not multiplied twice")
	stage.set_parameter("u_speed", 0.0)
	stage._process(10.0)
	_near(stage.elapsed, 14.0, "zero speed holds phase")
	stage.paused = true
	stage.set_parameter("u_speed", 3.0)
	stage.set_parameter("u_intensity", 0.7)
	stage.set_parameter("u_color", Color.RED)
	stage._process(10.0)
	_near(stage.elapsed, 14.0, "pause holds time while speed and parameters change")
	stage.paused = false
	stage._process(0.5)
	_near(stage.elapsed, 15.5, "resume continues from held time")
	stage.player.seek(3.25)
	_near(stage.shader_material.get_shader_parameter("u_time"), 3.25, "explicit seek updates shader immediately")
	var other := _stage(34)
	other._process(0.5)
	_near(stage.elapsed, 3.25, "different previews own independent clocks")
	_check(stage.shader_material != other.shader_material, "different previews own independent materials")
	var clock = EffectPlayer.new()
	var first := stage.shader_material.duplicate() as ShaderMaterial
	var second := stage.shader_material.duplicate() as ShaderMaterial
	clock.bind_materials([first, second])
	clock.playback_speed = 2.0
	clock.advance(0.75)
	_near(first.get_shader_parameter("u_time"), 1.5, "first material follows shared player")
	_near(second.get_shader_parameter("u_time"), 1.5, "second material follows shared player")
	stage.player.trigger_event()
	stage.reset()
	_near(stage.elapsed, 0.0, "reset clears time")
	_near(stage.speed, 1.0, "reset restores playback speed")
	_near(stage.amount, _entry(34)["amount"], "reset restores entry amount")
	_check(not stage.paused and stage.enabled and stage.player.event_time == -1.0, "reset clears pause and trigger state")
	_check(stage.shader_material.get_shader_parameter("u_color") == Color("#55e8bb"), "reset restores default color")
	other.free()
	stage.free()


func _pointer_tests(number: int) -> void:
	var stage := _stage(number)
	stage.elapsed = 2.0
	var local := Vector3.ZERO if number == 118 else Vector3(0, 0, 0.92)
	if number == 118:
		local.y = stage.water_height(Vector2.ZERO)
	else:
		local = stage.interaction_surface.to_local(stage.camera.global_position).normalized() * 0.92
	var pixel: Vector2 = stage.camera.unproject_position(stage.interaction_surface.to_global(local))
	var prefix := "%03d " % number
	_near(stage.player.event_time, -1.0, prefix + "starts without an event")
	stage.orbit_input(_button(pixel, true))
	_near(stage.player.event_time, -1.0, prefix + "press alone does not trigger")
	stage.orbit_input(_button(pixel, false))
	_near(stage.player.event_time, 2.0, prefix + "release triggers once")
	_check(stage.shader_material.get_shader_parameter("u_hit_position").distance_to(local) < 0.003, prefix + "event stores local surface position")
	stage.elapsed = 3.0
	_click(stage, pixel, Vector2(4, 0))
	_near(stage.player.event_time, 3.0, prefix + "four UI pixels still count as click")
	stage.elapsed = 4.0
	_click(stage, pixel, Vector2(4.1, 0))
	_near(stage.player.event_time, 3.0, prefix + "over four pixels cannot trigger without motion event")
	stage.orbit_input(_button(pixel, true))
	stage.orbit_input(_motion(pixel + Vector2(20, 8)))
	_check(stage.orbit != 0.0, prefix + "drag rotates camera")
	stage.orbit_input(_motion(pixel))
	stage.orbit_input(_button(pixel, false))
	_near(stage.player.event_time, 3.0, prefix + "drag returning to origin cannot trigger")
	stage.orbit_input(_button(pixel, true))
	stage.orbit_input(_motion(pixel, false))
	stage.orbit_input(_button(pixel, false))
	_near(stage.player.event_time, 3.0, prefix + "lost button mask cancels gesture")
	stage.orbit_input(_button(pixel, true))
	root.focus_exited.emit()
	stage.orbit_input(_button(pixel, false))
	_near(stage.player.event_time, 3.0, prefix + "window focus loss cancels gesture")
	stage.orbit_input(_button(pixel, false))
	_near(stage.player.event_time, 3.0, prefix + "unpaired release cannot trigger")
	_click(stage, Vector2(-20, -20))
	_click(stage, Vector2(2, 2))
	_near(stage.player.event_time, 3.0, prefix + "outside preview and outside model do not trigger")
	stage.orbit_input(_button(pixel, true, MOUSE_BUTTON_WHEEL_UP))
	_near(stage.player.event_time, 3.0, prefix + "wheel zoom does not trigger")
	_check(stage.distance < 5.0, prefix + "wheel still zooms camera")
	stage.reset()
	stage.elapsed = 7.0
	stage.set_parameter("u_enabled", false)
	_check(not stage.trigger_at(pixel), prefix + "disabled effect rejects trigger")
	stage.set_parameter("u_enabled", true)
	stage.paused = true
	_check(stage.trigger_at(pixel), prefix + "paused effect accepts a new event")
	stage._process(10.0)
	_near(stage.elapsed, 7.0, prefix + "paused event does not age")
	stage.reset()
	_near(stage.shader_material.get_shader_parameter("u_event_time"), -1.0, prefix + "reset clears shader event")
	stage.free()


func _capture(stage: Stage) -> Image:
	await process_frame
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	return stage.get_texture().get_image()


func _marker_shader(stage: Stage) -> Shader:
	# Reuse the actual effect's vertex code. The only replacement is a white
	# surface marker, allowing the GPU to independently check CPU hit positions.
	var source := stage.shader_material.shader.code
	var shader := Shader.new()
	shader.code = source.left(source.find("void fragment()")) + """
void fragment() {
    float marker=1.0-smoothstep(0.022,0.040,length(v_local-u_hit_position));
    ALBEDO=vec3(marker);
    EMISSION=vec3(marker);
    ROUGHNESS=1.0;
}
"""
	return shader


func _centroid(image: Image, around: Vector2) -> Vector2:
	var weighted := Vector2.ZERO
	var weight := 0.0
	for y in range(maxi(0, int(around.y) - 20), mini(image.get_height(), int(around.y) + 21)):
		for x in range(maxi(0, int(around.x) - 20), mini(image.get_width(), int(around.x) + 21)):
			var color := image.get_pixel(x, y)
			var brightness := minf(color.r, minf(color.g, color.b))
			if brightness > 0.1:
				weighted += Vector2(x + 0.5, y + 0.5) * brightness
				weight += brightness
	return weighted / weight if weight > 0.0 else Vector2(-10000, -10000)


func _hit_tests(number: int) -> void:
	var stage := _stage(number)
	stage.paused = true
	stage.elapsed = 1.7
	if render_checks:
		stage.shader_material.shader = _marker_shader(stage)
		stage._set_uniforms()
		stage.environment.background_color = Color.BLACK
		for instance: MeshInstance3D in stage.find_children("*", "MeshInstance3D", true, false):
			instance.visible = instance == stage.interaction_surface
	var water_points := [Vector2.ZERO, Vector2(-0.8, -0.8), Vector2(0.7, -0.6), Vector2(-0.6, 0.6), Vector2(0.75, 0.65)]
	var sphere_offsets := [Vector2.ZERO, Vector2(-0.35, 0.0), Vector2(0.35, 0.0), Vector2(0, -0.35), Vector2(0, 0.35)]
	for viewport_size in [Vector2i(900, 660), Vector2i(1280, 720)]:
		stage.size = viewport_size
		for pose in range(3):
			stage.orbit = [0.0, 0.8, -0.9][pose]
			stage.elevation = [0.28, 0.55, 0.18][pose]
			stage.distance = [5.0, 6.0, 4.4][pose]
			stage._position_camera()
			for sample in range(5):
				var local: Vector3
				if number == 118:
					var point: Vector2 = water_points[sample]
					# Independent specification, not the function under test.
					var height := (sin(point.x * TAU + 1.7 * 1.4) + sin(point.y * TAU - 1.7 * 1.1) * 0.5) * 0.04 / 1.5
					local = Vector3(point.x, height, point.y)
				else:
					var front := stage.interaction_surface.to_local(stage.camera.global_position).normalized()
					var right := stage.interaction_surface.global_basis.inverse() * stage.camera.global_basis.x
					var up := stage.interaction_surface.global_basis.inverse() * stage.camera.global_basis.y
					var offset: Vector2 = sphere_offsets[sample]
					local = (front + right * offset.x + up * offset.y).normalized() * 0.92
				var pixel: Vector2 = stage.camera.unproject_position(stage.interaction_surface.to_global(local))
				var hit := stage.surface_hit(pixel)
				var record := {"number": number, "viewport": [viewport_size.x, viewport_size.y], "pose": pose, "sample": sample}
				var label := "%03d %s pose=%d sample=%d" % [number, viewport_size, pose, sample]
				_check(not hit.is_empty(), label + " ray hits surface")
				if hit.is_empty():
					continue
				var point_error: float = hit["local_position"].distance_to(local)
				var projection_error: float = stage.camera.unproject_position(hit["world_position"]).distance_to(pixel)
				_check(point_error < 0.003 and projection_error <= 3.0, label + " matches known surface point", {"surface_error": point_error, "projection_error_px": projection_error})
				_check(stage.trigger_at(pixel), label + " triggers at surface")
				record["surface_error"] = point_error
				record["projection_error_px"] = projection_error
				if number == 118:
					var p: Vector3 = hit["local_position"]
					var residual := absf(p.y - stage.water_height(Vector2(p.x, p.z)))
					_check(residual <= 0.001, label + " wave residual", {"residual": residual})
					record["height_residual"] = residual
				if render_checks:
					var image := await _capture(stage)
					var center := _centroid(image, pixel)
					var gpu_error := center.distance_to(pixel)
					_check(gpu_error <= 3.0, label + " GPU vertex marker", {"error_px": gpu_error})
					record["gpu_marker_error_px"] = gpu_error
					if sample == 0:
						image.save_png(OUTPUT.path_join("marker_%03d_%d_%d.png" % [number, viewport_size.x, pose]))
				hits.append(record)
	_check(stage.surface_hit(Vector2(-5000, -5000)).is_empty(), "%03d off-model ray misses" % number)
	stage.free()


func _event_images(number: int) -> void:
	var stage := _stage(number)
	stage.paused = true
	stage.elapsed = 2.0
	var pixel := Vector2(stage.size) * 0.5
	_check(stage.trigger_at(pixel), "%03d rendered event trigger" % number)
	stage.elapsed = 2.2
	var active := await _capture(stage)
	active.save_png(OUTPUT.path_join("event_%03d_active.png" % number))
	stage.player.event_time = -1.0
	stage.player._write_event()
	var idle := await _capture(stage)
	_check(active.get_data() != idle.get_data(), "%03d actual event changes rendered pixels" % number)
	stage.elapsed = 3.3
	var expired_idle := await _capture(stage)
	stage.player.event_time = 2.0
	stage.player._write_event()
	var expired := await _capture(stage)
	_check(expired.get_data() == expired_idle.get_data(), "%03d expired event matches idle and does not repeat" % number)
	stage.free()


func _time_images(number: int) -> void:
	var stage := _stage(number)
	stage.elapsed = 1.37
	var before := await _capture(stage)
	stage.set_parameter("u_speed", 0.25)
	var changed_speed := await _capture(stage)
	_check(before.get_data() == changed_speed.get_data(), "%03d speed change preserves rendered phase" % number)
	stage.set_parameter("u_speed", 0.0)
	stage._process(10.0)
	var stopped := await _capture(stage)
	_check(before.get_data() == stopped.get_data(), "%03d zero speed preserves rendered phase" % number)
	stage.paused = true
	stage.set_parameter("u_speed", 2.0)
	stage._process(10.0)
	var paused_image := await _capture(stage)
	_check(before.get_data() == paused_image.get_data(), "%03d pause preserves rendered phase" % number)
	stage.paused = false
	stage._process(0.5)
	var resumed := await _capture(stage)
	_check(before.get_data() != resumed.get_data(), "%03d resume advances visible animation" % number)
	stage.free()


func _wave_tests() -> void:
	var stage := _stage(118)
	stage.interaction_surface.rotation_degrees = Vector3(12, 25, -8)
	stage.interaction_surface.scale = Vector3(1.1, 0.9, 0.8)
	stage.interaction_surface.position = Vector3(0.1, 0.05, -0.1)
	stage.elevation = 0.6
	stage._position_camera()
	if render_checks:
		stage.shader_material.shader = _marker_shader(stage)
		stage.environment.background_color = Color.BLACK
		for instance: MeshInstance3D in stage.find_children("*", "MeshInstance3D", true, false):
			instance.visible = instance == stage.interaction_surface
	for amount in [0.0, 0.125, 0.25]:
		for scale_value in [0.0, 0.6, 1.0]:
			for time in [0.0, 2.7, 7.2]:
				stage.elapsed = time
				stage.set_parameter("u_wave_height", amount)
				stage.set_parameter("u_strength", scale_value)
				var point := Vector2(0.6, 0.7)
				var height: float = (sin(point.x * TAU + time * 1.4) + sin(point.y * TAU - time * 1.1) * 0.5) * amount / 1.5
				_near(stage.water_height(point), height, "wave CPU specification")
				var local := Vector3(point.x, height, point.y)
				var world := stage.interaction_surface.to_global(local)
				var pixel: Vector2 = stage.camera.unproject_position(world)
				var hit := stage.surface_hit(pixel)
				# A tall wave may hide the specified point. Accept a nearer surface
				# on this ray; the GPU marker below must still be visible there.
				var valid := not hit.is_empty()
				if valid:
					var p: Vector3 = hit["local_position"]
					valid = absf(p.y - stage.water_height(Vector2(p.x, p.z))) <= 0.001 and stage.camera.global_position.distance_to(hit["world_position"]) <= stage.camera.global_position.distance_to(world) + 0.003
				_check(valid, "wave hit respects height, independent event strength, time and mesh transform", {"height": amount, "strength": scale_value, "time": time, "hit": str(hit)})
				var record := {"height": amount, "strength": scale_value, "time": time}
				if render_checks and not hit.is_empty():
					stage.trigger_at(pixel)
					var image := await _capture(stage)
					var error_px := _centroid(image, pixel).distance_to(pixel)
					_check(error_px <= 3.0, "wave CPU and actual GPU vertex formula agree", {"error_px": error_px, "case": record})
					record["gpu_marker_error_px"] = error_px
				waves.append(record)
	stage.interaction_surface.transform = Transform3D.IDENTITY
	stage.camera.position = Vector3(0, 0, 4)
	stage.camera.look_at(Vector3.ZERO)
	_check(stage.surface_hit(Vector2(stage.size) * 0.5).is_empty(), "parallel water ray is rejected")
	stage.free()
	stage = _stage(190)
	stage.camera.look_at(stage.camera.position + Vector3(0, 0, 1))
	_check(stage.surface_hit(Vector2(stage.size) * 0.5).is_empty(), "sphere behind camera is rejected")
	stage.free()
	stage = _stage(1)
	await process_frame
	var image_region := stage.canvas_picture.get_global_rect()
	var target := Vector2(0.2, 0.7)
	_check(stage.trigger_at(image_region.position + image_region.size * target), "2D image click is accepted")
	_check(stage.shader_material.get_shader_parameter("u_mouse").distance_to(target) < 0.00001, "2D click maps to image UV rather than viewport UV")
	_check(not stage.trigger_at(Vector2(1, 1)), "2D image margin does not move interaction center")
	stage.free()


func _gui_tests() -> void:
	var gallery = load("res://gallery.tscn").instantiate()
	root.add_child(gallery)
	await process_frame
	gallery._show(_entry(118))
	var stage: Stage = gallery.stage
	stage.set_process(false)
	stage.elapsed = 4.0
	gallery.parameter_controls["u_speed"]["slider"].value = 2.0
	_near(stage.speed, 2.0, "gallery speed slider controls clock")
	_near(stage.elapsed, 4.0, "gallery speed slider preserves phase")
	gallery._toggle_pause()
	stage._process(1.0)
	_near(stage.elapsed, 4.0, "gallery pause button holds time")
	gallery._reset()
	_near(stage.elapsed, 0.0, "gallery reset clears time")
	_near(stage.speed, 1.0, "gallery reset restores speed")
	var container := stage.get_parent() as SubViewportContainer
	for window_size in [Vector2i(1440, 900), Vector2i(1180, 720)]:
		root.size = window_size
		for shrink in [1, 2]:
			container.stretch_shrink = shrink
			await process_frame
			await process_frame
			stage.elapsed = float(window_size.x + shrink)
			var pixel: Vector2 = stage.camera.unproject_position(stage.interaction_surface.to_global(Vector3(0, stage.water_height(Vector2.ZERO), 0)))
			var local := pixel * container.size / Vector2(stage.size)
			var screen: Vector2 = container.get_global_transform() * local
			root.push_input(_button(screen, true), true)
			root.push_input(_button(screen, false), true)
			_near(stage.player.event_time, stage.elapsed, "real gallery input %s shrink=%d" % [window_size, shrink])
			_check(stage.shader_material.get_shader_parameter("u_hit_position").distance_to(Vector3(0, stage.water_height(Vector2.ZERO), 0)) < 0.003, "real gallery input converts container coordinates")
	gallery.free()
	root.size = Vector2i(1440, 900)
	for number in [1, 118, 190]:
		var demo = load(_entry(number)["scene"]).instantiate()
		root.add_child(demo)
		await process_frame
		var demo_container := demo.get_child(0) as SubViewportContainer
		var demo_stage: Stage = demo_container.get_child(0)
		demo_stage.set_process(false)
		_check(demo_stage.entry["number"] == number, "%03d standalone scene configures effect" % number)
		if number != 1:
			demo_stage.elapsed = 2.0
			var center := Vector2(demo_container.size) * 0.5
			root.push_input(_button(center, true), true)
			root.push_input(_button(center, false), true)
			_near(demo_stage.player.event_time, 2.0, "%03d standalone real GUI click reaches effect" % number)
		demo.free()


func _run() -> void:
	catalog = JSON.parse_string(FileAccess.get_file_as_string("res://catalog.json"))
	render_checks = "--render-checks" in OS.get_cmdline_user_args()
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUTPUT))
	_time_tests()
	_pointer_tests(118)
	_pointer_tests(190)
	await _hit_tests(118)
	await _hit_tests(190)
	await _wave_tests()
	await _gui_tests()
	if render_checks:
		await _time_images(34)
		await _time_images(405)
		await _event_images(118)
		await _event_images(190)
	var failed := checks.filter(func(check): return not check["passed"]).size()
	var hashes := {}
	for path in ["shared/effect_player.gd", "shared/stage.gd", "shared/gallery.gd", "shared/standalone.gd", "tools/test_runtime.gd", "effects/07_water/07_interactive/effect.gdshader", "effects/11_magic/03_shield_hit/effect.gdshader"]:
		hashes[path] = FileAccess.get_file_as_string("res://" + path).replace("\r\n", "\n").sha256_text()
	var report := {"engine": Engine.get_version_info()["string"], "gpu": RenderingServer.get_video_adapter_name(), "rendering_method": RenderingServer.get_current_rendering_method(), "render_checks": render_checks, "source_sha256_lf": hashes, "checks": checks, "hits": hits, "waves": waves, "total": checks.size(), "failures": failed}
	var filename := "runtime_gpu.json" if render_checks else "runtime_logic.json"
	var file := FileAccess.open(OUTPUT.path_join(filename), FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t") + "\n")
	file.close()
	print("M2_RUNTIME checks=%d hits=%d failures=%d render_checks=%s" % [checks.size(), hits.size(), failed, render_checks])
	quit(0 if failed == 0 else 1)
