"""Generate independent, readable Godot examples from the requested catalogue."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re
import struct
import sys
import tempfile
import zlib

sys.dont_write_bytecode = True
from effect_catalog import CATEGORIES
from plain_language import PRINCIPLES
from effect_profiles import PROFILES, parameter_notes

ROOT = Path(__file__).resolve().parents[1]
COMMON = """
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
"""


def canvas(body, sprite=False, post=False, extra=""):
    header = "shader_type canvas_item;\nrender_mode unshaded;\n"
    if post:
        header += "uniform sampler2D screen_texture : hint_screen_texture, repeat_disable, filter_linear_mipmap;\n"
    source = "texture(screen_texture, SCREEN_UV)" if post else "texture(TEXTURE, UV)"
    return header + COMMON + extra + """
void fragment() {
    vec2 uv=UV, p=(UV-0.5)*2.0;
    float t=u_time*u_speed;
    vec4 base=""" + source + """;
    vec4 out_color=base;
    vec3 col=base.rgb;
    if (u_enabled) {
""" + body + """
    }
""" + ("    COLOR=out_color;\n" if sprite else "    COLOR=vec4(col,1.0);\n") + "}\n"


def spatial(body, vertex="", light="", extra="", modes=""):
    return "shader_type spatial;\n" + ("render_mode "+modes+";\n" if modes else "") + COMMON + extra + """
varying vec3 v_world;
varying vec3 v_local;
void vertex() {
    float t=u_time*u_speed;
    if (u_enabled) {
""" + vertex + """
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
""" + body + """
    }
}
""" + light


def refined_shader(group, slug):
    """M3 formulas; other 401 effects retain their original generation path."""
    key = group + "/" + slug
    if group == "dissolve":
        mask = "fbm(uv*u_noise_scale)" if slug != "direction" else "(dot(uv-0.5,direction)/extent)+0.5"
        extra = "" if slug != "direction" else "vec2 direction=vec2(cos(radians(u_direction_deg)),sin(radians(u_direction_deg))); float extent=abs(direction.x)+abs(direction.y);"
        return canvas(f"""
        {extra}
        float value={mask};
        if (u_amount>=1.0) {{ out_color.a=0.0; }}
        else if (u_amount>0.0) {{
            float visible=step(u_amount,value);
            float edge=u_edge_width>0.0 ? 1.0-smoothstep(0.0,u_edge_width,max(value-u_amount,0.0)) : 0.0;
            out_color.rgb=mix(base.rgb,u_color.rgb*1.8,edge);
            out_color.a=base.a*visible;
        }}
""", sprite=True), "sprite"
    if group == "outline":
        treatment = "float alpha=base.a+hi*(1.0-base.a); out_color=vec4((base.rgb*base.a+u_color.rgb*hi*(1.0-base.a))/max(alpha,0.00001),alpha);" if slug == "outer" else "out_color=vec4(mix(base.rgb,u_color.rgb,1.0-lo),base.a);"
        return canvas("""
        if (u_width_px>0.0) {
            float hi=base.a, lo=base.a;
            for (int i=0;i<32;i++) {
                float a=float(i)*TAU_/32.0;
                vec2 direction=vec2(cos(a),sin(a))*TEXTURE_PIXEL_SIZE*u_width_px;
                float hard=texture(TEXTURE,uv+direction).a;
                float soft=(hard+texture(TEXTURE,uv+direction*0.75).a+texture(TEXTURE,uv+direction*0.5).a+texture(TEXTURE,uv+direction*0.25).a)*0.25;
                float coverage=mix(hard,soft,u_softness);
                hi=max(hi,coverage); lo=min(lo,coverage);
            }
""" + treatment + "\n        }", sprite=True), "sprite"
    if group == "emission":
        signal = "mix(u_min_brightness,1.0,0.5+0.5*sin(t*TAU_*u_frequency))" if slug == "breathing" else "1.0-smoothstep(0.0,u_band_width*0.5,abs(dot(uv-0.5,direction)-center))"
        setup = "" if slug == "breathing" else "vec2 direction=vec2(cos(radians(u_angle_deg)),sin(radians(u_angle_deg))); float span=abs(direction.x)+abs(direction.y)+u_band_width; float center=(fract(t/u_period)-0.5)*span;"
        return canvas(setup + f"\n out_color.rgb=base.rgb+u_color.rgb*({signal})*u_intensity;", sprite=True), "sprite"
    if key == "sprite/flash":
        return canvas("float age=u_time-u_event_time; if(u_event_time>=0.0 && age>=0.0 && age<u_duration) { out_color.rgb=mix(base.rgb,u_color.rgb,u_strength*(1.0-age/u_duration)); }", sprite=True, extra="uniform float u_event_time=-1.0;\n"), "sprite"
    if key == "sprite/recolor":
        return canvas("float distance_rgb=length(base.rgb-u_source_color.rgb)/sqrt(3.0); float selected=1.0-step(u_tolerance+0.000001,distance_rgb); out_color.rgb=mix(base.rgb,u_color.rgb,selected*u_amount);", sprite=True), "sprite"
    if group == "ui":
        setup = "p.x*=SCREEN_PIXEL_SIZE.y/SCREEN_PIXEL_SIZE.x; float radius=length(p); float shape=1.0-smoothstep(0.78,0.78+fwidth(radius),radius);"
        if slug == "liquid":
            fill = "float level=(0.78-p.y)/1.56; float wave=sin((p.x/1.56+0.5)*TAU_*u_wave_frequency+t*2.0)*u_wave_height; float fill=u_amount<=0.0 ? 0.0 : (u_amount>=1.0 ? 1.0 : 1.0-step(u_amount+wave,level));"
        else:
            fill = "float turn=fract((atan(p.x,-p.y)-radians(u_start_deg))/TAU_); if(!u_clockwise){turn=fract(-turn);} float fill=u_amount<=0.0 ? 0.0 : (u_amount>=1.0 ? 1.0 : 1.0-step(u_amount,turn));"
            if slug == "ring":
                setup += "shape*=smoothstep(0.78-u_ring_width*2.0-fwidth(radius),0.78-u_ring_width*2.0,radius);"
        return canvas(setup + fill + "col=mix(vec3(0.035,0.06,0.10),u_color.rgb,shape*fill);"), "canvas"
    if group == "water":
        extra = """
uniform sampler2D depth_texture : hint_depth_texture, repeat_disable, filter_nearest;
float water_height(vec2 point, float time) {
    return (sin(point.x*TAU_/u_wave_length+time*1.4)+sin(point.y*TAU_/u_wave_length-time*1.1)*0.5)*u_wave_height/1.5;
}
"""
        if slug == "interactive":
            extra = """
uniform float u_wave_length=1.0;
uniform vec4 u_shallow_color : source_color = vec4(0.1019608,0.6196078,0.6117647,1.0);
uniform vec4 u_deep_color : source_color = vec4(0.0156863,0.1215686,0.2705882,1.0);
uniform float u_depth_distance=2.0;
uniform vec3 u_hit_position=vec3(0.0);
uniform float u_event_time=-1.0;
""" + extra
        vertex = """
        VERTEX.y+=water_height(VERTEX.xz,t);
        float k=TAU_/u_wave_length;
        NORMAL=normalize(vec3(-cos(VERTEX.x*k+t*1.4)*k*u_wave_height/1.5,1.0,-cos(VERTEX.z*k-t*1.1)*k*u_wave_height/3.0));
"""
        body = """
        float depth_sample=texture(depth_texture,SCREEN_UV).r;
        vec4 scene=INV_PROJECTION_MATRIX*vec4(SCREEN_UV*2.0-1.0,depth_sample,1.0);
        float water_depth=max(0.0,(-scene.z/scene.w)-(-VERTEX.z));
        float depth_mix=clamp(water_depth/u_depth_distance,0.0,1.0);
        ALBEDO=mix(u_shallow_color.rgb,u_deep_color.rgb,depth_mix);
        ROUGHNESS=0.18; METALLIC=0.25; ALPHA=1.0;
"""
        if slug == "interactive":
            body += """
        float age=u_time-u_event_time;
        if(u_event_time>=0.0 && age>=0.0 && age<u_duration) {
            float r=length(v_local.xz-u_hit_position.xz);
            float ring=exp(-pow((r-age*u_ripple_speed)/u_ripple_width,2.0))*(1.0-age/u_duration)*u_strength;
            ALBEDO+=vec3(ring)*0.55; EMISSION=vec3(ring)*0.15;
        }
"""
        return spatial(body, vertex=vertex, extra=extra, modes="depth_draw_never"), "spatial"
    if key == "magic/hologram":
        return spatial("float line=pow(0.5+0.5*sin(v_local.y*TAU_*u_line_density-t*2.0),6.0); ALBEDO=u_color.rgb*(line*u_intensity+rim*u_rim_strength); ALPHA=u_opacity;", modes="unshaded"), "spatial"
    if key == "magic/shield_hit":
        return spatial("""
        ALBEDO=u_color.rgb*0.08; ALPHA=0.12+rim*0.25;
        float age=u_time-u_event_time;
        if(u_event_time>=0.0 && age>=0.0 && age<u_duration) {
            float arc=acos(clamp(dot(normalize(v_local),normalize(u_hit_position)),-1.0,1.0))*0.92;
            float radius=age/u_duration*2.8;
            float ring=exp(-pow((arc-radius)/u_ring_width,2.0))*(1.0-age/u_duration);
            ALBEDO+=u_color.rgb*ring*u_intensity; ALPHA=clamp(ALPHA+ring*0.6,0.0,1.0);
        }
""", extra="uniform vec3 u_hit_position=vec3(0.0,0.0,0.92);\nuniform float u_event_time=-1.0;\n", modes="unshaded"), "spatial"
    if key == "glass/clear":
        return spatial("vec2 half_pixel=0.5/vec2(textureSize(screen_texture,0)); vec2 sample_uv=clamp(SCREEN_UV+NORMAL.xy*u_distortion,half_pixel,1.0-half_pixel); ALBEDO=textureLod(screen_texture,sample_uv,0.0).rgb*u_color.rgb; ALPHA=u_opacity;", extra="uniform sampler2D screen_texture : hint_screen_texture, repeat_disable, filter_linear;\n", modes="unshaded, cull_disabled"), "spatial"
    if key == "lens/gaussian":
        return canvas("""
        if(u_radius_px>0.0) {
            int count=u_quality==0 ? 2 : (u_quality==1 ? 4 : 6);
            vec2 pixel=SCREEN_PIXEL_SIZE;
            vec2 axis=u_vertical ? vec2(0.0,pixel.y) : vec2(pixel.x,0.0);
            vec3 sum=base.rgb; float weights=1.0;
            for(int i=-6;i<=6;i++) {
                if(i!=0 && abs(i)<=count) {
                    float x=float(i)/float(count);
                    float weight=exp(-4.5*x*x);
                    vec2 sample_uv=clamp(SCREEN_UV+axis*x*u_radius_px,pixel*0.5,1.0-pixel*0.5);
                    sum+=textureLod(screen_texture,sample_uv,0.0).rgb*weight;
                    weights+=weight;
                }
            }
            col=sum/weights;
        }
""", post=True, extra="uniform bool u_vertical=false;\n"), "post"
    if key == "color/lut":
        return canvas("""
        vec3 input_color=clamp(base.rgb,0.0,1.0);
        float blue=input_color.b*15.0;
        float low=floor(blue), high=min(low+1.0,15.0);
        vec2 within=vec2(input_color.r*15.0+0.5,input_color.g*15.0+0.5);
        vec3 a=textureLod(lut_texture,(vec2(low*16.0,0.0)+within)/vec2(256.0,16.0),0.0).rgb;
        vec3 b=textureLod(lut_texture,(vec2(high*16.0,0.0)+within)/vec2(256.0,16.0),0.0).rgb;
        col=mix(base.rgb,mix(a,b,fract(blue)),u_amount);
""", post=True, extra="uniform sampler2D lut_texture : filter_linear, repeat_disable;\n"), "post"
    if key == "retro/crt":
        return canvas("""
        vec2 warped=p*(1.0+u_curvature*dot(p,p));
        vec2 q=warped*0.5+0.5;
        col=texture(screen_texture,q).rgb;
        if(any(lessThan(q,vec2(0.0))) || any(greaterThan(q,vec2(1.0)))) { col=vec3(0.0); }
        float scan=0.5+0.5*cos(FRAGCOORD.y*3.14159265);
        col*=1.0-u_scanline_strength*scan;
        col*=1.0-u_vignette*clamp(dot(p,p)*0.5,0.0,1.0);
        int channel=int(mod(FRAGCOORD.x,3.0));
        vec3 mask=vec3(channel==0 ? 1.0 : 0.0,channel==1 ? 1.0 : 0.0,channel==2 ? 1.0 : 0.0);
        col*=mix(vec3(1.0),mask,u_rgb_mask);
""", post=True), "post"
    raise ValueError("No refined shader: " + key)


def profile_uniforms(source, profile):
    declarations = []
    for p in profile["parameters"]:
        key, kind, value = p["key"], p["type"], p["default"]
        if kind == "texture":
            continue
        if kind == "color":
            rgb = [int(value[i:i+2], 16)/255 for i in (1, 3, 5)]
            declaration = f"uniform vec4 {key} : source_color = vec4({','.join(str(v) for v in rgb)},1.0);"
        elif kind == "bool":
            declaration = f"uniform bool {key} = {str(value).lower()};"
        elif kind == "enum":
            declaration = f"uniform int {key} = {value};"
        else:
            declaration = f"uniform float {key} : hint_range({float(p['min'])},{float(p['max'])},{float(p['step'])}) = {float(value)};"
        pattern = r"uniform \w+ " + key + r"\b[^;]*;"
        if re.search(pattern, source):
            source = re.sub(pattern, declaration, source)
        else:
            declarations.append(declaration)
    return source.replace("const float TAU_", "\n".join(declarations) + "\nconst float TAU_")


def dissolve(slug, index):
    mask = {
        "noise": "fbm(uv*8.0*u_scale)",
        "direction": "uv.x",
        "height": "1.0-uv.y",
        "radial": "length(uv-0.5)*1.414",
        "sphere": "length((uv-u_mouse)*vec2(1.0,0.8))*1.6",
        "mask": "0.5+0.5*sin(uv.x*20.0*u_scale+sin(uv.y*17.0))",
        "burn": "fbm(uv*8.0*u_scale)+0.24*(1.0-uv.y)",
        "char": "fbm(uv*9.0*u_scale)",
        "glow": "fbm(uv*6.0*u_scale)",
        "pixel": "h21(floor(uv*28.0*u_scale))",
        "sand": "n2(vec2(floor(uv.x*80.0),uv.y*100.0-t*2.0))",
        "corrosion": "cells(uv*12.0*u_scale).x",
        "scan": "uv.y+0.04*sin(uv.x*90.0)",
        "teleport": "uv.y+0.12*h21(vec2(floor(uv.y*48.0),0.0))",
        "fade": "1.0",
        "dither": "h21(floor(FRAGCOORD.xy))",
    }[slug]
    if slug == "fade":
        return canvas("out_color.a *= 1.0-u_amount;", sprite=True)
    edge = "vec3(1.0,0.32,0.025)" if slug in ["burn", "char"] else "u_color.rgb"
    return canvas(f"""
        float mask_value={mask};
        float threshold=u_amount;
        float visible=step(threshold,mask_value);
        float edge=1.0-smoothstep(0.0,0.065,mask_value-threshold);
        out_color.rgb=mix(base.rgb,{edge}*1.8,edge);
        out_color.a=base.a*visible;
""", sprite=True)


def outline(slug, index):
    if slug in ["rim", "fresnel", "silhouette", "occlusion", "xray", "occluder_fade", "camera_fade", "cutaway"]:
        bodies = {
            "rim": "ALBEDO=vec3(0.07,0.20,0.24); EMISSION=u_color.rgb*rim*(1.0+u_amount*5.0);",
            "fresnel": "ALBEDO=mix(vec3(0.035,0.10,0.20),u_color.rgb,pow(rim,0.2+u_amount*2.0)); METALLIC=0.65; ROUGHNESS=0.15;",
            "silhouette": "ALBEDO=u_color.rgb; EMISSION=u_color.rgb*0.4;",
            "occlusion": "ALBEDO=vec3(0.02,0.06,0.09)+u_color.rgb*step(0.22,rim)*2.0;",
            "xray": "ALBEDO=u_color.rgb*(0.1+rim+0.25*step(0.55,sin(v_world.y*45.0))); ALPHA=0.2+rim*0.65;",
            "occluder_fade": "ALBEDO=u_color.rgb; ALPHA=1.0-u_amount*0.95;",
            "camera_fade": "ALBEDO=u_color.rgb; ALPHA=smoothstep(0.0,3.5*u_amount,length(VERTEX));",
            "cutaway": "if (v_local.y>mix(-0.9,0.9,u_amount)) { discard; } ALBEDO=mix(vec3(0.05,0.2,0.2),u_color.rgb,UV.y);",
        }
        modes = "unshaded, depth_test_disabled, cull_disabled" if slug in ["silhouette", "occlusion", "xray"] else "cull_disabled"
        return spatial(bodies[slug], modes=modes), "spatial"
    treatment = {
        "outer": "out_color=mix(vec4(u_color.rgb,outer_alpha),base,base.a);",
        "inner": "out_color=vec4(mix(base.rgb,u_color.rgb,inner_edge),base.a);",
        "dual": "out_color=mix(vec4(u_color.rgb,outer_alpha),base,base.a); out_color.rgb=mix(out_color.rgb,vec3(1.0,0.47,0.25),inner_edge);",
        "gradient": "out_color=mix(vec4(mix(u_color.rgb,vec3(0.65,0.4,1.0),uv.y),outer_alpha),base,base.a);",
        "dashed": "float dash=step(0.45,fract((uv.x+uv.y)*18.0-t)); out_color=mix(vec4(u_color.rgb,outer_alpha*dash),base,base.a);",
        "glow": "out_color=mix(vec4(u_color.rgb*2.0,outer_alpha*0.8),base,base.a);",
        "pulse": "out_color=mix(vec4(u_color.rgb,outer_alpha*(0.5+0.5*sin(t*3.0))),base,base.a);",
        "selection": "out_color=mix(vec4(u_color.rgb,outer_alpha),vec4(mix(base.rgb,u_color.rgb,0.3*u_amount),base.a),base.a);",
    }[slug]
    return canvas("""
        vec2 off=TEXTURE_PIXEL_SIZE*(2.0+u_amount*16.0);
        float hi=0.0, lo=1.0;
        for (int i=0;i<12;i++) {
            float a=float(i)*TAU_/12.0;
            float alpha=texture(TEXTURE,uv+vec2(cos(a),sin(a))*off).a;
            hi=max(hi,alpha); lo=min(lo,alpha);
        }
        float outer_alpha=max(hi-base.a,0.0);
        float inner_edge=max(base.a-lo,0.0);
""" + treatment, sprite=True), "sprite"


def emission(slug, index):
    expressions = {
        "emission": "1.0",
        "breathing": "0.5+0.5*sin(t*2.5)",
        "flicker": "step(0.35,h21(vec2(floor(t*12.0),0.0)))",
        "band": "pow(max(0.0,1.0-abs(uv.x-fract(t*0.25))*7.0),3.0)",
        "diagonal": "pow(max(0.0,1.0-abs(fract(uv.x+uv.y-t*0.3)-0.5)*10.0),2.0)",
        "border": "ring_sdf(p,0.65,0.035)*(0.25+pow(max(0.0,cos(atan(p.y,p.x)-t*2.0)),12.0))",
        "path": "ring_sdf(p,0.5,0.08)*pow(max(0.0,cos(atan(p.y,p.x)-t*2.0)),7.0)",
        "flow": "pow(fbm(uv*9.0*u_scale+vec2(t,-t*0.4)),4.0)*7.0",
        "scanline": "pow(0.5+0.5*sin(uv.y*80.0*u_scale-t*8.0),16.0)",
        "marquee": "step(0.5,fract(atan(p.y,p.x)*5.0-t))*ring_sdf(p,0.65,0.04)",
        "neon": "ring_sdf(p,0.58,0.018)+0.15/(0.07+abs(length(p)-0.58))",
        "circuit": "step(0.91,cos(uv.x*80.0*u_scale))*step(0.4,sin(uv.y*28.0-t*4.0))+step(0.95,cos(uv.y*60.0))*step(0.7,sin(uv.x*40.0+t*3.0))",
        "cracks": "1.0-smoothstep(0.015,0.06,cells(uv*14.0*u_scale).y)",
        "rainbow": "0.4+0.6*sin(uv.x*12.0-t*3.0)*sin(uv.y*12.0+t)",
        "glitter": "step(0.975,h21(floor(uv*95.0*u_scale)))*pow(max(0.0,sin(t*3.0+h21(floor(uv*95.0))*30.0)),12.0)",
        "stars": "pow(max(0.0,1.0-length(fract(uv*12.0*u_scale)-0.5)*3.0),12.0)*(0.5+0.5*sin(t*3.0+h21(floor(uv*12.0))*20.0))",
    }
    color = "rainbow(uv.x+uv.y-t*0.15)" if slug == "rainbow" else "u_color.rgb"
    mask = "1.0" if slug in ["border","path","marquee","neon","stars"] else "base.a"
    return canvas(f"""
        float signal={expressions[slug]};
        col=vec3(0.025,0.045,0.075)+{color}*signal*{mask}*(0.45+u_amount*2.0);
        col += base.rgb*base.a*0.35;
""")


def toon(slug, index):
    if slug in ["toon", "cel", "bands", "ramp", "highlight", "shadow", "flat", "low_poly", "matcap"]:
        if slug == "matcap":
            return spatial("vec2 cap=normalize(NORMAL).xy*0.5+0.5; ALBEDO=mix(vec3(0.05,0.07,0.18),u_color.rgb,cap.y); ALBEDO+=vec3(pow(max(0.0,1.0-length(cap-vec2(0.3,0.7))*1.7),7.0));", modes="unshaded"), "spatial"
        if slug in ["flat", "low_poly"]:
            return spatial("vec3 flat_normal=normalize(cross(dFdx(VERTEX),dFdy(VERTEX))); float band=floor((dot(flat_normal,normalize(vec3(-0.5,0.8,0.6)))*0.5+0.5)*5.0)/5.0; ALBEDO=u_color.rgb*(0.18+band);", modes="unshaded"), "spatial"
        count = 2 if slug in ["cel", "shadow"] else 3
        lighting = f"""
void light() {{
    float n=max(dot(NORMAL,LIGHT),0.0);
    float bands={float(count):.1f}+floor(u_amount*3.0);
    float value=u_enabled ? floor(n*bands)/max(bands-1.0,1.0) : n;
    DIFFUSE_LIGHT += ALBEDO*LIGHT_COLOR*ATTENUATION*mix(0.18,1.0,value);
""" + ("    SPECULAR_LIGHT+=LIGHT_COLOR*step(0.96-u_amount*0.1,dot(NORMAL,normalize(LIGHT+VIEW)));\n" if slug == "highlight" else "") + "}\n"
        return spatial("ALBEDO=mix(vec3(0.10,0.20,0.40),u_color.rgb,UV.y); ROUGHNESS=0.7;", light=lighting), "spatial"
    bodies = {
        "halftone": "float l=dot(col,vec3(0.299,0.587,0.114)); float dot_mask=step(length(fract(uv*100.0*u_scale)-0.5),sqrt(max(l,0.0))*0.65); col=mix(vec3(0.06,0.08,0.14),vec3(0.97,0.85,0.63),dot_mask);",
        "hatching": "float l=dot(col,vec3(0.333)); float line=step(0.75,sin((uv.x+uv.y)*700.0*u_scale)); col=mix(vec3(0.97,0.94,0.84),vec3(0.10,0.13,0.19),line*(1.0-l));",
        "crosshatch": "float l=dot(col,vec3(0.333)); float a=step(0.6,sin((uv.x+uv.y)*600.0*u_scale)); float b=step(0.65,sin((uv.x-uv.y)*600.0*u_scale)); col=vec3(0.95)-vec3(max(a*(1.0-l),b*step(l,0.5)))*0.8;",
        "pencil": "vec2 d=vec2(0.002); float edge=length(texture(screen_texture,uv+d).rgb-texture(screen_texture,uv-d).rgb); float grain=n2(uv*900.0); col=vec3(0.96)-vec3(edge*4.0+(1.0-dot(col,vec3(0.333)))*grain*0.65);",
        "charcoal": "float l=dot(col,vec3(0.333)); col=vec3(smoothstep(0.12,0.85,l+n2(uv*500.0)*0.22));",
        "ink": "float l=dot(col,vec3(0.333)); col=mix(vec3(0.035,0.055,0.08),vec3(0.92,0.90,0.80),smoothstep(0.25,0.72,l+fbm(uv*20.0)*0.13));",
        "watercolor": "vec2 wobble=(vec2(fbm(uv*16.0),fbm(uv*16.0+4.0))-0.5)*0.014*u_amount; col=texture(screen_texture,uv+wobble).rgb; col=floor(col*7.0)/7.0; col=mix(col,vec3(1.0,0.97,0.87),n2(uv*500.0)*0.15);",
        "oil": "col=blur9(screen_texture,uv,vec2(0.003,0.005)*(0.5+u_amount*2.0)).rgb; col=floor(col*10.0)/10.0; col*=0.9+0.13*sin(uv.x*700.0+fbm(uv*25.0)*12.0);",
        "woodcut": "float l=dot(col,vec3(0.333)); float line=sin(uv.y*700.0+fbm(uv*8.0)*35.0); col=mix(vec3(0.12,0.08,0.05),vec3(0.91,0.78,0.56),step(line,(l-0.5)*2.0));",
        "paper": "float l=dot(col,vec3(0.333)); col=mix(vec3(0.07,0.20,0.26),mix(vec3(0.38,0.64,0.51),vec3(0.98,0.77,0.48),step(0.66,l)),step(0.38,l));",
    }
    return canvas(bodies[slug], post=True), "post"


def pbr(slug, index):
    bodies = {
        "metal": "ALBEDO=vec3(0.68,0.75,0.82); METALLIC=1.0; ROUGHNESS=0.08+u_amount*0.65;",
        "brushed": "ALBEDO=vec3(0.58,0.65,0.72); METALLIC=1.0; ROUGHNESS=0.25+n2(uv*vec2(500.0,4.0))*0.25; ANISOTROPY=0.9; ANISOTROPY_FLOW=vec2(1.0,0.0);",
        "plastic": "ALBEDO=u_color.rgb; ROUGHNESS=0.06+u_amount*0.5; SPECULAR=0.65;",
        "rubber": "ALBEDO=vec3(0.035,0.045,0.055); ROUGHNESS=0.85; SPECULAR=0.2; NORMAL_MAP=vec3(0.5+0.06*n2(uv*160.0),0.5,1.0);",
        "ceramic": "ALBEDO=mix(vec3(0.93,0.9,0.77),u_color.rgb,step(0.7,sin(uv.y*45.0))); ROUGHNESS=0.12; CLEARCOAT=0.8; CLEARCOAT_ROUGHNESS=0.1;",
        "skin": "ALBEDO=mix(vec3(0.47,0.16,0.10),vec3(0.84,0.52,0.33),fbm(uv*12.0)*0.35+0.45); ROUGHNESS=0.48; SSS_STRENGTH=u_amount; BACKLIGHT=vec3(0.5,0.12,0.06)*u_amount;",
        "wax": "ALBEDO=vec3(0.89,0.56,0.25); ROUGHNESS=0.4; SSS_STRENGTH=u_amount; BACKLIGHT=vec3(0.8,0.3,0.05);",
        "jade": "ALBEDO=mix(vec3(0.04,0.23,0.12),vec3(0.48,0.83,0.54),fbm(uv*9.0)); ROUGHNESS=0.15; SSS_STRENGTH=u_amount; BACKLIGHT=vec3(0.15,0.8,0.3)*u_amount;",
        "cloth": "float weave=sin(uv.x*500.0)*sin(uv.y*500.0); ALBEDO=u_color.rgb*(0.8+0.14*weave); ROUGHNESS=0.9; NORMAL_MAP=vec3(0.5+weave*0.06,0.5,1.0);",
        "silk": "ALBEDO=mix(u_color.rgb,vec3(0.8,0.65,0.9),rim); ROUGHNESS=0.25; ANISOTROPY=0.8; ANISOTROPY_FLOW=vec2(1.0,0.0); RIM=0.7;",
        "velvet": "ALBEDO=mix(vec3(0.13,0.025,0.18),u_color.rgb,rim); ROUGHNESS=1.0; RIM=1.0; RIM_TINT=0.7;",
        "leather": "float grain=cells(uv*100.0).y; ALBEDO=vec3(0.20,0.07,0.035)*(0.65+grain); ROUGHNESS=0.6; NORMAL_MAP=vec3(0.5+grain*0.22,0.5+grain*0.12,1.0);",
        "hair": "float strand=n2(uv*vec2(240.0,4.0)); ALBEDO=mix(vec3(0.025,0.012,0.008),vec3(0.33,0.14,0.045),strand); ANISOTROPY=0.92; ANISOTROPY_FLOW=vec2(0.0,1.0); ROUGHNESS=0.27;",
        "eye": "vec2 iris=(UV-vec2(0.5,0.5))*vec2(2.0,1.0); float r=length(iris); float streak=sin(atan(iris.y,iris.x)*100.0+fbm(iris*30.0)*5.0); ALBEDO=mix(vec3(0.9,0.88,0.8),u_color.rgb*(0.5+streak*0.18),1.0-smoothstep(0.19,0.21,r)); ALBEDO=mix(ALBEDO,vec3(0.005),1.0-smoothstep(0.07,0.09,r)); ROUGHNESS=0.05;",
        "clearcoat": "ALBEDO=u_color.rgb; METALLIC=0.3; ROUGHNESS=0.35; CLEARCOAT=u_amount; CLEARCOAT_ROUGHNESS=0.04;",
        "car_paint": "float flake=step(0.98,h21(floor(uv*700.0))); ALBEDO=mix(vec3(0.45,0.025,0.06),vec3(0.9),flake*0.8); METALLIC=0.75; ROUGHNESS=0.2; CLEARCOAT=1.0; CLEARCOAT_ROUGHNESS=0.05;",
        "pearl": "ALBEDO=mix(vec3(0.84,0.79,0.70),vec3(0.48,0.75,0.84),rim); METALLIC=0.15; ROUGHNESS=0.22; CLEARCOAT=0.8;",
        "iridescence": "ALBEDO=rainbow(rim*2.0+uv.y*0.15+t*0.06); METALLIC=0.72; ROUGHNESS=0.18;",
        "thin_film": "float thickness=0.3+u_amount+fbm(uv*4.0)*0.15; ALBEDO=rainbow(dot(NORMAL,VIEW)*thickness*4.0); METALLIC=0.7; ROUGHNESS=0.1;",
        "flakes": "float flake=step(0.94,h21(floor(uv*180.0*u_scale))); ALBEDO=mix(u_color.rgb,vec3(0.95,0.77,0.36),flake); METALLIC=0.9; ROUGHNESS=mix(0.5,0.03,flake);",
        "pbr": "ALBEDO=u_color.rgb; METALLIC=u_amount; ROUGHNESS=clamp(UV.x,0.05,1.0);",
        "normal": "NORMAL_MAP=normalize(vec3(sin(uv.x*35.0)*0.4,cos(uv.y*35.0)*0.4,1.0))*0.5+0.5; NORMAL_MAP_DEPTH=u_amount*2.0; ALBEDO=u_color.rgb;",
        "bump": "float h=fbm(uv*25.0); vec2 d=vec2(dFdx(h),dFdy(h))*u_amount*5.0; NORMAL=normalize(NORMAL+vec3(d,0.0)); ALBEDO=u_color.rgb;",
        "detail_normal": "vec2 normal_detail=vec2(sin(uv.x*90.0),cos(uv.y*90.0))*0.08+vec2(sin(uv.x*18.0),cos(uv.y*18.0))*0.3; NORMAL_MAP=vec3(normal_detail*u_amount+0.5,1.0);",
        "anisotropy": "ALBEDO=vec3(0.8,0.56,0.2); METALLIC=1.0; ROUGHNESS=0.25; ANISOTROPY=u_amount; ANISOTROPY_FLOW=vec2(cos(t*0.3),sin(t*0.3));",
        "sss": "ALBEDO=u_color.rgb; SSS_STRENGTH=u_amount; BACKLIGHT=u_color.rgb*1.5; ROUGHNESS=0.4;",
        "transmission": "ALBEDO=u_color.rgb*0.4; BACKLIGHT=u_color.rgb*u_amount*2.0; SSS_STRENGTH=u_amount; ROUGHNESS=0.25;",
        "layered": "float mask=smoothstep(u_amount-0.08,u_amount+0.08,fbm(uv*9.0)); ALBEDO=mix(vec3(0.48,0.22,0.08),u_color.rgb,mask); METALLIC=1.0-mask; ROUGHNESS=mix(0.18,0.8,mask);",
    }
    return spatial(bodies[slug])


def glass(slug, index):
    if slug in ["mirror", "blurred", "fresnel"]:
        body = "ALBEDO=vec3(0.8,0.9,0.95); METALLIC=1.0; ROUGHNESS=" + ("0.05;" if slug == "mirror" else "0.15+u_amount*0.7;" if slug == "blurred" else "0.12; ALBEDO=mix(vec3(0.12),u_color.rgb,rim);")
        return spatial(body)
    distort = {
        "clear": "NORMAL.xy*0.03*u_amount",
        "frosted": "(vec2(n2(SCREEN_UV*350.0),n2(SCREEN_UV*350.0+7.0))-0.5)*0.035*u_amount",
        "stained": "NORMAL.xy*0.018",
        "ice": "NORMAL.xy*0.035+(vec2(fbm(uv*10.0),fbm(uv*10.0+4.0))-0.5)*0.025",
        "crystal": "floor(NORMAL.xy*8.0)/8.0*0.06",
        "gem": "floor(NORMAL.xy*5.0)/5.0*0.08",
        "bubble": "NORMAL.xy*rim*0.025",
        "jelly": "NORMAL.xy*0.04+vec2(sin(uv.y*20.0+t*3.0),cos(uv.x*17.0+t*2.0))*0.008",
        "liquid": "vec2(sin(uv.y*18.0+t*2.0),cos(uv.x*15.0+t))*0.025",
        "absorption": "NORMAL.xy*0.045",
        "dispersion": "NORMAL.xy*0.045",
        "invisibility": "NORMAL.xy*0.06*u_amount",
        "air": "vec2(fbm(uv*10.0-vec2(0,t)),fbm(uv*10.0+vec2(t,0)))*0.025*u_amount",
    }[slug]
    sampling = "vec3 refracted=textureLod(screen_texture,SCREEN_UV+offset,0.0).rgb;"
    if slug == "frosted":
        sampling = "vec3 refracted=textureLod(screen_texture,SCREEN_UV+offset,1.0+u_amount*4.0).rgb;"
    if slug == "dispersion":
        sampling = "vec3 refracted=vec3(texture(screen_texture,SCREEN_UV+offset*1.3).r,texture(screen_texture,SCREEN_UV+offset).g,texture(screen_texture,SCREEN_UV+offset*0.7).b);"
    tint = "vec3(0.7,0.9,0.95)"
    if slug in ["stained", "gem", "jelly"]: tint = "mix(u_color.rgb,vec3(0.7,0.25,0.8),fbm(uv*5.0))"
    if slug == "bubble": tint = "rainbow(rim*2.0+t*0.05)"
    if slug == "absorption": tint = "exp(-vec3(0.8,0.2,0.05)*(1.0-rim)*(0.5+u_amount*3.0))"
    body = f"vec2 offset={distort}; {sampling} ALBEDO=refracted*{tint}; EMISSION={tint}*rim*0.35; ALPHA=0.85; ROUGHNESS=0.05;"
    vertex = "VERTEX += NORMAL*sin(VERTEX.y*5.0+t*3.0)*0.07*u_amount;" if slug == "jelly" else ""
    return spatial(body, vertex=vertex, extra="uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;\n", modes="unshaded, cull_disabled")


def water(slug, index):
    if slug in ["underwater", "droplets"]:
        offset = "vec2(sin(uv.y*30.0+t*2.0),cos(uv.x*22.0+t))*0.012*u_amount" if slug == "underwater" else "vec2(sin(uv.x*90.0+t),cos(uv.y*60.0-t*2.0))*pow(n2(uv*vec2(14.0,4.0)+vec2(0,t)),8.0)*0.08"
        return canvas(f"col=texture(screen_texture,uv+{offset}).rgb; col*=vec3(0.65,0.88,1.0);", post=True), "post"
    if slug == "fog":
        return spatial("ALBEDO=vec3(0.1,0.6,0.65); ROUGHNESS=0.2;"), "pipeline"
    extra = "uniform sampler2D depth_texture : hint_depth_texture, filter_nearest;\n"
    vertex = """
        float wave=sin(VERTEX.x*3.0*u_scale+t*1.4)+sin(VERTEX.z*4.0-t*1.1)*0.5;
        VERTEX.y+=wave*u_amount*0.15;
        NORMAL=normalize(vec3(-cos(VERTEX.x*3.0*u_scale+t*1.4)*u_amount*0.45,1.0,-cos(VERTEX.z*4.0-t*1.1)*u_amount*0.3));
"""
    detail = {
        "calm": "float pattern=sin(uv.x*40.0+t)*sin(uv.y*38.0-t)*0.04;",
        "ocean": "float pattern=pow(max(0.0,sin(uv.x*28.0+t*2.0)+sin(uv.y*40.0-t)),7.0)*0.1;",
        "river": "float pattern=pow(fbm(uv*vec2(8.0,28.0)-vec2(0,t*2.0)),4.0)*1.4;",
        "waterfall": "float pattern=pow(n2(uv*vec2(45.0,4.0)-vec2(0,t*5.0)),3.0);",
        "vortex": "vec2 q=uv-0.5; float pattern=sin(atan(q.y,q.x)*6.0+length(q)*35.0-t*4.0)*0.25;",
        "ripple": "float pattern=sin(length(uv-0.5)*80.0-t*5.0)*0.18;",
        "interactive": """float pattern=0.0;
        float age=u_time-u_event_time;
        if (u_event_time>=0.0 && age>=0.0 && age<u_duration) {
            float r=length(v_local.xz-u_hit_position.xz);
            pattern=exp(-pow((r-age*0.6)/0.04,2.0))*(1.0-age/u_duration)*u_amount;
        }""",
        "depth": "float pattern=0.0;",
        "shore": "float pattern=step(water_depth+fbm(uv*15.0+t*0.3)*0.15,0.27+u_amount*0.25);",
        "crest": "float pattern=step(0.7,sin(v_local.x*8.0+t*2.0)+sin(v_local.z*10.0-t)*0.5);",
        "caustics": "float pattern=pow(1.0-smoothstep(0.01,0.13,cells(uv*12.0+vec2(t*0.2)).y),3.0);",
        "reflection": "float pattern=0.0; METALLIC=0.85;",
        "rain": "float pattern=0.0; for(int i=0;i<8;i++){ vec2 c=vec2(h21(vec2(float(i),1)),h21(vec2(float(i),8))); float age=fract(t*0.6+float(i)*0.13); pattern+=sin((length(UV-c)-age*0.3)*160.0)*exp(-abs(length(UV-c)-age*0.3)*70.0)*(1.0-age)*0.25; }",
        "sloshing": "float pattern=sin(uv.x*20.0+t*3.0)*0.12;",
        "container": "float pattern=step(0.47,fract(uv.y*12.0+t*0.1))*0.08;",
        "slime": "float pattern=fbm(uv*9.0+t*0.3);",
    }[slug]
    if slug == "interactive":
        extra += """
uniform vec3 u_hit_position = vec3(0.0);
uniform float u_event_time = -1.0;
uniform float u_duration = 1.0;
// Keep this wave and its derivatives paired with shared/stage.gd.
float water_height(vec2 point, float time) {
    return (sin(point.x*3.0*u_scale+time*1.4)+sin(point.y*4.0-time*1.1)*0.5)*u_amount*0.15;
}
"""
        vertex = """
        VERTEX.y+=water_height(VERTEX.xz,t);
        NORMAL=normalize(vec3(-cos(VERTEX.x*3.0*u_scale+t*1.4)*u_amount*0.45*u_scale,1.0,-cos(VERTEX.z*4.0-t*1.1)*u_amount*0.3));
"""
    body = """
        float depth_sample=texture(depth_texture,SCREEN_UV).r;
        vec4 scene_position=INV_PROJECTION_MATRIX*vec4(SCREEN_UV*2.0-1.0,depth_sample,1.0);
        float water_depth=max(0.0,-scene_position.z/scene_position.w+VERTEX.z);
        ALBEDO=mix(vec3(0.10,0.62,0.61),vec3(0.015,0.12,0.27),smoothstep(0.0,2.0,water_depth));
        ROUGHNESS=0.14;
        METALLIC=0.35;
""" + detail + "\n ALBEDO+=vec3(pattern)*0.55; EMISSION=vec3(max(pattern,0.0))*0.15;"
    if slug == "slime": body += "\n ALBEDO=mix(vec3(0.06,0.2,0.03),u_color.rgb,pattern); ROUGHNESS=0.07;"
    if slug in ["sloshing", "container"]: vertex += "\n VERTEX.y += VERTEX.x*sin(t*2.0)*u_amount*0.2;"
    return spatial(body, vertex=vertex, extra=extra), "spatial"


def fire(slug, index):
    if slug in ["embers", "dust", "sandstorm", "steam", "poison", "smoke", "toon_smoke"]:
        color = "vec3(1.0,0.3,0.06)" if slug == "embers" else "vec3(0.7,0.55,0.33)" if slug in ["dust", "sandstorm"] else "u_color.rgb" if slug == "poison" else "vec3(0.65,0.72,0.8)"
        return canvas(f"""
        col=vec3(0.025,0.04,0.065);
        for(int i=0;i<18;i++) {{
            float seed=float(i);
            float age=fract(t*(0.12+u_amount*0.2)+h21(vec2(seed,2)));
            vec2 center=vec2((h21(vec2(seed,4))-.5)*(0.15+age*0.7)+sin(age*8.0+seed)*0.04,0.95-age*0.9);
            float radius={"0.004+age*0.004" if slug == "embers" else "0.035+age*0.11"};
            float puff=1.0-smoothstep(radius*0.4,radius,length(uv-center));
            {"puff=step(0.3,puff);" if slug == "toon_smoke" else ""}
            col+={color}*puff*(1.0-age)*0.5;
        }}
""")
    if slug == "shockwave":
        return canvas("float age=fract(t*0.45); float ring=ring_sdf(p,age*1.1,0.018+u_amount*0.035); col=vec3(0.025,0.04,0.07)+u_color.rgb*ring*(1.0-age)*2.0;")
    if slug in ["lava", "magma", "burning"]:
        return canvas("""
        vec2 q=uv*9.0*u_scale+vec2(t*0.18,-t*0.12);
        float crust=cells(q+fbm(q)*0.6).y;
        float hot=1.0-smoothstep(0.025,0.11+u_amount*0.07,crust);
        col=mix(vec3(0.045,0.025,0.03),vec3(1.0,0.16,0.008),hot);
        col+=vec3(1.0,0.6,0.05)*pow(hot,8.0)*0.7;
""")
    if slug == "distortion":
        return canvas("vec2 offset=vec2(fbm(uv*12.0-vec2(0,t*2.0))-0.5,0.0)*0.05*u_amount; col=texture(screen_texture,uv+offset).rgb;", post=True)
    if slug == "explosion":
        return canvas("""
        float age=fract(t*0.28), r=length(p);
        float cloud=fbm(p*5.0*u_scale+vec2(t,0));
        float mask=1.0-smoothstep(age*1.0,age*1.0+0.13,r+cloud*0.25);
        col=mix(vec3(0.025,0.035,0.06),mix(vec3(1.0,0.07,0.008),vec3(1.0,0.9,0.3),clamp((1.0-r)*cloud*2.0,0.0,1.0)),mask*(1.0-age));
""")
    jet = "p=vec2(p.y,p.x);" if slug == "jet" else ""
    return canvas(jet + """
        vec2 q=vec2(p.x*1.5,(1.0-uv.y));
        float turbulence=fbm(vec2(q.x*6.0*u_scale,q.y*5.0-t*2.0));
        float flame=1.0-smoothstep(0.40,0.64,abs(q.x)+q.y*0.58+(turbulence-0.5)*0.4);
        flame*=smoothstep(0.0,0.08,q.y);
""" + ("flame=step(0.4,flame);" if slug == "toon_flame" else "") + """
        col=mix(vec3(0.025,0.035,0.06),mix(vec3(1.0,0.10,0.005),vec3(1.0,0.88,0.28),pow(flame,3.0)*(1.0-uv.y)*0.9+flame*0.5),flame);
""")


def terrain(slug, index):
    palette = {
        "snow": ("vec3(0.16,0.24,0.20)", "vec3(0.9,0.94,1.0)"),
        "melt": ("vec3(0.20,0.15,0.08)", "vec3(0.86,0.93,1.0)"),
        "frost": ("vec3(0.15,0.3,0.35)", "vec3(0.68,0.91,1.0)"),
        "moss": ("vec3(0.25,0.24,0.19)", "vec3(0.22,0.46,0.08)"),
        "dust": ("vec3(0.13,0.2,0.24)", "vec3(0.65,0.52,0.32)"),
        "mud": ("vec3(0.27,0.38,0.17)", "vec3(0.23,0.12,0.055)"),
        "rust": ("vec3(0.34,0.42,0.45)", "vec3(0.56,0.17,0.045)"),
        "oil": ("vec3(0.09,0.11,0.13)", "rainbow(fbm(uv*5.0)*2.0+rim)"),
        "char": ("vec3(0.52,0.3,0.13)", "vec3(0.025,0.02,0.017)"),
    }
    a,b=palette.get(slug, ("vec3(0.38,0.27,0.14)", "u_color.rgb"))
    mask = "smoothstep(u_amount-0.08,u_amount+0.08,fbm(uv*8.0))"
    extra = ""
    if slug == "slope": mask = "smoothstep(u_amount-0.1,u_amount+0.1,NORMAL.y)"
    if slug == "height_blend": mask = "smoothstep(u_amount-0.08,u_amount+0.08,fbm(uv*8.0)+v_local.y*0.4)"
    if slug == "vertex_blend": mask = "COLOR.r"
    if slug in ["wet", "puddle", "road"]:
        extra = "ROUGHNESS=mix(0.85,0.045,1.0-mask); METALLIC=(1.0-mask)*0.35;"
        a,b="vec3(0.035,0.08,0.1)","vec3(0.28,0.3,0.31)"
    if slug == "scratch":
        mask="step(0.97,sin(uv.x*180.0+fbm(uv*20.0)*8.0))*step(0.5,fbm(uv*6.0))"
    if slug == "crack":
        mask="1.0-smoothstep(0.015,0.04+u_amount*0.05,cells(uv*10.0).y)"
        b="vec3(0.035,0.025,0.02)"
    if slug in ["footprint", "snow_track"]:
        mask="1.0-smoothstep(0.12,0.16,length((fract(uv*vec2(4,6))-0.5)*vec2(2.0,1.0)))"
        a,b=("vec3(0.84,0.9,0.96)","vec3(0.35,0.48,0.56)") if slug=="snow_track" else ("vec3(0.53,0.4,0.24)","vec3(0.22,0.15,0.09)")
    if slug == "tire":
        mask="step(abs(UV.x-0.5),0.25)*step(0.45,fract(uv.y*40.0+step(0.0,UV.x-0.5)*0.5))"
        b="vec3(0.1,0.08,0.045)"
    vertex="VERTEX.y += (fbm(VERTEX.xz*1.4)-0.5)*0.4; NORMAL=normalize(vec3(-0.15*cos(VERTEX.x*4.0),1.0,0.12*sin(VERTEX.z*3.0)));"
    return spatial(f"float mask={mask}; ALBEDO=mix({a},{b},mask); ROUGHNESS=0.78; {extra}", vertex)


def sky_effect(slug, index):
    if slug in ["distance_fog","height_fog","local_fog","volume_fog","light_column","god_rays"]:
        return spatial("ALBEDO=u_color.rgb; ROUGHNESS=0.4;"), "pipeline"
    if slug in ["rain","snow","sand","dust"]:
        direction = "vec2(t*0.3,t*1.6)" if slug=="rain" else "vec2(t*0.13,t*0.25)"
        body=f"""
        col=mix(vec3(0.025,0.05,0.09),vec3(0.13,0.22,0.3),uv.y);
        vec2 q=uv*vec2(24.0,16.0)*u_scale+{direction};
        vec2 cell=floor(q), f=fract(q)-0.5;
        float radius=0.03+h21(cell)*0.08;
        float particle=1.0-smoothstep(radius,radius+0.03,length(f*{"vec2(3.0,0.3)" if slug=="rain" else "vec2(1.0)"}));
        col+=vec3(0.75,0.85,0.95)*particle*(0.3+u_amount);
"""
        return canvas(body), "canvas"
    body="""
        vec3 night=vec3(0.008,0.018,0.065);
        vec3 daylight=mix(vec3(0.05,0.24,0.52),vec3(0.84,0.66,0.46),uv.y);
        col=daylight;
"""
    additions={
        "gradient": "col=mix(u_color.rgb*0.2,vec3(0.8,0.55,0.4),uv.y);",
        "procedural": "float sun=exp(-length(uv-vec2(0.72,0.3))*25.0); col+=vec3(1.0,0.72,0.3)*sun; col+=pow(fbm(uv*vec2(5,9)+vec2(t*0.03,0)),4.0)*1.2;",
        "day_night": "float daylight_amount=0.5+0.5*sin(t*0.25); col=mix(night,daylight,daylight_amount);",
        "stars": "vec2 grid=uv*vec2(110,75)*u_scale; float star=step(0.985,h21(floor(grid)))*(1.0-smoothstep(0.02,0.18,length(fract(grid)-0.5))); col=night+vec3(star);",
        "twinkle": "vec2 grid=uv*vec2(110,75)*u_scale; float star=step(0.98,h21(floor(grid)))*(1.0-smoothstep(0.02,0.15,length(fract(grid)-0.5))); col=night+vec3(star*(0.5+0.5*sin(t*3.0+h21(floor(grid))*40.0)));",
        "sun": "float r=length(uv-vec2(0.6,0.35)); col+=vec3(1.0,0.7,0.3)*(exp(-r*15.0)+1.0-smoothstep(0.06,0.067,r));",
        "moon": "float r=length(uv-vec2(0.6,0.35)); col=night+vec3(0.55,0.7,0.95)*(exp(-r*12.0)*0.3+(1.0-smoothstep(0.055,0.06,r))*(0.8+n2(uv*180.0)*0.2));",
        "clouds": "float cloud=fbm(uv*vec2(6,10)*u_scale+vec2(t*0.06,0)); col=mix(col,vec3(0.9,0.91,0.89),smoothstep(0.42,0.7-u_amount*0.15,cloud));",
        "volume_clouds": "float density=0.0; for(int i=0;i<12;i++){ density+=smoothstep(0.43,0.75,fbm(uv*vec2(5,8)*u_scale+vec2(float(i)*0.06+t*0.04,float(i)*0.09)))*0.09; } col=mix(col,vec3(0.85,0.88,0.9),1.0-exp(-density*2.0));",
        "aurora": "float curtain=pow(max(0.0,1.0-abs(uv.y-(0.4+sin(uv.x*9.0+t*0.3)*0.08+fbm(vec2(uv.x*8.0,t*0.1))*0.2))*5.0),3.0); col=night+mix(u_color.rgb,vec3(0.47,0.25,1),uv.x)*curtain*(0.5+0.5*n2(vec2(uv.x*140.0,t*0.5)));",
    }
    return canvas(body+additions[slug]), "canvas"


def magic(slug, index):
    if slug in ["shield","hex_shield","shield_hit","hologram","holo_scan","digital"]:
        patterns={
            "shield": "float field=0.1+rim;",
            "hex_shield": "vec2 q=uv*vec2(22.0,13.0); q.x+=mod(floor(q.y),2.0)*0.5; float field=0.1+rim+0.5*(1.0-smoothstep(0.38,0.46,length(fract(q)-0.5)));",
            "shield_hit": """float field=rim;
            float age=u_time-u_event_time;
            if (u_event_time>=0.0 && age>=0.0 && age<u_duration) {
                float arc=acos(clamp(dot(normalize(v_local),normalize(u_hit_position)),-1.0,1.0))*length(u_hit_position);
                field+=exp(-pow((arc-age*1.5)/0.08,2.0))*(1.0-age/u_duration)*2.0;
            }""",
            "hologram": "float field=rim+step(0.6,sin(v_world.y*75.0*u_scale-t*5.0))*0.2;",
            "holo_scan": "float field=rim+exp(-abs(v_local.y-(fract(t*0.3)*2.0-1.0))*25.0);",
            "digital": "float field=step(0.45,h21(floor(uv*vec2(45,28))+floor(t*4.0)))*(0.25+rim);",
        }
        body=patterns[slug]+" ALBEDO=u_color.rgb*(0.12+field*(1.0+u_amount*2.0)); ALPHA=clamp(0.15+field*0.65,0.0,0.9);"
        extra = "uniform vec3 u_hit_position = vec3(0.0,0.0,0.92);\nuniform float u_event_time = -1.0;\nuniform float u_duration = 1.0;\n" if slug == "shield_hit" else ""
        return spatial(body,extra=extra,modes="unshaded"),"spatial"
    if slug in ["beam","laser","arc","lightning","slash","sword","trail","afterimage"]:
        center = "sin(uv.y*24.0+t*4.0)*0.015"
        if slug in ["arc","lightning"]: center="(fbm(vec2(uv.y*18.0,floor(t*12.0)))-0.5)*0.45"
        if slug in ["slash","sword"]: center="sin(uv.y*3.14159)*0.4-0.2"
        if slug in ["trail","afterimage"]: center="sin(uv.y*7.0-t*2.0)*0.18"
        width = "0.008" if slug=="laser" else "0.025+u_amount*0.04"
        return canvas(f"float center={center}; float d=abs(p.x-center); float beam=exp(-d/(0.008+{width})); col=vec3(0.025,0.035,0.07)+u_color.rgb*(beam+0.008/(d+0.01));"),"canvas"
    patterns={
        "core":"exp(-length(p)*7.0)*3.0+ring_sdf(p,0.28+sin(t*2.0)*0.025,0.025)",
        "portal":"ring_sdf(p,0.56+fbm(p*6.0+t)*0.08,0.04)+0.12/(0.08+abs(length(p)-0.62))",
        "rift":"exp(-abs(p.x+sin(p.y*15.0+t)*0.035)*55.0)*(0.5+fbm(p*10.0+t))",
        "circle":"ring_sdf(p,0.65,0.018)+ring_sdf(p,0.48,0.012)+ring_sdf(p,0.3,0.015)+step(0.85,cos(atan(p.y,p.x)*12.0-t))*ring_sdf(p,0.56,0.05)",
        "runes":"step(0.55,sin(atan(p.y,p.x)*14.0-t*1.5))*step(0.1,sin(length(p)*85.0))*ring_sdf(p,0.55,0.1)",
        "summon":"ring_sdf(p,0.66,0.02)+ring_sdf(p,0.36,0.02)+step(0.93,cos(atan(p.y,p.x)*6.0+t))*smoothstep(0.7,0.0,length(p))",
        "charge":"ring_sdf(p,0.28+fract(t*0.4)*0.5,0.025)*(1.0-fract(t*0.4))+ring_sdf(p,0.28,0.045)",
        "shock_ring":"ring_sdf(p,fract(t*0.6)*1.1,0.025)*(1.0-fract(t*0.6))*3.0",
        "black_hole":"0.05/(0.02+abs(length(p)-0.35))*step(0.35,length(p))*(0.6+sin(atan(p.y,p.x)*8.0+length(p)*40.0-t*3.0)*0.25)",
        "nebula":"pow(fbm(p*3.0+vec2(t*0.04,0)),3.0)*3.0+step(0.998,h21(floor(uv*300.0)))",
    }
    return canvas("float signal="+patterns[slug]+"; col=vec3(0.018,0.025,0.06)+mix(u_color.rgb,vec3(0.55,0.22,1.0),fbm(p*4.0))*signal*(0.4+u_amount*1.4);"),"canvas"


def status(slug, index):
    bodies={
        "white":"ALBEDO=mix(ALBEDO,vec3(1),u_amount*(0.5+0.5*sin(t*4.0)));",
        "red":"ALBEDO=mix(ALBEDO,vec3(1,0.04,0.02),u_amount*(0.5+0.5*sin(t*4.0)));",
        "invincible":"EMISSION=rainbow(t*0.3)*u_amount; ALPHA=0.45+0.5*step(0.0,sin(t*14.0));",
        "heal":"float band=exp(-abs(UV.y-fract(t*0.3))*30.0); EMISSION=vec3(0.15,1.0,0.4)*band*3.0;",
        "poison":"ALBEDO=mix(ALBEDO,vec3(0.5,0.1,0.7),u_amount); EMISSION=vec3(0.4,0.1,0.7)*fbm(uv*8.0+t)*0.5;",
        "burn":"float fire=1.0-smoothstep(0.02,0.08,cells(uv*12.0+t*0.15).y); ALBEDO=vec3(0.045,0.025,0.02); EMISSION=vec3(1,0.12,0.01)*fire*2.0;",
        "freeze":"float mask=smoothstep(u_amount-0.1,u_amount+0.1,UV.y); ALBEDO=mix(vec3(0.6,0.88,1.0),ALBEDO,mask); ROUGHNESS=0.12;",
        "ice":"ALBEDO=vec3(0.25,0.65,0.85); ROUGHNESS=0.08; METALLIC=0.3; EMISSION=vec3(0.3,0.7,1.0)*rim;",
        "stone":"float grain=fbm(uv*24.0); ALBEDO=vec3(0.3,0.32,0.3)*(0.6+grain); ROUGHNESS=0.95;",
        "metal":"ALBEDO=mix(ALBEDO,vec3(0.7,0.75,0.8),u_amount); METALLIC=u_amount; ROUGHNESS=0.16;",
        "gold":"ALBEDO=vec3(0.83,0.49,0.10); METALLIC=1.0; ROUGHNESS=0.14;",
        "infection":"float mask=1.0-smoothstep(u_amount-0.05,u_amount+0.05,fbm(uv*10.0)); ALBEDO=mix(ALBEDO,vec3(0.18,0.03,0.25),mask); EMISSION=vec3(0.55,0.08,0.8)*mask*0.2;",
        "cracks":"float crack=1.0-smoothstep(0.015,0.035,cells(uv*9.0).y); ALBEDO*=1.0-crack*0.8; EMISSION=u_color.rgb*crack*u_amount*2.0;",
        "wound":"float wound=exp(-abs(UV.x-0.5-sin(UV.y*35.0)*0.02)*100.0)*step(abs(UV.y-0.5),u_amount*0.3); ALBEDO=mix(ALBEDO,vec3(0.3,0.005,0.015),wound);",
        "damage":"float damage=step(fbm(uv*12.0),u_amount*0.75); ALBEDO=mix(ALBEDO,vec3(0.065,0.035,0.02),damage); ROUGHNESS=0.9;",
        "ghost":"ALBEDO=vec3(0.08,0.3,0.4); EMISSION=u_color.rgb*rim*2.0; ALPHA=0.1+rim*0.6;",
        "death":"float n=fbm(uv*10.0); if(n<u_amount){discard;} EMISSION=u_color.rgb*(1.0-smoothstep(u_amount,u_amount+0.08,n))*2.0;",
    }
    return spatial(bodies[slug])


def vertex_effect(slug, index):
    cases={
        "wave":"VERTEX.y+=sin(VERTEX.x*4.0*u_scale+t*2.0)*u_amount*0.45;",
        "flag":"VERTEX.z+=sin(VERTEX.x*4.0+t*3.0)*sin(UV.x*1.5708)*u_amount*0.5;",
        "wind":"VERTEX.x+=sin(t*2.0+VERTEX.x*2.0)*pow(UV.y,2.0)*u_amount*0.5;",
        "leaves":"VERTEX+=NORMAL*sin(t*8.0+VERTEX.x*12.0+VERTEX.z*14.0)*u_amount*0.09;",
        "jelly":"VERTEX.x+=sin(VERTEX.y*6.0+t*4.0)*u_amount*0.15; VERTEX.z+=cos(VERTEX.y*7.0+t*3.0)*u_amount*0.15;",
        "squash":"float s=sin(t*3.0)*u_amount*0.35; VERTEX*=vec3(1.0-s*0.5,1.0+s,1.0-s*0.5);",
        "breathing":"VERTEX*=1.0+sin(t*2.0)*u_amount*0.12;",
        "bend":"float a=VERTEX.y*u_amount; VERTEX.xy=rot(a)*VERTEX.xy;",
        "twist":"VERTEX.xz=rot(VERTEX.y*u_amount*3.0+sin(t)*0.3)*VERTEX.xz;",
        "sphere":"VERTEX=mix(VERTEX,normalize(VERTEX)*0.95,u_amount);",
        "inflate":"VERTEX+=NORMAL*(0.5+0.5*sin(t*2.0))*u_amount*0.35;",
        "explode":"VERTEX+=NORMAL*(0.5+0.5*sin(t))*u_amount*(0.2+h21(UV)*0.5);",
        "vortex":"float a=u_amount*(1.0+VERTEX.y)*3.0+sin(t); VERTEX.xz=rot(a)*VERTEX.xz; VERTEX.xz*=1.0-u_amount*0.5;",
        "snap":"float resolution=8.0+u_amount*22.0; VERTEX=floor(VERTEX*resolution+0.5)/resolution;",
        "vat":"vec3 offset=textureLod(vat_texture,vec2(UV.x,fract(t*0.2)),0.0).rgb*2.0-1.0; VERTEX+=offset*u_amount*0.5;",
        "billboard":"MODELVIEW_MATRIX=VIEW_MATRIX*mat4(INV_VIEW_MATRIX[0],INV_VIEW_MATRIX[1],INV_VIEW_MATRIX[2],MODEL_MATRIX[3]); MODELVIEW_NORMAL_MATRIX=mat3(MODELVIEW_MATRIX);",
    }
    extra="uniform sampler2D vat_texture : repeat_enable, filter_linear;\n" if slug=="vat" else ""
    return spatial("ALBEDO=mix(u_color.rgb,vec3(0.12,0.25,0.5),step(0.5,fract(uv.x*12.0))+step(0.5,fract(uv.y*12.0))*0.3); ROUGHNESS=0.45;",cases[slug],extra=extra,modes="cull_disabled")


def uv_effect(slug, index):
    if slug=="triplanar":
        return spatial("vec3 weights=abs(normalize(v_local)); weights/=max(weights.x+weights.y+weights.z,0.001); float x=n2(v_world.yz*8.0*u_scale), y=n2(v_world.xz*8.0*u_scale), z=n2(v_world.xy*8.0*u_scale); ALBEDO=mix(vec3(0.08,0.16,0.24),u_color.rgb,dot(vec3(x,y,z),weights));"),"spatial"
    if slug in ["parallax","pom"]:
        body="""
        vec2 direction=VIEW.xy/max(abs(VIEW.z),0.15)*0.05*u_amount;
        vec2 q=uv;
"""
        if slug=="pom":
            body+="""
        float layer=0.0;
        for(int i=0;i<24;i++) {
            float height=fbm(q*8.0);
            if(layer>height){break;}
            q-=direction/24.0;
            layer+=1.0/24.0;
        }
"""
        else: body+="q-=direction*fbm(q*8.0);\n"
        body+="float height=fbm(q*8.0); ALBEDO=mix(vec3(0.12,0.07,0.04),vec3(0.7,0.5,0.24),height); ROUGHNESS=0.75;"
        return spatial(body),"spatial"
    transformations={
        "scroll":"q+=vec2(t*0.12,t*0.04);",
        "rotate":"q=rot(t*0.4)*(q-0.5)+0.5;",
        "zoom":"q=(q-0.5)*(0.6+u_amount*3.0)+0.5;",
        "distort":"q+=vec2(sin(q.y*18.0+t*2.0),cos(q.x*17.0+t))*0.04*u_amount;",
        "polar":"q=vec2(atan(p.y,p.x)/TAU_+0.5,length(p));",
        "kaleidoscope":"float a=atan(p.y,p.x); a=abs(mod(a,TAU_/6.0)-TAU_/12.0); q=vec2(cos(a),sin(a))*length(p)+0.5;",
        "flowmap":"vec2 flow=vec2(sin(q.y*8.0),cos(q.x*8.0)); float phase=fract(t*0.2); q+=flow*phase*0.3*u_amount;",
        "flipbook":"float frame=mod(floor(t*8.0),16.0); q=(q+vec2(mod(frame,4.0),floor(frame/4.0)))/4.0;",
        "random_tile":"vec2 cell=floor(q*4.0); q=fract(q*4.0)+vec2(h21(cell),h21(cell+8.0));",
        "stochastic":"vec2 cell=floor(q*5.0); q=rot(h21(cell)*TAU_)*(fract(q*5.0)-0.5)+0.5;",
    }
    if slug in transformations:
        return canvas("vec2 q=uv*u_scale; "+transformations[slug]+" vec2 checker_cell=floor(q*8.0); float check=mod(checker_cell.x+checker_cell.y,2.0); col=mix(vec3(0.04,0.1,0.17),u_color.rgb,check); col=mix(col,texture(TEXTURE,fract(q)).rgb,texture(TEXTURE,fract(q)).a*0.75);"),"canvas"
    if slug=="interior":
        return canvas("vec2 q=fract(uv*vec2(4,3)*u_scale); vec2 perspective=(q-0.5)*(1.0+u_amount*1.5); float room=1.0-step(0.42,max(abs(perspective.x),abs(perspective.y))); float frame=step(0.045,min(min(q.x,1.0-q.x),min(q.y,1.0-q.y))); col=mix(vec3(0.12,0.17,0.23),mix(vec3(0.14,0.09,0.1),vec3(0.9,0.6,0.28),room),frame);"),"canvas"
    fields={
        "noise":"fbm(uv*12.0*u_scale+vec2(t*0.1,0))",
        "voronoi":"cells(uv*12.0*u_scale).x",
        "wood":"0.5+0.5*sin(uv.y*90.0*u_scale+fbm(uv*vec2(3,15))*20.0)",
        "marble":"0.5+0.5*sin(uv.x*14.0*u_scale+fbm(uv*7.0)*15.0)",
        "stone":"fbm(uv*35.0*u_scale)*0.7+n2(uv*150.0)*0.3",
        "checker":"mod(floor(uv.x*16.0*u_scale)+floor(uv.y*16.0*u_scale),2.0)",
        "camouflage":"floor(fbm(uv*12.0*u_scale)*4.0)/3.0",
        "cracks":"1.0-smoothstep(0.015,0.05,cells(uv*12.0*u_scale).y)",
    }
    return canvas("float value="+fields[slug]+"; col=mix(vec3(0.035,0.085,0.13),u_color.rgb,value);"),"canvas"


def sprite_effect(slug, index):
    if slug=="outline": return outline("outer",0)[0]
    if slug=="glow": return outline("glow",0)[0]
    if slug in ["dissolve","spine"]: return dissolve("noise",0)
    if slug in ["text_outline"]: return outline("outer",0)[0]
    treatments={
        "shadow":"float shadow_alpha=texture(TEXTURE,uv-vec2(0.035,0.045)*(0.5+u_amount)).a; out_color=mix(vec4(0.02,0.03,0.05,shadow_alpha*0.85),base,base.a);",
        "flash":"out_color.rgb=mix(base.rgb,vec3(1),u_amount*(0.5+0.5*sin(t*4.0)));",
        "recolor":"float mask=step(base.g,base.b+0.15)*step(base.r,base.b); out_color.rgb=mix(base.rgb,u_color.rgb,mask*u_amount);",
        "palette":"float l=dot(base.rgb,vec3(0.299,0.587,0.114)); out_color.rgb=mix(vec3(0.05,0.1,0.18),u_color.rgb,floor(l*5.0)/4.0);",
        "color_key":"float distance_to_key=length(base.rgb-vec3(0.2,0.7,0.6)); out_color.a*=smoothstep(u_amount*0.8,u_amount*0.8+0.08,distance_to_key);",
        "pixel":"float count=12.0+u_amount*80.0; out_color=texture(TEXTURE,(floor(uv*count)+0.5)/count);",
        "dither":"out_color.a*=step(h21(floor(FRAGCOORD.xy)),u_amount);",
        "pixel_light":"vec2 q=(floor(uv*40.0)+0.5)/40.0; float lighting=clamp(1.0-length(q-u_mouse)*1.4,0.1,1.0); out_color.rgb=floor(base.rgb*lighting*6.0)/6.0;",
        "normal_light":"vec2 d=TEXTURE_PIXEL_SIZE*2.0; float dx=texture(TEXTURE,uv+d*vec2(1,0)).a-texture(TEXTURE,uv-d*vec2(1,0)).a; float dy=texture(TEXTURE,uv+d*vec2(0,1)).a-texture(TEXTURE,uv-d*vec2(0,1)).a; vec3 n=normalize(vec3(-dx*4.0,-dy*4.0,1.0)); vec3 light=normalize(vec3(u_mouse-uv,0.2)); out_color.rgb=base.rgb*(0.2+max(0.0,dot(n,light)));",
        "bend":"vec2 q=uv; q.x+=sin(uv.y*3.14159)*u_amount*0.15*sin(t); out_color=texture(TEXTURE,q);",
        "page":"vec2 q=uv; float fold=u_amount; q.x=abs(q.x-fold)+fold; out_color=texture(TEXTURE,q); out_color.rgb*=0.5+0.5*smoothstep(0.0,0.15,abs(uv.x-fold));",
        "reflection":"vec2 q=uv; q.y=abs(uv.y-0.5)*1.8; q.x+=sin(q.y*80.0+t*3.0)*0.009*u_amount; out_color=texture(TEXTURE,q); out_color.a*=uv.y>0.5 ? (1.0-uv.y)*1.3 : 1.0; out_color.rgb*=uv.y>0.5 ? vec3(0.5,0.75,0.9) : vec3(1.0);",
        "distort":"out_color=texture(TEXTURE,uv+vec2(sin(uv.y*30.0+t*3.0),cos(uv.x*20.0+t))*0.02*u_amount);",
    }
    return canvas(treatments[slug],sprite=True)


def ui_effect(slug, index):
    if slug in ["gradient_text","text_outline","text_shadow","text_shine","text_wave","typewriter"]:
        if slug=="text_outline": return outline("outer",0)[0],"sprite"
        if slug=="text_shadow": return sprite_effect("shadow",0),"sprite"
        bodies={
            "gradient_text":"out_color.rgb=mix(u_color.rgb,vec3(0.75,0.35,1.0),uv.x);",
            "text_shine":"float band=exp(-pow((uv.x+uv.y*0.3-fract(t*0.3))*12.0,2.0)); out_color.rgb+=u_color.rgb*band*2.0;",
            "text_wave":"out_color=texture(TEXTURE,uv+vec2(0,sin(uv.x*20.0+t*3.0)*0.04*u_amount));",
            "typewriter":"out_color.a*=step(uv.x,u_amount);",
        }
        return canvas(bodies[slug],sprite=True),"sprite"
    if slug=="frosted":
        return canvas("vec3 blurred=textureLod(screen_texture,uv,2.0+u_amount*4.0).rgb; float mask=1.0-smoothstep(-0.01,0.01,box_sdf(p,vec2(0.65,0.47),0.08)); col=mix(col,mix(blurred,u_color.rgb,0.12),mask);",post=True),"post"
    bg="col=vec3(0.025,0.045,0.075);"
    bodies={
        "gradient":"float mask=1.0-smoothstep(-0.008,0.008,box_sdf(p,vec2(0.7,0.4),0.08)); col=mix(col,mix(u_color.rgb,vec3(0.6,0.3,1),uv.x),mask);",
        "button_shine":"float mask=1.0-smoothstep(-0.008,0.008,box_sdf(p,vec2(0.7,0.2),0.08)); float band=exp(-pow((uv.x+uv.y*0.3-fract(t*0.25))*12.0,2.0)); col=mix(col,u_color.rgb*0.35+vec3(band)*0.7,mask);",
        "border":"float d=box_sdf(p,vec2(0.7,0.4),0.09); float border=1.0-smoothstep(0.012,0.025,abs(d)); col+=u_color.rgb*border*(0.3+pow(max(0.0,sin(atan(p.y,p.x)-t*2.0)),10.0)*3.0);",
        "rounded":"float d=box_sdf(p,vec2(0.68,0.42),u_amount*0.4); col=mix(col,u_color.rgb,1.0-smoothstep(-0.004,0.004,d));",
        "feather":"float mask=1.0-smoothstep(0.2,0.2+u_amount*0.6,length(p)); col=mix(col,u_color.rgb,mask);",
        "clip":"float mask=smoothstep(0.2-u_amount*0.2,0.3,uv.x)*(1.0-smoothstep(0.7,0.8+u_amount*0.15,uv.x)); col=mix(col,base.rgb,mask*base.a);",
        "ring":"float angle=fract(atan(p.x,-p.y)/TAU_+1.0); float ring=ring_sdf(p,0.55,0.07); col+=mix(vec3(0.10,0.17,0.23),u_color.rgb,step(angle,u_amount))*ring;",
        "cooldown":"float angle=fract(atan(p.x,-p.y)/TAU_+1.0); float disk=1.0-smoothstep(0.55,0.56,length(p)); col+=mix(vec3(0.08,0.13,0.2),u_color.rgb,step(angle,u_amount))*disk;",
        "liquid":"float mask=1.0-smoothstep(0.65,0.66,length(p)); float level=1.0-u_amount+sin(uv.x*18.0+t*3.0)*0.025; col+=mix(vec3(0.08,0.16,0.23),u_color.rgb,step(level,uv.y))*mask;",
        "health":"float mask=1.0-smoothstep(-0.005,0.005,box_sdf(p,vec2(0.75,0.1),0.04)); col+=mix(vec3(0.13,0.17,0.22),mix(vec3(1,0.1,0.1),u_color.rgb,step(0.3,u_amount)),step(uv.x,0.125+u_amount*0.75))*mask*(0.85+0.15*sin(t*8.0));",
        "radar":"float angle=fract(atan(p.y,p.x)/TAU_-t*0.15); float sweep=pow(1.0-angle,12.0); float grid=ring_sdf(p,0.25,0.006)+ring_sdf(p,0.5,0.006)+ring_sdf(p,0.75,0.006); col+=u_color.rgb*(sweep*0.65+grid*0.4)*step(length(p),0.8);",
        "fog_of_war":"float terrain=fbm(uv*15.0); vec3 map_color=mix(vec3(0.14,0.23,0.1),vec3(0.49,0.43,0.22),terrain); float vision=1.0-smoothstep(0.16,0.16+u_amount*0.4,length(uv-u_mouse)); col=mix(vec3(0.025,0.035,0.055),map_color,vision);",
        "vision":"float vision=1.0-smoothstep(u_amount*0.4,u_amount*0.4+0.08,length(uv-u_mouse)); col=mix(base.rgb*0.08,base.rgb,vision);",
        "contours":"float height=fbm(uv*7.0*u_scale); float line=1.0-smoothstep(0.025,0.09,abs(fract(height*18.0)-0.5)); col=mix(vec3(0.05,0.12,0.16),u_color.rgb,line*0.65);",
        "dashed_path":"float path=exp(-pow((uv.y-0.5-sin(uv.x*8.0)*0.12)*60.0,2.0)); col+=u_color.rgb*path*step(0.4,fract(uv.x*22.0-t*2.0));",
        "arrows":"vec2 q=vec2(fract(uv.x*8.0-t)-0.5,(uv.y-0.5)*5.0); float arrow=step(abs(q.y),0.22-q.x*0.7)*step(abs(q.x),0.3); col+=u_color.rgb*arrow;",
    }
    return canvas(bg+bodies[slug]),"canvas"


def color_effect(slug, index):
    bodies={
        "brightness":"col+=u_amount*0.65-0.15;",
        "contrast":"col=(col-0.5)*(0.3+u_amount*3.0)+0.5;",
        "saturation":"col=mix(vec3(dot(col,vec3(0.299,0.587,0.114))),col,u_amount*2.5);",
        "hue":"vec3 axis=normalize(vec3(1)); float angle=u_amount*TAU_; col=col*cos(angle)+cross(axis,col)*sin(angle)+axis*dot(axis,col)*(1.0-cos(angle));",
        "grayscale":"col=mix(col,vec3(dot(col,vec3(0.299,0.587,0.114))),u_amount);",
        "invert":"col=mix(col,vec3(1)-col,u_amount);",
        "duotone":"float l=dot(col,vec3(0.299,0.587,0.114)); col=mix(vec3(0.06,0.09,0.21),u_color.rgb,l);",
        "gradient_map":"float l=dot(col,vec3(0.299,0.587,0.114)); col=mix(mix(vec3(0.11,0.03,0.25),u_color.rgb,smoothstep(0.0,0.6,l)),vec3(1,0.8,0.4),smoothstep(0.5,1.0,l));",
        "posterize":"float levels=2.0+floor(u_amount*10.0); col=floor(col*levels)/levels;",
        "quantize":"vec3 levels=vec3(3.0,5.0,3.0)+floor(u_amount*vec3(6,7,5)); col=floor(col*levels)/levels;",
        "lut":"float z=col.b*15.0; vec2 a=vec2((col.r*15.0+floor(z)*16.0+0.5)/256.0,(col.g*15.0+0.5)/16.0); vec2 b=a+vec2(16.0/256.0,0); vec3 mapped=mix(texture(lut_texture,a).rgb,texture(lut_texture,b).rgb,fract(z)); col=mix(col,mapped,u_amount);",
        "temperature":"col*=mix(vec3(0.7,0.9,1.25),vec3(1.3,0.92,0.65),u_amount);",
        "white_balance":"col*=mix(vec3(0.83,1.1,1.05),vec3(1.16,0.86,0.97),u_amount);",
        "exposure":"col*=pow(2.0,u_amount*5.0-1.5);",
        "tonemap":"vec3 hdr=col*(0.5+u_amount*4.0); col=(hdr*(2.51*hdr+0.03))/(hdr*(2.43*hdr+0.59)+0.14);",
        "local":"float mask=1.0-smoothstep(0.15,0.35,length(uv-u_mouse)); col=mix(col,col*u_color.rgb*1.8,mask*u_amount);",
        "night":"float l=dot(col,vec3(0.299,0.587,0.114)); col=vec3(0.05,1.0,0.2)*l*(1.0+u_amount)+vec3(h21(FRAGCOORD.xy+floor(t*30.0))*0.035);",
        "thermal":"col=thermal(dot(col,vec3(0.299,0.587,0.114)));",
        "damage":"float edge=smoothstep(0.15,0.65,length(uv-0.5)); col=mix(col,vec3(0.65,0.015,0.025),edge*u_amount*(0.75+0.25*sin(t*4.0)));",
    }
    extra="uniform sampler2D lut_texture : repeat_disable, filter_linear;\n" if slug=="lut" else ""
    return canvas(bodies[slug],post=True,extra=extra)


def depth_shader(slug):
    body={
        "depth":"col=vec3(clamp(linear_depth/(3.0+u_amount*12.0),0.0,1.0));",
        "dof":"float circle_of_confusion=clamp(abs(linear_depth-5.0)*0.4*u_amount,0.0,4.0); col=textureLod(screen_texture,SCREEN_UV,circle_of_confusion).rgb;",
        "bokeh":"float circle_of_confusion=clamp(abs(linear_depth-4.7)*0.4*u_amount,0.0,1.0); vec3 sum=vec3(0); for(int i=0;i<12;i++){float a=float(i)*2.39996; vec2 offset=vec2(cos(a),sin(a))*sqrt(float(i)/12.0)*0.03*circle_of_confusion; sum+=texture(screen_texture,SCREEN_UV+offset).rgb;} col=sum/12.0;",
    }[slug]
    return """shader_type spatial;
render_mode unshaded, fog_disabled, depth_draw_never, depth_test_disabled;
uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform sampler2D depth_texture : hint_depth_texture, filter_nearest;
""" + COMMON + """
void vertex() { POSITION=vec4(VERTEX.xy,1.0,1.0); }
void fragment() {
    vec3 col=texture(screen_texture,SCREEN_UV).rgb;
    float depth_value=texture(depth_texture,SCREEN_UV).r;
    vec4 position_view=INV_PROJECTION_MATRIX*vec4(SCREEN_UV*2.0-1.0,depth_value,1.0);
    float linear_depth=-position_view.z/position_view.w;
    if(u_enabled) {
""" + body + """
    }
    ALBEDO=col;
}
"""


def lens(slug,index):
    if slug in ["dof","bokeh"]: return depth_shader(slug),"depth"
    blur="vec2 radius=SCREEN_PIXEL_SIZE*(1.0+u_amount*12.0); col=blur9(screen_texture,uv,radius).rgb;"
    bodies={
        "gaussian":blur,
        "kawase":"vec2 d=SCREEN_PIXEL_SIZE*(1.0+u_amount*18.0); col=(texture(screen_texture,uv+d).rgb+texture(screen_texture,uv-d).rgb+texture(screen_texture,uv+vec2(d.x,-d.y)).rgb+texture(screen_texture,uv+vec2(-d.x,d.y)).rgb)*0.25;",
        "bilateral":"vec3 sum=col; float total=1.0; for(int i=0;i<8;i++){float angle=float(i)*TAU_/8.0; vec3 c=texture(screen_texture,uv+vec2(cos(angle),sin(angle))*SCREEN_PIXEL_SIZE*(2.0+u_amount*14.0)).rgb; float weight=exp(-length(c-col)*18.0); sum+=c*weight; total+=weight;} col=sum/total;",
        "directional":"vec3 sum=vec3(0); for(int i=-5;i<=5;i++){sum+=texture(screen_texture,uv+vec2(float(i)*u_amount*0.006,0)).rgb;} col=sum/11.0;",
        "motion":"vec3 sum=vec3(0); vec2 velocity=vec2(sin(t)*0.012,cos(t*0.7)*0.004)*u_amount; for(int i=0;i<10;i++){sum+=texture(screen_texture,uv+velocity*float(i)).rgb;} col=sum/10.0;",
        "radial":"vec3 sum=vec3(0); vec2 delta=uv-u_mouse; for(int i=0;i<10;i++){sum+=texture(screen_texture,u_mouse+rot(float(i)*u_amount*0.015)*delta).rgb;} col=sum/10.0;",
        "zoom":"vec3 sum=vec3(0); for(int i=0;i<10;i++){sum+=texture(screen_texture,uv+(uv-u_mouse)*float(i)*0.008*u_amount).rgb;} col=sum/10.0;",
        "tilt_shift":"float blur=abs(uv.y-0.53)*u_amount*8.0; col=textureLod(screen_texture,uv,blur).rgb;",
        "bloom":"vec3 bright=max(blur9(screen_texture,uv,vec2(0.008+u_amount*0.025)).rgb-vec3(0.55),vec3(0)); col+=bright*(0.5+u_amount*3.0);",
        "flare":"vec2 q=uv-vec2(0.70,0.25); float flare=0.025/(0.015+length(q))+exp(-abs(q.y)*180.0)*exp(-abs(q.x)*4.0); col+=vec3(1,0.67,0.25)*flare*u_amount;",
        "dirt":"float bright=dot(blur9(screen_texture,uv,vec2(0.02)).rgb,vec3(0.333)); float dirt=pow(n2(uv*80.0),8.0); col+=vec3(0.8,0.65,0.4)*dirt*bright*u_amount;",
        "vignette":"col*=1.0-smoothstep(0.15,0.72,length(uv-0.5))*u_amount;",
        "chromatic":"vec2 shift=(uv-0.5)*0.025*u_amount; col=vec3(texture(screen_texture,uv+shift).r,col.g,texture(screen_texture,uv-shift).b);",
        "fisheye":"float r=length(p); vec2 q=0.5+p/(1.0+u_amount*r*r)*0.5; col=texture(screen_texture,q).rgb;",
        "barrel":"vec2 q=p*(1.0+dot(p,p)*u_amount*0.2); col=texture(screen_texture,q*0.5+0.5).rgb;",
        "pincushion":"vec2 q=p*(1.0-dot(p,p)*u_amount*0.15); col=texture(screen_texture,q*0.5+0.5).rgb;",
        "heat":"vec2 shift=vec2(sin(uv.y*95.0+t*5.0),cos(uv.x*65.0+t*3.0))*0.006*u_amount; col=texture(screen_texture,uv+shift).rgb;",
        "shockwave":"float age=fract(t*0.5), radius=length(uv-u_mouse); vec2 shift=normalize(uv-u_mouse+0.00001)*exp(-pow((radius-age*0.6)*50.0,2.0))*u_amount*0.025; col=texture(screen_texture,uv+shift).rgb;",
        "rain":"vec2 q=uv*vec2(18,12); vec2 drop=fract(q+vec2(0,t*0.15))-0.5; float mask=1.0-smoothstep(0.12,0.17,length(drop*vec2(1,1.4))); col=texture(screen_texture,uv+drop*mask*0.025*u_amount).rgb;",
        "underwater":"col=texture(screen_texture,uv+vec2(sin(uv.y*25.0+t*2.0),cos(uv.x*20.0+t))*0.012*u_amount).rgb*vec3(0.6,0.87,1.05);",
    }
    return canvas(bodies[slug],post=True),"post"


def retro(slug,index):
    if slug=="ps1":
        source=spatial("ALBEDO=mix(u_color.rgb,vec3(0.06,0.1,0.2),step(0.5,fract(UV.x*12.0)));",vertex="vec4 clip=PROJECTION_MATRIX*MODELVIEW_MATRIX*vec4(VERTEX,1); float grid=50.0+u_amount*200.0; clip.xy=floor(clip.xy/clip.w*grid+0.5)/grid*clip.w; POSITION=clip;")
        source=source.replace("void vertex() {","void vertex() {\n    POSITION=PROJECTION_MATRIX*MODELVIEW_MATRIX*vec4(VERTEX,1.0);",1)
        return source,"spatial"
    if slug=="affine":
        return spatial("vec2 q=affine_uv.xy/affine_uv.z; float check=mod(floor(q.x*12.0)+floor(q.y*12.0),2.0); ALBEDO=mix(vec3(0.06,0.12,0.2),u_color.rgb,check);",vertex="vec4 clip=PROJECTION_MATRIX*MODELVIEW_MATRIX*vec4(VERTEX,1); affine_uv=vec3(UV*clip.w,clip.w);",extra="varying vec3 affine_uv;\n"),"spatial"
    bodies={
        "crt":"vec2 q=p*(1.0+dot(p,p)*0.07*u_amount)*0.5+0.5; col=texture(screen_texture,q).rgb; col*=0.82+0.18*sin(FRAGCOORD.y*3.14159); col*=1.0-smoothstep(0.3,0.8,length(p))*0.6;",
        "scanlines":"col*=1.0-u_amount*(0.5+0.5*sin(FRAGCOORD.y*3.14159))*0.7;",
        "phosphor":"float channel=mod(floor(FRAGCOORD.x),3.0); vec3 mask=vec3(channel==0.0?1.0:0.25,channel==1.0?1.0:0.25,channel==2.0?1.0:0.25); col=mix(col,col*mask,u_amount);",
        "curvature":"vec2 q=p*(1.0+dot(p,p)*0.12*u_amount)*0.5+0.5; col=texture(screen_texture,q).rgb; col*=step(0.0,q.x)*step(q.x,1.0)*step(0.0,q.y)*step(q.y,1.0);",
        "vhs":"float jitter=(h21(vec2(floor(uv.y*90.0),floor(t*20.0)))-0.5)*0.018*u_amount; vec2 q=uv+vec2(jitter,0); col=vec3(texture(screen_texture,q+vec2(0.004,0)).r,texture(screen_texture,q).g,texture(screen_texture,q-vec2(0.004,0)).b); col+=h21(FRAGCOORD.xy+floor(t*30.0))*0.07;",
        "tape":"float line=step(0.965,h21(vec2(floor(uv.y*100.0),floor(t*5.0)))); col=mix(col,vec3(h21(FRAGCOORD.xy+floor(t*24.0))),line*u_amount);",
        "tv":"float static_noise=h21(FRAGCOORD.xy+vec2(floor(t*30.0))); col=mix(col,vec3(static_noise),u_amount*0.7);",
        "rgb":"vec2 shift=vec2(0.02*u_amount*sin(t),0); col=vec3(texture(screen_texture,uv+shift).r,col.g,texture(screen_texture,uv-shift).b);",
        "glitch":"float band=floor(uv.y*30.0); float trigger=step(0.82,h21(vec2(band,floor(t*8.0)))); vec2 q=uv+vec2((h21(vec2(band,0))-0.5)*trigger*u_amount*0.3,0); col=texture(screen_texture,q).rgb; col.r=texture(screen_texture,q+vec2(trigger*0.02,0)).r;",
        "displace":"float offset=(h21(vec2(floor(uv.y*18.0),floor(t*2.0)))-0.5)*u_amount*0.2; col=texture(screen_texture,uv+vec2(offset,0)).rgb;",
        "tearing":"float split=fract(t*0.3); vec2 q=uv; q.x+=step(split,uv.y)*u_amount*0.15; col=texture(screen_texture,fract(q)).rgb;",
        "mosaic":"float blocks=16.0+u_amount*120.0; col=texture(screen_texture,(floor(uv*blocks)+0.5)/blocks).rgb;",
        "banding":"col=floor(col*(3.0+floor(u_amount*12.0)))/(3.0+floor(u_amount*12.0));",
        "dither":"float noise=h21(floor(FRAGCOORD.xy))-0.5; float levels=3.0+floor(u_amount*6.0); col=floor(col*levels+noise)/levels;",
        "grain":"col+=(h21(FRAGCOORD.xy+floor(t*24.0))-0.5)*u_amount*0.3;",
        "scratches":"float scratches=step(0.995,h21(vec2(floor(uv.x*700.0),floor(t*3.0)))); float l=dot(col,vec3(0.299,0.587,0.114)); col=vec3(l)*vec3(1.0,0.88,0.66)+scratches*u_amount;",
    }
    return canvas(bodies[slug],post=True),"post"


def transition(slug,index):
    masks={
        "fade":"progress",
        "crossfade":"progress",
        "wipe":"1.0-smoothstep(progress-0.02,progress+0.02,uv.x)",
        "circle":"1.0-smoothstep(progress*0.8-0.02,progress*0.8+0.02,length(uv-0.5))",
        "radial":"step(fract(atan(p.x,-p.y)/TAU_+1.0),progress)",
        "blinds":"step(fract(uv.y*12.0),progress)",
        "checker":"step(mod(floor(uv.x*12.0)+floor(uv.y*8.0),2.0)*0.5+fract(uv.x*12.0)*0.5,progress)",
        "pixel":"step(h21(floor(uv*32.0*u_scale)),progress)",
        "noise":"1.0-smoothstep(progress-0.035,progress+0.035,fbm(uv*12.0*u_scale))",
        "burn":"1.0-smoothstep(progress-0.04,progress+0.04,fbm(uv*10.0))",
        "ripple":"1.0-smoothstep(progress*0.8-0.02,progress*0.8+0.02,length(uv-0.5)+sin(length(uv-0.5)*55.0-t*2.0)*0.025)",
        "ink":"1.0-smoothstep(progress*1.1-0.03,progress*1.1+0.03,length(p)*0.55+fbm(uv*10.0)*0.25)",
        "glitch":"step(h21(vec2(floor(uv.y*35.0),0))*0.2+uv.x*0.8,progress)",
        "vortex":"step(fract(atan(p.y,p.x)/TAU_+length(p)*1.5),progress)",
        "page":"step(uv.x,progress)",
        "portal":"1.0-smoothstep(progress*0.85-0.015,progress*0.85+0.015,length(uv-u_mouse))",
    }
    body="float progress=u_amount; float mask="+masks[slug]+"; vec3 next=texture(destination_texture,uv).rgb; col=mix(col,next,mask);"
    if slug=="burn":
        body+="float edge=1.0-smoothstep(0.0,0.06,abs(fbm(uv*10.0)-progress)); col+=vec3(1,0.25,0.01)*edge;"
    if slug=="page":
        body+="col*=1.0-exp(-abs(uv.x-progress)*70.0)*0.6;"
    return canvas(body,post=True,extra="uniform sampler2D destination_texture : source_color, filter_linear;\n")


def lighting(slug,index):
    if slug in ["self_shadow","shadow","soft_shadow","contact","ssao","ssr","ssil","probe"]:
        return spatial("ALBEDO=u_color.rgb; METALLIC=0.7*u_amount; ROUGHNESS=0.12;"),"pipeline"
    if slug in ["diffuse","specular","soft_specular"]:
        body="ALBEDO=u_color.rgb; ROUGHNESS=0.15+u_amount*0.8;"
        if slug=="diffuse": body+="SPECULAR=0.0;"
        return spatial(body),"spatial"
    if slug=="ao":
        return spatial("float cavities=cells(uv*15.0).y; ALBEDO=u_color.rgb; AO=mix(1.0,smoothstep(0.0,0.2,cavities),u_amount); AO_LIGHT_AFFECT=1.0;"),"spatial"
    if slug=="lightmap":
        return spatial("vec3 baked=vec3(0.2,0.35,0.5)+vec3(0.8,0.5,0.18)*max(0.0,sin(UV.x*3.14159)); ALBEDO=mix(u_color.rgb,baked*u_color.rgb,u_amount);"),"spatial"
    if slug=="cookie":
        return spatial("vec2 projection=v_world.xz*2.0+vec2(t*0.1,0); float cookie=step(0.5,fract(projection.x))*step(0.5,fract(projection.y)); ALBEDO=u_color.rgb*mix(0.18,1.0,cookie);"),"spatial"
    return spatial("float light=pow(1.0-smoothstep(0.01,0.12,cells(v_world.xz*4.0+vec2(t*0.15)).y),3.0); ALBEDO=vec3(0.09,0.28,0.35)+vec3(light)*u_amount; EMISSION=vec3(0.4,0.9,1.0)*light*u_amount;"),"spatial"


RAY_HELPERS="""
float smooth_union(float a,float b,float k) {
    float h=clamp(0.5+0.5*(b-a)/k,0.0,1.0);
    return mix(b,a,h)-k*h*(1.0-h);
}
"""


def advanced(slug,index):
    if slug in ["mandelbrot","fractal"]:
        return canvas("""
        vec2 c=p*vec2(1.7,1.2)/(0.5+u_amount*2.5)-vec2(0.6,0.0);
        vec2 z=vec2(0.0); float iterations=0.0;
        for(int i=0;i<72;i++){
            z=vec2(z.x*z.x-z.y*z.y,2.0*z.x*z.y)+c;
            if(dot(z,z)>64.0){break;}
            iterations+=1.0;
        }
        col=rainbow(iterations*0.025+t*0.015)*min(iterations/10.0,1.0);
        if(iterations>71.0){col=vec3(0.015,0.025,0.045);}
""")
    if slug=="sdf":
        return canvas("vec2 q=rot(t*0.25)*p; float circle=length(q-vec2(sin(t)*0.2,0))-0.34; float square=box_sdf(q+vec2(0.25,0),vec2(0.3),0.07); float d=smooth_union(circle,square,0.15+u_amount*0.4); col=mix(vec3(0.02,0.05,0.08),u_color.rgb,1.0-smoothstep(-0.005,0.005,d)); col+=vec3(0.2)*step(0.93,cos(d*100.0));",extra=RAY_HELPERS)
    if slug in ["reaction","feedback","tunnel","infinite","volume_light"]:
        bodies={
            "reaction":"vec2 q=uv*12.0*u_scale; float field=sin(q.x+fbm(q+t*0.06)*12.0)*cos(q.y+fbm(q+5.0-t*0.05)*12.0); col=mix(vec3(0.025,0.06,0.12),u_color.rgb,smoothstep(-0.1,0.1,field));",
            "feedback":"col=vec3(0.02,0.035,0.06); for(int i=0;i<20;i++){float age=float(i)*0.10; vec2 center=vec2(sin(t-age),cos((t-age)*1.3))*0.45; col+=u_color.rgb*exp(-length(p-center)*60.0)*exp(-age*2.0);}",
            "tunnel":"float r=max(length(p),0.01); vec2 q=vec2(atan(p.y,p.x)/TAU_,0.3/r+t*0.25); float check=mod(floor(q.x*24.0)+floor(q.y*12.0),2.0); col=mix(vec3(0.03,0.07,0.12),u_color.rgb,check)*smoothstep(0.0,0.35,r);",
            "infinite":"vec2 q=p; col=vec3(0.015,0.025,0.045); for(int i=0;i<6;i++){q=abs(q*1.7)-0.7; float edge=1.0-smoothstep(0.01,0.035,abs(max(abs(q.x),abs(q.y))-0.5)); col+=rainbow(float(i)*0.1+t*0.05)*edge*0.3;}",
            "volume_light":"float ray=pow(max(0.0,cos(atan(p.x,p.y+1.2)*35.0+t*0.15)),10.0); float falloff=pow(max(0.0,1.0-uv.y),1.5); col=vec3(0.02,0.04,0.065)+vec3(0.95,0.8,0.5)*ray*falloff*u_amount;",
        }
        return canvas(bodies[slug])
    sdf = {
        "raymarch":"return length(p)-0.85;",
        "terrain":"return p.y+0.45-fbm(p.xz*1.8)*0.7;",
        "cloud":"float a=length(p-vec3(-0.35,0.05,0))-0.65; float b=length(p-vec3(0.4,0.1,0))-0.7; return smooth_union(a,b,0.5)+fbm(p.xz*5.0+p.y*2.0)*0.12;",
        "metaball":"float a=length(p-vec3(sin(u_time*u_speed)*0.55,0,0))-0.55; float b=length(p-vec3(-sin(u_time*u_speed)*0.55,0.15,0))-0.55; return smooth_union(a,b,0.3+u_amount*0.4);",
        "viscous":"float a=length(p-vec3(sin(u_time*u_speed)*0.4,cos(u_time*0.6)*0.2,0))-0.6; float b=length(p-vec3(-0.4,-0.2,0.1))-0.55; return smooth_union(a,b,0.6);",
        "mandelbulb":"""
    vec3 z=p; float dr=1.0, r=0.0;
    for(int j=0;j<5;j++){
        r=length(z);
        if(r>2.0){break;}
        float theta=acos(clamp(z.z/max(r,0.0001),-1.0,1.0));
        float phi=atan(z.y,z.x);
        dr=pow(r,7.0)*8.0*dr+1.0;
        float zr=pow(r,8.0); theta*=8.0; phi*=8.0;
        z=zr*vec3(sin(theta)*cos(phi),sin(theta)*sin(phi),cos(theta))+p;
    }
    return 0.5*log(max(r,0.0001))*r/dr;
""",
    }[slug]
    extra=RAY_HELPERS+"\nfloat map_scene(vec3 p){\n"+sdf+"\n}\n"
    return canvas("""
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
""",extra=extra)


def debug_effect(slug,index):
    if slug=="depth": return depth_shader("depth"),"depth"
    bodies={
        "wireframe":"vec3 width=fwidth(COLOR.rgb)*(0.8+u_amount*2.0); vec3 edge=smoothstep(vec3(0),width,COLOR.rgb); float line=1.0-min(min(edge.r,edge.g),edge.b); ALBEDO=mix(vec3(0.035,0.07,0.12),u_color.rgb,line);",
        "normal":"ALBEDO=normalize(NORMAL)*0.5+0.5;",
        "uv":"float check=mod(floor(uv.x*20.0)+floor(uv.y*20.0),2.0); ALBEDO=mix(vec3(0.05),vec3(0.85),check);",
        "world":"ALBEDO=fract(abs(v_world)*u_scale);",
        "id":"ALBEDO=vec3(fract(instance_id*0.73),fract(instance_id*0.37+0.2),fract(instance_id*0.57+0.4));",
        "vertex":"ALBEDO=COLOR.rgb;",
        "texel":"float density=length(fwidth(UV))*160.0*u_scale; ALBEDO=thermal(clamp(density,0.0,1.0));",
        "overdraw":"ALBEDO=thermal(clamp((1.0-abs(dot(NORMAL,VIEW)))*1.2,0.0,1.0));",
        "lod":"if(h21(floor(FRAGCOORD.xy))<u_amount){discard;} ALBEDO=u_color.rgb;",
        "distance":"ALPHA=1.0-smoothstep(2.0,3.0+u_amount*6.0,length(VERTEX)); ALBEDO=u_color.rgb;",
    }
    extra="instance uniform float instance_id = 1.0;\n" if slug=="id" else ""
    return spatial(bodies[slug],extra=extra,modes="unshaded"),"spatial"


FAMILY_NOTES = {
    "dissolve": "核心就是决定哪里还画、哪里不画。消失顺序可以按位置、距离或随机花纹来排；边缘亮色是另外涂上去的。",
    "outline": "图片描边主要靠检查旁边有没有图案；模型亮边主要看表面朝向。轮廓附近加线、加亮或变透明，就有了不同外观。",
    "emission": "把一部分颜色画得很亮，再让亮的位置或亮度变化。这些二维亮色本身不会变成能照亮周围的灯。",
    "stylized": "可以改变模型的明暗上色规则，也可以把已经画好的图片再加工。把细腻变化压成色块、线条或颗粒，就会接近不同画风。",
    "materials": "材质就是物体表面遇到光时怎么表现。底色、反光强弱、反光清晰度和细纹一起决定它更像金属、塑料还是布。",
    "glass": "反射是看见周围环境的倒影，折射是透过去看时景物被折弯。这里的折射取自当前画面，镜头外没有画出的内容无法补出来。",
    "water": "一层会起伏的表面，加上波纹、反光和深浅颜色，就能让人联想到水。水下物体离水面多远，还能帮助决定浅水色和岸边泡沫。",
    "fire": "火焰靠跳动边缘和红黄颜色，烟靠会移动、变大、变淡的团块。这些示例用公式画外观，没有计算真实空气与热量的流动。",
    "terrain": "先决定哪里覆盖哪种东西，再分别改颜色和反光。积雪、锈斑、潮湿等外观，很多都能从这个共同做法变化出来。",
    "sky": "云、星星和雨雪可以先在二维画面中做出气氛。标为“管线功能”的雾则会交给 Godot，在整个三维场景中计算。",
    "magic": "先画圆环、线条或不规则花纹，再让它们移动和发亮。有些效果还能把点击位置当作命中点或扩散中心。",
    "status": "保留角色原来的形状，改变表面的颜色、反光、发光或透明程度。示例会循环展示外观，真实受击、治疗或死亡时机需要游戏代码控制。",
    "vertex": "模型由许多小点连接成面，挪动这些点就能让模型弯曲或抖动。点越密，变形通常越平滑；这里没有跟着修改用于物理碰撞的形状。",
    "uv": "贴图位置就像图片上的地址。改地址能让图案平移、旋转或扭曲；也可以不用图片，直接用公式算出花纹。",
    "sprite": "先读取图片的颜色和透明部分，再决定哪些地方换色、加边或隐藏。很多效果能直接用于普通二维图片，放进大图集时还要对应好图片区域。",
    "ui": "先决定按钮、文字、圆环或视野的范围，再决定范围内怎么填色和变化。这里的文字是一张固定字形图片，便于观察效果。",
    "color": "先拿到预览里已经画好的图，再逐点换颜色。处理范围只有中间预览，旁边的目录和参数面板不会一起变色。",
    "lens": "同一张图，换地方取颜色就会扭曲，把附近颜色混起来就会模糊。需要反复取色的效果，在大画面上通常更费显卡。",
    "retro": "有意加入错位、颗粒、条纹、少量颜色或跳动，就能接近老设备的观感。暂停后可以看清单次变化。",
    "transition": "手里同时拿着旧图和新图，决定每个位置现在该显示哪一张。进度条控制切换到哪一步。",
    "lighting": "光照要同时考虑灯在哪、表面朝哪和有没有被挡住。有些示例改表面规则，有些打开 Godot 自带的全场景效果。",
    "advanced": "有些图形不靠现成模型，而是反复计算哪里有表面、该涂什么颜色。这里为了方便观看限制了计算次数，具体简化写在下面。",
    "debug": "把平常藏起来的位置、朝向或编号换成颜色，方便检查模型。画出热力色的样子，并不一定代表真的测量了性能。",
}

LIMITS = {
    ("dissolve","sand"): "这里只画细沙般的消散花纹，没有生成一粒粒会飞动、碰撞的沙子。",
    ("outline","occlusion"): "轮廓会直接越过前面的物体显示，没有单独挑出真正被挡住的那部分。",
    ("outline","cutaway"): "只隐藏切掉的表面，没有给切口补一块盖子。",
    ("materials","hair"): "发丝是画在球面上的花纹，没有一根根真实的立体头发。",
    ("materials","eye"): "虹膜和瞳孔都画在同一层球面上，没有另外制作透明角膜和眼球内部。",
    ("materials","thin_film"): "用角度和假定厚度挑选彩虹色，没有计算不同波长的光在薄膜里如何互相影响。",
    ("glass","absorption"): "厚度是根据观察角度猜的，没有测量光真正穿过玻璃多远。",
    ("sky","volume_clouds"): "叠的是多层二维云纹，没有计算光穿过三维云团时如何散开。",
    ("sky","god_rays"): "使用引擎的雾和灯光；换灯的位置、强弱或遮挡物，光束可能变得不明显。",
    ("water","container"): "只展示有限大小的液面，没有让液体自动贴合任意瓶子形状，也没有保证晃动时水量不变。",
    ("water","sloshing"): "晃动由预设公式驱动，没有计算液体受力后的真实运动。",
    ("terrain","footprint"): "脚印是预先排好的花纹，不会随着角色真正走路而不断留下新脚印。",
    ("terrain","snow_track"): "压痕只改变颜色，雪面没有真的被踩凹，也不会记录新的踩踏。",
    ("terrain","tire"): "车辙是预设图案，没有记录车辆开过的路径。",
    ("vertex","explode"): "只是把模型上的点往外挪，连接关系还在，没有把模型拆成会碰撞的独立碎片。",
    ("uv","flipbook"): "现在读取的是自带图案的十六个小区域；换成真正的动画图片表后才能播放对应动画。",
    ("uv","stochastic"): "只随机改变每块纹理的方向，没有完整处理块与块之间的接缝。",
    ("uv","interior"): "只用二维色块暗示房间深度，没有计算视线进入真实房间后会碰到哪面墙。",
    ("sprite","normal_light"): "表面朝向是从图片透明轮廓猜出来的，没有使用美术专门画好的表面朝向图。",
    ("sprite","page"): "翻页靠图片镜像和暗影营造，纸张本身没有真的弯成曲面。",
    ("sprite","spine"): "这里只演示溶解的上色方法，没有附带 Spine 骨骼动画播放器。",
    ("ui","typewriter"): "显现边界可以停在一个字的中间，没有按完整汉字或字母逐个播放。",
    ("lens","motion"): "模糊方向是预设的，没有记录每个物体刚才往哪移动、移动多快。",
    ("lens","bokeh"): "只在圆盘内取十二份颜色混合，光斑细节和真实镜头还有差别。",
    ("lens","bloom"): "从普通预览图中挑亮处加光，没有使用引擎完整的高亮范围泛光流程。",
    ("lens","flare"): "光斑位置是设好的，不会自动找到画面里真正的太阳或灯。",
    ("lens","dirt"): "污点是公式生成的花纹，没有模拟真实镜片内部的光路。",
    ("color","thermal"): "颜色只根据图片亮暗分配，不能用于判断物体真实温度。",
    ("color","local"): "只改变点击位置附近一圈的颜色，没有自动分析各区域需要多少曝光。",
    ("lighting","contact"): "只借现有阴影展示贴地感，没有另外沿画面搜索和计算接触阴影。",
    ("lighting","lightmap"): "预照明颜色由公式画出，没有提前计算整个场景中的真实光照。",
    ("lighting","cookie"): "图案直接根据表面位置画出，没有放一盏真正携带图片的投影灯。",
    ("lighting","caustics"): "亮纹是移动花纹，没有追踪光穿过水之后实际聚焦在哪里。",
    ("advanced","cloud"): "画的是像云的外壳，没有计算光在云团内部穿透和散射。",
    ("advanced","reaction"): "只模仿反应扩散的花纹，没有让上一帧的物质分布继续反应、扩散到下一帧。",
    ("advanced","feedback"): "残影位置由时间公式直接算出，没有保存上一帧的真实画面。",
    ("advanced","terrain"): "地形只有画面外观，没有碰撞，也没有随距离更换精细程度或分块加载。",
    ("advanced","volume_light"): "光束直接画在二维画面上，没有计算灯光穿过真实三维烟雾的过程。",
    ("debug","overdraw"): "这些热力色只随观察角度改变，不能用来判断显卡真正重复画了多少次。",
}

ENVIRONMENTS = {
    ("water","fog"): {"fog_enabled": True, "fog_light_color": [0.10,0.45,0.52,1]},
    ("sky","distance_fog"): {"fog_enabled": True},
    ("sky","height_fog"): {"fog_enabled": True, "fog_height": 1.2, "fog_height_density": 0.8},
    ("sky","local_fog"): {"volumetric_fog_enabled": True},
    ("sky","volume_fog"): {"volumetric_fog_enabled": True},
    ("sky","light_column"): {"volumetric_fog_enabled": True},
    ("sky","god_rays"): {"volumetric_fog_enabled": True},
    ("lighting","ssao"): {"ssao_enabled": True, "ssao_radius": 1.5},
    ("lighting","ssr"): {"ssr_enabled": True},
    ("lighting","ssil"): {"ssil_enabled": True, "ssil_intensity": 1.5},
}


def choose_shader(group,slug,index):
    if group + "/" + slug in PROFILES:
        source, kind = refined_shader(group, slug)
        return profile_uniforms(source, PROFILES[group + "/" + slug]), kind
    direct={
        "dissolve":dissolve, "emission":emission, "materials":pbr,
        "glass":glass, "fire":fire, "terrain":terrain, "status":status,
        "vertex":vertex_effect, "sprite":sprite_effect, "color":color_effect,
        "transition":transition, "advanced":advanced,
    }
    dispatched={
        "outline":outline,"stylized":toon,"water":water,"sky":sky_effect,
        "magic":magic,"uv":uv_effect,"ui":ui_effect,"lens":lens,
        "retro":retro,"lighting":lighting,"debug":debug_effect,
    }
    if group in dispatched:
        return dispatched[group](slug,index)
    kind = "spatial" if group in ["materials","glass","terrain","status","vertex"] else "sprite" if group in ["dissolve","sprite"] else "post" if group in ["color","transition"] else "canvas"
    if group=="fire" and slug=="distortion": kind="post"
    return direct[group](slug,index),kind


def write_png(path,width,height,pixels):
    def chunk(kind,data):
        return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
    raw=b"".join(b"\0"+bytes(pixels[y*width*3:(y+1)*width*3]) for y in range(height))
    path.write_bytes(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(raw))+chunk(b"IEND",b""))


def assets(output_root):
    if not (ROOT/"assets"/"cottage.png").is_file():
        raise FileNotFoundError("Missing repository asset: assets/cottage.png. Restore it from Git before building.")
    folder=output_root/"assets"
    folder.mkdir(exist_ok=True)
    (folder/"icon.svg").write_text('''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><rect width="64" height="64" rx="15" fill="#162a39"/><path d="M32 8 54 20v24L32 56 10 44V20Z" fill="none" stroke="#55e8bb" stroke-width="3"/><path d="m16 24 16 9 16-9M32 33v18" fill="none" stroke="#55e8bb" stroke-width="3"/><circle cx="32" cy="20" r="4" fill="#e5b574"/></svg>''',encoding="utf-8")
    (folder/"subject.svg").write_text('''<svg xmlns="http://www.w3.org/2000/svg" width="640" height="560" viewBox="0 0 640 560">
<defs><linearGradient id="body" x2="0.85" y2="1"><stop stop-color="#b6ffe8"/><stop offset=".5" stop-color="#4bd4ba"/><stop offset="1" stop-color="#23789d"/></linearGradient><linearGradient id="gold" x2="1" y2="1"><stop stop-color="#ffe7a2"/><stop offset="1" stop-color="#ef9b5f"/></linearGradient></defs>
<path d="m320 74 165 95v190l-165 96-165-96V169Z" fill="#112e43" stroke="#9df6da" stroke-width="9"/>
<path d="m320 98 143 83v165l-143 83-143-83V181Z" fill="url(#body)"/>
<path d="m320 98 143 83-143 87-143-87Z" fill="#a2f6da"/>
<path d="m320 268 143-87v165l-143 83Z" fill="#21899c"/>
<path d="m227 224 93 54 93-54v120l-93 55-93-55Z" fill="#132e45"/>
<path d="m320 245 47 28v54l-47 28-47-28v-54Z" fill="url(#gold)"/>
<path d="m320 245 47 28-47 29-47-29Z" fill="#ffe9b0"/>
<path d="m320 302 47-29v54l-47 28Z" fill="#ee9d62"/>
<path d="M111 222c-61 82-9 166 121 199 139 35 293 0 344-78" fill="none" stroke="#f8cd83" stroke-width="8" stroke-linecap="round"/>
<path d="m108 196 14 27-29 6Z" fill="#f8cd83"/>
<path d="m503 95 9 21 22 2-17 15 5 22-19-12-19 12 5-22-17-15 22-2Z" fill="#d2fff0"/>
<circle cx="136" cy="405" r="8" fill="#63e6c5"/><circle cx="520" cy="414" r="6" fill="#a68cff"/>
<path d="m109 117 5 13 14 1-11 9 3 14-11-8-12 8 4-14-11-9 14-1Z" fill="#a68cff"/>
</svg>''',encoding="utf-8")
    (folder/"destination.svg").write_text('''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="900" viewBox="0 0 1200 900"><defs><linearGradient id="sky" x2="0" y2="1"><stop stop-color="#283c72"/><stop offset="1" stop-color="#e8a57c"/></linearGradient></defs><rect width="1200" height="900" fill="url(#sky)"/><circle cx="850" cy="260" r="100" fill="#ffe1a3"/><path d="M0 630 280 220 470 490 650 300 1050 640 1200 500V900H0Z" fill="#485778"/><path d="m280 220-95 140 106-36 77 34Z" fill="#c4d1d4"/><path d="M0 690 260 510 570 720 930 480 1200 700V900H0Z" fill="#283f57"/><path d="M0 760q300-80 600 0t600 0V900H0Z" fill="#3e7883"/><path d="M700 800h280m-350 30h420m-500 30h500" stroke="#eab98d" stroke-width="6" opacity=".45"/></svg>''',encoding="utf-8")
    glyphs={
        "S":["11111","10000","10000","11111","00001","00001","11111"],
        "H":["10001","10001","10001","11111","10001","10001","10001"],
        "A":["01110","10001","10001","11111","10001","10001","10001"],
        "D":["11110","10001","10001","10001","10001","10001","11110"],
        "E":["11111","10000","10000","11110","10000","10000","11111"],
        "R":["11110","10001","10001","11110","10100","10010","10001"],
    }
    rects=[]
    for letter_index,letter in enumerate("SHADER"):
        for y,row in enumerate(glyphs[letter]):
            for x,value in enumerate(row):
                if value=="1": rects.append(f'<rect x="{42+letter_index*96+x*16}" y="{135+y*16}" width="15" height="15" rx="2"/>')
    (folder/"lettering.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="660" height="390" viewBox="0 0 660 390"><g fill="#a3ffe1">'+"".join(rects)+'</g><path d="M45 285h565" stroke="#9c8df0" stroke-width="5"/></svg>',encoding="utf-8")
    vat=[]
    for y in range(64):
        for x in range(256):
            phase=y/64*math.tau+x/256*math.tau
            vat.extend([round(127.5+95*math.sin(phase)),round(127.5+100*math.sin(phase*2)),128])
    write_png(folder/"vat.png",256,64,vat)
    lut=[]
    for y in range(16):
        for x in range(256):
            r,g,b=(x%16)/15,y/15,(x//16)/15
            lut.extend([round(min(1,r*1.08+0.03)*255),round(min(1,g*0.98+0.015)*255),round(max(0,min(1,b*0.87))*255)])
    write_png(folder/"warm_lut.png",256,16,lut)
    # RGB data, 16 blue slices horizontally; exact 8-bit identity grid.
    neutral = []
    for y in range(16):
        for x in range(256):
            neutral.extend([(x % 16)*17, y*17, (x // 16)*17])
    write_png(folder/"neutral_lut.png",256,16,neutral)


def build(output_root):
    assets(output_root)
    catalog,groups=[],[]
    index_rows=[]
    for category_number,(group,name,encoded) in enumerate(CATEGORIES,1):
        cases=[pair.strip().split("=",1) for pair in encoded.strip().split("|")]
        groups.append({"number":category_number,"slug":group,"name":name,"count":len(cases)})
        for local_index,(slug,title) in enumerate(cases,1):
            source,kind=choose_shader(group,slug,local_index-1)
            directory=f"effects/{category_number:02d}_{group}/{local_index:02d}_{slug}"
            folder=output_root/directory
            folder.mkdir(parents=True,exist_ok=True)
            limit=LIMITS.get((group,slug),"")
            if kind=="pipeline" and slug=="contact":
                limit=LIMITS[(group,slug)]
            implementation="演示近似" if limit else "管线功能" if kind=="pipeline" else "深度后处理" if kind=="depth" else "三维材质" if kind=="spatial" else "屏幕后处理" if kind=="post" else "二维 Shader"
            if group=="stylized" and kind=="post":
                limit=limit or "这是把一张图片加工成绘画观感，没有真的生成一笔笔立体笔触；画面动起来时也没有专门稳定笔触。"
                implementation="演示近似"
            if group=="fire" and slug in ["smoke","toon_smoke","steam","dust","sandstorm","poison","flame","explosion"]:
                limit=limit or "这里只用二维图案模仿外观，没有计算真实空气、火焰或气团的受力流动。"
                implementation="演示近似"
            if group=="magic" and slug in ["trail","afterimage"]:
                limit="这里只画会变化的光带，没有记录物体过去走过哪些位置。"
                implementation="演示近似"
            shape="plane" if group in ["water","terrain"] and kind=="spatial" else "sphere"
            if group=="vertex" and slug in ["flag","wind","leaves","bend","wave","vat"]: shape="cloth"
            if group=="vertex" and slug=="sphere": shape="cube"
            if group=="vertex" and slug=="billboard": shape="quad"
            explanation=PRINCIPLES[group][slug]
            plain_summary,_,plain_steps=explanation.partition("。")
            entry={
                "number":len(catalog)+1,"name":title,"slug":slug,"category":name,
                "category_slug":group,"category_number":category_number,"kind":kind,
                "implementation":implementation,"approximation":bool(limit),
                "summary":plain_summary+"。",
                "directory":"res://"+directory,"shader":"res://"+directory+"/effect.gdshader",
                "readme":"res://"+directory+"/README.md","scene":"res://"+directory+"/demo.tscn",
                "shape":shape,"amount":0.32 if group=="dissolve" else 0.55,"keywords":f"{group} {slug} {kind}",
                "text":group=="ui" and slug.startswith("text") or group=="ui" and slug in ["gradient_text","typewriter"],
            }
            profile = PROFILES.get(group + "/" + slug)
            if profile:
                entry.update(profile)
            if (group,slug) in ENVIRONMENTS: entry["environment"]=ENVIRONMENTS[(group,slug)]
            if group=="outline" and slug in ["silhouette","occlusion","xray"]: entry["occluder"]=True
            if group=="water" and shape=="plane": entry["rocks"]=True
            if group=="lighting" and slug=="probe": entry["reflection_probes"]=True
            if group=="sky" and slug=="local_fog": entry["fog_volume"]=True
            if group=="lighting" and slug=="soft_shadow": entry["soft_shadow"]=True
            if group=="debug" and slug in ["wireframe","vertex"]: entry["vertex_colors"]=True
            if group=="debug" and slug=="wireframe": entry["barycentric"]=True
            if group=="terrain" and slug=="vertex_blend": entry["vertex_colors"]=True
            if group=="debug" and slug=="id": entry["object_ids"]=True
            if slug=="volume_clouds" and group=="sky": entry["approximation"]=True
            source="\n".join(line.rstrip() for line in source.splitlines()).rstrip()+"\n"
            parameter_comment = "Parameters and defaults: metadata.json" if profile else "Adjust u_amount, u_speed, u_scale and u_color in the gallery."
            (folder/"effect.gdshader").write_text(f"// {title} | {implementation}\n// {parameter_comment}\n"+source,encoding="utf-8")
            (folder/"metadata.json").write_text(json.dumps(entry,ensure_ascii=False,indent=2),encoding="utf-8")
            (folder/"demo.tscn").write_text(f'''[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://shared/standalone.gd" id="1"]

[node name="Demo" type="Control"]
layout_mode = 3
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
script = ExtResource("1")
metadata_path = "res://{directory}/metadata.json"
''',encoding="utf-8")
            pipeline=json.dumps(entry.get("environment",{}),ensure_ascii=False,indent=2)
            if kind=="pipeline":
                (folder/"environment.json").write_text(pipeline,encoding="utf-8")
            interaction_notes={
                ("water","interactive"): "点击当前预览的起伏水面才触发一次涟漪，拖动只旋转相机。命中针对本例有限平面和同一套波形求解，不包含任意模型碰撞或多次点击叠加；新点击替换上一圈。",
                ("magic","shield_hit"): "点击本例球形护盾触发一次沿球面扩散的亮圈，结束后不自动重播。新点击替换上一圈；其他形状需要另外实现命中方法。",
            }.get((group,slug),"")
            notes=f"""# {title}

编号：{entry['number']:03d}  |  分类：{name}
实现标签：{implementation}

## 查看

- 图鉴入口：打开 project.godot，按 F5，搜索“{title}”或“{slug}”。
- 单独查看：打开本目录 demo.tscn，按 F6。
- 临时试效果：可编辑本目录 effect.gdshader；要长期保存，请把改动合回 tools/build_library.py 对应公式后再重建。
- 重建前检查：python tools/build_library.py --check。检测到手改文件时会停止覆盖，先确认并保留改动。
- 每个效果的代码保存在本目录 effect.gdshader；展示场景共用 shared/ 里的脚本。
- 先关掉“启用效果”看原样，再打开比较；想看清静止画面时点“暂停动画”。

## 原理

{entry['summary']}

## 它是怎么做到的？

{plain_steps}

## 这一类效果的共同思路

{FAMILY_NOTES[group]}

## 右侧参数怎么理解？

- 强度 / 进度（u_amount）：从 0 到 1，表示效果有多强或走到哪一步；具体含义看上面的解释。
- 动画速度：控制播放时间前进的快慢；0 会停下。改速度不会跳到另一个时刻，材质的 u_speed 固定为 1，避免重复乘速度。
- 纹理 / 图案尺度（u_scale）：调图案的疏密或大小；本效果用到它时才会变化。
- 强调色（u_color）：调亮边、花纹等使用的颜色；本效果用到它时才会变化。
- 启用效果（u_enabled）：开关效果，方便和原样比较。
- 点击位置：{('使用三维表面命中点 u_hit_position；u_event_time 记录点击时刻，u_duration 默认为 1 秒。按下并释放才触发，拖动不触发。' if (group,slug) in [('water','interactive'),('magic','shield_hit')] else '支持二维位置交互的案例使用 u_mouse；它是当前预览内的点击位置比例。')}
- 播放时间（u_time）：告诉效果现在播放到几秒，暂停动画时这个数字也停下。

## 这个演示做到哪一步？

{limit or interaction_notes or '这里演示画面变化的方法。放进游戏时，还要由游戏代码决定何时出现、变化多久，并按实际模型和画面大小调整。'}

{('这项使用 Godot 自带的场景渲染功能。下面的配置负责打开和调整它，单独复制 Shader 文件不能带走整个效果。') if kind=='pipeline' else ''}
{('取的是当前预览已经画出的背景颜色。镜头外没画出来的内容，单靠这张图无法补出来。') if 'hint_screen_texture' in source else ''}
{('这里还会读取远近信息，也就是每个位置离相机多远，用它判断深浅、遮挡或模糊程度。') if 'hint_depth_texture' in source else ''}

项目默认使用 Forward+ 渲染器。切换到 Compatibility 等其他模式时，部分反射、雾和环境光功能会有差别，需要重新检查。

## 接入配置

{('WorldEnvironment 设置：'+pipeline) if kind=='pipeline' else '效果公式保存在本目录的 effect.gdshader。'}

## 相关官方文档

- https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/spatial_shader.html
- https://docs.godotengine.org/en/stable/tutorials/shaders/screen-reading_shaders.html
- https://docs.godotengine.org/en/stable/tutorials/3d/environment_and_post_processing.html
"""
            if profile:
                start = notes.index("- 强度 / 进度（u_amount）")
                end = notes.index("\n## 这个演示做到哪一步？", start)
                notes = notes[:start] + parameter_notes(profile["parameters"]) + "\n\n" + profile["profile_note"] + "\n" + ("播放区：速度 0–3，默认 1；暂停、调速保持当前时刻。\n" if profile["animated"] else "静态效果不显示播放速度。\n") + ("操作：" + profile["action"] + "。\n" if profile["action"] else "") + "重置恢复以上元数据默认值、播放时刻和效果开关，并清除事件。\n" + notes[end:]
            (folder/"README.md").write_text(notes,encoding="utf-8")
            catalog.append(entry)
            index_rows.append(f"| {entry['number']:03d} | {name} | [{title}](../{directory}/README.md) | {implementation} |")
    (output_root/"catalog.json").write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding="utf-8")
    (output_root/"categories.json").write_text(json.dumps(groups,ensure_ascii=False,indent=2),encoding="utf-8")
    docs=output_root/"docs"
    docs.mkdir(exist_ok=True)
    (docs/"INDEX.md").write_text("# 全部效果索引\n\n| 编号 | 分类 | 效果与目录 | 实现 |\n|---|---|---|---|\n"+"\n".join(index_rows)+"\n",encoding="utf-8")
    approximate=sum(item["approximation"] for item in catalog)
    (output_root/"README.md").write_text(f"""# Shader Atlas · Godot 效果图鉴

{len(catalog)} 个独立效果目录，覆盖对话中的 23 类。使用 Godot 4.7.2 标准版，无外部插件、网络依赖或 .NET 依赖。

## 运行与查看

1. 用 Godot 导入本目录的 project.godot。
2. 第一次打开等待 SVG、PNG 与脚本导入完成，按 F5。
3. 左侧选择分类或输入中文/英文关键词；中间查看实时效果、源码、原理与限制；右侧调整参数。
4. 每个效果目录都有 demo.tscn，可在编辑器中打开后按 F6 单独运行。

三维预览支持左键拖动旋转和滚轮缩放。空格暂停动画，Ctrl+F 搜索，左右方向键切换过滤结果。
点击“启用效果”可比较原始画面。右侧“打开效果目录”打开当前案例所在目录。
动画速度可以随时调整，设为 0 或暂停会保留当前时刻。交互涟漪与护盾受击需要点击表面触发一次；拖动旋转不会触发，重置参数会清除事件。
首批 20 项已完成 M3 精修：右侧按各项元数据显示中文参数、范围、单位、步长与默认值，数值可以拖滑块或用键盘输入。静态项隐藏播放速度，其余 401 项保留“基础参数”。受击闪白点击“播放一次”或图案触发；LUT 可选暖色/中性表；高斯使用真正横、竖两遍。

421 项的“原理与限制”及目录 README 都采用大白话：先讲画面像什么，再讲本示例具体怎么画出来。参数和演示局限也用日常语言说明。

## 目录

- effects/01_dissolve/01_noise/ 这样的目录：每个效果一个文件夹。
- 每个文件夹：effect.gdshader、demo.tscn、metadata.json、README.md；管线案例另有 environment.json。
- shared/：通用场景、展示入口与参数控制，不放具体效果公式。
- assets/：矢量示例图、文字贴图、VAT、LUT，以及本地 Blender 小屋渲染参考图。
- docs/INDEX.md：全部目录与实现标签的完整索引。
- tools/build_library.py 与 effect_catalog.py：维护/重建库的源文件。
- tools/effect_profiles.py：首批 20 项的参数规格、默认值和说明；公式仍在 build_library.py。
- tools/plain_language.py：各项大白话解释的维护源。
- tools/generated_manifest.json：生成文件的上次内容记录，用于保护手改内容。
- tools/validate.gd：结构、资源和 Shader 语言检查。
- tools/test_runtime.gd：M2 播放、命中与输入行为检查，报告保存到 artifacts/m2/。
- tools/test_m3.gd：首批参数、重置、端点、透明边、高斯和 LUT 的实际像素检查，报告及截图在 artifacts/m3/。
- docs/OPTIMIZATION_PLAN.md：M1–M3 已完成，下一步 M4 可复用材质和最小接入场景；结果见 docs/M3_VERIFICATION.md。
- artifacts/：实际运行审查输出的报告与截图。

## 安全重建

在工程根目录运行（仅需 Python 标准库）：

    python tools/build_library.py --check
    python tools/build_library.py --effect dissolve/noise
    python tools/build_library.py

第一条只检查，不修改工程文件；第二条只更新指定案例与确有变化的总索引；第三条全量重建。也可以组合 --check --effect dissolve/noise。
生成结果先写到系统临时目录，通过手改检查后才写回有变化的文件。发现将被更新的文件已被修改或删除，会列出并停止；不会静默覆盖。请先备份、合回生成源，再按需从 Git 恢复受影响的生成文件；不要为绕过保护删除清单。
退出码：0 为一致或生成成功，1 为检查发现待生成的变化，2 为手改冲突或配置错误。
清单只管理生成文件，不包含人工方案、验证记录和画面样本。内容比较兼容 LF / CRLF 换行；空格、文字和二进制内容仍逐项检查。
assets/cottage.png 是仓库内输入素材，正常重建不访问相邻 Blender 工程，也不重写这张图片。
生成器安全检查：python -B -m unittest discover -s tools/tests -v。M1 的实施与样本记录见 [M1 验收记录](docs/M1_VERIFICATION.md)。

## 实现边界

完整清单中有 {approximate} 个案例明确标为“演示近似”。例如运动模糊没有运动矢量，反应扩散没有跨帧数值求解，过度绘制热力图不是实际 GPU 计数。限制同时显示在图鉴中与各目录 README 中。
SSAO、SSR、SSIL、体积雾等管线案例使用 Godot 内置渲染功能，材质文件不冒充完整算法的实现。效果按原问题分目录；相近变体共享数学原理，但各自保留独立 Shader 源文件。
这是教学展示库，不表示每个案例都能直接用于生产环境。所有公式和占位素材均随项目提供。

## 验证

结构与语言检查：

    Godot_v4.7.2-stable_win64_console.exe --headless --path . --script res://tools/validate.gd

首批 20 项的真实显卡行为检查（不加 --headless）：

    Godot_v4.7.2-stable_win64_console.exe --path . --script res://tools/test_m3.gd

真实渲染器逐项审查并保存各类截图：

    Godot_v4.7.2-stable_win64_console.exe --path . -- --audit --quit-after-audit

审查报告写入 artifacts/runtime_audit.json。只在审查真正完成后，才能把报告作为运行结果。

本机已完成的检查及其范围见 [验证记录](docs/VERIFICATION.md)。
M3 的逐项结论、复查命令、未验证项与限制见 [M3 验收记录](docs/M3_VERIFICATION.md)。M4–M6 尚未实施；全库退出时仍有已知的 7 个 Texture RID 释放警告。

## 界面与素材说明

界面采用目录—预览—参数的通用开发工具布局。设计检索返回的 FAQ 页面模式不适合本地 Godot 工具，布局采用通用可访问性原则；使用深色高对比配色、清晰焦点与动画暂停控制。
字体通过系统字体回退，不从网络下载。小屋参考图来自本工作区的 Blender 建模示例；其余图片由项目脚本生成。

官方资料：
- https://docs.godotengine.org/en/stable/tutorials/shaders/introduction_to_shaders.html
- https://docs.godotengine.org/en/stable/tutorials/shaders/screen-reading_shaders.html
- https://docs.godotengine.org/en/stable/tutorials/shaders/advanced_postprocessing.html
""",encoding="utf-8")
    return {"effects":len(catalog),"categories":len(groups),"approximations":approximate,"kinds":{kind:sum(item["kind"]==kind for item in catalog) for kind in ["sprite","canvas","spatial","post","pipeline","depth"]}}


MANIFEST_PATH = "tools/generated_manifest.json"
TEXT_SUFFIXES = {".gdshader", ".tscn", ".json", ".md", ".svg"}
INDEX_PATHS = {"catalog.json", "categories.json", "docs/INDEX.md", "README.md"}


class BuildError(Exception):
    pass


def content_hash(path):
    data = path.read_bytes()
    if path.suffix in TEXT_SUFFIXES:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def managed_path(root, relative):
    path = Path(relative)
    if (not path.parts or path.is_absolute() or path.drive or "\\" in relative
            or ".." in path.parts or path.parts[0] == ".git"
            or path.as_posix() != relative):
        raise BuildError("Invalid generated path: " + relative)
    target = root / path
    if target.resolve() != target.absolute():
        raise BuildError("Generated paths must not traverse links: " + relative)
    return target


def read_manifest(root):
    path = root / MANIFEST_PATH
    if not path.is_file():
        raise BuildError("Missing " + MANIFEST_PATH + "; restore the reviewed manifest from Git. It cannot be re-created by trusting current files.")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(manifest, dict) or manifest.get("version") != 1 or manifest.get("hash_algorithm") != "sha256-lf-text"
            or not isinstance(manifest.get("files"), dict)):
        raise BuildError("Unsupported generated manifest format")
    for name, digest in manifest["files"].items():
        managed_path(root, name)
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise BuildError("Invalid generated hash: " + name)
    return manifest


def apply_generated(root, staged, manifest, effect=None, check=False):
    outputs = {path.relative_to(staged).as_posix(): path for path in staged.rglob("*") if path.is_file()}
    if effect:
        catalog = json.loads((staged / "catalog.json").read_text(encoding="utf-8"))
        entry = next(item for item in catalog if item["category_slug"] + "/" + item["slug"] == effect)
        prefix = entry["directory"].removeprefix("res://") + "/"
        selected = {name for name in outputs if name.startswith(prefix) or name in INDEX_PATHS}
    else:
        selected = set(outputs)
        obsolete = set(manifest["files"]) - selected
        if obsolete:
            raise BuildError("Generator no longer produces these files; review their removal and manifest explicitly:\n" + "\n".join(sorted(obsolete)))

    desired = {name: content_hash(outputs[name]) for name in selected}
    current = {}
    conflicts = []
    for name in sorted(selected):
        target = managed_path(root, name)
        current[name] = content_hash(target) if target.is_file() else None
        if name in manifest["files"]:
            if current[name] != manifest["files"][name]:
                conflicts.append(name + (" (deleted or not a regular file)" if current[name] is None else " (locally modified)"))
        elif target.exists() and current[name] != desired[name]:
            conflicts.append(name + " (unmanaged file already exists)")
    if conflicts:
        raise BuildError("Protected files; nothing was written:\n" + "\n".join(conflicts)
                         + "\nPreserve your edits, merge them into the generator sources, then restore the affected generated files from Git before rebuilding. Do not delete the manifest to bypass protection.")

    changed = sorted(name for name in selected if current[name] != desired[name])
    updated_manifest = dict(manifest)
    updated_manifest["files"] = dict(sorted((manifest["files"] | desired).items()))
    manifest_text = json.dumps(updated_manifest, ensure_ascii=False, indent=2) + "\n"
    manifest_changed = (root / MANIFEST_PATH).read_text(encoding="utf-8") != manifest_text
    if check:
        for name in changed:
            print("UPDATE " + name)
        if manifest_changed:
            print("UPDATE " + MANIFEST_PATH)
        print("CHECK " + ("DIFFERENT" if changed or manifest_changed else "OK") + " files=" + str(len(selected)))
        return 1 if changed or manifest_changed else 0

    for name in changed:
        target = managed_path(root, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(outputs[name].read_bytes())
    if manifest_changed:
        (root / MANIFEST_PATH).write_text(manifest_text, encoding="utf-8")
    print("BUILD OK scope=" + (effect or "all") + " files=" + str(len(selected)) + " updated=" + str(len(changed)))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Safely generate the Shader Atlas library.")
    parser.add_argument("--check", action="store_true", help="Compare temporary output without writing project files; exit 1 if different.")
    parser.add_argument("--effect", metavar="CATEGORY/SLUG", help="Update one effect and changed shared indexes, leaving other effects and shared assets untouched.")
    arguments = parser.parse_args(argv)
    try:
        keys = {group + "/" + pair.strip().split("=", 1)[0]
                for group, _, encoded in CATEGORIES for pair in encoded.strip().split("|")}
        if arguments.effect is not None and arguments.effect not in keys:
            raise BuildError("Unknown effect: " + arguments.effect + ". Use CATEGORY/SLUG, for example dissolve/noise.")
        manifest = read_manifest(ROOT)
        with tempfile.TemporaryDirectory(prefix="shader-atlas-build-") as temporary:
            build(Path(temporary))
            return apply_generated(ROOT, Path(temporary), manifest, arguments.effect, arguments.check)
    except (BuildError, OSError, ValueError) as error:
        print("BUILD ERROR: " + str(error), file=sys.stderr)
        return 2


if __name__=="__main__":
    sys.exit(main())
