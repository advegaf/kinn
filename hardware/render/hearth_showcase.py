"""Hearth showcase renders: product photography of the finished Hearth and the iPhone app.

Run: blender -b -P hearth_showcase.py -- <breakfast|playing|phone|studio> [abs out.png] [samples] [res %]
The Hearth assembly (STLs, Fire tablet, screen plane, TO_SCENE, lean) is copied from hearth_scene_v4.py.
Props are built from primitives here. Units: metres.
"""
import math
import os
import sys

import bpy
from mathutils import Euler, Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.join(HERE, "..", "cad")
sys.path.insert(0, CAD)
import hearth_parts as hp  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SHOT = argv[0] if argv else "breakfast"
OUT = os.path.abspath(argv[1]) if len(argv) > 1 else os.path.join(HERE, f"showcase-{SHOT}.png")
SAMPLES = int(argv[2]) if len(argv) > 2 else 160
RES_PCT = int(argv[3]) if len(argv) > 3 else 100
SCREENS = os.path.join(HERE, "..", "..", "docs", "screens")
HEARTH_IMG = os.environ.get("HEARTH_IMG") or os.path.join(SCREENS, "hearth-v4c-playing.png" if SHOT == "playing" else "hearth-v4c-waiting.png")
PHONE_IMG = os.path.join(SCREENS, "ios-v4c-entry.png" if SHOT == "phone" else "ios-v4c-week.png")
CREAM = (0.93, 0.89, 0.80)
LEAN_DEG = 9.0
mm = 0.001

hp.FACE_T = hp.GLASS_Z = 1.6
hp.FOAM_T, hp.CAP_HEAD_T = 3.0, 6.0

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
coll = scene.collection


# ---------------------------------------------------------------- helpers

def mat(name, color, rough=0.5, metallic=0.0, emission=None, strength=1.0, image=None, sss=0.0, sss_scale=0.002):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Subsurface Weight"].default_value = sss
    b.inputs["Subsurface Scale"].default_value = sss_scale
    b.inputs["Subsurface Radius"].default_value = (1.0, 0.6, 0.35)
    if emission:
        b.inputs["Emission Color"].default_value = (*emission, 1)
        b.inputs["Emission Strength"].default_value = strength
    if image:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(image)
        tex.extension = "EXTEND"
        b.inputs["Base Color"].default_value = (0, 0, 0, 1)
        nt.links.new(tex.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = strength
    return m


def bsdf(m):
    return m.node_tree.nodes["Principled BSDF"]


def N(nt, kind, **kw):
    n = nt.nodes.new(kind)
    for k, v in kw.items():
        if k in n.inputs:
            n.inputs[k].default_value = v
        else:
            setattr(n, k, v)
    return n


def L(nt, a, b):
    nt.links.new(a, b)


def M(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def maprange(nt, v, a, b, lo=0.0, hi=1.0):
    n = N(nt, "ShaderNodeMapRange")
    n.inputs["From Min"].default_value, n.inputs["From Max"].default_value = a, b
    n.inputs["To Min"].default_value, n.inputs["To Max"].default_value = lo, hi
    n.clamp = True
    L(nt, v, n.inputs["Value"])
    return n.outputs["Result"]


def bump(nt, height, distance, strength=1.0):
    n = N(nt, "ShaderNodeBump", Strength=strength, Distance=distance)
    L(nt, height, n.inputs["Height"])
    L(nt, n.outputs["Normal"], bsdf_of(nt).inputs["Normal"])
    return n


def bsdf_of(nt):
    return nt.nodes["Principled BSDF"]


def obj_coords(nt):
    return N(nt, "ShaderNodeTexCoord").outputs["Object"]


def select(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def smooth(o, angle=35):
    select(o)
    bpy.ops.object.shade_auto_smooth(angle=math.radians(angle))


def new_obj(name, me):
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


def empty(name, loc=(0, 0, 0), rot=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    coll.objects.link(e)
    e.location, e.rotation_euler = loc, rot
    return e


def parent(objs, p):
    for o in objs:
        o.parent = p


def lathe(name, profile, material, steps=96, subsurf=2, loc=(0, 0, 0)):
    """Revolve an open (r, z) polyline around z. Profile runs from the axis round to the axis."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([(r, 0, z) for r, z in profile], [(i, i + 1) for i in range(len(profile) - 1)], [])
    o = new_obj(name, me)
    o.location = loc
    s = o.modifiers.new("screw", "SCREW")
    s.axis, s.steps, s.render_steps = "Z", steps, steps
    s.use_merge_vertices, s.merge_threshold = True, 1e-6
    s.use_normal_calculate = True
    if subsurf:
        d = o.modifiers.new("subd", "SUBSURF")
        d.levels = d.render_levels = subsurf
    me.materials.append(material)
    for p in me.polygons:
        p.use_smooth = True
    smooth(o, 180)
    return o


def rr_points(w, h, r, seg=12):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def slab(name, w, h, t, r, material, z0=0.0, uv=False, seg=12):
    """Rounded rectangle slab, centred in xy, from z0 to z0 + t. Optional planar UVs over w x h."""
    pts = rr_points(w, h, r, seg)
    n = len(pts)
    verts = [(x, y, z0) for x, y in pts] + [(x, y, z0 + t) for x, y in pts]
    faces = [list(range(n - 1, -1, -1)), list(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    o = new_obj(name, me)
    if uv:
        lay = me.uv_layers.new()
        for loop in me.loops:
            co = me.vertices[loop.vertex_index].co
            lay.data[loop.index].uv = (co.x / w + 0.5, co.y / h + 0.5)
    me.materials.append(material)
    return o


def bevel(o, width, segs=4):
    b = o.modifiers.new("bevel", "BEVEL")
    b.width, b.segments, b.limit_method = width, segs, "ANGLE"
    b.harden_normals = False
    for p in o.data.polygons:
        p.use_smooth = True
    smooth(o, 40)
    return o


def cube(name, size, loc, material, bev=0.0, segs=3, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    if bev:
        bevel(o, bev, segs)
    return o


def curve(name, pts, radius, material, order=4):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth, cu.bevel_resolution, cu.use_fill_caps = radius, 4, True
    sp = cu.splines.new("NURBS")
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (*c, 1)
    sp.use_endpoint_u, sp.order_u = True, min(order, len(pts))
    sp.resolution_u = 24
    cu.materials.append(material)
    return new_obj(name, cu)


def sphere(name, loc, scale, material, rot=(0, 0, 0), seg=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    o.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return o


def look(o, target, up="Y"):
    o.rotation_euler = (Vector(target) - o.location).to_track_quat("-Z", up).to_euler()


# ---------------------------------------------------------------- materials

def wood_mat():
    m = mat("oak", (0.4, 0.25, 0.14), rough=0.42)
    nt = m.node_tree
    b = bsdf_of(nt)
    b.inputs["Coat Weight"].default_value = 0.25
    b.inputs["Coat Roughness"].default_value = 0.18
    co = obj_coords(nt)
    sep = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, co, sep.inputs[0])
    plank = M(nt, "FLOOR", M(nt, "DIVIDE", sep.outputs["Y"], 0.16))
    seam = M(nt, "FRACT", M(nt, "DIVIDE", sep.outputs["Y"], 0.16))
    groove = M(nt, "MAXIMUM", maprange(nt, seam, 0.012, 0.0), maprange(nt, seam, 0.988, 1.0))
    # per-plank offset so the grain does not line up across seams
    wn = N(nt, "ShaderNodeTexWhiteNoise", noise_dimensions="1D")
    L(nt, plank, wn.inputs["W"])
    comb = N(nt, "ShaderNodeCombineXYZ")
    L(nt, M(nt, "ADD", M(nt, "MULTIPLY", sep.outputs["X"], 0.22), M(nt, "MULTIPLY", wn.outputs["Value"], 7.0)), comb.inputs["X"])
    L(nt, M(nt, "MULTIPLY", sep.outputs["Y"], 1.0), comb.inputs["Y"])
    L(nt, sep.outputs["Z"], comb.inputs["Z"])
    wave = N(nt, "ShaderNodeTexWave", bands_direction="Y", Scale=55.0, Distortion=9.0, Detail=5.0)
    wave.inputs["Detail Scale"].default_value = 1.4
    L(nt, comb.outputs[0], wave.inputs["Vector"])
    fine = N(nt, "ShaderNodeTexNoise", Scale=60.0, Detail=6.0)
    L(nt, comb.outputs[0], fine.inputs["Vector"])
    ramp = N(nt, "ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.2, 0.1, 0.045, 1)
    ramp.color_ramp.elements[1].color = (0.42, 0.25, 0.13, 1)
    grain = M(nt, "ADD", M(nt, "MULTIPLY", wave.outputs["Fac"], 0.75), M(nt, "MULTIPLY", fine.outputs["Fac"], 0.25))
    L(nt, M(nt, "ADD", grain, M(nt, "MULTIPLY", M(nt, "SUBTRACT", wn.outputs["Value"], 0.5), 0.25)), ramp.inputs["Fac"])
    dark = N(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    L(nt, groove, dark.inputs["Factor"])
    L(nt, ramp.outputs["Color"], dark.inputs[6])
    dark.inputs[7].default_value = (0.25, 0.18, 0.12, 1)
    L(nt, dark.outputs[2], b.inputs["Base Color"])
    L(nt, maprange(nt, wave.outputs["Fac"], 0, 1, 0.34, 0.52), b.inputs["Roughness"])
    bump(nt, M(nt, "SUBTRACT", M(nt, "MULTIPLY", wave.outputs["Fac"], 0.3), groove), 0.0012)
    return m


def linen_mat(name, color, scale=1.0):
    m = mat(name, color, rough=0.85)
    nt = m.node_tree
    b = bsdf_of(nt)
    b.inputs["Sheen Weight"].default_value = 0.25
    b.inputs["Sheen Roughness"].default_value = 0.4
    co = obj_coords(nt)
    w1 = N(nt, "ShaderNodeTexWave", bands_direction="X", Scale=700.0 * scale, Distortion=0.8, Detail=0.0)
    w2 = N(nt, "ShaderNodeTexWave", bands_direction="Y", Scale=700.0 * scale, Distortion=0.8, Detail=0.0)
    nz = N(nt, "ShaderNodeTexNoise", Scale=90.0 * scale, Detail=8.0)
    slub = N(nt, "ShaderNodeTexNoise", Scale=12.0 * scale, Detail=3.0)
    for t in (w1, w2, nz, slub):
        L(nt, co, t.inputs["Vector"])
    weave = M(nt, "MAXIMUM", w1.outputs["Fac"], w2.outputs["Fac"])
    h = M(nt, "ADD", M(nt, "MULTIPLY", weave, 0.6), M(nt, "MULTIPLY", nz.outputs["Fac"], 0.4))
    bump(nt, h, 0.0005, 1.0)
    tint = N(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    L(nt, maprange(nt, slub.outputs["Fac"], 0.3, 0.7, 0.0, 0.4), tint.inputs["Factor"])
    tint.inputs[6].default_value = (*color, 1)
    tint.inputs[7].default_value = (0.78, 0.72, 0.64, 1)
    L(nt, tint.outputs[2], b.inputs["Base Color"])
    return m


def ceramic_mat(name, color, speck=True, rough=0.1):
    m = mat(name, color, rough=rough, sss=0.12, sss_scale=0.003)
    nt = m.node_tree
    b = bsdf_of(nt)
    b.inputs["Coat Weight"].default_value = 0.4
    b.inputs["Coat Roughness"].default_value = 0.05
    if speck:
        co = obj_coords(nt)
        nz = N(nt, "ShaderNodeTexNoise", Scale=900.0, Detail=1.0)
        L(nt, co, nz.inputs["Vector"])
        mix = N(nt, "ShaderNodeMix", data_type="RGBA")
        L(nt, maprange(nt, nz.outputs["Fac"], 0.66, 0.70), mix.inputs["Factor"])
        mix.inputs[6].default_value = (*color, 1)
        mix.inputs[7].default_value = (0.25, 0.18, 0.13, 1)
        L(nt, mix.outputs[2], b.inputs["Base Color"])
        wob = N(nt, "ShaderNodeTexNoise", Scale=30.0, Detail=2.0)
        L(nt, co, wob.inputs["Vector"])
        bump(nt, wob.outputs["Fac"], 0.0002, 0.3)
    return m


def concha_mat(name, topping):
    """Bread dome with a sugar topping scored in a shell pattern. Object coords: dome base at z=0, r=45 mm."""
    m = mat(name, (0.6, 0.35, 0.15), rough=0.75, sss=0.05)
    nt = m.node_tree
    b = bsdf_of(nt)
    co = obj_coords(nt)
    sep = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, co, sep.inputs[0])
    x = M(nt, "DIVIDE", sep.outputs["X"], 0.045)
    y = M(nt, "DIVIDE", sep.outputs["Y"], 0.045)
    r = M(nt, "SQRT", M(nt, "ADD", M(nt, "MULTIPLY", x, x), M(nt, "MULTIPLY", y, y)))
    th = M(nt, "ARCTAN2", y, x)
    wob = N(nt, "ShaderNodeTexNoise", Scale=40.0, Detail=2.0)
    L(nt, co, wob.inputs["Vector"])
    jit = M(nt, "SUBTRACT", wob.outputs["Fac"], 0.5)
    r = M(nt, "ADD", r, M(nt, "MULTIPLY", jit, 0.12))
    th = M(nt, "ADD", th, M(nt, "MULTIPLY", jit, 0.5))
    # swirling ribs from the crown plus two growth rings: the concha shell
    u = M(nt, "ADD", M(nt, "MULTIPLY", th, 11 / (2 * math.pi)), M(nt, "MULTIPLY", r, 1.1))
    ribs = maprange(nt, M(nt, "ABSOLUTE", M(nt, "SUBTRACT", M(nt, "FRACT", u), 0.5)), 0.445, 0.5)
    rings = maprange(nt, M(nt, "ABSOLUTE", M(nt, "SUBTRACT", M(nt, "FRACT", M(nt, "MULTIPLY", r, 3.2)), 0.5)), 0.45, 0.5)
    groove = M(nt, "MULTIPLY", M(nt, "MAXIMUM", ribs, rings), maprange(nt, r, 0.12, 0.3))
    edge_n = N(nt, "ShaderNodeTexNoise", Scale=60.0, Detail=3.0)
    L(nt, co, edge_n.inputs["Vector"])
    zt = M(nt, "ADD", sep.outputs["Z"], M(nt, "MULTIPLY", M(nt, "SUBTRACT", edge_n.outputs["Fac"], 0.5), 0.006))
    top = maprange(nt, zt, 0.0145, 0.0165)
    sugar = M(nt, "MULTIPLY", top, M(nt, "SUBTRACT", 1.0, groove))
    crumb = N(nt, "ShaderNodeTexNoise", Scale=400.0, Detail=4.0)
    L(nt, co, crumb.inputs["Vector"])
    bread = N(nt, "ShaderNodeMix", data_type="RGBA")
    L(nt, maprange(nt, sep.outputs["Z"], 0.0, 0.02), bread.inputs["Factor"])
    bread.inputs[6].default_value = (0.36, 0.17, 0.06, 1)
    bread.inputs[7].default_value = (0.5, 0.26, 0.08, 1)
    col = N(nt, "ShaderNodeMix", data_type="RGBA")
    L(nt, sugar, col.inputs["Factor"])
    L(nt, bread.outputs[2], col.inputs[6])
    shade = N(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    L(nt, maprange(nt, crumb.outputs["Fac"], 0.3, 0.7, 0.0, 0.12), shade.inputs["Factor"])
    shade.inputs[6].default_value = (*topping, 1)
    shade.inputs[7].default_value = (0.75, 0.7, 0.65, 1)
    L(nt, shade.outputs[2], col.inputs[7])
    L(nt, col.outputs[2], b.inputs["Base Color"])
    L(nt, maprange(nt, sugar, 0, 1, 0.8, 0.95), b.inputs["Roughness"])
    bump(nt, M(nt, "ADD", M(nt, "MULTIPLY", sugar, 1.0), M(nt, "MULTIPLY", crumb.outputs["Fac"], 0.35)), 0.0025)
    return m


def glass_mat():
    m = mat("glass", (0.97, 0.98, 0.97), rough=0.02)
    b = bsdf(m)
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.47
    return m


def plaster_mat(color):
    m = mat("plaster", color, rough=0.92)
    nt = m.node_tree
    nz = N(nt, "ShaderNodeTexNoise", Scale=18.0, Detail=10.0, Roughness=0.62)
    L(nt, obj_coords(nt), nz.inputs["Vector"])
    bump(nt, nz.outputs["Fac"], 0.002, 0.25)
    return m


# ---------------------------------------------------------------- the Hearth (from hearth_scene_v4.py)

def load(path, material):
    bpy.ops.wm.stl_import(filepath=path)
    o = bpy.context.selected_objects[0]
    o.data.materials.append(material)
    smooth(o, 50)
    return o


def build_hearth(image):
    cream = mat("cream_pla", CREAM, rough=0.7, sss=0.15)
    nt = cream.node_tree
    nz = N(nt, "ShaderNodeTexNoise", Scale=2500.0, Detail=2.0)
    L(nt, obj_coords(nt), nz.inputs["Vector"])
    bump(nt, nz.outputs["Fac"], 0.00002, 0.15)   # faint matte print texture (object coords are mm)
    black = mat("fire_black", (0.02, 0.02, 0.022), rough=0.35)
    screen_m = mat("screen", (0, 0, 0), rough=0.15, image=image, strength=1.6)
    bezel = load(os.path.join(CAD, "stl", "front_bezel.stl"), cream)
    shell = load(os.path.join(CAD, "stl", "back_shell.stl"), cream)
    shell.data.transform(Matrix.Translation((0, 0, hp.FACE_T)))
    tablet = hp.rrect("fire_hd8", hp.TAB_W, hp.TAB_H, hp.FACE_T + 0.1, hp.FACE_T + hp.TAB_T, hp.TAB_CORNER_R)
    tablet.data.materials.append(black)
    o = hp.box("screen", -hp.ACT_W / 2, hp.ACT_W / 2, -hp.ACT_H / 2, hp.ACT_H / 2, hp.FACE_T + 0.05, hp.FACE_T + 0.06)
    o.data.uv_layers.new()
    for loop in o.data.loops:
        co = o.data.vertices[loop.vertex_index].co
        o.data.uv_layers.active.data[loop.index].uv = (-co.x / hp.ACT_W + 0.5, co.y / hp.ACT_H + 0.5)
    o.data.materials.append(screen_m)
    parts = [bezel, shell, tablet, o]
    for p in parts:   # booleans leave an empty slot 0 on hp meshes
        real = [m for m in p.data.materials if m]
        if len(real) == 1 and len(p.data.materials) > 1:
            p.data.materials.clear()
            p.data.materials.append(real[0])
    to_scene = Matrix.Scale(mm, 4) @ Matrix(((-1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    rig = empty("hearth")
    for p in parts:
        p.matrix_world = to_scene
        p.parent = rig
    return rig, parts


def place_hearth(rig, parts, x, y, yaw_deg=0.0, floor=0.0):
    rig.rotation_euler = (-math.radians(LEAN_DEG), 0, math.radians(yaw_deg))
    rig.location = (x, y, 0)
    bpy.context.view_layer.update()
    low = min((p.matrix_world @ v.co).z for p in parts[:2] for v in p.data.vertices)
    rig.location.z = floor - low
    bpy.context.view_layer.update()


# ---------------------------------------------------------------- props

def iphone(loc, rot, image):
    """iPhone 16 Pro class slab: titanium frame, black glass, emissive screen. Origin at the back centre."""
    ti = mat("titanium", (0.62, 0.6, 0.56), rough=0.28, metallic=1.0)
    glass_blk = mat("phone_glass", (0.008, 0.008, 0.01), rough=0.06)
    bsdf(glass_blk).inputs["Coat Weight"].default_value = 1.0
    scr = mat("phone_screen", (0, 0, 0), rough=0.05, image=image, strength=1.25)
    bsdf(scr).inputs["Coat Weight"].default_value = 0.15
    bsdf(scr).inputs["Coat Roughness"].default_value = 0.03
    body = bevel(slab("phone_body", 71.5 * mm, 149.6 * mm, 7.6 * mm, 11 * mm, ti, seg=16), 1.6 * mm, 4)
    front = bevel(slab("phone_front", 70.6 * mm, 148.7 * mm, 0.7 * mm, 10.5 * mm, glass_blk, z0=7.5 * mm, seg=16), 0.4 * mm, 3)
    screen = slab("phone_screen", 65.8 * mm, 143.0 * mm, 0.05 * mm, 8.5 * mm, scr, z0=8.2 * mm, uv=True, seg=16)
    island = slab("phone_island", 19.5 * mm, 5.8 * mm, 0.05 * mm, 2.9 * mm, glass_blk, z0=8.26 * mm, seg=8)
    island.location.y = (143.0 / 2 - 7.0) * mm
    buttons = [cube("phone_btn", (1.2 * mm, l * mm, 2.4 * mm), (sx * 36.0 * mm, cy * mm, 3.9 * mm), ti, bev=0.5 * mm)
               for sx, cy, l in ((-1, 38, 9), (-1, 22, 16), (-1, 2, 16), (1, 22, 22))]
    rig = empty("iphone", loc, rot)
    parent([body, front, screen, island] + buttons, rig)
    return rig


def cup_and_saucer(loc, yaw_deg, glaze):
    saucer = lathe("saucer", [(0, 0.0), (0.036, 0.0), (0.04, 0.0025), (0.044, 0.0042), (0.062, 0.0092), (0.073, 0.0152),
                              (0.0752, 0.0168), (0.0745, 0.0178), (0.072, 0.0172), (0.058, 0.0118), (0.044, 0.0076),
                              (0.040, 0.0068), (0, 0.0066)], glaze)
    cup = lathe("cup", [(0, 0.0004), (0.024, 0.0004), (0.0255, 0.0), (0.028, 0.0), (0.0292, 0.004), (0.031, 0.011),
                        (0.036, 0.04), (0.0398, 0.075), (0.0408, 0.0885), (0.0404, 0.0898), (0.0392, 0.0898),
                        (0.0383, 0.087), (0.0372, 0.07), (0.033, 0.04), (0.027, 0.012), (0.018, 0.0072), (0, 0.007)],
                glaze, loc=(0, 0, 0.0066))
    coffee = mat("coffee", (0.07, 0.035, 0.015), rough=0.04)
    c = lathe("coffee", [(0, 0.0756), (0.0378, 0.0756)], coffee, subsurf=0, loc=(0, 0, 0.0066))
    handle = curve("handle", [(0.0372, 0, 0.073), (0.056, 0, 0.074), (0.064, 0, 0.055), (0.056, 0, 0.032), (0.0335, 0, 0.026)],
                   0.0042, glaze, order=4)
    handle.location.z = 0.0066
    handle.scale.y = 1.35
    rig = empty("cup_set", loc, (0, 0, math.radians(yaw_deg)))
    parent([saucer, cup, c, handle], rig)
    return rig


def plate_with_conchas(loc, glaze):
    plate = lathe("plate", [(0, 0.0), (0.055, 0.0), (0.058, 0.003), (0.062, 0.0052), (0.088, 0.0105), (0.108, 0.0195),
                            (0.1105, 0.0212), (0.1098, 0.0222), (0.107, 0.0215), (0.087, 0.0145), (0.062, 0.0098),
                            (0, 0.0094)], glaze, loc=loc)
    dome = [(0, 0.0), (0.036, 0.0), (0.042, 0.0015), (0.0452, 0.006), (0.0458, 0.012), (0.0435, 0.019), (0.038, 0.027),
            (0.029, 0.035), (0.017, 0.0405), (0, 0.0425)]
    pink = lathe("concha_rosa", dome, concha_mat("concha_rosa", (0.84, 0.47, 0.44)), loc=(loc[0] - 0.042, loc[1] + 0.022, loc[2] + 0.0094))
    pink.rotation_euler.z = 0.7
    vanilla = lathe("concha_vainilla", dome, concha_mat("concha_vainilla", (0.92, 0.84, 0.68)),
                    loc=(loc[0] + 0.046, loc[1] - 0.018, loc[2] + 0.0094))
    vanilla.rotation_euler.z = 2.1
    return [plate, pink, vanilla]


def vase_with_flowers(loc):
    g = glass_mat()
    vase = lathe("vase", [(0, 0.0), (0.026, 0.0), (0.0305, 0.006), (0.033, 0.03), (0.03, 0.06), (0.019, 0.095),
                          (0.0125, 0.118), (0.0128, 0.132), (0.0162, 0.1405), (0.0148, 0.1415), (0.0112, 0.133),
                          (0.0104, 0.118), (0.0168, 0.095), (0.0278, 0.06), (0.0302, 0.03), (0.0278, 0.009),
                          (0.02, 0.0055), (0, 0.0052)], g, loc=loc)
    water = mat("water", (0.95, 0.97, 0.96), rough=0.0)
    bsdf(water).inputs["Transmission Weight"].default_value = 1.0
    bsdf(water).inputs["IOR"].default_value = 1.33
    wat = lathe("water", [(0, 0.0056), (0.0198, 0.0058), (0.0276, 0.0092), (0.0299, 0.03), (0.0276, 0.06), (0.0255, 0.068),
                          (0, 0.068)], water, loc=loc, subsurf=1)
    stem_m = mat("stem", (0.16, 0.25, 0.09), rough=0.5, sss=0.2)
    petal = mat("petal", (0.95, 0.93, 0.88), rough=0.45, sss=0.4, sss_scale=0.004)
    heart = mat("heart", (0.85, 0.55, 0.08), rough=0.7)
    nt = heart.node_tree
    nz = N(nt, "ShaderNodeTexVoronoi", Scale=1500.0)
    L(nt, obj_coords(nt), nz.inputs["Vector"])
    bump(nt, nz.outputs["Distance"], 0.0006, 0.8)
    leaf_m = mat("leaf", (0.13, 0.24, 0.07), rough=0.45, sss=0.15)
    objs = [vase, wat]
    x0, y0, z0 = loc
    # (top offset x, y, height, head tilt toward camera, bloom size)
    for i, (dx, dy, h, size) in enumerate(((-0.05, -0.012, 0.215, 1.0), (0.04, -0.03, 0.195, 0.9), (-0.004, 0.025, 0.228, 1.05),
                                          (0.065, 0.015, 0.175, 0.0))):
        top = Vector((x0 + dx, y0 + dy, z0 + h))
        pts = [(x0 + dx * 0.02, y0 + dy * 0.02, z0 + 0.012), (x0 + dx * 0.05, y0 + dy * 0.05, z0 + 0.10),
               (x0 + dx * 0.18, y0 + dy * 0.18, z0 + 0.15), (x0 + dx * 0.6, y0 + dy * 0.6, z0 + h * 0.8), tuple(top)]
        objs.append(curve(f"stem{i}", pts, 0.0013, stem_m))
        d = (top - Vector(pts[-2])).normalized()
        d = (d + Vector((0, -0.9, 0.3))).normalized()   # face the room
        head = empty(f"head{i}", tuple(top))
        head.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
        if size == 0.0:   # a closed bud
            objs.append(sphere(f"bud{i}", tuple(top), (0.0045, 0.0045, 0.008), leaf_m))
            continue
        bloom = [sphere(f"heart{i}", (0, 0, 0.002), (0.0065 * size, 0.0065 * size, 0.0035 * size), heart)]
        for k in range(14):
            a = 2 * math.pi * k / 14 + i
            rr = 0.0145 * size
            p = sphere(f"petal{i}_{k}", (math.cos(a) * rr, math.sin(a) * rr, -0.0005 * (k % 2)),
                       (0.0115 * size, 0.0032 * size, 0.0006), petal, rot=(0.12 * (k % 3 - 1), -0.18, a), seg=16)
            bloom.append(p)
        parent(bloom, head)
        objs += bloom
        for s, (fx, side) in enumerate(((0.45, 1), (0.7, -1))):
            base = Vector(pts[2]).lerp(Vector(pts[3]), fx)
            lf = sphere(f"leaf{i}_{s}", tuple(base + Vector((side * 0.009, 0, 0.012))), (0.003, 0.0012, 0.016), leaf_m,
                        rot=(0, side * 0.6, 0))
            objs.append(lf)
    return objs


def napkin(loc, yaw_deg, color):
    m = linen_mat("napkin_linen", color)
    a = cube("napkin", (0.15, 0.11, 0.003), (0, 0, 0.0015), m, bev=0.0014, segs=3)
    b = cube("napkin_fold", (0.15, 0.065, 0.0025), (0, -0.022, 0.0042), m, bev=0.0012, segs=3)
    tex = bpy.data.textures.new("napkin_soft", "CLOUDS")
    tex.noise_scale = 0.035
    for o in (a, b):   # soft, slightly rumpled cloth instead of a hard slab
        sd = o.modifiers.new("subd", "SUBSURF")
        sd.subdivision_type, sd.levels, sd.render_levels = "SIMPLE", 4, 4
        dp = o.modifiers.new("soft", "DISPLACE")
        dp.texture, dp.strength, dp.mid_level, dp.direction = tex, 0.005, 0.5, "Z"
    rig = empty("napkin_rig", loc, (0, 0, math.radians(yaw_deg)))
    parent([a, b], rig)
    return rig


def runner(y, width, color):
    m = linen_mat("runner_linen", color)
    o = cube("runner", (2.0, width, 0.0016), (0, y, 0.0008), m, bev=0.0006, segs=2)
    return o


def table(z_top=0.0):
    o = cube("table", (3.0, 2.2, 0.04), (0, 0.2, z_top - 0.02), wood_mat(), bev=0.003, segs=3)
    return o


def sweep(color):
    """Seamless studio sweep: floor curving up into a back wall."""
    prof = [(-3.0, 0.0), (0.35, 0.0)]
    R = 0.55
    for i in range(1, 17):
        a = math.radians(90 * i / 16)
        prof.append((0.35 + R * math.sin(a), R - R * math.cos(a)))
    prof.append((0.35 + R, 3.0))
    verts, faces = [], []
    for x in (-3.0, 3.0):
        verts += [(x, y, z) for y, z in prof]
    n = len(prof)
    faces = [(i, i + 1, n + i + 1, n + i) for i in range(n - 1)]
    me = bpy.data.meshes.new("sweep")
    me.from_pydata(verts, [], faces)
    o = new_obj("sweep", me)
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(plaster_mat(color))
    return o


def area(name, loc, target, energy, size, size_y=None, color=(1, 1, 1)):
    bpy.ops.object.light_add(type="AREA", location=loc)
    o = bpy.context.object
    o.name = name
    d = o.data
    d.energy, d.color = energy, color
    if size_y:
        d.shape, d.size, d.size_y = "RECTANGLE", size, size_y
    else:
        d.size = size
    look(o, target)
    return o


def world(color, strength):
    w = bpy.data.worlds.new("w")
    scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*color, 1)
    bg.inputs["Strength"].default_value = strength


def camera(loc, target, lens, focus, fstop):
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.object
    cam.data.lens = lens
    look(cam, target)
    cam.data.dof.use_dof = True
    if isinstance(focus, (int, float)):
        cam.data.dof.focus_distance = focus
    else:
        cam.data.dof.focus_distance = (Vector(focus) - Vector(loc)).length
    cam.data.dof.aperture_fstop = fstop
    cam.data.dof.aperture_blades = 7
    scene.camera = cam
    return cam


def morning():
    """Low warm sun through a window on the left, soft sky from the same window, a faint bounce on the right."""
    bpy.ops.object.light_add(type="SUN", location=(-1, 0, 1))
    sun = bpy.context.object
    sun.data.energy, sun.data.angle, sun.data.color = float(os.environ.get("SUN", "7")), math.radians(2.5), (1.0, 0.74, 0.5)
    sun.rotation_euler = Vector((-1.0, -0.3, 0.45)).to_track_quat("Z", "Y").to_euler()   # light travels toward -dir
    # the window wall: an opening with one mullion, so the sun lays a frame shadow across the room
    wm = mat("window_wall", (0.5, 0.45, 0.4), rough=0.9)
    x = -0.8
    for nm, (y0, y1, z0, z1) in {"below": (-3, 0.95, -0.1, 0.08), "above": (-3, 0.95, 1.5, 3.0), "front": (-3, -0.95, 0.08, 1.5),
                                 "back": (0.55, 0.95, 0.08, 1.5), "mullion": (-0.24, -0.2, 0.08, 1.5),
                                 "transom": (-0.95, 0.55, 0.9, 0.94)}.items():
        cube(f"win_{nm}", (0.06, y1 - y0, z1 - z0), (x, (y0 + y1) / 2, (z0 + z1) / 2), wm)
    area("window", (-1.5, 0.1, 0.8), (0, 0.05, 0.05), float(os.environ.get("WIN", "14")), 1.6, 1.2, (0.92, 0.9, 0.9))
    area("bounce", (1.2, -0.7, 0.5), (0, 0, 0.05), 6, 1.5, 1.5, (1.0, 0.93, 0.85))


# ---------------------------------------------------------------- shots

rig, parts = build_hearth(HEARTH_IMG)
glaze = ceramic_mat("glaze", (0.9, 0.87, 0.8))
plate_glaze = ceramic_mat("plate_glaze", (0.93, 0.91, 0.86))
OATMEAL = (0.70, 0.62, 0.50)
OXBLOOD = (0.19, 0.035, 0.03)
# the Hearth face centre sits about 80 mm up once it stands on the table
FACE = lambda x, y: (x, y, 0.082)  # noqa: E731

if SHOT == "icon":
    dark = os.environ.get("ICON_DARK") == "1"
    sweep((0.05, 0.045, 0.04) if dark else (0.62, 0.47, 0.36))
    place_hearth(rig, parts, 0.0, 0.0, -22.0)
    world((0.9, 0.86, 0.8), 0.002 if dark else 0.03)
    area("key", (-0.8, -0.45, 0.55), (0, 0, 0.08), 3 if dark else 22, 0.9, 0.7, (1.0, 0.9, 0.78))
    area("fill", (0.8, -0.5, 0.25), (0, 0, 0.08), 0.6 if dark else 3, 1.2, 1.2, (0.95, 0.95, 1.0))
    area("rim", (0.5, 0.6, 0.5), (0, 0, 0.08), 2 if dark else 6, 0.8, 0.8, (1.0, 0.85, 0.7))
    camera((0.2, -0.62, 0.2), (0.012, 0.0, 0.082), 92, FACE(0, -0.005), 9.0)
elif SHOT == "studio":
    sweep((0.66, 0.58, 0.48))
    place_hearth(rig, parts, 0.0, 0.0, -14.0)
    world((0.9, 0.86, 0.8), 0.03)
    area("key", (-0.85, -0.35, 0.6), (0, 0, 0.08), 20, 0.9, 0.7, (1.0, 0.93, 0.84))
    area("fill", (0.8, -0.5, 0.25), (0, 0, 0.08), 3, 1.2, 1.2, (0.95, 0.95, 1.0))
    area("top", (0.0, 0.3, 0.8), (0, 0.4, 0.05), 4, 1.4, 0.6)
    camera((0.0, -0.9, 0.24), (0.012, 0.0, 0.08), 75, FACE(0, -0.005), 5.6)
else:
    table()
    world((0.85, 0.78, 0.68), 0.015)
    wall = cube("wall", (4.0, 0.05, 2.5), (0, 0.95, 1.25), plaster_mat((0.62, 0.52, 0.42)))
    if SHOT == "breakfast":
        runner(0.04, 0.42, OATMEAL)
        place_hearth(rig, parts, 0.0, 0.12, 0.0, 0.0016)
        vase_with_flowers((-0.215, 0.17, 0.0016))
        cup_and_saucer((0.225, 0.04, 0.0016), 200, glaze)
        plate_with_conchas((-0.17, -0.1, 0.0016), plate_glaze)
        napkin((0.235, -0.17, 0.0016), 12, OXBLOOD)
        iphone((0.04, -0.16, 0.0016), (0, 0, math.radians(-14)), PHONE_IMG)
        morning()
        camera((0.04, -1.08, 0.5), (0.0, 0.0, 0.072), 60, FACE(0, 0.125), 2.8)
    elif SHOT == "playing":
        runner(0.04, 0.42, OATMEAL)
        place_hearth(rig, parts, 0.0, 0.08, 0.0, 0.0016)
        vase_with_flowers((-0.24, 0.3, 0.0))
        cup_and_saucer((-0.32, 0.12, 0.0), 160, glaze)
        plate_with_conchas((0.2, 0.36, 0.0), plate_glaze)
        morning()
        camera((0.33, -0.46, 0.16), (-0.04, 0.1, 0.085), 60, FACE(0.03, 0.085), 2.8)
    elif SHOT == "phone":
        runner(0.04, 0.42, OATMEAL)
        place_hearth(rig, parts, -0.05, 0.25, 12.0, 0.0016)
        vase_with_flowers((-0.30, 0.36, 0.0016))
        cup_and_saucer((0.18, 0.24, 0.0016), 200, glaze)
        # small walnut stand: base and back rest; phone leans back 18 degrees
        walnut = mat("walnut", (0.085, 0.045, 0.025), rough=0.4)
        tilt = math.radians(18)
        st = empty("stand", (0.03, -0.06, 0.0016), (0, 0, math.radians(-8)))
        base = cube("stand_base", (0.08, 0.07, 0.012), (0, 0.01, 0.006), walnut, bev=0.003)
        lip = cube("stand_lip", (0.08, 0.008, 0.01), (0, -0.016, 0.017), walnut, bev=0.002)
        back = cube("stand_back", (0.07, 0.012, 0.075), (0, 0.012 + 0.0375 * math.sin(tilt), 0.012 + 0.0375 * math.cos(tilt) - 0.002),
                    walnut, bev=0.003, rot=(-tilt, 0, 0))
        parent([base, lip, back], st)
        ph = iphone((0, -0.0115, 0.075 * math.cos(tilt) + 0.012), (math.pi / 2 - tilt, 0, 0), PHONE_IMG)
        ph.parent = st
        morning()
        camera((0.15, -0.52, 0.17), (0.0, -0.02, 0.085), 50, (0.03, -0.075, 0.085), 2.8)

scene.render.engine = "CYCLES"
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.cycles.max_bounces, scene.cycles.transmission_bounces = 10, 10
scene.cycles.caustics_reflective = scene.cycles.caustics_refractive = False
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    scene.cycles.device = "GPU"
except Exception as e:
    print("GPU unavailable, using CPU:", e)
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = float(os.environ.get("EXPOSURE", "-0.4"))
scene.render.resolution_x, scene.render.resolution_y = (1024, 1024) if SHOT == "icon" else (1920, 1200)
scene.render.resolution_percentage = RES_PCT
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("rendered", OUT)
