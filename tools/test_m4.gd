extends SceneTree

# Copied into each fresh project as test-only scaffolding. No gallery imports.
var spec: Dictionary
var scene: Node
var view: SubViewport
var adapter: Node
var materials: Array[ShaderMaterial] = []
var saved: Array[Dictionary] = []
var checks: Array = []
var captures: Array = []


func _initialize() -> void:
	call_deferred("_run")


func check(ok: bool, label: String, details: Dictionary = {}) -> void:
	checks.append({"name":label,"passed":ok,"details":details})
	if not ok: push_error("M4 FAIL: "+label+" "+JSON.stringify(details))


func capture(label: String = "") -> Image:
	await process_frame
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var image := view.get_texture().get_image()
	if not label.is_empty():
		var path := "res://"+label+".png"
		image.save_png(path)
		captures.append({"path":path,"sha256":FileAccess.get_sha256(path)})
	return image


func difference(a: Image, b: Image) -> float:
	var total := 0.0
	for y in range(0,a.get_height(),4):
		for x in range(0,a.get_width(),4):
			var delta := a.get_pixel(x,y)-b.get_pixel(x,y)
			total+=absf(delta.r)+absf(delta.g)+absf(delta.b)
	return total/(ceilf(a.get_width()/4.0)*ceilf(a.get_height()/4.0)*3.0)


func set_value(key: String, value: Variant) -> void:
	for material in materials: material.set_shader_parameter(key,value)


func reset() -> void:
	if adapter: adapter.reset()
	else:
		for i in range(materials.size()):
			for key in saved[i]: materials[i].set_shader_parameter(key,saved[i][key])


func state() -> void:
	if adapter:
		adapter.player.seek(0.37)
		if spec["number"] in [118,190,270]:
			adapter.player.seek(0.0)
			adapter.player.trigger_event()
			adapter.player.seek(0.03 if spec["number"]==270 else 0.3)
			if spec["number"] in [118,190]: set_value("u_hit_position",Vector3(0,0,0.92) if spec["number"]==190 else Vector3.ZERO)


func parameter_checks() -> void:
	state()
	var initial := await capture("default")
	for p: Dictionary in spec["parameters"]:
		var expected: Variant = p["default"]
		if p["type"]=="color": expected=Color(expected)
		if p["type"]=="texture": expected=load(expected)
		reset()
		for material in materials: check(material.get_shader_parameter(p["key"])==expected,"preset/reset default: "+p["key"])
		state()
		var low: Variant
		var high: Variant
		match p["type"]:
			"float":
				low=p["min"]
				high=90.0 if p["key"].ends_with("_deg") else p["max"]
			"color":
				low=Color(p["default"])
				high=Color.RED
			"bool":
				low=false
				high=true
			_:
				low=p["options"][0]["value"]
				high=p["options"][-1]["value"]
				if p["type"]=="texture":
					low=load(low)
					high=load(high)
		if spec["number"]==37 and p["key"]=="u_period": adapter.player.seek(0.5)
		set_value(p["key"],low)
		var a := await capture(p["key"]+"_low")
		set_value(p["key"],high)
		var b := await capture(p["key"]+"_high")
		var delta := difference(a,b)
		check(delta>0.000005,"parameter changes actual usage pixels: "+p["key"],{"mean_rgb_difference":delta})
	reset()
	state()
	check(initial.get_data()==(await capture("reset")).get_data(),"reset reproduces fixed default pixels")


func playback_checks() -> void:
	if not adapter: return
	reset()
	adapter._process(2.0)
	adapter.player.playback_speed=0.25
	check(adapter.player.effect_time==2.0,"speed change preserves clock")
	adapter._process(0.4)
	check(is_equal_approx(adapter.player.effect_time,2.1),"continuous quarter speed")
	adapter.player.playback_speed=0.0
	adapter._process(1.0)
	check(is_equal_approx(adapter.player.effect_time,2.1),"zero speed holds clock")
	adapter.player.playback_speed=1.0
	adapter.player.paused=true
	var before := await capture()
	adapter._process(1.0)
	check(before.get_data()==(await capture()).get_data(),"pause holds actual usage pixels")
	adapter.player.paused=false
	adapter._process(0.2)
	check(is_equal_approx(adapter.player.effect_time,2.3),"resume continues clock")
	reset()
	check(adapter.player.effect_time==0 and adapter.player.event_time==-1 and not adapter.player.paused,"reset clears time and event")
	if spec["number"]==270:
		var idle := await capture("before_event")
		adapter.play_once()
		adapter.player.seek(0.03)
		check(difference(idle,await capture("event"))>0.0001,"flash visible after single trigger")
		adapter.player.seek(2.0)
		check(idle.get_data()==(await capture("expired")).get_data(),"flash expires without repeating")
		adapter.play_once()
		check(difference(idle,await capture())>0.0001,"flash can retrigger")
	if spec["number"] in [118,190]: await hit_checks()


func hit_checks() -> void:
	reset()
	adapter.player.seek(0.37)
	var target: MeshInstance3D = adapter.target
	var local := Vector3(0,0,0.92) if spec["number"]==190 else Vector3(0,sin(-0.37*1.1)*0.5*0.04/1.5,0)
	var pixel: Vector2 = adapter.camera.unproject_position(target.to_global(local))
	check(adapter.trigger_at(pixel),"projected surface click accepted")
	var hit: Vector3 = materials[0].get_shader_parameter("u_hit_position")
	var error: float = adapter.camera.unproject_position(target.to_global(hit)).distance_to(pixel)
	check(error<=3.0,"surface response projects to click",{"pixels":error})
	var old_transform: Transform3D=scene.transform
	scene.position=Vector3(1.2,0.4,-0.6)
	scene.rotation_degrees=Vector3(0,25,0)
	adapter._position_camera()
	var moved_pixel: Vector2=adapter.camera.unproject_position(target.to_global(local))
	check(adapter.trigger_at(moved_pixel),"translated/rotated usage root still accepts surface hit")
	var moved_hit: Vector3=materials[0].get_shader_parameter("u_hit_position")
	check(adapter.camera.unproject_position(target.to_global(moved_hit)).distance_to(moved_pixel)<=3.0,"transformed usage projects response within three pixels")
	scene.transform=old_transform
	adapter._position_camera()
	adapter.trigger_at(pixel)
	adapter.player.seek(0.57)
	var event := await capture("event")
	reset()
	adapter.player.seek(0.57)
	check(difference(event,await capture("no_event"))>0.000005,"surface event changes actual pixels")
	check(not adapter.trigger_at(Vector2(-10,-10)),"outside click rejected")
	for drag in [true,false]:
		reset()
		adapter.player.seek(0.37)
		var press := InputEventMouseButton.new()
		press.button_index=MOUSE_BUTTON_LEFT
		press.pressed=true
		press.position=pixel
		adapter._unhandled_input(press)
		var motion := InputEventMouseMotion.new()
		motion.position=pixel+Vector2(20 if drag else 2,0)
		motion.button_mask=MOUSE_BUTTON_MASK_LEFT
		adapter._unhandled_input(motion)
		var release := InputEventMouseButton.new()
		release.button_index=MOUSE_BUTTON_LEFT
		release.position=motion.position
		adapter._unhandled_input(release)
		check((adapter.player.event_time<0)==drag,"drag suppression" if drag else "small click triggers on release")
	reset()
	adapter.player.seek(4.0)
	var idle := await capture()
	adapter.player.seek(0.0)
	adapter.trigger_at(pixel)
	adapter.player.seek(4.0)
	check(idle.get_data()==(await capture("expired")).get_data(),"surface event expires without repeating")


func endpoint_checks() -> void:
	reset()
	set_value("u_enabled",false)
	var original := await capture("off")
	set_value("u_enabled",true)
	var number: int = spec["number"]
	if number in [1,2,7,17,18,271]:
		set_value("u_width_px" if number in [17,18] else "u_amount",0.0)
		check(original.get_data()==(await capture("zero")).get_data(),"zero endpoint restores source")
	if number in [1,2,7]:
		set_value("u_amount",1.0)
		var gone := await capture("one")
		scene.get_node("Center/Effect").visible=false
		check(gone.get_data()==(await capture()).get_data(),"full dissolve leaves only background")
		scene.get_node("Center/Effect").visible=true
	if number in [296,297,298]:
		set_value("u_amount",0.0)
		var empty := await capture("zero")
		set_value("u_amount",1.0)
		var full := await capture("one")
		check(difference(empty,full)>0.01,"empty/full progress visibly differs")
		if adapter:
			adapter.player.seek(2.0)
			check(full.get_data()==(await capture()).get_data(),"full liquid has no moving holes")
	if number==348:
		for key in ["u_curvature","u_scanline_strength","u_vignette","u_rgb_mask"]: set_value(key,0.0)
		check(original.get_data()==(await capture("zero")).get_data(),"CRT all zero restores source")
	if number==317:
		set_value("lut_texture",load("res://assets/neutral_lut.png"))
		check(original.get_data()==(await capture("neutral")).get_data(),"neutral LUT preserves source")
	if number==326:
		check(materials.size()==2 and not materials[0].get_shader_parameter("u_vertical") and materials[1].get_shader_parameter("u_vertical"),"separate horizontal/vertical materials")
		check(scene.get_node("BetweenPasses").get_index()>scene.get_node("Effect").get_index() and scene.get_node("BetweenPasses").get_index()<scene.get_node("EffectVertical").get_index(),"screen copy occurs between passes")
		set_value("u_radius_px",0.0)
		check(original.get_data()==(await capture("zero")).get_data(),"Gaussian zero restores source")
		await gaussian_checks()
	if number==112:
		set_value("u_wave_height",0.0)
		adapter.player.seek(0.5)
		var flat := await capture("flat_early")
		adapter.player.seek(2.0)
		check(flat.get_data()==(await capture("flat_late")).get_data(),"zero wave height stops visible motion")
	reset()


func gaussian_checks() -> void:
	view.size=Vector2i(129,129)
	var impulse := Image.create(129,129,false,Image.FORMAT_RGBA8)
	impulse.fill(Color.BLACK)
	impulse.set_pixel(64,64,Color.WHITE)
	scene.get_node("Background").texture=ImageTexture.create_from_image(impulse)
	set_value("u_radius_px",4.0)
	set_value("u_quality",1)
	var image := await capture("two_pass_impulse")
	var weights: Array[float]=[]
	var sum := 0.0
	for i in range(-4,5):
		var weight := exp(-4.5*pow(float(i)/4.0,2.0))
		weights.append(weight)
		sum+=weight
	var maximum_error := 0.0
	for y in range(-4,5):
		for x in range(-4,5):
			var expected := weights[x+4]*weights[y+4]/(sum*sum)
			maximum_error=maxf(maximum_error,absf(image.get_pixel(64+x,64+y).r-expected))
	check(maximum_error<=2.0/255.0,"usage Gaussian matches independent separable CPU kernel",{"max_channel_error":maximum_error})
	check(image.get_pixel(65,65).r>0.0,"both Gaussian directions contribute diagonal energy")
	for quality in [0,1,2]:
		impulse.fill(Color(0.25,0.5,0.75))
		scene.get_node("Background").texture=ImageTexture.create_from_image(impulse)
		set_value("u_enabled",false)
		var pure := await capture()
		set_value("u_enabled",true)
		set_value("u_quality",quality)
		check(pure.get_data()==(await capture()).get_data(),"Gaussian normalized pure color quality %d" % quality)
	view.size=Vector2i(640,480)


func _run() -> void:
	spec=JSON.parse_string(FileAccess.get_file_as_string("res://case.json"))
	spec["number"]=int(spec["number"])
	view=SubViewport.new()
	view.size=Vector2i(640,480)
	view.own_world_3d=true
	view.render_target_update_mode=SubViewport.UPDATE_ALWAYS
	root.add_child(view)
	var packed: PackedScene=load(spec["directory"].path_join("usage.tscn"))
	scene=packed.instantiate()
	view.add_child(scene)
	adapter=scene.get_node_or_null("Player")
	if adapter: adapter.set_process(false)
	var effect := scene.find_child("Effect",true,false)
	materials.append(effect.material_override if effect is MeshInstance3D else effect.material)
	if scene.has_node("EffectVertical"): materials.append(scene.get_node("EffectVertical").material)
	for material in materials:
		var values := {}
		for p: Dictionary in material.shader.get_shader_uniform_list():
			var value: Variant=material.get_shader_parameter(p["name"])
			if value!=null: values[p["name"]]=value
		saved.append(values)
	var other := packed.instantiate()
	view.add_child(other)
	var second := other.find_child("Effect",true,false)
	var second_material: ShaderMaterial=second.material_override if second is MeshInstance3D else second.material
	check(materials[0]!=second_material,"scene instances have independent material objects")
	var first_key: String=spec["parameters"][0]["key"]
	var old: Variant=second_material.get_shader_parameter(first_key)
	materials[0].set_shader_parameter(first_key,Color.RED if spec["parameters"][0]["type"]=="color" else 0.0)
	check(second_material.get_shader_parameter(first_key)==old,"scene instance parameter isolation")
	if adapter:
		adapter.player.seek(1.0)
		check(other.get_node("Player").player.effect_time==0.0 and second_material.get_shader_parameter("u_time")==0.0,"scene instance clocks are independent")
	other.free()
	reset()
	check((adapter!=null)==bool(spec["animated"]),"dynamic scene explicitly owns player")
	await parameter_checks()
	await playback_checks()
	await endpoint_checks()
	var failures := 0
	for result: Dictionary in checks:
		if not result["passed"]: failures+=1
	var report := {"number":spec["number"],"failures":failures,"checks":checks,"captures":captures,"render_size":[640,480],"adapter":RenderingServer.get_video_adapter_name(),"godot":Engine.get_version_info()}
	var file := FileAccess.open("res://report.json",FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"\t"))
	file.close()
	view.free()
	print("M4_GPU checks=%d failures=%d" % [checks.size(),failures])
	quit(0 if failures==0 else 1)
