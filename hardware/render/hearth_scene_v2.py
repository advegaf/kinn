"""Hearth v2 render: the printable parts from ../cad/hearth_parts.py in frosted translucent PLA.

Run: blender -b -P hearth_scene_v2.py -- <hero|front|exploded> <abs out.png>
Needs screen_v2.png (python3 make_screen.py screen_v2.png v2).
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cad"))
import hearth_parts as hp  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE = argv[0] if argv else "hero"
OUT = os.path.abspath(argv[1]) if len(argv) > 1 else os.path.join(HERE, f"hearth-v2-{MODE}.png")
SCREEN = os.environ.get("HEARTH_SCREEN", os.path.join(HERE, "screen_v2.png"))
PHONE = os.path.join(HERE, "..", "..", "docs", "screens", "family-thread.png")
GLOW = (1.0, 0.36, 0.08)
GLOW_STRENGTH, BUTTON_STRENGTH = 2.2, 25.0
mm = 0.001

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def mat(name, color, rough=0.5, metallic=0.0, transmission=0.0, emission=None, strength=1.0, image=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Transmission Weight"].default_value = transmission
    b.inputs["Subsurface Weight"].default_value = 0.0
    b.inputs["IOR"].default_value = 1.45
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
    """Plane in plate frame (mm), facing the front (-z)."""
    o = hp.box(name, cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2, z, z + 0.01)
    o.data.uv_layers.new()
    # project UVs from x/y so the screen image maps across the panel (front view: X = -x)
    for loop in o.data.loops:
        co = o.data.vertices[loop.vertex_index].co
        o.data.uv_layers.active.data[loop.index].uv = ((-(co.x - cx)) / w + 0.5, (co.y - cy) / h + 0.5)
    o.data.materials.append(material)
    return o


def smooth(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.shade_auto_smooth(angle=math.radians(35))


pla = mat("frosted_pla", (0.97, 0.90, 0.80), rough=0.5, transmission=0.6)
black = mat("fire_black", (0.02, 0.02, 0.022), rough=0.35)
copper = mat("copper", (0.98, 0.62, 0.42), rough=0.55, metallic=1.0)
glow = mat("glow", (0, 0, 0), emission=GLOW, strength=GLOW_STRENGTH)
glow_btn = mat("glow_btn", (0, 0, 0), emission=(1.0, 0.45, 0.15), strength=BUTTON_STRENGTH)
screen_m = mat("screen", (0, 0, 0), rough=0.15, image=SCREEN, strength=2.2)

parts = hp.build_all()
plate, cap = parts["front_plate"], parts["button_cap"]
clips = [parts[k] for k in parts if k.startswith("clip_")]
for o in [plate, cap] + clips:
    o.data.materials.append(pla)
    smooth(o)

tablet = hp.rrect("fire_hd8", hp.TAB_W, hp.TAB_H, hp.FACE_T + 0.3, hp.FACE_T + 0.3 + hp.TAB_T, hp.TAB_CORNER_R)
tablet.data.materials.append(black)
sx, sy = hp.px(hp.SCREEN_OFF_X), hp.SCREEN_OFF_Y
screen = plane("screen", hp.ACT_W, hp.ACT_H, sx, sy, hp.FACE_T + 0.2, screen_m)
band_h = hp.ACT_H / 4
bands = [plane(f"band_{i}", hp.ACT_W, band_h, sx, sy + s * 3 * band_h / 2, hp.FACE_T + 0.15, glow)
         for i, s in enumerate((-1, 1))]
spot = hp.cyl("button_spot", 16, hp.FACE_T + 0.1, hp.FACE_T + 0.11, hp.px(hp.BTN_X), hp.BTN_Y)
spot.data.materials.append(glow_btn)
cx, cy = hp.px(hp.BTN_X), hp.BTN_Y
head_top = -hp.FOAM_T - hp.CAP_HEAD_T
tape = hp.box("tape", cx, cx + hp.CAP_D / 2 - 0.6, cy - hp.TAPE_W / 2 + 0.3, cy + hp.TAPE_W / 2 - 0.3,
              head_top + 0.05, head_top + hp.TAPE_DEPTH - 0.05)
tape.data.materials.append(copper)
foam = hp.cyl("foam", hp.CAP_D - 2, -hp.FOAM_T, -0.05, cx, cy)
hp.boolean(foam, hp.cyl("foam_in", hp.BTN_HOLE_D + 1, -hp.FOAM_T - 1, 1, cx, cy))
foam.data.materials.append(mat("foam", (0.9, 0.9, 0.88), rough=0.9))
feet = [hp.build_foot("foot_l"), hp.build_foot("foot_r", mirror=True)]
for f in feet:
    f.data.materials.append(pla)

# booleans leave an empty slot 0 on hp meshes; collapse to the one real material
for o in bpy.data.objects:
    if o.type == "MESH":
        real = [m for m in o.data.materials if m]
        if len(real) == 1 and len(o.data.materials) > 1:
            o.data.materials.clear()
            o.data.materials.append(real[0])

# plate frame (mm, face toward -z, +x = viewer's left) to scene (m, face toward -y, +x = viewer's right)
TO_SCENE = Matrix.Scale(mm, 4) @ Matrix(((-1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
FOOT_TO_SCENE = Matrix.Scale(mm, 4) @ Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))

rig = bpy.data.objects.new("hearth", None)
scene.collection.objects.link(rig)
assembly = [plate, cap, tape, foam, tablet, screen, spot] + bands + clips
for o in assembly:
    o.matrix_world = TO_SCENE
    o.parent = rig


def lowest_z(objs):
    bpy.context.view_layer.update()
    return min((o.matrix_world @ v.co).z for o in objs for v in o.data.vertices)


a = math.radians(hp.LEAN_DEG)
if MODE == "exploded":
    rig.rotation_euler = (0, 0, math.radians(55))
    rig.location = (0, 0, hp.PLATE_H / 2 * mm + 30 * mm)
    for o, dy in [(cap, -120), (tape, -120), (foam, -65), (tablet, 120), (screen, 120), (spot, 120)] + \
                 [(b, 120) for b in bands] + [(c, 210) for c in clips]:
        o.location.y += dy * mm
    for f, x in zip(feet, (-1, 1)):
        f.parent = rig
        f.matrix_basis = Matrix.Translation((x * 0.07, 0.29, -(hp.PLATE_H / 2 + 30) * mm)) @ FOOT_TO_SCENE
else:
    rig.rotation_euler = (-a, 0, 0)
    rig.location = (0, 0, 0)
    rig.location.z = -lowest_z([plate])
    bpy.context.view_layer.update()
    # back rim plane passes through the plate's rear centre-bottom; slide each foot so its rebate face meets it
    q = rig.matrix_world @ TO_SCENE @ Vector((0, -hp.PLATE_H / 2, hp.PLATE_D))
    t = (q.z + hp.FOOT_REBATE_D * math.sin(a)) / math.cos(a)
    y_off = q.y - hp.FOOT_REBATE_D * math.cos(a) - t * math.sin(a)
    rim_in = hp.PLATE_W / 2 - hp.WALL - 0.3
    for f, x in zip(feet, (-(rim_in + hp.FOOT_W), rim_in)):
        f.matrix_world = Matrix.Translation((x * mm, y_off, 0)) @ FOOT_TO_SCENE

# Counter, wall, grandkid's phone (same set as v1).
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
bpy.ops.mesh.primitive_plane_add(size=3, location=(0, 0, 0))
bpy.context.object.data.materials.append(wood)
bpy.ops.mesh.primitive_plane_add(size=3, location=(0, 0.32, 1.0), rotation=(math.pi / 2, 0, 0))
bpy.context.object.data.materials.append(mat("wall", (0.80, 0.72, 0.62), rough=0.9))

if MODE != "exploded" and os.path.exists(PHONE):
    rot = math.radians(24)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.19, -0.13, 4 * mm))
    ph = bpy.context.object
    ph.scale = (71.5 * mm, 149.6 * mm, 8 * mm)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bev = ph.modifiers.new("bevel", "BEVEL")
    bev.width, bev.segments = 9 * mm, 6
    ph.rotation_euler = (0, 0, rot)
    ph.data.materials.append(mat("phone", (0.12, 0.12, 0.13), rough=0.3, metallic=0.6))
    smooth(ph)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0.19, -0.13, 8.1 * mm), rotation=(0, 0, rot))
    ps = bpy.context.object
    ps.scale = (66 * mm, 143 * mm, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ps.data.materials.append(mat("phone_screen", (0, 0, 0), image=PHONE, strength=1.6))

world = bpy.data.worlds.new("w")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.03, 0.025, 0.02, 1)
bpy.ops.object.light_add(type="AREA", location=(-0.6, -0.5, 0.7))
key = bpy.context.object
key.data.energy, key.data.size, key.data.color = 12 if MODE == "exploded" else 7, 0.9, (1.0, 0.86, 0.7)
key.rotation_euler = (math.radians(50), 0, math.radians(-45))
bpy.ops.object.light_add(type="AREA", location=(0.7, -0.3, 0.4))
fill = bpy.context.object
fill.data.energy, fill.data.size, fill.data.color = 2, 0.8, (0.8, 0.85, 1.0)
fill.rotation_euler = (math.radians(65), 0, math.radians(60))

cam_loc, target, lens = {
    "hero": ((0.34, -0.50, 0.24), (0.04, -0.01, 0.075), 50),
    "front": ((0.0, -0.62, 0.09), (0.0, 0.0, 0.08), 70),
    "exploded": ((0.30, -0.62, 0.36), (-0.06, 0.05, 0.10), 40),
}[MODE]
bpy.ops.object.camera_add(location=cam_loc)
cam = bpy.context.object
cam.data.lens = lens
cam.data.dof.use_dof = MODE == "hero"
cam.data.dof.focus_distance = (Vector(cam_loc) - Vector((0, -0.02, 0.08))).length
cam.data.dof.aperture_fstop = 2.8
cam.rotation_euler = (Vector(target) - Vector(cam_loc)).to_track_quat("-Z", "Y").to_euler()
scene.camera = cam

scene.render.engine = "CYCLES"
scene.cycles.samples = 96
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 16
scene.cycles.transmission_bounces = 12
scene.cycles.transparent_max_bounces = 12
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
scene.view_settings.look = "AgX - Punchy"
scene.render.resolution_x, scene.render.resolution_y = 1600, 1000
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("rendered", OUT)
