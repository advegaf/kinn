import math
import os

import bpy
import hearth_parts as hp
from mathutils import Matrix, Vector

from showcase_kit import (L, N, bevel, bsdf, bump, cube, curve, empty, lathe, look, mat, mm, new_obj, obj_coords, parent,
                          slab, smooth, sphere)
from showcase_materials import concha_mat, glass_mat, linen_mat, plaster_mat, wood_mat

STL = os.path.join(os.path.dirname(hp.__file__), "stl")
CREAM = (0.93, 0.89, 0.80)
LEAN_DEG = 9.0


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
    bezel = load(os.path.join(STL, "front_bezel.stl"), cream)
    shell = load(os.path.join(STL, "back_shell.stl"), cream)
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
    bpy.context.scene.world = w
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
    bpy.context.scene.camera = cam
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
