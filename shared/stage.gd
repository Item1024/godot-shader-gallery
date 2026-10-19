extends SubViewport

const EffectPlayer = preload("res://shared/effect_player.gd")

var entry: Dictionary = {}
var shader_material: ShaderMaterial
var environment: Environment
var subject: Node3D
var camera: Camera3D
var player = EffectPlayer.new()
var elapsed: float:
	get: return player.effect_time
	set(value): player.seek(value)
var paused: bool:
	get: return player.paused
	set(value): player.paused = value
var enabled := true
var amount := 0.55
var speed: float:
	get: return player.playback_speed
	set(value): player.playback_speed = value
var scale_value := 1.0
var orbit := 0.0
var elevation := 0.28
var distance := 5.0
var canvas_root: Control
var canvas_picture: TextureRect
var interaction_surface: MeshInstance3D
var parameter_values: Dictionary = {}
var uniform_names: Dictionary = {}
var vertical_material: ShaderMaterial
var _pointer_down := false
var _dragging := false
var _press_position := Vector2.ZERO
var _last_pointer := Vector2.ZERO


func _init() -> void:
	size = Vector2i(900, 660)
	own_world_3d = true
	render_target_update_mode = SubViewport.UPDATE_ALWAYS
	handle_input_locally = false
	transparent_bg = false


func _ready() -> void:
	get_window().focus_exited.connect(cancel_pointer)
	if get_parent() is SubViewportContainer:
		get_parent().visibility_changed.connect(cancel_pointer)


func configure(data: Dictionary) -> void:
	player.bind_materials([])
	for child in get_children():
		child.free()
	entry = data
	parameter_values.clear()
	uniform_names.clear()
	vertical_material = null
	player.reset()
	cancel_pointer()
	orbit = 0.0
	amount = float(data.get("amount", 0.55))
	scale_value = 1.0
	enabled = true
	subject = null
	camera = null
	environment = null
	canvas_picture = null
	interaction_surface = null
	shader_material = ShaderMaterial.new()
	shader_material.shader = load(str(data["shader"]))
	for uniform: Dictionary in shader_material.shader.get_shader_uniform_list():
		uniform_names[str(uniform["name"])] = true
	player.bind_materials([shader_material])
	if data["category_slug"] == "vertex" and data["slug"] == "vat":
		shader_material.set_shader_parameter("vat_texture", load("res://assets/vat.png"))
	if data["category_slug"] == "color" and data["slug"] == "lut":
		shader_material.set_shader_parameter("lut_texture", load("res://assets/warm_lut.png"))
	if data["category_slug"] == "transition":
		shader_material.set_shader_parameter("destination_texture", load("res://assets/destination.svg"))
	_set_uniforms()
	var kind: String = data["kind"]
	if kind in ["spatial", "pipeline", "depth"]:
		_build_3d()
	else:
		_build_canvas(kind)


func _set_uniforms() -> void:
	if shader_material == null:
		return
	shader_material.set_shader_parameter("u_amount", amount)
	shader_material.set_shader_parameter("u_scale", scale_value)
	shader_material.set_shader_parameter("u_enabled", enabled)
	shader_material.set_shader_parameter("u_color", Color("#55e8bb"))
	if vertical_material:
		vertical_material.set_shader_parameter("u_enabled", enabled)
	for parameter: Dictionary in entry.get("parameters", []):
		set_parameter(parameter["key"], parameter["default"])


func _build_canvas(kind: String) -> void:
	canvas_root = Control.new()
	canvas_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	canvas_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(canvas_root)
	var backdrop := ColorRect.new()
	backdrop.color = Color("#0a1220")
	backdrop.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	canvas_root.add_child(backdrop)
	if kind == "post":
		var picture := TextureRect.new()
		picture.texture = load("res://assets/cottage.png")
		picture.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		picture.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		picture.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		canvas_root.add_child(picture)
		var effect := ColorRect.new()
		effect.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		effect.material = shader_material
		effect.mouse_filter = Control.MOUSE_FILTER_IGNORE
		canvas_root.add_child(effect)
		if entry.get("category_slug") == "lens" and entry.get("slug") == "gaussian":
			# The second screen sampler must see the completed horizontal pass.
			var copy := BackBufferCopy.new()
			copy.copy_mode = BackBufferCopy.COPY_MODE_VIEWPORT
			canvas_root.add_child(copy)
			vertical_material = shader_material.duplicate() as ShaderMaterial
			vertical_material.set_shader_parameter("u_vertical", true)
			var vertical := ColorRect.new()
			vertical.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
			vertical.material = vertical_material
			vertical.mouse_filter = Control.MOUSE_FILTER_IGNORE
			canvas_root.add_child(vertical)
			player.bind_materials([shader_material, vertical_material])
	else:
		var picture := TextureRect.new()
		canvas_picture = picture
		picture.texture = load("res://assets/lettering.svg" if entry.get("text", false) else "res://assets/subject.svg")
		picture.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		picture.stretch_mode = TextureRect.STRETCH_SCALE
		picture.material = shader_material
		picture.mouse_filter = Control.MOUSE_FILTER_IGNORE
		picture.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		if kind == "sprite":
			picture.anchor_left = 0.13
			picture.anchor_top = 0.12
			picture.anchor_right = 0.87
			picture.anchor_bottom = 0.88
		canvas_root.add_child(picture)


func _surface(color: Color, roughness: float = 0.5) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = roughness
	return material


func _mesh(parent: Node, geometry: Mesh, position_value: Vector3, material: Material) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.mesh = geometry
	instance.position = position_value
	instance.material_override = material
	parent.add_child(instance)
	return instance


func _colored_mesh(geometry: Mesh) -> ArrayMesh:
	var arrays := geometry.surface_get_arrays(0)
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
	var uvs: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	var tool := SurfaceTool.new()
	tool.begin(Mesh.PRIMITIVE_TRIANGLES)
	for index in range(indices.size()):
		var source := indices[index]
		var color := Color(uvs[source].x, uvs[source].y, 1.0 - uvs[source].x)
		if entry.get("barycentric", false):
			color = [Color.RED, Color.GREEN, Color.BLUE][index % 3]
		tool.set_color(color)
		tool.set_normal(normals[source])
		tool.set_uv(uvs[source])
		tool.add_vertex(vertices[source])
	tool.generate_tangents()
	return tool.commit()


func _build_3d() -> void:
	var world := Node3D.new()
	add_child(world)
	var world_environment := WorldEnvironment.new()
	environment = Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color("#101c2d")
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("#91abc5")
	environment.ambient_light_energy = 0.55
	environment.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	var sky := Sky.new()
	var sky_material := ProceduralSkyMaterial.new()
	sky_material.sky_top_color = Color("#203e62")
	sky_material.sky_horizon_color = Color("#9ab4bd")
	sky_material.ground_bottom_color = Color("#142435")
	sky_material.ground_horizon_color = Color("#85999e")
	sky.sky_material = sky_material
	environment.sky = sky
	world_environment.environment = environment
	world.add_child(world_environment)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-42, -32, 0)
	sun.light_color = Color("#ffe5bd")
	sun.light_energy = 1.5
	sun.shadow_enabled = true
	world.add_child(sun)
	var fill := OmniLight3D.new()
	fill.position = Vector3(-2, 2.5, 2)
	fill.light_color = Color("#58b5ff")
	fill.light_energy = 3.5
	fill.omni_range = 8.0
	world.add_child(fill)
	var floor_mesh := PlaneMesh.new()
	floor_mesh.size = Vector2(20, 20)
	_mesh(world, floor_mesh, Vector3(0, -1.05, 0), _surface(Color("#172b3d"), 0.22))
	subject = Node3D.new()
	world.add_child(subject)
	var shape: String = entry.get("shape", "sphere")
	if shape == "quad":
		var quad := QuadMesh.new()
		quad.size = Vector2(2, 2)
		_mesh(subject, quad, Vector3.ZERO, shader_material)
	elif shape == "cube":
		var cube := BoxMesh.new()
		cube.size = Vector3(1.55, 1.55, 1.55)
		cube.subdivide_width = 16
		cube.subdivide_height = 16
		cube.subdivide_depth = 16
		_mesh(subject, cube, Vector3.ZERO, shader_material)
	elif shape in ["plane", "cloth"]:
		var plane := PlaneMesh.new()
		plane.size = Vector2(3.6, 3.1)
		plane.subdivide_width = 70
		plane.subdivide_depth = 70
		var surface := _mesh(subject, _colored_mesh(plane) if entry.get("vertex_colors", false) else plane, Vector3.ZERO, shader_material)
		interaction_surface = surface
		if shape == "cloth":
			surface.rotation_degrees.x = 80
	else:
		var sphere := SphereMesh.new()
		sphere.radius = 0.92
		sphere.height = 1.84
		sphere.radial_segments = 64
		sphere.rings = 40
		interaction_surface = _mesh(subject, _colored_mesh(sphere) if entry.get("vertex_colors", false) else sphere, Vector3(0, 0.10, 0), shader_material)
		var torus := TorusMesh.new()
		torus.inner_radius = 0.19
		torus.outer_radius = 0.34
		torus.rings = 40
		torus.ring_segments = 20
		var ring := _mesh(world, torus, Vector3(-1.48, -0.58, 0.45), _surface(Color("#e7b772"), 0.23))
		ring.rotation_degrees = Vector3(65, 15, 10)
		var cube := BoxMesh.new()
		cube.size = Vector3(0.68, 0.68, 0.68)
		var block := _mesh(world, cube, Vector3(1.4, -0.69, -0.4), _surface(Color("#5bc9bc"), 0.35))
		block.rotation_degrees.y = 25
		for index in range(4):
			var post := BoxMesh.new()
			post.size = Vector3(0.34, 0.50 + index * 0.26, 0.34)
			_mesh(world, post, Vector3(-1.6 + index * 0.85, -0.75 + index * 0.13, -2.1), _surface(Color("#8d99bc")))
	if entry.get("rocks", false):
		for index in range(4):
			var rock := SphereMesh.new()
			rock.radius = 0.32 + index * 0.035
			rock.height = 0.7
			_mesh(world, rock, Vector3(-1.3 + index * 0.85, -0.2, -0.5), _surface(Color("#8e9c99"), 0.8))
	if entry.get("occluder", false):
		var wall := BoxMesh.new()
		wall.size = Vector3(2.4, 1.15, 0.16)
		_mesh(world, wall, Vector3(0.15, -0.25, 0.8), _surface(Color("#354b68"), 0.7))
	if entry.get("reflection_probes", false):
		for index in range(2):
			var probe := ReflectionProbe.new()
			probe.position = Vector3(-0.8 + index * 1.6, 0, 0)
			probe.size = Vector3(4, 4, 4)
			probe.box_projection = true
			probe.intensity = 0.7 + index * 0.5
			world.add_child(probe)
	if entry.get("fog_volume", false):
		var volume := FogVolume.new()
		volume.size = Vector3(2.5, 2.0, 2.0)
		var fog_material := FogMaterial.new()
		fog_material.density = 0.7
		fog_material.albedo = Color("#8bc9c1")
		volume.material = fog_material
		world.add_child(volume)
	if entry.get("soft_shadow", false):
		sun.light_angular_distance = 2.5
	var pedestal := CylinderMesh.new()
	pedestal.top_radius = 1.16
	pedestal.bottom_radius = 1.25
	pedestal.height = 0.16
	_mesh(world, pedestal, Vector3(0, -0.97, 0), _surface(Color("#263e52"), 0.5))
	camera = Camera3D.new()
	camera.current = true
	camera.fov = 43
	camera.near = 0.05
	world.add_child(camera)
	_position_camera()
	if entry["kind"] == "depth":
		var quad := QuadMesh.new()
		quad.size = Vector2(2, 2)
		var screen := _mesh(camera, quad, Vector3.ZERO, shader_material)
		screen.extra_cull_margin = 100
		shader_material.render_priority = 127
		for instance in subject.get_children():
			if instance is MeshInstance3D:
				instance.material_override = _surface(Color("#6c9d96"))
	if entry.get("object_ids", false):
		var id_index := 1
		for instance in world.find_children("*", "MeshInstance3D", true, false):
			instance.material_override = shader_material
			instance.set_instance_shader_parameter("instance_id", float(id_index))
			id_index += 1
	_apply_pipeline()


func _apply_pipeline() -> void:
	if environment == null or entry.get("kind", "") != "pipeline":
		return
	for property_name in ["ssao_enabled", "ssil_enabled", "ssr_enabled", "glow_enabled", "fog_enabled", "volumetric_fog_enabled"]:
		environment.set(property_name, false)
	if not enabled:
		return
	var properties: Dictionary = entry.get("environment", {})
	for property_name in properties:
		var value: Variant = properties[property_name]
		if value is Array and value.size() == 4:
			value = Color(value[0], value[1], value[2], value[3])
		environment.set(property_name, value)
	if properties.has("glow_enabled"):
		environment.glow_intensity = 0.3 + amount * 2.0
	if properties.has("fog_enabled"):
		environment.fog_density = amount * 0.12
	if properties.has("ssao_enabled"):
		environment.ssao_intensity = amount * 4.0
	if properties.has("volumetric_fog_enabled"):
		environment.volumetric_fog_density = amount * 0.12


func _position_camera() -> void:
	if camera:
		camera.position = Vector3(sin(orbit) * distance, distance * elevation + 0.6, cos(orbit) * distance)
		camera.look_at(Vector3(0, -0.05, 0))


func set_parameter(key: String, value: Variant) -> bool:
	if key == "u_speed":
		if not (value is float or value is int) or not is_finite(float(value)) or float(value) < 0.0 or float(value) > 3.0:
			return false
		speed = float(value)
		return true
	if entry.has("parameters"):
		var specification: Dictionary = {}
		for parameter: Dictionary in entry["parameters"]:
			if parameter["key"] == key:
				specification = parameter
				break
		if not specification.is_empty():
			match specification["type"]:
				"float":
					if not (value is float or value is int) or not is_finite(float(value)) or float(value) < float(specification["min"]) or float(value) > float(specification["max"]):
						return false
					value = float(value)
				"bool":
					if not value is bool: return false
				"color":
					if value is String and Color.html_is_valid(value): value = Color(value)
					if not value is Color: return false
				"enum", "texture":
					var valid := false
					for option: Dictionary in specification["options"]:
						if option["value"] == value: valid = true
					if not valid: return false
					value = load(value) if specification["type"] == "texture" else int(value)
		elif key not in ["u_enabled", "u_mouse", "u_hit_position"]:
			return false
		if not uniform_names.has(key): return false
		parameter_values[key] = value
	match key:
		"u_amount": amount = float(value)
		"u_scale": scale_value = float(value)
		"u_enabled": enabled = bool(value)
	for material: ShaderMaterial in player.materials:
		material.set_shader_parameter(key, value)
	_apply_pipeline()
	return true


func play_once() -> void:
	if enabled and entry.get("action", "") == "播放一次":
		player.trigger_event()


func reset() -> void:
	player.reset()
	cancel_pointer()
	amount = float(entry.get("amount", 0.55))
	scale_value = 1.0
	enabled = true
	_set_uniforms()
	shader_material.set_shader_parameter("u_mouse", Vector2(0.5, 0.5))


func cancel_pointer() -> void:
	_pointer_down = false
	_dragging = false


func viewport_position(control_position: Vector2) -> Vector2:
	var container := get_parent() as SubViewportContainer
	if container != null and container.stretch:
		return control_position * Vector2(size) / container.size
	return control_position


func orbit_input(event: InputEvent) -> void:
	# gui_input positions are local to the container; the 4 px threshold stays
	# in UI units even when stretch_shrink reduces the actual render resolution.
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed:
				_pointer_down = true
				_dragging = false
				_press_position = event.position
				_last_pointer = event.position
			else:
				if _pointer_down and not _dragging and event.position.distance_to(_press_position) <= 4.0:
					trigger_at(viewport_position(event.position))
				cancel_pointer()
		elif event.pressed and camera != null:
			if event.button_index == MOUSE_BUTTON_WHEEL_UP:
				distance = maxf(3.2, distance - 0.3)
			elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
				distance = minf(9.0, distance + 0.3)
			cancel_pointer()
			_position_camera()
	elif event is InputEventMouseMotion and _pointer_down:
		if not event.button_mask & MOUSE_BUTTON_MASK_LEFT:
			cancel_pointer()
			return
		if not _dragging and event.position.distance_to(_press_position) > 4.0:
			_dragging = true
		if _dragging and camera != null:
			var movement: Vector2 = event.position - _last_pointer
			orbit -= movement.x * 0.008
			elevation = clampf(elevation + movement.y * 0.003, -0.05, 1.0)
			_position_camera()
		_last_pointer = event.position


func trigger_at(pixel: Vector2) -> bool:
	if not enabled or not Rect2(Vector2.ZERO, Vector2(size)).has_point(pixel):
		return false
	if entry.get("category_slug") == "water" and entry.get("slug") == "interactive" or entry.get("category_slug") == "magic" and entry.get("slug") == "shield_hit":
		var hit := surface_hit(pixel)
		if hit.is_empty():
			return false
		shader_material.set_shader_parameter("u_hit_position", hit["local_position"])
		player.trigger_event()
	else:
		var region := Rect2(Vector2.ZERO, Vector2(size))
		if canvas_picture != null:
			region = canvas_picture.get_global_rect()
		if not region.has_point(pixel):
			return false
		set_parameter("u_mouse", (pixel - region.position) / region.size)
		play_once()
	return true


func water_height(point: Vector2) -> float:
	if not enabled:
		return 0.0
	var k := TAU / float(parameter_values.get("u_wave_length", 1.0))
	return (sin(point.x * k + elapsed * 1.4) + sin(point.y * k - elapsed * 1.1) * 0.5) * float(parameter_values.get("u_wave_height", 0.04)) / 1.5


func _water_gradient(point: Vector2) -> Vector2:
	var k := TAU / float(parameter_values.get("u_wave_length", 1.0))
	return Vector2(cos(point.x * k + elapsed * 1.4) * k, cos(point.y * k - elapsed * 1.1) * k * 0.5) * float(parameter_values.get("u_wave_height", 0.04)) / 1.5


func surface_hit(pixel: Vector2) -> Dictionary:
	if camera == null or interaction_surface == null:
		return {}
	var inverse := interaction_surface.global_transform.affine_inverse()
	var origin := inverse * camera.project_ray_origin(pixel)
	var direction := (inverse.basis * camera.project_ray_normal(pixel)).normalized()
	var travel: float
	if interaction_surface.mesh is PlaneMesh:
		if absf(direction.y) < 0.00001:
			return {}
		travel = -origin.y / direction.y
		# Bracket the nearest crossing inside the finite wave volume before
		# Newton refinement. Steep waves can otherwise send Newton off-plane.
		var height := float(parameter_values.get("u_wave_height", 0.04)) if enabled else 0.0
		var extent: Vector2 = interaction_surface.mesh.size * 0.5
		var low := maxf(0.0, minf((-height-origin.y)/direction.y, (height-origin.y)/direction.y))
		var high := maxf((-height-origin.y)/direction.y, (height-origin.y)/direction.y)
		for axis in [0, 2]:
			var bound: float = extent.x if axis==0 else extent.y
			if absf(direction[axis])<0.00001:
				if absf(origin[axis])>bound: return {}
			else:
				var a: float = (-bound-origin[axis])/direction[axis]
				var b: float = (bound-origin[axis])/direction[axis]
				low=maxf(low,minf(a,b))
				high=minf(high,maxf(a,b))
		if high<low: return {}
		var start := origin+direction*low
		var residual_low := start.y-water_height(Vector2(start.x,start.z))
		var samples := maxi(1, int(ceil((high-low)*Vector2(direction.x,direction.z).length()*16.0/float(parameter_values.get("u_wave_length",1.0)))))
		var previous := low
		var found := false
		for sample in range(1,samples+1):
			var next := lerpf(low,high,float(sample)/samples)
			var point := origin+direction*next
			var residual := point.y-water_height(Vector2(point.x,point.z))
			if residual_low*residual<=0.0:
				low=previous
				high=next
				found=true
				break
			previous=next
			residual_low=residual
		if not found: return {}
		travel=clampf(travel,low,high)
		for iteration in range(8):
			var point := origin + direction * travel
			var residual := point.y - water_height(Vector2(point.x, point.z))
			if absf(residual) <= 0.00001:
				break
			if residual*residual_low>0.0:
				low=travel
				residual_low=residual
			else:
				high=travel
			var gradient := _water_gradient(Vector2(point.x, point.z))
			var slope := direction.y - gradient.dot(Vector2(direction.x, direction.z))
			var candidate := travel-residual/slope if absf(slope)>=0.00001 else INF
			travel=candidate if candidate>low and candidate<high else (low+high)*0.5
		var point := origin + direction * travel
		if absf(point.x) > extent.x or absf(point.z) > extent.y or absf(point.y - water_height(Vector2(point.x, point.z))) > 0.001:
			return {}
	elif interaction_surface.mesh is SphereMesh:
		var radius: float = interaction_surface.mesh.radius
		var projected := origin.dot(direction)
		var discriminant := projected * projected - (origin.length_squared() - radius * radius)
		if discriminant < 0.0:
			return {}
		travel = -projected - sqrt(discriminant)
		if travel <= 0.0:
			travel = -projected + sqrt(discriminant)
	else:
		return {}
	if travel <= 0.0:
		return {}
	var local_position := origin + direction * travel
	return {"local_position": local_position, "world_position": interaction_surface.to_global(local_position)}


func _process(delta: float) -> void:
	player.advance(delta)
