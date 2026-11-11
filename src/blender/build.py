# 搏闻 7 个物件：Blender 建模 → 导出 GLB → 渲染预览
import bpy, bmesh, math, sys, os
from mathutils import Vector
OUT = "/home/claude/b3d/out"; os.makedirs(OUT, exist_ok=True)
TEX = "/home/claude/b3d/"
ONLY = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def mat(name, color, metal=0.0, rough=0.4, emit=None, emit_s=0.0, trans=0.0, ior=1.45, coat=0.0, alpha=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    lin = lambda c: c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4
    color = tuple(lin(c) for c in color)
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    b.inputs["IOR"].default_value = ior
    b.inputs["Transmission Weight"].default_value = trans
    b.inputs["Coat Weight"].default_value = coat
    if emit:
        emit = tuple(lin(c) for c in emit)
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = emit_s
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    return m

def img_node(m, path, socket, noncolor=False, normal=False):
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(path)
    if noncolor: t.image.colorspace_settings.name = "Non-Color"
    if normal:
        n = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(t.outputs["Color"], n.inputs["Color"]); nt.links.new(n.outputs["Normal"], b.inputs["Normal"])
    elif socket == "Roughness":
        s = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(t.outputs["Color"], s.inputs[0]); nt.links.new(s.outputs[1], b.inputs["Roughness"])
    else:
        nt.links.new(t.outputs["Color"], b.inputs[socket])
    return t

def give(o, m):
    o.data.materials.clear(); o.data.materials.append(m); return o

def smooth(o, angle=40):
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    try: bpy.ops.object.shade_auto_smooth(angle=math.radians(angle))
    except Exception: bpy.ops.object.shade_smooth()
    o.select_set(False); return o

def bevel(o, w, seg=4):
    m = o.modifiers.new("bevel", "BEVEL"); m.width = w; m.segments = seg; m.limit_method = "ANGLE"; return o

def apply_all(o):
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)

def lathe(name, prof, seg=96):
    """prof: [(r, z), ...] 自下而上，绕 Z 轴旋转"""
    verts = []; faces = []; n = len(prof)
    for i in range(seg):
        a = 2*math.pi*i/seg
        for r, z in prof: verts.append((r*math.cos(a), r*math.sin(a), z))
    for i in range(seg):
        j = (i+1) % seg
        for k in range(n-1):
            faces.append((i*n+k, j*n+k, j*n+k+1, i*n+k+1))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    bpy.ops.object.select_all(action="DESELECT")
    return smooth(o, 60)

def rbox(name, size, r, seg=6):
    bpy.ops.mesh.primitive_cube_add(size=1); o = bpy.context.object; o.name = name
    o.scale = size; bpy.ops.object.transform_apply(scale=True)
    bevel(o, r, seg); apply_all(o); return smooth(o, 50)

def root(name):
    e = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(e); return e

def parent(children, p):
    for c in children: c.parent = p

def export_and_render(name, cam_dist=4.2, cam_h=0.6, look_z=0.0):
    # 导出
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=f"{OUT}/{name}.glb", export_format="GLB", use_selection=False,
                              export_apply=True, export_yup=True)
    # 预览渲染
    sc = bpy.context.scene
    bpy.ops.object.camera_add(location=(0, -cam_dist, cam_h+look_z))
    cam = bpy.context.object; sc.camera = cam
    d = Vector((0, 0, look_z)) - cam.location; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 50
    for loc, e, s in (((3, -3, 4), 900, 4), ((-4, -2, 1.5), 350, 5), ((0, 4, 3), 500, 4)):
        bpy.ops.object.light_add(type="AREA", location=loc); L = bpy.context.object; L.data.energy = e; L.data.size = s
        dd = Vector((0, 0, 0)) - L.location; L.rotation_euler = dd.to_track_quat("-Z", "Y").to_euler()
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.95, 0.94, 0.92, 1); bg.inputs[1].default_value = 0.45
    sc.render.engine = "CYCLES"; sc.cycles.samples = 64; sc.cycles.use_denoising = True
    sc.render.film_transparent = True; sc.render.resolution_x = sc.render.resolution_y = 420
    sc.view_settings.view_transform = "Standard"
    sc.render.filepath = f"{OUT}/{name}.png"; bpy.ops.render.render(write_still=True)

# ---------------- 物件 ----------------
def globe():
    reset(); R = root("globe")
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=48, radius=1)
    s = smooth(bpy.context.object, 80); s.name = "ball"
    m = mat("ceramic", (1, 1, 1), rough=0.25, coat=0.6)
    img_node(m, TEX+"globe_albedo.jpg", "Base Color")
    img_node(m, TEX+"globe_normal.png", None, noncolor=True, normal=True)
    img_node(m, TEX+"globe_rough.png", "Roughness", noncolor=True)
    give(s, m)
    s.rotation_euler = (0, 0, math.radians(-200))  # 让亚洲朝前
    bpy.ops.object.transform_apply(rotation=True)
    tilt = root("tilt"); s.parent = tilt; tilt.rotation_euler = (0, math.radians(-23.4), 0); tilt.parent = R
    export_and_render("globe", cam_dist=4.4, cam_h=0.5)

def coin():
    reset(); R = root("coin")
    gold = mat("gold", (1.0, 0.70, 0.28), metal=1, rough=0.18)
    goldd = mat("gold_dark", (0.95, 0.58, 0.18), metal=1, rough=0.32)
    # 主体：带边缘凸起的回转体
    prof = [(0, -0.09), (0.80, -0.09), (0.84, -0.115), (0.97, -0.115), (1.0, -0.09), (1.0, 0.09), (0.97, 0.115), (0.84, 0.115), (0.80, 0.09), (0, 0.09)]
    body = give(lathe("body", prof, 160), gold)
    # 侧面竖纹
    edge = []
    for i in range(120):
        a = 2*math.pi*i/120
        bpy.ops.mesh.primitive_cube_add(size=1, location=(1.0*math.cos(a), 1.0*math.sin(a), 0), rotation=(0, 0, a))
        c = bpy.context.object; c.scale = (0.022, 0.012, 0.15); edge.append(c)
    for c in edge: c.select_set(True)
    bpy.context.view_layer.objects.active = edge[0]; bpy.ops.object.join(); ridges = give(bpy.context.object, gold)
    # 双面 ¥
    syms = []
    for side in (1, -1):
        bpy.ops.object.text_add(); t = bpy.context.object; t.data.body = "¥"
        t.data.align_x = "CENTER"; t.data.align_y = "CENTER"; t.data.size = 1.15; t.data.extrude = 0.035; t.data.bevel_depth = 0.012; t.data.bevel_resolution = 3
        t.location = (0, 0, side*0.095); t.rotation_euler = (0 if side > 0 else math.pi, 0, 0)
        bpy.ops.object.convert(target="MESH"); give(t, goldd); smooth(t, 30); syms.append(t)
    parent([body, ridges] + syms, R)
    R.rotation_euler = (math.radians(90), 0, 0)   # 正面朝向相机（-Y）
    export_and_render("coin", cam_dist=4.4, cam_h=0.3)

def chip():
    reset(); R = root("chip")
    sub = give(rbox("substrate", (2.2, 2.2, 0.14), 0.06), mat("substrate", (0.10, 0.16, 0.32), rough=0.5))
    top = rbox("die", (1.9, 1.9, 0.26), 0.09); top.location.z = 0.18
    m = mat("die", (1, 1, 1), rough=0.35, coat=0.5)
    img_node(m, TEX+"chip_albedo.jpg", "Base Color"); img_node(m, TEX+"chip_emit.jpg", "Emission Color")
    m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 1.4
    give(top, m)
    # 让贴图只在顶面：用平面投影 UV（顶视）
    bpy.context.view_layer.objects.active = top; top.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.cube_project(cube_size=1.9, scale_to_bounds=False); bpy.ops.object.mode_set(mode="OBJECT")
    me = top.data; uv = me.uv_layers.active.data
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            uv[li].uv = ((v.x/1.9)+0.5, (v.y/1.9)+0.5)
    top.select_set(False)
    # 金色引脚
    gold = mat("pin", (1.0, 0.72, 0.30), metal=1, rough=0.25)
    pins = []
    for side in range(4):
        for k in range(14):
            t = -0.95 + 0.07 + k*(1.9-0.14)/13
            bpy.ops.mesh.primitive_cube_add(size=1); p = bpy.context.object
            p.scale = (0.055, 0.32, 0.03)
            a = side*math.pi/2; r = 1.18
            p.location = (r*math.cos(a) - t*math.sin(a), r*math.sin(a) + t*math.cos(a), -0.03)
            p.rotation_euler = (0, 0, a+math.pi/2); bevel(p, 0.012, 2); apply_all(p); give(p, gold); pins.append(p)
    for p in pins: p.select_set(True)
    bpy.context.view_layer.objects.active = pins[0]; bpy.ops.object.join(); pinsj = bpy.context.object
    parent([sub, top, pinsj], R)
    R.rotation_euler = (math.radians(58), 0, math.radians(35))
    export_and_render("chip", cam_dist=5.2, cam_h=0.4)

def bulb():
    reset(); R = root("bulb")
    # 玻璃泡：经典 A 形轮廓，Catmull-Rom 插值
    key = [(0.30,-0.50),(0.31,-0.32),(0.40,-0.10),(0.58,0.15),(0.72,0.42),(0.77,0.66),(0.74,0.90),(0.62,1.10),(0.42,1.24),(0.20,1.31),(0.0,1.33)]
    prof = []
    for i in range(len(key)-1):
        p0 = key[max(i-1,0)]; p1 = key[i]; p2 = key[i+1]; p3 = key[min(i+2,len(key)-1)]
        for k in range(8):
            t = k/8; t2=t*t; t3=t2*t
            f = lambda a,b,c,d: 0.5*(2*b+(-a+c)*t+(2*a-5*b+4*c-d)*t2+(-a+3*b-3*c+d)*t3)
            prof.append((max(f(p0[0],p1[0],p2[0],p3[0]),0.0), f(p0[1],p1[1],p2[1],p3[1])))
    prof.append(key[-1])
    glass = lathe("glass", prof, 128)
    gm = mat("glass", (1.0, 0.93, 0.85), rough=0.04, trans=1.0, ior=1.45)
    give(glass, gm)
    # 灯丝 + 支架
    bpy.ops.curve.primitive_bezier_curve_add(); cu = bpy.context.object
    sp = cu.data.splines[0]; sp.bezier_points.add(4)
    pts = [(-0.16, 0, -0.45), (-0.13, 0, 0.10), (-0.11, 0, 0.42), (0.11, 0, 0.42), (0.13, 0, 0.10), (0.16, 0, -0.45)]
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p; bp.handle_left_type = bp.handle_right_type = "AUTO"
    cu.data.bevel_depth = 0.012; cu.data.bevel_resolution = 3
    bpy.ops.object.convert(target="MESH"); wire = give(bpy.context.object, mat("wire", (0.5, 0.45, 0.4), metal=1, rough=0.3))
    bpy.ops.mesh.primitive_torus_add(major_radius=0.06, minor_radius=0.011, major_segments=48, minor_segments=8)
    coil = bpy.context.object
    m = coil.modifiers.new("screw", "SCREW")  # 螺旋灯丝
    bpy.data.objects.remove(coil)
    # 用细螺旋代替：沿 x 方向的螺旋曲线
    verts = []
    N = 220
    for i in range(N):
        a = i/N*18*math.pi; x = -0.11 + 0.22*i/N
        verts.append((x*1.2, 0.05*math.cos(a), 0.42 + 0.05*math.sin(a)))
    cd = bpy.data.curves.new("coil", "CURVE"); cd.dimensions = "3D"; s = cd.splines.new("POLY"); s.points.add(N-1)
    for p, v in zip(s.points, verts): p.co = (*v, 1)
    cd.bevel_depth = 0.018; cd.bevel_resolution = 3
    co = bpy.data.objects.new("coil", cd); bpy.context.collection.objects.link(co)
    bpy.context.view_layer.objects.active = co; co.select_set(True); bpy.ops.object.convert(target="MESH")
    give(co, mat("filament", (1, 0.7, 0.3), emit=(1.0, 0.62, 0.22), emit_s=8))
    # 螺口：带螺纹的回转体
    prof2 = [(0, -1.22), (0.12, -1.22), (0.17, -1.16), (0.20, -1.10)]
    z = -1.10
    for k in range(5):
        prof2 += [(0.30, z+0.04), (0.33, z+0.08), (0.30, z+0.12)]; z += 0.12
    prof2 += [(0.33, z+0.02), (0.34, -0.48), (0.0, -0.48)]
    base = give(lathe("base", prof2, 96), mat("alu", (0.82, 0.82, 0.84), metal=1, rough=0.28))
    tip = give(lathe("tip", [(0, -1.27), (0.1, -1.26), (0.13, -1.21), (0.0, -1.20)], 48), mat("black", (0.05, 0.05, 0.05), rough=0.4))
    parent([glass, wire, co, base, tip], R)
    R.location.z = 0.35; R.rotation_euler = (math.radians(90), 0, 0)
    R.rotation_euler = (0, 0, 0)
    export_and_render("bulb", cam_dist=5.0, cam_h=0.4, look_z=0.0)

def lens():
    reset(); R = root("lens")
    purple = mat("purple", (0.50, 0.30, 0.95), rough=0.22, coat=0.8)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.82, minor_radius=0.13, major_segments=128, minor_segments=32)
    ring = give(smooth(bpy.context.object, 80), purple); ring.scale.z = 1.25
    gl = lathe("lensglass", [(0, -0.05), (0.72, -0.02), (0.72, 0.02), (0, 0.05)], 96)
    give(gl, mat("lensg", (0.92, 0.96, 1.0), rough=0.03, trans=1.0, ior=1.5))
    # 金属连接件 + 手柄
    neck = give(lathe("neck", [(0, 0), (0.12, 0), (0.13, 0.05), (0.13, 0.30), (0.11, 0.34), (0, 0.34)], 64), mat("steel", (0.85, 0.86, 0.9), metal=1, rough=0.25))
    handle = give(lathe("handle", [(0, 0), (0.15, 0.0), (0.17, 0.05), (0.17, 1.05), (0.12, 1.15), (0, 1.17)], 64), purple)
    for o, z in ((neck, 0.92), (handle, 1.24)):
        o.location = (0, 0, 0); o.rotation_euler = (0, 0, 0)
    # 手柄沿 -Y 方向（局部），再整体旋转
    neck.rotation_euler = (math.radians(90), 0, 0); neck.location = (0, -0.90, 0)
    handle.rotation_euler = (math.radians(90), 0, 0); handle.location = (0, -1.22, 0)
    neck.scale = handle.scale = (1, 1, 1)
    # 修正：lathe 沿 +Z，旋转 90° 到 -Y
    neck.rotation_euler = (math.radians(90), 0, 0); handle.rotation_euler = (math.radians(90), 0, 0)
    for o in (neck, handle):
        o.location.y = -0.9 if o is neck else -1.22
        o.rotation_euler = (math.radians(90), 0, 0)
    parent([ring, gl, neck, handle], R)
    # 镜面朝相机，手柄指向左下
    R.rotation_euler = (math.radians(90), math.radians(0), math.radians(0))
    R.rotation_euler = (math.radians(80), math.radians(-35), 0)
    R.location = (0.25, 0, 0.35); R.scale = (0.9, 0.9, 0.9)
    export_and_render("lens", cam_dist=5.0, cam_h=0.3)

def stack():
    reset(); R = root("stack")
    cols = [(0.93, 0.22, 0.24), (1.0, 0.52, 0.16), (1.0, 0.80, 0.18), (0.20, 0.72, 0.48), (0.22, 0.52, 0.95), (0.55, 0.36, 0.92)]
    layers = []
    for i, c in enumerate(cols):
        o = rbox(f"layer{i}", (1.8, 1.8, 0.16), 0.08, 6); o.location.z = 0.85 - i*0.34
        give(o, mat(f"c{i}", c, rough=0.28, coat=0.7)); layers.append(o)
    parent(layers, R)
    R.rotation_euler = (math.radians(55), 0, math.radians(38))
    export_and_render("stack", cam_dist=5.6, cam_h=0.6)

def plane():
    reset(); R = root("plane")
    # 纸飞机：机头在 +X，两片机翼 + 两片机身（龙骨）
    nose = (1.9, 0, 0.0)
    tailL = (-1.2, 1.45, 0.18); tailR = (-1.2, -1.45, 0.18)
    keel_bot = (-1.0, 0.0, -0.55)
    spineL = (-1.2, 0.03, 0.0); spineR = (-1.2, -0.03, 0.0)
    def tri(name, pts, m, solid=0.012):
        me = bpy.data.meshes.new(name); me.from_pydata(pts, [], [list(range(len(pts)))]); me.update()
        o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
        s = o.modifiers.new("s", "SOLIDIFY"); s.thickness = solid
        bpy.context.view_layer.objects.active = o; apply_all(o); give(o, m); return o
    white = mat("paper", (0.97, 0.97, 0.98), rough=0.6)
    blue = mat("paperb", (0.38, 0.66, 0.93), rough=0.55)
    wingL = tri("wingL", [nose, tailL, spineL], white)
    wingR = tri("wingR", [nose, spineR, tailR], blue)
    keelL = tri("keelL", [nose, spineL, keel_bot], blue)
    keelR = tri("keelR", [nose, keel_bot, spineR], white)
    parent([wingL, wingR, keelL, keelR], R)
    R.rotation_euler = (math.radians(-58), math.radians(-14), math.radians(32))
    export_and_render("plane", cam_dist=5.0, cam_h=0.6)

ALL = {"globe": globe, "coin": coin, "chip": chip, "bulb": bulb, "lens": lens, "stack": stack, "plane": plane}
for k, f in ALL.items():
    if ONLY and k not in ONLY: continue
    try:
        f(); print("OK", k)
    except Exception as ex:
        import traceback; traceback.print_exc(); print("FAIL", k, ex)
