extends SceneTree

func _initialize() -> void:
	for name in ClassDB.class_get_integer_constant_list("Environment"):
		if "REFLECT" in name:
			print("CONSTANT ", name, "=", ClassDB.class_get_integer_constant("Environment", name))
	for property: Dictionary in ClassDB.class_get_property_list("Environment"):
		if "fog" in property["name"]:
			print("PROPERTY ", property["name"])
	quit()
