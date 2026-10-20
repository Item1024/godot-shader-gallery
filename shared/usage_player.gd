extends Node

# A small scene adapter. It owns no gallery, metadata or scene-building logic.
const EffectPlayer = preload("res://shared/effect_player.gd")
const SurfaceHit = preload("res://shared/surface_hit.gd")

@export var material_targets: Array[NodePath] = []
@export var camera_path: NodePath
@export_enum("none", "flash", "water", "shield") var interaction := "none"

var player = EffectPlayer.new()
var materials: Array[ShaderMaterial] = []
var defaults: Array[Dictionary] = []
var camera: Camera3D
var target: Node
var orbit := 0.0
var elevation := 0.28
var distance := 5.0
var _pointer_down := false
var _dragging := false
var _press_position := Vector2.ZERO
var _last_pointer := Vector2.ZERO


func _ready() -> void:
	for path in material_targets:
		var node := get_node(path)
		if target == null: target = node
		var material: ShaderMaterial = node.material_override if node is MeshInstance3D else node.material
		materials.append(material)
		var values := {}
		for uniform: Dictionary in material.shader.get_shader_uniform_list():
			var value: Variant = material.get_shader_parameter(uniform["name"])
			if value != null: values[uniform["name"]] = value
		defaults.append(values)
	player.bind_materials(materials)
	if not camera_path.is_empty(): camera = get_node(camera_path)
	get_window().focus_exited.connect(cancel_pointer)


func _process(delta: float) -> void:
	player.advance(delta)


func set_parameter(key: String, value: Variant) -> void:
	for material in materials:
		material.set_shader_parameter(key, value)


func reset() -> void:
	for index in range(materials.size()):
		for key in defaults[index]:
			materials[index].set_shader_parameter(key, defaults[index][key])
	player.reset()
	cancel_pointer()


func play_once() -> void:
	if interaction == "flash" and materials[0].get_shader_parameter("u_enabled"):
		player.trigger_event()


func surface_hit(pixel: Vector2) -> Dictionary:
	var material := materials[0]
	return SurfaceHit.solve(camera, target as MeshInstance3D, pixel, player.effect_time, float(material.get_shader_parameter("u_wave_height")) if interaction == "water" else 0.0, 1.0)


func trigger_at(pixel: Vector2) -> bool:
	if not materials[0].get_shader_parameter("u_enabled") or not get_viewport().get_visible_rect().has_point(pixel):
		return false
	if interaction in ["water", "shield"]:
		var hit := surface_hit(pixel)
		if hit.is_empty(): return false
		set_parameter("u_hit_position", hit["local_position"])
		player.trigger_event()
		return true
	if interaction == "flash" and target.get_rect().has_point(target.get_global_transform_with_canvas().affine_inverse()*pixel):
		play_once()
		return true
	return false


func cancel_pointer() -> void:
	_pointer_down = false
	_dragging = false


func _position_camera() -> void:
	if camera:
		camera.position = Vector3(sin(orbit)*distance, distance*elevation+0.6, cos(orbit)*distance)
		camera.look_at(camera.get_parent().to_global(Vector3(0, -0.05, 0)))


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed:
				_pointer_down = true
				_dragging = false
				_press_position = event.position
				_last_pointer = event.position
			else:
				if _pointer_down and not _dragging and event.position.distance_to(_press_position)<=4.0:
					trigger_at(event.position)
				cancel_pointer()
		elif event.pressed and camera:
			if event.button_index == MOUSE_BUTTON_WHEEL_UP: distance=maxf(3.2,distance-0.3)
			elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN: distance=minf(9.0,distance+0.3)
			cancel_pointer()
			_position_camera()
	elif event is InputEventMouseMotion and _pointer_down:
		if not event.button_mask & MOUSE_BUTTON_MASK_LEFT:
			cancel_pointer()
			return
		if event.position.distance_to(_press_position)>4.0: _dragging=true
		if _dragging and camera:
			var movement: Vector2 = event.position-_last_pointer
			orbit-=movement.x*0.008
			elevation=clampf(elevation+movement.y*0.003,-0.05,1.0)
			_position_camera()
		_last_pointer=event.position
