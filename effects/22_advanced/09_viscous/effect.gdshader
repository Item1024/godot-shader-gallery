// 黏性融合 | 二维 Shader
// Adjust u_amount, u_speed, u_scale and u_color in the gallery.
shader_type canvas_item;
render_mode unshaded;

uniform float u_time = 0.0;
uniform float u_amount : hint_range(0.0, 1.0) = 0.55;
uniform float u_speed : hint_range(0.0, 3.0) = 1.0;
uniform float u_scale : hint_range(0.4, 3.0) = 1.0;
uniform bool u_enabled = true;
uniform vec4 u_color : source_color = vec4(0.33, 0.91, 0.73, 1.0);
uniform vec2 u_mouse = vec2(0.5);
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

float smooth_union(float a,float b,float k) {
    float h=clamp(0.5+0.5*(b-a)/k,0.0,1.0);
    return mix(b,a,h)-k*h*(1.0-h);
}

float map_scene(vec3 p){
float a=length(p-vec3(sin(u_time*u_speed)*0.4,cos(u_time*0.6)*0.2,0))-0.6; float b=length(p-vec3(-0.4,-0.2,0.1))-0.55; return smooth_union(a,b,0.6);
}

void fragment() {
    vec2 uv=UV, p=(UV-0.5)*2.0;
    float t=u_time*u_speed;
    vec4 base=texture(TEXTURE, UV);
    vec4 out_color=base;
    vec3 col=base.rgb;
    if (u_enabled) {

        vec3 origin=vec3(0,0.15,3.2), direction=normalize(vec3(p.x,-p.y,-2.3));
        origin.xz=rot(t*0.12)*origin.xz;
        direction.xz=rot(t*0.12)*direction.xz;
        float travel=0.0; bool hit=false;
        for(int i=0;i<48;i++){
            vec3 point=origin+direction*travel;
            float d=map_scene(point);
            if(d<0.003){hit=true;break;}
            travel+=max(d,0.002);
            if(travel>8.0){break;}
        }
        col=vec3(0.025,0.045,0.075);
        if(hit){
            vec3 point=origin+direction*travel;
            vec2 e=vec2(0.004,0);
            vec3 normal=normalize(vec3(map_scene(point+e.xyy)-map_scene(point-e.xyy),map_scene(point+e.yxy)-map_scene(point-e.yxy),map_scene(point+e.yyx)-map_scene(point-e.yyx)));
            float light=max(dot(normal,normalize(vec3(-0.5,0.8,1))),0.0);
            col=u_color.rgb*(0.15+light*0.85)+vec3(pow(max(dot(reflect(direction,normal),normalize(vec3(-0.5,0.8,1))),0.0),30.0))*0.5;
        }

    }
    COLOR=vec4(col,1.0);
}
