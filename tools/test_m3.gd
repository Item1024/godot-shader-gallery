extends SceneTree

const Stage = preload("res://shared/stage.gd")
const OUTPUT := "res://artifacts/m3"
var catalog: Array
var checks: Array = []
var captures: Array = []


func _initialize() -> void:
	call_deferred("_run")


func check(passed: bool, name: String, details: Dictionary = {}) -> void:
	checks.append({"name": name, "passed": passed, "details": details})
	if not passed: push_error("M3 FAIL: " + name + " " + JSON.stringify(details))


func make_stage(number: int) -> Stage:
	var stage := Stage.new()
	root.add_child(stage)
	stage.set_process(false)
	stage.configure(catalog[number - 1])
	stage.size = Vector2i(640, 480)
	state(stage)
	return stage


func state(stage: Stage) -> void:
	stage.elapsed = 0.37
	if int(stage.entry["number"]) in [118, 190, 270]:
		stage.player.event_time = stage.elapsed - (0.03 if stage.entry["number"] == 270 else 0.3)
		stage.player._write_event()
		stage.shader_material.set_shader_parameter("u_hit_position", Vector3(0, 0, 0.92) if stage.entry["number"] == 190 else Vector3.ZERO)


func capture(stage: Stage, name: String = "") -> Image:
	await process_frame
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var image := stage.get_texture().get_image()
	if not name.is_empty():
		var path := OUTPUT.path_join(name + ".png")
		image.save_png(path)
		captures.append({"path": path, "sha256": FileAccess.get_sha256(path)})
	return image


func difference(a: Image, b: Image) -> float:
	var total := 0.0
	for y in range(0, a.get_height(), 4):
		for x in range(0, a.get_width(), 4):
			var d := a.get_pixel(x, y) - b.get_pixel(x, y)
			total += absf(d.r) + absf(d.g) + absf(d.b)
	return total / (ceilf(a.get_width()/4.0)*ceilf(a.get_height()/4.0)*3.0)


func alternative(p: Dictionary, high: bool) -> Variant:
	match p["type"]:
		"float":
			if p["key"].ends_with("_deg"): return 90.0 if high else 0.0
			return p["max"] if high else p["min"]
		"color": return Color.RED if high else Color(p["default"])
		"bool": return high
		_: return p["options"][-1 if high else 0]["value"]


func parameters(stage: Stage) -> void:
	var number: int = stage.entry["number"]
	var initial := await capture(stage, "%03d_default" % number)
	for p: Dictionary in stage.entry["parameters"]:
		var key: String = p["key"]
		check(stage.uniform_names.has(key), "%03d %s uniform exists" % [number, key])
		stage.reset()
		state(stage)
		check(stage.set_parameter(key, alternative(p, false)), "%03d %s accepts low" % [number, key])
		if number==37 and key=="u_period": stage.elapsed=0.5
		var low := await capture(stage, "%03d_%s_low" % [number, key])
		check(stage.set_parameter(key, alternative(p, true)), "%03d %s accepts high" % [number, key])
		var high := await capture(stage, "%03d_%s_high" % [number, key])
		var delta := difference(low, high)
		check(delta > 0.000005, "%03d %s changes actual pixels" % [number, key], {"mean_rgb_difference": delta})
		if p["type"] == "float":
			check(not stage.set_parameter(key, float(p["max"])+1.0), "%03d %s rejects out of range" % [number, key])
			check(not stage.set_parameter(key, "wrong type"), "%03d %s rejects wrong type" % [number, key])
	stage.reset()
	check(stage.elapsed == 0.0 and stage.speed == 1.0 and stage.player.event_time == -1.0 and not stage.paused and stage.enabled, "%03d reset clears playback/event" % number)
	for p: Dictionary in stage.entry["parameters"]:
		var expected: Variant = p["default"]
		if p["type"] == "color": expected = Color(expected)
		if p["type"] == "texture": expected = load(expected)
		for material: ShaderMaterial in stage.player.materials:
			check(material.get_shader_parameter(p["key"]) == expected, "%03d %s reset equals metadata on every pass" % [number, p["key"]])
	state(stage)
	check(initial.get_data() == (await capture(stage)).get_data(), "%03d reset reproduces default pixels" % number)
	print("M3_PARAMETERS %03d" % number)


func endpoints() -> void:
	for number in [1, 2, 7]:
		var stage := make_stage(number)
		stage.set_parameter("u_enabled", false)
		var original := await capture(stage)
		stage.set_parameter("u_enabled", true)
		for angle_value in ([0, 45, 90, 180, 270, 360] if number == 2 else [0]):
			if number == 2: stage.set_parameter("u_direction_deg", angle_value)
			stage.set_parameter("u_amount", 0.0)
			check(original.get_data() == (await capture(stage)).get_data(), "%03d direction %d progress zero is original" % [number, angle_value])
			stage.set_parameter("u_amount", 1.0)
			var empty := await capture(stage)
			var expected_empty := empty.duplicate()
			expected_empty.fill(empty.get_pixel(0,0))
			check(empty.get_data()==expected_empty.get_data() and difference(empty, original)>0.01, "%03d direction %d progress one removes all subject pixels" % [number, angle_value])
		# Width may change color but must not change visible coverage.
		stage.transparent_bg = true
		stage.canvas_root.get_child(0).hide()
		stage.set_parameter("u_amount", 0.32)
		stage.set_parameter("u_edge_width", 0.0)
		var narrow := await capture(stage)
		stage.set_parameter("u_edge_width", 0.15)
		var wide := await capture(stage)
		var same_alpha := true
		for y in range(0,480,3):
			for x in range(0,640,3):
				if narrow.get_pixel(x,y).a != wide.get_pixel(x,y).a: same_alpha = false
		check(same_alpha and difference(narrow,wide)>0.00001, "%03d edge width only colors retained boundary" % number)
		stage.free()
	for number in [296,297,298]:
		var stage := make_stage(number)
		stage.set_parameter("u_amount", 0.0)
		var empty := await capture(stage)
		var expected_empty := empty.duplicate()
		expected_empty.fill(empty.get_pixel(0,0))
		check(empty.get_data()==expected_empty.get_data(),"%03d zero has no completed pixels" % number)
		if number == 298:
			stage.set_parameter("u_wave_height",0.08)
			stage.elapsed = 2.73
		else:
			stage.set_parameter("u_start_deg",137.0)
			stage.set_parameter("u_clockwise",false)
		check(empty.get_data() == (await capture(stage)).get_data(), "%03d empty endpoint independent of wave/angle/direction" % number)
		stage.set_parameter("u_amount",1.0)
		var full := await capture(stage)
		stage.reset()
		stage.set_parameter("u_amount",1.0)
		check(full.get_data() == (await capture(stage)).get_data(), "%03d full endpoint has no seam or wave hole" % number)
		check(difference(full,empty)>0.01, "%03d full and empty visibly differ" % number)
		var cardinal := [Vector2i(320,72),Vector2i(488,240),Vector2i(320,408),Vector2i(152,240)]
		check(cardinal.all(func(point): return full.get_pixelv(point)==full.get_pixelv(cardinal[0])),"%03d full circle covers all four cardinal points without seam" % number)
		if number != 298:
			stage.set_parameter("u_amount",0.25)
			var clockwise_image := await capture(stage)
			stage.set_parameter("u_clockwise",false)
			var counter := await capture(stage)
			# Default top start: right side fills clockwise, left side counterclockwise.
			var right := Vector2i(445,115) if number == 296 else Vector2i(380,195)
			var left := Vector2i(640-right.x-1,right.y)
			check(clockwise_image.get_pixelv(right).g > clockwise_image.get_pixelv(left).g and counter.get_pixelv(left).g > counter.get_pixelv(right).g, "%03d fill follows requested direction" % number)
		stage.free()


func sprite_edges() -> void:
	for number in [17,18,34,37,270,271]:
		var stage := make_stage(number)
		stage.transparent_bg = true
		stage.canvas_root.get_child(0).hide()
		stage.set_parameter("u_enabled",false)
		var original := await capture(stage)
		stage.set_parameter("u_enabled",true)
		if number in [17,18]: stage.set_parameter("u_width_px",0.0)
		if number == 271: stage.set_parameter("u_amount",0.0)
		if number in [17,18,271]: check(original.get_data()==(await capture(stage)).get_data(), "%03d zero width/strength is original" % number)
		stage.reset()
		state(stage)
		var effected := await capture(stage)
		var transparent_ok := true
		var interior_ok := true
		for y in range(0,480,3):
			for x in range(0,640,3):
				var a := original.get_pixel(x,y)
				var b := effected.get_pixel(x,y)
				if number != 17 and absf(a.a-b.a)>0.001: transparent_ok=false
				if number == 17 and a.a==1.0 and a!=b: interior_ok=false
		check(transparent_ok and effected.get_pixel(0,0).a==0.0, "%03d transparent area/alpha preserved" % number)
		if number==17: check(interior_ok,"outer outline preserves opaque interior RGB")
		stage.free()
	var flash := make_stage(270)
	flash.reset()
	flash.elapsed=3.0
	var idle := await capture(flash)
	flash.play_once()
	var active := await capture(flash,"270_triggered")
	check(difference(idle,active)>0.01,"flash play once changes subject")
	flash.elapsed=4.0
	check(idle.get_data()==(await capture(flash)).get_data(),"flash expires and does not repeat")
	flash.play_once()
	check(active.get_data()==(await capture(flash)).get_data(),"flash can be retriggered")
	flash.free()
	var recolor := make_stage(271)
	var stripes := Image.create(640,480,false,Image.FORMAT_RGBA8)
	stripes.fill(Color("#a2f6da"))
	stripes.fill_rect(Rect2i(320,0,320,480),Color.RED)
	recolor.canvas_picture.texture=ImageTexture.create_from_image(stripes)
	recolor.set_parameter("u_tolerance",0.0)
	var exact := await capture(recolor,"271_exact_source")
	check(exact.get_pixel(200,240)==Color("#55e8bb") and exact.get_pixel(450,240)==Color.RED,"recolor exact match replaces source and preserves unselected RGB")
	recolor.set_parameter("u_tolerance",1.0)
	check((await capture(recolor)).get_pixel(450,240)==Color("#55e8bb"),"recolor tolerance expands selected range")
	recolor.free()


func fixture(stage: Stage, image: Image) -> void:
	var picture := stage.canvas_root.get_child(1) as TextureRect
	picture.texture = ImageTexture.create_from_image(image)


func brightness_center(image: Image) -> Vector2:
	var total := 0.0
	var center := Vector2.ZERO
	for y in range(0,image.get_height(),2):
		for x in range(0,image.get_width(),2):
			var color := image.get_pixel(x,y)
			var weight := color.r+color.g+color.b
			center+=Vector2(x,y)*weight
			total+=weight
	return center/maxf(total,0.0001)


func motion_and_surfaces() -> void:
	var breath := make_stage(34)
	var samples: Array[Image]=[]
	for time in [0.0,0.5,1.0,1.5,2.0]:
		breath.elapsed=time
		samples.append(await capture(breath))
	check(samples[0].get_data()==samples[4].get_data() and difference(samples[1],samples[3])>0.01 and difference(samples[0],samples[1])>0.001,"breathing continuous light/dark cycle returns after one period")
	breath.set_parameter("u_enabled",false)
	var disabled := await capture(breath)
	breath.elapsed=0.7
	check(disabled.get_data()==(await capture(breath)).get_data(),"breathing disabled is stable original")
	breath.free()
	var sweep := make_stage(37)
	var black := Image.create(640,480,false,Image.FORMAT_RGB8)
	black.fill(Color.BLACK)
	sweep.canvas_picture.texture=ImageTexture.create_from_image(black)
	sweep.canvas_root.get_child(0).hide()
	for angle_value in [0.0,90.0]:
		sweep.set_parameter("u_angle_deg",angle_value)
		sweep.elapsed=1.5*0.35
		var start := brightness_center(await capture(sweep))
		sweep.elapsed=1.5*0.65
		var end := brightness_center(await capture(sweep))
		check((end.x-start.x>100.0 and absf(end.y-start.y)<3.0) if angle_value==0.0 else (end.y-start.y>80.0 and absf(end.x-start.x)<3.0),"sweep moves along %d degree direction" % angle_value,{"from":str(start),"to":str(end)})
	sweep.free()
	var water := make_stage(112)
	water.set_parameter("u_wave_height",0.0)
	check(water.water_height(Vector2(0.37,0.68))==0.0,"zero water height is flat on CPU")
	var flat := await capture(water,"112_flat")
	water.elapsed=2.7
	check(flat.get_data()==(await capture(water)).get_data(),"zero water height stops all visible surface motion")
	water.set_parameter("u_shallow_color",Color.RED)
	water.set_parameter("u_deep_color",Color.BLUE)
	await capture(water,"112_depth_colors")
	water.free()
	var hologram := make_stage(192)
	await capture(hologram,"192_local_lines_front")
	hologram.subject.rotation_degrees=Vector3(20,35,15)
	var rotated := await capture(hologram,"192_local_lines_rotated")
	check(difference(rotated,await capture(hologram))==0.0,"hologram local lines stable after model rotation")
	hologram.free()
	var glass := make_stage(96)
	glass.set_parameter("u_distortion",0.0)
	glass.set_parameter("u_color",Color.WHITE)
	glass.set_parameter("u_opacity",1.0)
	var straight := await capture(glass,"096_zero_distortion")
	glass.interaction_surface.hide()
	var background := await capture(glass)
	var error := 0.0
	for y in range(180,260,5):
		for x in range(280,360,5):
			var a:=straight.get_pixel(x,y)
			var b:=background.get_pixel(x,y)
			error=maxf(error,maxf(absf(a.r-b.r),maxf(absf(a.g-b.g),absf(a.b-b.b))))
	check(error<=2.0/255.0,"zero glass distortion samples background without offset",{"max_channel_error":error})
	glass.free()


func gaussian_lut_crt() -> void:
	var gaussian := make_stage(326)
	gaussian.size=Vector2i(129,129)
	var solid := Image.create(129,129,false,Image.FORMAT_RGB8)
	solid.fill(Color(0.3,0.6,0.8))
	fixture(gaussian,solid)
	gaussian.set_parameter("u_enabled",false)
	var original := await capture(gaussian)
	gaussian.set_parameter("u_enabled",true)
	for quality in [0,1,2]:
		gaussian.set_parameter("u_quality",quality)
		gaussian.set_parameter("u_radius_px",16.0)
		check(difference(original,await capture(gaussian))<1.0/255.0,"Gaussian quality %d preserves solid color" % quality)
	gaussian.set_parameter("u_radius_px",0.0)
	check(original.get_data()==(await capture(gaussian)).get_data(),"Gaussian radius zero is original")
	var impulse := Image.create(129,129,false,Image.FORMAT_RGB8)
	impulse.fill(Color.BLACK)
	impulse.set_pixel(64,64,Color.WHITE)
	fixture(gaussian,impulse)
	gaussian.set_parameter("u_radius_px",6.0)
	gaussian.set_parameter("u_quality",2)
	var blurred := await capture(gaussian,"326_impulse_two_pass")
	var weights := 0.0
	for i in range(-6,7): weights+=exp(-4.5*pow(i/6.0,2.0))
	var error := 0.0
	for y in range(-6,7):
		for x in range(-6,7):
			var expected := exp(-4.5*pow(x/6.0,2.0))*exp(-4.5*pow(y/6.0,2.0))/(weights*weights)
			error=maxf(error,absf(blurred.get_pixel(64+x,64+y).r-expected))
	check(blurred.get_pixel(66,66).r>0.0 and error<2.0/255.0,"Gaussian GPU impulse equals separable normalized CPU kernel",{"max_error":error})
	check(gaussian.player.materials.size()==2,"Gaussian binds both passes to player")
	gaussian.free()
	var lut := make_stage(317)
	var gradient := Image.create(640,480,false,Image.FORMAT_RGB8)
	for y in range(480):
		for x in range(640): gradient.set_pixel(x,y,Color(x/639.0,y/479.0,1.0 if y>240 else x/639.0))
	fixture(lut,gradient)
	lut.set_parameter("u_enabled",false)
	var source := await capture(lut)
	lut.set_parameter("u_enabled",true)
	lut.set_parameter("u_amount",0.0)
	check(source.get_data()==(await capture(lut)).get_data(),"LUT amount zero is original")
	lut.set_parameter("u_amount",1.0)
	lut.set_parameter("lut_texture","res://assets/neutral_lut.png")
	var neutral := await capture(lut,"317_neutral_gradient")
	var max_error := 0.0
	for y in range(0,480,3):
		for x in range(0,640,3):
			var d := source.get_pixel(x,y)-neutral.get_pixel(x,y)
			max_error=maxf(max_error,maxf(absf(d.r),maxf(absf(d.g),absf(d.b))))
	check(max_error<=1.0/255.0,"neutral LUT preserves gradient including blue=1",{"max_channel_error":max_error})
	lut.set_parameter("lut_texture","res://assets/warm_lut.png")
	var warm := await capture(lut,"317_warm_gradient")
	var expected := Color(minf(1.0,source.get_pixel(100,400).r*1.08+0.03),minf(1.0,source.get_pixel(100,400).g*0.98+0.015),0.87)
	var actual := warm.get_pixel(100,400)
	check(absf(actual.r-expected.r)<0.01 and absf(actual.g-expected.g)<0.01 and absf(actual.b-expected.b)<0.01,"warm LUT blue maximum stays in final slice",{"actual":str(actual),"expected":str(expected)})
	lut.free()
	var crt := make_stage(348)
	crt.set_parameter("u_enabled",false)
	var crt_original := await capture(crt)
	crt.set_parameter("u_enabled",true)
	for p: Dictionary in crt.entry["parameters"]: crt.set_parameter(p["key"],0.0)
	check(crt_original.get_data()==(await capture(crt)).get_data(),"CRT all zero restores original")
	crt.set_parameter("u_curvature",0.2)
	check((await capture(crt)).get_pixel(0,0)==Color.BLACK,"CRT curvature produces black outside boundary")
	crt.free()


func gui() -> void:
	var gallery = load("res://gallery.tscn").instantiate()
	root.add_child(gallery)
	root.size=Vector2i(1440,900)
	await process_frame
	for entry: Dictionary in catalog:
		if not entry.has("parameters"): continue
		gallery._show(entry)
		gallery.stage.set_process(false)
		for p: Dictionary in entry["parameters"]:
			var input: Control = gallery.parameter_controls[p["key"]]["input"]
			match p["type"]:
				"float": input.value=alternative(p,true)
				"color":
					input.color=Color.RED
					input.color_changed.emit(Color.RED)
				"bool": input.button_pressed=not p["default"]
				_: input.item_selected.emit(p["options"].size()-1)
			var expected: Variant=alternative(p,true)
			if p["type"]=="bool": expected=not p["default"]
			if p["type"]=="texture": expected=load(expected)
			check(gallery.stage.parameter_values[p["key"]]==expected,"GUI %03d %s sends edited value to material" % [entry["number"],p["key"]])
			if p["type"]=="float": check(gallery.parameter_controls[p["key"]]["slider"].value==input.value,"GUI numeric and slider stay synchronized")
		gallery._reset()
		check(gallery.pause_button.visible==entry["animated"],"GUI %03d playback only when animated" % entry["number"])
		for p: Dictionary in entry["parameters"]:
			var input: Control=gallery.parameter_controls[p["key"]]["input"]
			if p["type"]=="float": check(absf(input.value-float(p["default"]))<0.000000001,"GUI %03d %s reset restores numeric default" % [entry["number"],p["key"]],{"actual":input.value,"expected":p["default"]})
			elif p["type"]=="color": check(input.color==Color(p["default"]),"GUI reset restores color default")
			elif p["type"]=="bool": check(input.button_pressed==p["default"],"GUI reset restores bool default")
			else: check(p["options"][input.selected]["value"]==p["default"],"GUI reset restores selection default")
	gallery._show(catalog[2])
	check(gallery.parameter_controls.keys().size()==4 and gallery.parameter_controls.has("u_amount") and gallery.parameter_controls.has("u_scale") and gallery.parameter_controls.has("u_color") and gallery.parameter_controls.has("u_speed"),"unrefined effect retains all basic controls")
	gallery.parameter_controls["u_scale"]["input"].value=1.7
	check(absf(gallery.stage.shader_material.get_shader_parameter("u_scale")-1.7)<0.00001,"basic scale control still binds")
	gallery._show(catalog[6])
	gallery.items.select(6)
	await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png(OUTPUT.path_join("gallery_parameters.png"))
	gallery.search.text="no-result-m3-test"
	gallery._filter()
	check(gallery.current.is_empty() and gallery.stage.get_child_count()==0,"zero search results clear previous preview")
	gallery.free()


func _run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUTPUT))
	catalog=JSON.parse_string(FileAccess.get_file_as_string("res://catalog.json"))
	for entry: Dictionary in catalog:
		if not entry.has("parameters"): continue
		var stage := make_stage(entry["number"])
		await parameters(stage)
		stage.free()
	await endpoints()
	await sprite_edges()
	await motion_and_surfaces()
	await gaussian_lut_crt()
	await gui()
	var failures := checks.filter(func(c): return not c["passed"]).size()
	var report := {"engine":Engine.get_version_info(),"adapter":RenderingServer.get_video_adapter_name(),"checks":checks,"captures":captures,"failures":failures,"render_size":[640,480]}
	var hashes := {}
	for entry: Dictionary in catalog:
		if entry.has("parameters"): hashes[entry["shader"]]=FileAccess.get_sha256(entry["shader"])
	for path in ["res://shared/stage.gd","res://shared/gallery.gd","res://shared/effect_player.gd","res://tools/test_m3.gd","res://tools/effect_profiles.py","res://catalog.json","res://assets/neutral_lut.png","res://assets/warm_lut.png","res://assets/subject.svg","res://assets/cottage.png"]: hashes[path]=FileAccess.get_sha256(path)
	report["source_sha256"]=hashes
	FileAccess.open(OUTPUT.path_join("report.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"\t"))
	print("M3_COMPLETE checks=%d failures=%d captures=%d" % [checks.size(),failures,captures.size()])
	quit(0 if failures==0 else 1)
