// 交互涟漪 | 三维材质
// Parameters and defaults: metadata.json
shader_type spatial;
render_mode depth_draw_never;

uniform float u_time = 0.0;
uniform float u_amount : hint_range(0.0, 1.0) = 0.55;
uniform float u_speed : hint_range(0.0, 3.0) = 1.0;
uniform float u_scale : hint_range(0.4, 3.0) = 1.0;
uniform bool u_enabled = true;
uniform vec4 u_color : source_color = vec4(0.33, 0.91, 0.73, 1.0);
uniform vec2 u_mouse = vec2(0.5);
uniform float u_ripple_speed : hint_range(0.1,2.0,0.01) = 0.6;
uniform float u_ripple_width : hint_range(0.01,0.2,0.001) = 0.04;
uniform float u_duration : hint_range(0.2,3.0,0.01) = 1.0;
uniform float u_strength : hint_range(0.0,1.0,0.01) = 0.6;
uniform float u_wave_height : hint_range(0.0,0.25,0.001) = 0.04;
const float TAU_ = 6.28318530718;

float h21(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}
float n2(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    f = f*f*(3.0-2.0*f);
    return mix(mix(h21(i), h21(i+vec2(1,0)), f.x),
               mix(h21(i+vec2(0,1)), h21(i+vec2(1,1)), f.x), f.y);
}
float fbm(vec2 p) {
    float v = 0.0, a = 0.5;
    for (int i=0; i<5; i++) {
        v += a*n2(p);
        p = mat2(vec2(1.6,1.2),vec2(-1.2,1.6))*p + 3.17;
        a *= 0.5;
    }
    return v;
}
mat2 rot(float a) {
    return mat2(vec2(cos(a),-sin(a)),vec2(sin(a),cos(a)));
}
vec2 cells(vec2 p) {
    vec2 ip = floor(p), fp = fract(p);
    float first = 8.0, second = 8.0;
    for (int y=-1; y<=1; y++) {
        for (int x=-1; x<=1; x++) {
            vec2 g = vec2(float(x),float(y));
            vec2 point = vec2(h21(ip+g),h21(ip+g+19.7));
            float d = length(g+point-fp);
            if (d<first) { second=first; first=d; }
            else { second=min(second,d); }
        }
    }
    return vec2(first,second-first);
}
float ring_sdf(vec2 p, float radius, float width) {
    return 1.0-smoothstep(width,width+0.009,abs(length(p)-radius));
}
float box_sdf(vec2 p, vec2 half_size, float radius) {
    vec2 q = abs(p)-half_size+radius;
    return length(max(q,vec2(0)))+min(max(q.x,q.y),0.0)-radius;
}
vec3 rainbow(float x) {
    return 0.5+0.5*cos(TAU_*(x+vec3(0.0,0.33,0.67)));
}
vec3 thermal(float x) {
    return clamp(vec3(1.5-abs(4.0*x-3.0),1.5-abs(4.0*x-2.0),1.5-abs(4.0*x-1.0)),0.0,1.0);
}
vec4 blur9(sampler2D image, vec2 uv, vec2 offset) {
    vec4 value = texture(image,uv)*0.20;
    value += texture(image,uv+vec2(offset.x,0))*0.12;
    value += texture(image,uv-vec2(offset.x,0))*0.12;
    value += texture(image,uv+vec2(0,offset.y))*0.12;
    value += texture(image,uv-vec2(0,offset.y))*0.12;
    value += texture(image,uv+offset)*0.08;
    value += texture(image,uv-offset)*0.08;
    value += texture(image,uv+vec2(offset.x,-offset.y))*0.08;
    value += texture(image,uv+vec2(-offset.x,offset.y))*0.08;
    return value;
}

uniform float u_wave_length=1.0;
uniform vec4 u_shallow_color : source_color = vec4(0.1019608,0.6196078,0.6117647,1.0);
uniform vec4 u_deep_color : source_color = vec4(0.0156863,0.1215686,0.2705882,1.0);
uniform float u_depth_distance=2.0;
uniform vec3 u_hit_position=vec3(0.0);
uniform float u_event_time=-1.0;

uniform sampler2D depth_texture : hint_depth_texture, repeat_disable, filter_nearest;
float water_height(vec2 point, float time) {
    return (sin(point.x*TAU_/u_wave_length+time*1.4)+sin(point.y*TAU_/u_wave_length-time*1.1)*0.5)*u_wave_height/1.5;
}

varying vec3 v_world;
varying vec3 v_local;
void vertex() {
    float t=u_time*u_speed;
    if (u_enabled) {

        VERTEX.y+=water_height(VERTEX.xz,t);
        float k=TAU_/u_wave_length;
        NORMAL=normalize(vec3(-cos(VERTEX.x*k+t*1.4)*k*u_wave_height/1.5,1.0,-cos(VERTEX.z*k-t*1.1)*k*u_wave_height/3.0));

    }
    v_local=VERTEX;
    v_world=(MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;
}
void fragment() {
    vec2 uv=UV*u_scale;
    float t=u_time*u_speed;
    float rim=pow(clamp(1.0-dot(normalize(NORMAL),normalize(VIEW)),0.0,1.0),2.5);
    ALBEDO=vec3(0.12,0.58,0.48);
    ROUGHNESS=0.42;
    if (u_enabled) {

        float depth_sample=texture(depth_texture,SCREEN_UV).r;
        vec4 scene=INV_PROJECTION_MATRIX*vec4(SCREEN_UV*2.0-1.0,depth_sample,1.0);
        float water_depth=max(0.0,(-scene.z/scene.w)-(-VERTEX.z));
        float depth_mix=clamp(water_depth/u_depth_distance,0.0,1.0);
        ALBEDO=mix(u_shallow_color.rgb,u_deep_color.rgb,depth_mix);
        ROUGHNESS=0.18; METALLIC=0.25; ALPHA=1.0;

        float age=u_time-u_event_time;
        if(u_event_time>=0.0 && age>=0.0 && age<u_duration) {
            float r=length(v_local.xz-u_hit_position.xz);
            float ring=exp(-pow((r-age*u_ripple_speed)/u_ripple_width,2.0))*(1.0-age/u_duration)*u_strength;
            ALBEDO+=vec3(ring)*0.55; EMISSION=vec3(ring)*0.15;
        }

    }
}
