extends RefCounted

# The owner advances this clock, so gallery previews and standalone scenes share
# the same pause/speed/seek behavior without relying on the engine's global TIME.
var materials: Array[ShaderMaterial] = []
var effect_time := 0.0
var playback_speed := 1.0
var paused := false
var event_time := -1.0


func bind_materials(values: Array[ShaderMaterial]) -> void:
	materials = values.duplicate()
	_write_time()
	_write_event()


func advance(delta: float) -> void:
	if not paused and playback_speed != 0.0:
		seek(effect_time + delta * playback_speed)


func seek(seconds: float) -> void:
	effect_time = maxf(0.0, seconds)
	_write_time()


func trigger_event() -> void:
	event_time = effect_time
	_write_event()


func reset() -> void:
	effect_time = 0.0
	playback_speed = 1.0
	paused = false
	event_time = -1.0
	_write_time()
	_write_event()


func _write_time() -> void:
	for material in materials:
		material.set_shader_parameter("u_time", effect_time)
		# Existing effects multiply these uniforms; speed is already in the clock.
		material.set_shader_parameter("u_speed", 1.0)


func _write_event() -> void:
	for material in materials:
		material.set_shader_parameter("u_event_time", event_time)
