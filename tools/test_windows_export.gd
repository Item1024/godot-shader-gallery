extends SceneTree


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var manifest := ""
	var output := ""
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--manifest="): manifest = argument.trim_prefix("--manifest=")
		elif argument.begins_with("--output="): output = argument.trim_prefix("--output=")
	var expected: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(manifest))
	var failures: Array = []
	for path: String in expected:
		if FileAccess.get_sha256("res://" + path) != expected[path]: failures.append(path)
	var catalog: Array = JSON.parse_string(FileAccess.get_file_as_string("res://catalog.json"))
	for entry: Dictionary in catalog:
		if not ResourceLoader.exists(entry["shader"]) or not ResourceLoader.exists(entry["scene"]): failures.append(entry["directory"])
	for path in ["res://tests/visual/reference/capture.json", "res://tools/build_library.py", "res://artifacts/m5/capture-final/capture.json"]:
		if FileAccess.file_exists(path): failures.append("Unexpected packaged development file: " + path)
	DirAccess.make_dir_recursive_absolute(output)
	var report := {"engine": Engine.get_version_info()["string"], "executable": OS.get_executable_path(),
		"catalog_count": catalog.size(), "raw_file_checks": expected.size(), "failures": failures}
	FileAccess.open(output.path_join("resources.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"\t") + "\n")
	FileAccess.open(output.path_join("GODOT_LICENSE.txt"),FileAccess.WRITE).store_string(Engine.get_license_text())
	var notices := "Godot third-party copyright information\n\n" + JSON.stringify(Engine.get_copyright_info(),"\t") + "\n\n"
	var licenses: Dictionary = Engine.get_license_info()
	for name: String in licenses: notices += name + "\n" + str(licenses[name]) + "\n\n"
	FileAccess.open(output.path_join("THIRD_PARTY_NOTICES.txt"),FileAccess.WRITE).store_string(notices)
	print("WINDOWS_RESOURCES effects=%d raw_files=%d failures=%d" % [catalog.size(), expected.size(), failures.size()])
	quit(1 if not failures.is_empty() or catalog.size() != 421 else 0)
