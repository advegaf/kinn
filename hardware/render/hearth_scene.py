"""Blender mockup of the Hearth: a printed shell around a Fire HD 8.

Run: blender -b -P hearth_scene.py -- <hero|front|exploded> <out.png>
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE = argv[0] if argv else "hero"
OUT = os.path.abspath(argv[1]) if len(argv) > 1 else os.path.join(HERE, f"hearth-{MODE}.png")
SCREEN = os.path.join(HERE, "screen.png")
PHONE = os.path.join(HERE, "..", "..", "docs", "screens", "family-thread.png")

mm = 0.001
SHELL_W, SHELL_D, SHELL_H = 232 * mm, 34 * mm, 160 * mm
FRONT_T = 6 * mm
TAB_W, TAB_D, TAB_H = 202 * mm, 9.6 * mm, 137 * mm
PANEL_W, PANEL_H = 172 * mm, 107.5 * mm
WIN_W, WIN_H = 166 * mm, 63 * mm

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def mat(name, color, rough=0.5, emission=None, image=None, metallic=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    if image:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(image)
        bsdf.inputs["Base Color"].default_value = (0, 0, 0, 1)
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = emission or 1.0
        bsdf.inputs["Roughness"].default_value = 0.15
    return m


def box(name, size, loc, bevel=0.0, segments=6, material=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = o.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = segments
        mod.limit_method = "NONE"
        bpy.ops.object.modifier_apply(modifier=mod.name)
    if material:
        o.data.materials.append(material)
    return o


def boolean(target, cutter, op="DIFFERENCE"):
    mod = target.modifiers.new("bool", "BOOLEAN")
    mod.operation = op
    mod.object = cutter
    mod.solver = "EXACT"
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=mod.name)


def duplicate(o):
    c = o.copy()
    c.data = o.data.copy()
    bpy.context.collection.objects.link(c)
    return c


def smooth(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.shade_auto_smooth(angle=math.radians(35))


def screen_plane(name, w, h, loc, image, rot=(math.pi / 2, 0, 0), strength=1.4):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = (w, h, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat(name + "_m", (0, 0, 0), image=image, emission=strength))
    return o


shell_m = mat("oat_pla", (0.86, 0.82, 0.75), rough=0.62)
btn_m = mat("terracotta_pla", (0.62, 0.24, 0.14), rough=0.5)
tab_m = mat("fire_black", (0.02, 0.02, 0.022), rough=0.35)
remote_m = mat("remote", (0.05, 0.05, 0.06), rough=0.4)

# Shell: one rounded slab, split into a front plate and a back body.
front_y = -SHELL_D / 2
slab = box("slab", (SHELL_W, SHELL_D, SHELL_H), (0, 0, 0), bevel=14 * mm, segments=10)
cut_front = box("cut_front", (SHELL_W * 2, SHELL_D, SHELL_H * 2), (0, front_y + FRONT_T + SHELL_D / 2, 0))
front = duplicate(slab)
front.name = "front_plate"
boolean(front, cut_front, "DIFFERENCE")
back = slab
back.name = "back_body"
cut_back = box("cut_back", (SHELL_W * 2, FRONT_T * 2, SHELL_H * 2), (0, front_y, 0))
boolean(back, cut_back, "DIFFERENCE")

window = box("window", (WIN_W, 40 * mm, WIN_H), (0, front_y, 6 * mm), bevel=5 * mm, segments=6)
boolean(front, window)
for i in range(9):
    for j in range(3):
        bpy.ops.mesh.primitive_cylinder_add(radius=1.7 * mm, depth=30 * mm,
                                            location=(40 * mm + i * 6 * mm, front_y, -50 * mm - j * 6 * mm),
                                            rotation=(math.pi / 2, 0, 0))
        hole = bpy.context.object
        boolean(front, hole)
        bpy.data.objects.remove(hole)

tab_y = front_y + FRONT_T + TAB_D / 2 + 0.2 * mm
cavity = box("cavity", (TAB_W + 1 * mm, TAB_D + 1 * mm, TAB_H + 1 * mm), (0, tab_y, 6 * mm))
boolean(back, cavity)

# Button pocket on top for the shutter remote, then the printed cap.
btn_x, top_z = 70 * mm, SHELL_H / 2
pocket = box("pocket", (34 * mm, 16 * mm, 20 * mm), (btn_x, 2 * mm, top_z - 6 * mm))
boolean(back, pocket)
for o in (front, back):
    o.data.materials.clear()
    o.data.materials.append(shell_m)
    smooth(o)

bpy.ops.mesh.primitive_cylinder_add(radius=15 * mm, depth=9 * mm, location=(btn_x, 2 * mm, top_z + 3 * mm))
cap = bpy.context.object
cap.name = "button_cap"
bev = cap.modifiers.new("bevel", "BEVEL")
bev.width, bev.segments = 3 * mm, 6
cap.data.materials.append(btn_m)
smooth(cap)

remote = box("shutter_remote", (28 * mm, 10 * mm, 14 * mm), (btn_x, 2 * mm, top_z - 8 * mm), bevel=3 * mm, material=remote_m)

tablet = box("fire_hd8", (TAB_W, TAB_D, TAB_H), (0, tab_y, 6 * mm), bevel=6 * mm, material=tab_m)
smooth(tablet)
panel = screen_plane("panel", PANEL_W, PANEL_H, (0, tab_y - TAB_D / 2 - 0.15 * mm, 6 * mm), SCREEN, strength=2.2)

for p in (front, back, cap, remote, tablet, panel):
    p["part"] = True
for o in list(bpy.data.objects):
    if o.name in {"cut_front", "cut_back", "window", "cavity", "pocket"}:
        bpy.data.objects.remove(o)

rig = bpy.data.objects.new("hearth", None)
scene.collection.objects.link(rig)
parts = [front, back, cap, remote, tablet, panel]
for p in parts:
    p.parent = rig

if MODE == "exploded":
    front.location.y -= 70 * mm
    back.location.y += 60 * mm
    cap.location.z += 70 * mm
    cap.location.y += 60 * mm
    remote.location.z += 38 * mm
    remote.location.y += 60 * mm
    rig.rotation_euler = (0, 0, math.radians(-28))
    rig.location = (0, 0, SHELL_H / 2 + 20 * mm)
else:
    rig.rotation_euler = (math.radians(-8), 0, 0)
    rig.location = (0, 0, SHELL_H / 2 - 2 * mm)
    foot = box("foot", (120 * mm, 40 * mm, 14 * mm), (0, 32 * mm, 7 * mm), bevel=6 * mm, material=shell_m)
    smooth(foot)

# Counter, wall, grandkid's phone.
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

if MODE != "exploded":
    phone_rot = math.radians(24)
    phone = box("iphone", (71.5 * mm, 149.6 * mm, 8 * mm), (0.17, -0.13, 4 * mm), bevel=9 * mm,
                material=mat("phone", (0.12, 0.12, 0.13), rough=0.3, metallic=0.6))
    phone.rotation_euler = (0, 0, phone_rot)
    smooth(phone)
    ps = screen_plane("phone_screen", 66 * mm, 143 * mm, (0.17, -0.13, 8.1 * mm), PHONE, rot=(0, 0, phone_rot), strength=1.6)

# Light and camera.
world = bpy.data.worlds.new("w")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.05, 0.04, 0.035, 1)
bpy.ops.object.light_add(type="AREA", location=(-0.6, -0.5, 0.7))
key = bpy.context.object
key.data.energy, key.data.size, key.data.color = 45, 0.9, (1.0, 0.86, 0.7)
key.rotation_euler = (math.radians(50), 0, math.radians(-45))
bpy.ops.object.light_add(type="AREA", location=(0.7, -0.3, 0.4))
fill = bpy.context.object
fill.data.energy, fill.data.size, fill.data.color = 10, 0.8, (0.8, 0.85, 1.0)
fill.rotation_euler = (math.radians(65), 0, math.radians(60))

cam_loc, target, lens = {
    "hero": ((0.34, -0.50, 0.24), (0.05, -0.02, 0.07), 50),
    "front": ((0.0, -0.62, 0.09), (0.0, 0.0, 0.085), 70),
    "exploded": ((0.40, -0.46, 0.32), (0.0, 0.0, 0.11), 45),
}[MODE]
bpy.ops.object.camera_add(location=cam_loc)
cam = bpy.context.object
cam.data.lens = lens
cam.data.dof.use_dof = MODE == "hero"
cam.data.dof.focus_distance = (Vector(cam_loc) - Vector((0, -0.02, 0.08))).length
cam.data.dof.aperture_fstop = 2.8
direction = Vector(target) - Vector(cam_loc)
cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
scene.camera = cam

scene.render.engine = "CYCLES"
scene.cycles.samples = 96
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
scene.view_settings.look = "AgX - Medium High Contrast"
scene.render.resolution_x, scene.render.resolution_y = 1600, 1000
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "hearth.blend"))
print("rendered", OUT)
