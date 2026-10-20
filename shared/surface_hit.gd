extends RefCounted

# Shared by the gallery and the minimal usage scenes. These formulas match the
# refined water shader; the solver is limited to PlaneMesh and SphereMesh.
static func water_height(point: Vector2, time: float, height: float, wavelength: float) -> float:
	var k := TAU / wavelength
	return (sin(point.x*k+time*1.4)+sin(point.y*k-time*1.1)*0.5)*height/1.5


static func water_gradient(point: Vector2, time: float, height: float, wavelength: float) -> Vector2:
	var k := TAU / wavelength
	return Vector2(cos(point.x*k+time*1.4)*k, cos(point.y*k-time*1.1)*k*0.5)*height/1.5


static func solve(camera: Camera3D, surface: MeshInstance3D, pixel: Vector2, time: float, height: float = 0.04, wavelength: float = 1.0) -> Dictionary:
	if camera == null or surface == null:
		return {}
	var inverse := surface.global_transform.affine_inverse()
	var origin := inverse * camera.project_ray_origin(pixel)
	var direction := (inverse.basis * camera.project_ray_normal(pixel)).normalized()
	var travel: float
	if surface.mesh is PlaneMesh:
		if absf(direction.y) < 0.00001:
			return {}
		travel = -origin.y / direction.y
		var extent: Vector2 = surface.mesh.size * 0.5
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
		var residual_low := start.y-water_height(Vector2(start.x,start.z),time,height,wavelength)
		var samples := maxi(1, int(ceil((high-low)*Vector2(direction.x,direction.z).length()*16.0/wavelength)))
		var previous := low
		var found := false
		for sample in range(1,samples+1):
			var next := lerpf(low,high,float(sample)/samples)
			var point := origin+direction*next
			var residual := point.y-water_height(Vector2(point.x,point.z),time,height,wavelength)
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
			var residual := point.y - water_height(Vector2(point.x, point.z),time,height,wavelength)
			if absf(residual) <= 0.00001:
				break
			if residual*residual_low>0.0:
				low=travel
				residual_low=residual
			else:
				high=travel
			var gradient := water_gradient(Vector2(point.x, point.z),time,height,wavelength)
			var slope := direction.y - gradient.dot(Vector2(direction.x, direction.z))
			var candidate := travel-residual/slope if absf(slope)>=0.00001 else INF
			travel=candidate if candidate>low and candidate<high else (low+high)*0.5
		var point := origin + direction * travel
		if absf(point.x) > extent.x or absf(point.z) > extent.y or absf(point.y-water_height(Vector2(point.x,point.z),time,height,wavelength)) > 0.001:
			return {}
	elif surface.mesh is SphereMesh:
		var radius: float = surface.mesh.radius
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
	return {"local_position": local_position, "world_position": surface.to_global(local_position)}
