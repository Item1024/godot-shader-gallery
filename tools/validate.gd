extends SceneTree


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var catalog: Array = JSON.parse_string(FileAccess.get_file_as_string("res://catalog.json"))
	var categories: Array = JSON.parse_string(FileAccess.get_file_as_string("res://categories.json"))
	var seen: Dictionary = {}
	var failures: Array[String] = []
	var profiles := 0
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
		if entry.has("parameters"):
			profiles += 1
			for file in ["material.tres", "usage.tscn", "dependencies.json"]:
				if not FileAccess.file_exists(path.path_join(file)): failures.append(path+" missing M4 "+file)
			var dependencies: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(path.path_join("dependencies.json")))
			for dependency: String in dependencies.get("files", []):
				if not dependency.begins_with("res://") or ".." in dependency or not FileAccess.file_exists(dependency): failures.append(path+" invalid/missing dependency "+dependency)
				if dependency in ["res://catalog.json", "res://shared/stage.gd", "res://shared/gallery.gd", "res://shared/standalone.gd"]: failures.append(path+" contains gallery dependency")
			if load(path.path_join("usage.tscn")) == null: failures.append(path+" usage scene failed to load")
			var preset: ShaderMaterial = load(path.path_join("material.tres"))
			if preset == null or not preset.resource_local_to_scene: failures.append(path+" missing/ non-local material preset")
			var uniforms := {}
			for uniform: Dictionary in shader.get_shader_uniform_list(): uniforms[uniform["name"]]=uniform
			var keys := {}
			for p: Dictionary in entry["parameters"]:
				var key: String = p.get("key", "")
				if key.is_empty() or keys.has(key) or not uniforms.has(key): failures.append(path+" invalid/duplicate uniform "+key)
				keys[key]=true
				var expected: Variant = p["default"]
				if p["type"]=="color": expected=Color(expected)
				if p["type"]=="texture": expected=load(expected)
				if preset != null and preset.get_shader_parameter(key)!=expected: failures.append(path+" preset default differs: "+key)
				for field in ["label","type","target","default","unit","help","advanced"]:
					if not p.has(field): failures.append(path+" parameter missing "+field)
				if p.get("target")!="material" or key=="u_speed": failures.append(path+" invalid parameter target")
				match p.get("type"):
					"float":
						if not (p["min"]<=p["default"] and p["default"]<=p["max"] and p["step"]>0): failures.append(path+" invalid numeric bounds")
						if uniforms.has(key) and uniforms[key]["type"]!=TYPE_FLOAT: failures.append(path+" wrong float uniform type")
					"color":
						if not Color.html_is_valid(p["default"]): failures.append(path+" invalid color")
					"bool":
						if not p["default"] is bool: failures.append(path+" invalid bool")
					"enum", "texture":
						var values: Array=[]
						for option: Dictionary in p["options"]:
							values.append(option["value"])
							if p["type"]=="texture" and not ResourceLoader.exists(option["value"]): failures.append(path+" missing LUT")
						if p["default"] not in values: failures.append(path+" missing default choice")
					_: failures.append(path+" unsupported parameter type")
		var scene: PackedScene = load(entry["scene"])
		if scene == null:
			failures.append("Scene failed to load: " + entry["scene"])
		if bool(entry["approximation"]) and "演示近似" not in entry["implementation"]:
			failures.append("Approximation not labeled: " + entry["name"])
	var main_scene: PackedScene = load("res://gallery.tscn")
	if profiles!=20: failures.append("Expected exactly twenty parameter profiles")
	if main_scene == null:
		failures.append("Gallery scene failed to load")
	print("VALIDATION effects=%d categories=%d failures=%d" % [catalog.size(), categories.size(), failures.size()])
	for failure in failures:
		push_error(failure)
	quit(0 if failures.is_empty() else 1)
