"""Hearth v4 render: the print STLs in matte cream PLA, with the real Hearth screen, next to Modem's Dream Recorder.

Run: blender -b -P hearth_scene_v4.py -- <hero|front|side|back|exploded|vs-dr|context> [abs out.png] [samples]
Needs ../cad/stl/{front_bezel,back_shell}.stl (cad/hearth_v4_sdf.py then cad/hearth_v4.py)
and ../reference/dream-recorder_{front,back}.stl for vs-dr.
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.join(HERE, "..", "cad")
REF = os.path.join(HERE, "..", "reference")
sys.path.insert(0, CAD)
import hearth_parts as hp  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE = argv[0] if argv else "hero"
OUT = os.path.abspath(argv[1]) if len(argv) > 1 else os.path.join(HERE, f"hearth-v4-{MODE}.png")
SAMPLES = int(argv[2]) if len(argv) > 2 else 128
SCREEN = os.environ.get("HEARTH_SCREEN", "/Users/advegaf/Desktop/fall-26/hacktx26/docs/screens/hearth-web-v2-waiting.png")
SCREENS = "/Users/advegaf/Desktop/fall-26/hacktx26/docs/screens"
PHONE = next((p for p in (os.path.join(SCREENS, "ios-v4c-week.png"), os.path.join(SCREENS, "family-thread.png"))
              if os.path.exists(p)), None)
CREAM = (0.93, 0.89, 0.80)
LEAN_DEG = 9.0           # same as cad/hearth_v4_sdf.py
DR_GAP = 10.66           # DR front tray rim height: back shell open face sits here
mm = 0.001

hp.FACE_T = hp.GLASS_Z = 1.6
hp.FOAM_T, hp.CAP_HEAD_T = 3.0, 6.0

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def mat(name, color, rough=0.5, metallic=0.0, emission=None, strength=1.0, image=None, sss=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Subsurface Weight"].default_value = sss
    b.inputs["Subsurface Scale"].default_value = 0.002
    b.inputs["Subsurface Radius"].default_value = (1.0, 0.6, 0.35)
    if emission:
        b.inputs["Emission Color"].default_value = (*emission, 1)
        b.inputs["Emission Strength"].default_value = strength
    if image:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(image)
        b.inputs["Base Color"].default_value = (0, 0, 0, 1)
        nt.links.new(tex.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = strength
    return m


def plane(name, w, h, cx, cy, z, material):
    """Plane in plate frame (mm), facing the front (-z), UVs so the image reads from the front."""
    o = hp.box(name, cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2, z, z + 0.01)
    o.data.uv_layers.new()
    for loop in o.data.loops:
        co = o.data.vertices[loop.vertex_index].co
        o.data.uv_layers.active.data[loop.index].uv = ((-(co.x - cx)) / w + 0.5, (co.y - cy) / h + 0.5)
    o.data.materials.append(material)
    return o


def smooth(o, angle=35):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.shade_auto_smooth(angle=math.radians(angle))


def load(path, material):
    bpy.ops.wm.stl_import(filepath=path)
    o = bpy.context.selected_objects[0]
    o.data.materials.append(material)
    smooth(o, 50)
    return o


cream = mat("cream_pla", CREAM, rough=0.7, sss=0.15)
black = mat("fire_black", (0.02, 0.02, 0.022), rough=0.35)
copper = mat("copper", (0.98, 0.62, 0.42), rough=0.55, metallic=1.0)
screen_m = mat("screen", (0, 0, 0), rough=0.15, image=SCREEN, strength=1.6)

bezel = load(os.path.join(CAD, "stl", "front_bezel.stl"), cream)
shell = load(os.path.join(CAD, "stl", "back_shell.stl"), cream)
shell.data.transform(Matrix.Translation((0, 0, hp.FACE_T)))   # printed open face down; put it back on the bezel
tablet = hp.rrect("fire_hd8", hp.TAB_W, hp.TAB_H, hp.FACE_T + 0.1, hp.FACE_T + hp.TAB_T, hp.TAB_CORNER_R)
tablet.data.materials.append(black)
screen = plane("screen", hp.ACT_W, hp.ACT_H, hp.px(hp.SCREEN_OFF_X), hp.SCREEN_OFF_Y, hp.FACE_T + 0.05, screen_m)
BUTTON = False  # grandma taps the screen window directly
extras = []
if BUTTON:
    cap = hp.build_cap()
    cap.data.materials.append(cream)
    smooth(cap)

    cx, cy = hp.px(hp.BTN_X), hp.BTN_Y
    head_top = -hp.FOAM_T - hp.CAP_HEAD_T
    tape = hp.box("tape", cx, cx + hp.CAP_D / 2 - 0.6, cy - hp.TAPE_W / 2 + 0.3, cy + hp.TAPE_W / 2 - 0.3,
                  head_top + 0.05, head_top + hp.TAPE_DEPTH - 0.05)
    tape.data.materials.append(copper)
    foam = hp.cyl("foam", hp.CAP_D - 2, -hp.FOAM_T, -0.05, cx, cy)
    hp.boolean(foam, hp.cyl("foam_in", hp.BTN_HOLE_D + 1, -hp.FOAM_T - 1, 1, cx, cy))
    foam.data.materials.append(mat("foam", (0.9, 0.9, 0.88), rough=0.9))
    extras = [cap, tape, foam]

# booleans leave an empty slot 0 on hp meshes; collapse to the one real material
for o in bpy.data.objects:
    if o.type == "MESH":
        real = [m for m in o.data.materials if m]
        if len(real) == 1 and len(o.data.materials) > 1:
            o.data.materials.clear()
            o.data.materials.append(real[0])

# plate frame (mm, face toward -z, +x = viewer's left) to scene (m, face toward -y, +x = viewer's right)
TO_SCENE = Matrix.Scale(mm, 4) @ Matrix(((-1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))


def lowest_z(objs):
    bpy.context.view_layer.update()
    return min((o.matrix_world @ v.co).z for o in objs for v in o.data.vertices)


rig = bpy.data.objects.new("hearth", None)
scene.collection.objects.link(rig)
for o in [bezel, shell, tablet, screen] + extras:
    o.matrix_world = TO_SCENE
    o.parent = rig

dr = []
if MODE == "vs-dr":
    # DR files: face at z=0 looking toward -z, y up, x 0..220. Same axis swap as ours.
    drm = mat("dr_cream", CREAM, rough=0.7, sss=0.15)
    dr_rig = bpy.data.objects.new("dream_recorder", None)
    scene.collection.objects.link(dr_rig)
    for n, dz in (("front", 0.0), ("back", DR_GAP)):
        o = load(os.path.join(REF, f"dream-recorder_{n}.stl"), drm)
        o.data.transform(Matrix.Translation((-110.0, -61.4, dz)))
        o.matrix_world = TO_SCENE
        o.parent = dr_rig
        dr.append(o)
    dr_rig.location = (0.25, 0.0, 0.0)
    dr_rig.location.z = -lowest_z(dr)

a = math.radians(LEAN_DEG)
if MODE == "exploded":
    rig.rotation_euler = (0, 0, math.radians(-35))
    rig.location = (0, 0, 0.09)
    for o, dy in [(tablet, 70), (screen, 70), (shell, 150)] + ([(cap, -110), (tape, -110), (foam, -60)] if BUTTON else []):
        o.location.y += dy * mm
else:
    # the bottom is one flat face tilted by LEAN_DEG; rotate it level so the body leans back
    rig.rotation_euler = (-a, 0, 0)
    rig.location.z = -lowest_z([bezel, shell])

wood = mat("counter", (0.42, 0.27, 0.16), rough=0.45)
nt = wood.node_tree
wave = nt.nodes.new("ShaderNodeTexWave")
wave.inputs["Scale"].default_value = 3.0
wave.inputs["Distortion"].default_value = 6.0
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].color = (0.30, 0.18, 0.10, 1)
ramp.color_ramp.elements[1].color = (0.50, 0.33, 0.20, 1)
nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
bpy.ops.mesh.primitive_plane_add(size=4, location=(0, 0, 0))
bpy.context.object.data.materials.append(wood)
if MODE in ("hero", "front", "exploded", "context"):
    bpy.ops.mesh.primitive_plane_add(size=4, location=(0, 0.40, 1.0), rotation=(math.pi / 2, 0, 0))
    bpy.context.object.data.materials.append(mat("wall", (0.78, 0.72, 0.64), rough=0.9))

if MODE == "context" and PHONE:
    # iPhone lying on the counter in front of the Hearth, showing the family side of the app
    rot, px_, py_ = math.radians(24), 0.17, -0.12
    bpy.ops.mesh.primitive_cube_add(size=1, location=(px_, py_, 4 * mm))
    ph = bpy.context.object
    ph.scale = (71.5 * mm, 149.6 * mm, 8 * mm)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bev = ph.modifiers.new("bevel", "BEVEL")
    bev.width, bev.segments = 9 * mm, 6
    ph.rotation_euler = (0, 0, rot)
    ph.data.materials.append(mat("phone", (0.12, 0.12, 0.13), rough=0.3, metallic=0.6))
    smooth(ph)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(px_, py_, 8.1 * mm), rotation=(0, 0, rot))
    ps = bpy.context.object
    ps.scale = (66 * mm, 143 * mm, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ps.data.materials.append(mat("phone_screen", (0, 0, 0), image=PHONE, strength=1.6))

world = bpy.data.worlds.new("w")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.05, 0.045, 0.04, 1)
bpy.ops.object.light_add(type="AREA", location=(-0.6, -0.55, 0.75))
key = bpy.context.object
key.data.energy, key.data.size, key.data.color = 22, 1.0, (1.0, 0.9, 0.78)
key.rotation_euler = (Vector((0, 0, 0.08)) - key.location).to_track_quat("-Z", "Y").to_euler()
bpy.ops.object.light_add(type="AREA", location=(0.8, -0.3, 0.45))
fill = bpy.context.object
fill.data.energy, fill.data.size, fill.data.color = 6, 1.0, (0.85, 0.9, 1.0)
fill.rotation_euler = (Vector((0, 0, 0.08)) - fill.location).to_track_quat("-Z", "Y").to_euler()
bpy.ops.object.light_add(type="AREA", location=(0.2, 0.7, 0.6))
rim = bpy.context.object
rim.data.energy, rim.data.size = 10, 0.8
rim.rotation_euler = (Vector((0, 0, 0.08)) - rim.location).to_track_quat("-Z", "Y").to_euler()

if MODE == "context":
    # warm late afternoon window off to the left
    key.data.energy *= 0.4
    bpy.ops.object.light_add(type="AREA", location=(-1.1, -0.2, 0.55))
    win = bpy.context.object
    win.data.shape, win.data.size, win.data.size_y = "RECTANGLE", 0.9, 0.6
    win.data.energy, win.data.color = 50, (1.0, 0.78, 0.55)
    win.rotation_euler = (Vector((0.05, 0, 0.05)) - win.location).to_track_quat("-Z", "Y").to_euler()

cam_loc, target, lens = {
    "hero": ((0.36, -0.52, 0.26), (0.0, 0.0, 0.075), 55),
    "front": ((0.0, -0.75, 0.10), (0.0, 0.0, 0.08), 70),
    "side": ((0.75, 0.0, 0.09), (0.0, 0.0, 0.08), 70),
    "back": ((-0.40, 0.55, 0.32), (0.0, 0.0, 0.07), 55),
    "exploded": ((0.40, -0.60, 0.36), (0.0, 0.02, 0.09), 52),
    "vs-dr": ((-0.05, 0.62, 0.36), (0.12, 0.0, 0.05), 45),
    "context": ((0.27, -0.58, 0.25), (0.07, -0.05, 0.06), 42),
}[MODE]
bpy.ops.object.camera_add(location=cam_loc)
cam = bpy.context.object
cam.data.lens = lens
cam.rotation_euler = (Vector(target) - Vector(cam_loc)).to_track_quat("-Z", "Y").to_euler()
scene.camera = cam

scene.render.engine = "CYCLES"
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
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
scene.view_settings.look = "AgX - Base Contrast"
scene.render.resolution_x, scene.render.resolution_y = 1600, 1000
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("rendered", OUT)
