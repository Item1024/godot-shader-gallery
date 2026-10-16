extends SceneTree


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var catalog: Array = JSON.parse_string(FileAccess.get_file_as_string("res://catalog.json"))
	var categories: Array = JSON.parse_string(FileAccess.get_file_as_string("res://categories.json"))
	var seen: Dictionary = {}
	var failures: Array[String] = []
	if categories.size() != 23:
		failures.append("Expected all 23 categories")
	for entry: Dictionary in catalog:
		var path: String = entry["directory"]
		if seen.has(path):
			failures.append("Duplicate directory: " + path)
		seen[path] = true
		for file in ["effect.gdshader", "demo.tscn", "metadata.json", "README.md"]:
			if not FileAccess.file_exists(path.path_join(file)):
				failures.append("Missing " + path.path_join(file))
		var shader: Shader = load(entry["shader"])
		if shader == null or shader.get_shader_uniform_list().is_empty():
			failures.append("Shader failed to compile: " + entry["shader"])
		var scene: PackedScene = load(entry["scene"])
		if scene == null:
			failures.append("Scene failed to load: " + entry["scene"])
		if bool(entry["approximation"]) and "演示近似" not in entry["implementation"]:
			failures.append("Approximation not labeled: " + entry["name"])
	var main_scene: PackedScene = load("res://gallery.tscn")
	if main_scene == null:
		failures.append("Gallery scene failed to load")
	print("VALIDATION effects=%d categories=%d failures=%d" % [catalog.size(), categories.size(), failures.size()])
	for failure in failures:
		push_error(failure)
	quit(0 if failures.is_empty() else 1)
