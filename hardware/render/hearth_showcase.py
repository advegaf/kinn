"""Hearth showcase renders: product photography of the finished Hearth and the iPhone app.

Run: blender -b -P hearth_showcase.py -- <breakfast|playing|phone|studio> [abs out.png] [samples] [res %]
The Hearth assembly (STLs, Fire tablet, screen plane, TO_SCENE, lean) is copied from hearth_scene_v4.py.
Props are built from primitives in showcase_props.py. Units: metres.
"""
import math
import os
import sys

import bpy
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.join(HERE, "..", "cad")
sys.path[:0] = [HERE, CAD]
import hearth_parts as hp  # noqa: E402
from showcase_build import L, N, bump, cube, empty, mat, mm, obj_coords, parent, smooth  # noqa: E402
from showcase_materials import ceramic_mat, plaster_mat  # noqa: E402
from showcase_props import (area, camera, cup_and_saucer, iphone, morning, napkin, plate_with_conchas,  # noqa: E402
                            runner, sweep, table, vase_with_flowers, world)

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

hp.FACE_T = hp.GLASS_Z = 1.6
hp.FOAM_T, hp.CAP_HEAD_T = 3.0, 6.0

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


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
