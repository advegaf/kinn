"""Hearth v4: clean the SDF meshes, build the button cap, check and export print STLs.

Run after cad/hearth_v4_sdf.py:
  blender -b -P cad/hearth_v4.py
Writes cad/stl/{front_bezel,back_shell,button_cap}.stl in print orientation (mm).
"""
import math
import os
import sys

import bpy
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hearth_parts as hp  # noqa: E402
import hearth_v4_sdf as sdf  # noqa: E402

BUILD = os.path.join(HERE, "build")
TARGET_TRIS = 300_000
RATES = (30.0, 22.0)        # cm3 per hour: our 0.28 mm estimate, and DR's real print
SUPPORT_EXTRA = 0.12        # tree supports inside the shell


def load(name):
    bpy.ops.wm.stl_import(filepath=os.path.join(BUILD, name + "_raw.stl"))
    o = bpy.context.selected_objects[0]
    o.name = name
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5)  # STL import splits verts; 0.01 pinches thin spots
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    n = len(o.data.polygons)
    print(f"RAW {name}: {n} faces, non-manifold edges {hp.check(o)[0]}")
    if n > TARGET_TRIS:
        d = o.modifiers.new("decimate", "DECIMATE")
        d.decimate_type, d.ratio, d.use_collapse_triangulate = "COLLAPSE", TARGET_TRIS / n, True
        bpy.ops.object.modifier_apply(modifier=d.name)
    return o


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    hp.FACE_T = hp.GLASS_Z = 1.6
    hp.FOAM_T, hp.CAP_HEAD_T = 3.0, 6.0
    stl_dir = hp.STL_DIR
    old = os.path.join(stl_dir, "old")
    os.makedirs(old, exist_ok=True)
    for f in ("corner_clip.stl", "stand_foot_left.stl", "stand_foot_right.stl", "front_plate.stl"):
        if os.path.exists(os.path.join(stl_dir, f)):
            os.replace(os.path.join(stl_dir, f), os.path.join(old, f))

    bezel = load("front_bezel")
    shell = load("back_shell")
    parts = [(bezel, "front_bezel.stl"), (shell, "back_shell.stl")]
    if sdf.BUTTON:
        cap = hp.build_cap()
        hp.to_print(cap, Matrix.Rotation(math.pi, 4, "X"))  # head face down
        parts.append((cap, "button_cap.stl"))
    elif os.path.exists(os.path.join(stl_dir, "button_cap.stl")):
        os.replace(os.path.join(stl_dir, "button_cap.stl"), os.path.join(old, "button_cap.stl"))

    total = 0.0
    for o, fname in parts:
        hp.export(o, os.path.join(stl_dir, fname))
        nm, vol, size = hp.check(o)
        total += vol
        fits = size[0] <= 250 and size[1] <= 250
        print(f"PART {fname}: {size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} mm, {vol:.2f} cm3, "
              f"{len(o.data.polygons)} faces, non-manifold edges {nm}, fits 250 bed {fits}")
    for r in RATES:
        print(f"TOTAL {total:.1f} cm3: {total / r:.1f} h at {r:.0f} cm3/h, "
              f"{total / r * (1 + SUPPORT_EXTRA):.1f} h with supports")


if __name__ == "__main__":
    main()
