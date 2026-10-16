"""The 23 categories requested in the conversation. Order is stable for browsing."""

CATEGORIES = [
    ("dissolve", "溶解、显隐与侵蚀", """
noise=噪声溶解|direction=方向溶解|height=高度溶解|radial=径向溶解|sphere=球形扩散溶解|mask=贴图遮罩溶解|burn=燃烧溶解|char=焦边溶解|glow=发光边缘溶解|pixel=像素块溶解|sand=沙化消散|corrosion=腐蚀消失|scan=扫描显现|teleport=传送显现|fade=渐隐渐现|dither=抖动透明
"""),
    ("outline", "描边、轮廓与遮挡", """
outer=外描边|inner=内描边|dual=双色描边|gradient=渐变描边|dashed=虚线描边|glow=发光描边|pulse=脉冲描边|selection=选中高亮|rim=轮廓光|fresnel=菲涅尔边缘光|silhouette=穿墙剪影|occlusion=遮挡轮廓|xray=X光透视|occluder_fade=遮挡物透明|camera_fade=靠近相机淡出|cutaway=剖切显示
"""),
    ("emission", "发光、流光与扫光", """
emission=自发光|breathing=呼吸发光|flicker=闪烁发光|band=条带扫光|diagonal=斜向扫光|border=边框流光|path=沿路径流光|flow=流动纹路|scanline=扫描线|marquee=跑马灯|neon=霓虹灯|circuit=电路流光|cracks=发光裂缝|rainbow=彩虹流光|glitter=闪粉|stars=星点闪烁
"""),
    ("stylized", "卡通与绘画风格", """
toon=Toon卡通渲染|cel=Cel赛璐璐|bands=二段三段明暗|ramp=Ramp色带光照|highlight=卡通高光|shadow=卡通阴影|flat=平面着色|low_poly=低多边形色块|matcap=MatCap|halftone=漫画网点|hatching=排线|crosshatch=交叉排线|pencil=铅笔素描|charcoal=炭笔|ink=水墨|watercolor=水彩|oil=油画|woodcut=版画|paper=剪纸风格
"""),
    ("materials", "真实与半真实材质", """
metal=金属|brushed=拉丝金属|plastic=塑料|rubber=橡胶|ceramic=陶瓷|skin=皮肤|wax=蜡|jade=玉石|cloth=布料|silk=丝绸|velvet=绒布|leather=皮革|hair=毛发|eye=眼球|clearcoat=清漆|car_paint=车漆|pearl=珠光|iridescence=虹彩|thin_film=薄膜干涉|flakes=金属闪片|pbr=PBR|normal=法线贴图|bump=凹凸贴图|detail_normal=细节法线|anisotropy=各向异性|sss=次表面散射|transmission=透射|layered=多层材质
"""),
    ("glass", "透明、折射与反射", """
clear=透明玻璃|frosted=磨砂玻璃|stained=彩色玻璃|ice=冰|crystal=晶体|gem=宝石|bubble=肥皂泡|jelly=果冻|liquid=液体折射|absorption=玻璃厚度吸收|dispersion=色散|mirror=镜面反射|blurred=模糊反射|fresnel=菲涅尔反射|invisibility=隐身折射|air=空气扰动
"""),
    ("water", "水体与液体表面", """
calm=平静水面|ocean=海浪|river=河流|waterfall=瀑布|vortex=漩涡|ripple=水波纹|interactive=交互涟漪|depth=深浅水渐变|shore=岸边泡沫|crest=浪尖白沫|caustics=水下焦散|underwater=水下扭曲|fog=水下雾|reflection=水面反射|droplets=水滴流淌|rain=雨滴波纹|sloshing=液面晃动|container=容器内液面|slime=黏液
"""),
    ("fire", "火焰、烟雾与爆炸", """
flame=写实火焰|toon_flame=卡通火焰|distortion=火焰扭曲|burning=燃烧表面|embers=余烬|lava=熔岩|magma=流动岩浆|smoke=烟雾|toon_smoke=卡通烟团|explosion=爆炸火球|shockwave=爆炸冲击波|dust=尘土|sandstorm=沙尘|steam=蒸汽|poison=毒气|jet=喷气尾焰
"""),
    ("terrain", "地表与表面变化", """
blend=多材质混合|height_blend=高度混合|slope=坡度混合|vertex_blend=顶点色混合|snow=积雪覆盖|melt=融雪|frost=结霜|moss=苔藓覆盖|dust=积灰|mud=泥土附着|wet=湿润表面|puddle=水洼|road=雨后路面|rust=锈蚀|oil=油污|scratch=划痕|crack=裂纹|char=烧焦|footprint=脚印|snow_track=雪地压痕|tire=车辙
"""),
    ("sky", "天空、天气与大气", """
gradient=渐变天空|procedural=程序化天空|day_night=昼夜渐变|stars=星空|twinkle=星星闪烁|sun=太阳光晕|moon=月亮光晕|clouds=流动云层|volume_clouds=体积云|distance_fog=距离雾|height_fog=高度雾|local_fog=局部雾|volume_fog=体积雾|light_column=光柱|god_rays=丁达尔光|aurora=极光|rain=雨丝|snow=雪花|sand=风沙|dust=漂浮尘埃
"""),
    ("magic", "科幻、能量与魔法", """
shield=能量护盾|hex_shield=六边形护盾|shield_hit=护盾受击波纹|core=能量核心|hologram=全息投影|holo_scan=全息扫描|digital=数字化身体|portal=传送门|rift=空间裂隙|circle=魔法阵|runes=旋转符文|summon=召唤阵|beam=能量光束|laser=激光|arc=电弧|lightning=闪电|charge=蓄力光圈|shock_ring=冲击环|slash=刀光|sword=剑气|trail=拖尾|afterimage=残影|black_hole=黑洞|nebula=星云
"""),
    ("status", "角色受击与状态", """
white=受击闪白|red=受击泛红|invincible=无敌闪烁|heal=治疗流光|poison=中毒染色|burn=灼烧|freeze=冻结|ice=冰层覆盖|stone=石化|metal=金属化|gold=黄金化|infection=感染扩散|cracks=身体裂痕|wound=伤口显现|damage=局部损伤|ghost=幽灵化|death=死亡消散
"""),
    ("vertex", "顶点变形与模型运动", """
wave=波浪起伏|flag=旗帜飘动|wind=草木风摆|leaves=树叶颤动|jelly=果冻抖动|squash=挤压拉伸|breathing=呼吸鼓胀|bend=弯曲|twist=扭转|sphere=球化|inflate=膨胀收缩|explode=顶点散开|vortex=旋涡吸入|snap=顶点吸附|vat=顶点动画贴图VAT播放|billboard=广告牌朝向相机
"""),
    ("uv", "UV、视差与程序纹理", """
scroll=UV滚动|rotate=UV旋转|zoom=UV缩放|distort=UV扭曲|polar=极坐标变换|kaleidoscope=万花筒|flowmap=流向图|flipbook=序列帧播放|triplanar=三平面映射|random_tile=随机平铺|stochastic=消除重复纹理|parallax=视差贴图|pom=视差遮蔽映射POM|interior=窗内假房间|noise=噪声|voronoi=Voronoi蜂窝|wood=木纹|marble=大理石纹|stone=石纹|checker=棋盘格|camouflage=迷彩|cracks=程序化裂纹
"""),
    ("sprite", "2D精灵与像素画", """
outline=精灵描边|glow=内外发光|shadow=精灵投影|flash=受击闪白|recolor=局部换色|palette=调色板替换|color_key=颜色键透明|pixel=像素化|dither=抖动渐变|pixel_light=像素风光照|normal_light=2D法线光照|dissolve=精灵溶解|bend=纸片弯曲|page=翻页|reflection=2D水面倒影|distort=精灵扭曲|spine=Spine特效材质
"""),
    ("ui", "UI、文字与地图", """
gradient=渐变填色|gradient_text=渐变文字|text_outline=文字描边|text_shadow=文字阴影|text_shine=文字流光|text_wave=文字波动|typewriter=打字显现遮罩|button_shine=按钮扫光|border=边框流光|rounded=圆角矩形|feather=柔边遮罩|clip=软裁剪|ring=环形进度|cooldown=扇形冷却|liquid=液体进度条|health=血条闪烁|frosted=磨砂背景|radar=雷达扫描|fog_of_war=战场迷雾|vision=视野遮罩|contours=地图等高线|dashed_path=行军虚线|arrows=流动路径箭头
"""),
    ("color", "屏幕调色", """
brightness=亮度|contrast=对比度|saturation=饱和度|hue=色相旋转|grayscale=灰度|invert=反色|duotone=双色调|gradient_map=渐变映射|posterize=色阶压缩|quantize=色彩量化|lut=LUT调色|temperature=冷暖色调整|white_balance=白平衡|exposure=曝光|tonemap=色调映射|local=局部调色|night=夜视仪风格|thermal=热成像风格|damage=受伤红屏
"""),
    ("lens", "模糊、镜头与扭曲", """
gaussian=高斯模糊|bilateral=双边模糊|kawase=Kawase模糊|directional=方向模糊|radial=径向模糊|zoom=缩放模糊|motion=运动模糊|dof=景深|bokeh=散景|tilt_shift=移轴效果|bloom=Bloom泛光|flare=镜头光晕|dirt=镜头污渍|vignette=暗角|chromatic=色差|fisheye=鱼眼|barrel=桶形畸变|pincushion=枕形畸变|heat=热浪扭曲|shockwave=冲击波扭曲|rain=屏幕雨滴|underwater=水下镜头
"""),
    ("retro", "复古、故障与显示器", """
crt=CRT显像管|scanlines=扫描线|phosphor=荧光点阵|curvature=屏幕弯曲|vhs=VHS录像带|tape=磁带噪点|tv=模拟电视干扰|rgb=RGB通道分离|glitch=数字故障|displace=画面错位|tearing=画面撕裂|mosaic=马赛克|banding=色带|dither=抖动降色|grain=胶片颗粒|scratches=老电影划痕|ps1=PS1顶点抖动|affine=仿射纹理变形
"""),
    ("transition", "场景切换与转场", """
fade=淡入淡出|crossfade=交叉渐变|wipe=方向擦除|circle=圆形展开|radial=扇形展开|blinds=百叶窗|checker=棋盘格切换|pixel=像素块切换|noise=噪声转场|burn=燃烧转场|ripple=水波转场|ink=墨迹扩散转场|glitch=故障转场|vortex=旋涡转场|page=翻页转场|portal=传送门过渡
"""),
    ("lighting", "光照、阴影与空间渲染", """
diffuse=漫反射|specular=高光|soft_specular=柔和高光|self_shadow=自阴影|shadow=投影|soft_shadow=软阴影|contact=接触阴影|ao=环境遮蔽|ssao=屏幕空间环境遮蔽SSAO|ssr=屏幕空间反射SSR|ssil=屏幕空间间接光|probe=反射探针混合|lightmap=光照贴图混合|cookie=投影纹理|caustics=模拟焦散
"""),
    ("advanced", "程序化与体积进阶", """
sdf=SDF距离场图形|raymarch=Raymarching光线步进|terrain=程序化地形|cloud=体积烟云|fractal=分形图形|mandelbrot=Mandelbrot|mandelbulb=Mandelbulb|metaball=融合球Metaball|viscous=黏性融合|reaction=反应扩散纹理|feedback=反馈拖影|tunnel=程序化隧道|infinite=无限空间|volume_light=伪体积光
"""),
    ("debug", "辅助显示与可视化", """
wireframe=线框|normal=法线显示|uv=UV棋盘格|world=世界坐标着色|depth=深度显示|id=物体ID着色|vertex=顶点色显示|texel=纹理密度热力图|overdraw=过度绘制热力图|lod=LOD抖动过渡|distance=距离渐隐
"""),
]
