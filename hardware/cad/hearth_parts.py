"""Printable parts for the Hearth: front plate, corner clips, button cap, stand feet.

Run: blender -b -P hearth_parts.py
Writes STLs to ./stl/ in millimetres, each already in its print orientation.

Frames. "Front view" X is right and Y is up when you look at the face.
Plate frame (mm): face on the bed at z=0, the plate grows toward +z (the back).
Seen from the front, plate-frame +x is on the LEFT, so px(X) = -X.
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix

# ---- Fire HD 8 (2024, 12th gen). Measured values live in the measure block of hearth_v4_sdf.py. ----
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hearth_v4_sdf import TAB_W, TAB_H, TAB_T, TAB_CORNER_R, ACT_W, ACT_H, SCREEN_OFF_X, SCREEN_OFF_Y, CLR  # noqa: E402
from hearth_v4_sdf import BTN_X, BTN_Y, BTN_HOLE_D  # noqa: E402

# ---- Plate ----
PLATE_W, PLATE_H, PLATE_D = 232.0, 160.0, 15.0
PLATE_R = 18.0          # corner radius seen from the front
FRONT_ROUND = 2.0       # 45 degree chamfer on the face edge (prints clean face down)
FACE_T = 2.0            # face thickness where solid
BAND_T = 1.0            # glow panels over top/bottom 25% of the display and under the button
WALL = 2.0              # side skirt
WIN_MARGIN_X = 3.0      # window = active width minus this per side
WIN_R = 3.0
USB_SIDE = -1           # -1 = left short edge seen from the front, +1 = right
USB_Y = 0.0             # notch centre along the short edge (front view Y)
USB_W, USB_H = 70.0, 8.0  # wide: USB-C, jack, power, volume share this edge

# ---- Clips and slots ----
BOSS_Y = 54.0           # clip boss centre (front view |Y|) on both short sides
BOSS_LEN = 14.0
SLOT_W, SLOT_L, SLOT_DEPTH = 3.4, 8.4, 7.0
CLIP_FIT = 0.1          # tongue is slot minus 2 x this per dimension (press fit)
CLIP_ARM_T, CLIP_ARM_W = 2.5, 10.0
CLIP_GAP = 0.25        # arm sits this far above the tablet back
CLIP_REACH = 12.0       # how far the arm reaches over the tablet back
LUG_X, LUG_W = 70.0, 10.0  # locating lugs on the long sides

# ---- Button ----
CAP_D, CAP_HEAD_T = 28.0, 5.0
FOAM_T = 3.0                 # adhesive foam ring under the cap head (rest height)
POST_D, SOCKET_D, SOCKET_DEPTH = 9.0, 5.2, 6.0
NIB_PROTRUDE = 2.0           # how far the stylus nib sticks out of the socket. MEASURE.
TIP_GAP = 1.0                # nib to glass at rest
TAPE_W, TAPE_DEPTH = 7.0, 0.4

# ---- Stand feet ----
LEAN_DEG = 10.0
FOOT_W, FOOT_H, FOOT_DEPTH = 10.0, 45.0, 30.0
FOOT_REBATE_W, FOOT_REBATE_D = 2.6, 4.0

HERE = os.path.dirname(os.path.abspath(__file__))
STL_DIR = os.path.join(HERE, "stl")

POCKET_HX, POCKET_HY = TAB_W / 2 + CLR, TAB_H / 2 + CLR
SKIRT_IN_HX, SKIRT_IN_HY = PLATE_W / 2 - WALL, PLATE_H / 2 - WALL
TAB_BACK_Z = FACE_T + TAB_T
SLOT_X = (POCKET_HX + SKIRT_IN_HX) / 2   # front view |X|
GLASS_Z = FACE_T


def px(X):
    return -X


def link(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def rrect(name, w, h, z0, z1, r, cx=0.0, cy=0.0, seg=12, face_round=0.0):
    """Rounded rectangle prism; x and y in plate frame."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(w, h, z1 - z0), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(cx, cy, (z0 + z1) / 2), verts=bm.verts)
    if r > 0:
        vert_edges = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 1e-6]
        bmesh.ops.bevel(bm, geom=vert_edges, offset=r, segments=seg, profile=0.5, affect="EDGES")
    if face_round > 0:
        bottom = [e for e in bm.edges if abs(e.verts[0].co.z - z0) < 1e-6 and abs(e.verts[1].co.z - z0) < 1e-6]
        bmesh.ops.bevel(bm, geom=bottom, offset=face_round, segments=1, affect="EDGES")
    return link(name, bm)


def box(name, x0, x1, y0, y1, z0, z1):
    return rrect(name, x1 - x0, y1 - y0, z0, z1, 0, (x0 + x1) / 2, (y0 + y1) / 2)


def cyl(name, d, z0, z1, cx=0.0, cy=0.0, n=72):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=n, radius1=d / 2, radius2=d / 2, depth=z1 - z0)
    bmesh.ops.translate(bm, vec=(cx, cy, (z0 + z1) / 2), verts=bm.verts)
    return link(name, bm)


def prism(name, pts, thick):
    """Extrude a 2D polygon (x, y) from z=0 to z=thick."""
    bm = bmesh.new()
    lo = [bm.verts.new((x, y, 0)) for x, y in pts]
    hi = [bm.verts.new((x, y, thick)) for x, y in pts]
    bm.faces.new(lo)
    bm.faces.new(hi)
    n = len(pts)
    for i in range(n):
        bm.faces.new((lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return link(name, bm)


def boolean(target, cutter, op="DIFFERENCE"):
    mod = target.modifiers.new("b", "BOOLEAN")
    mod.operation = op
    mod.object = cutter
    mod.solver = "EXACT"
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter)


def build_plate():
    p = rrect("front_plate", PLATE_W, PLATE_H, 0, PLATE_D, PLATE_R, face_round=FRONT_ROUND)
    boolean(p, rrect("hollow", PLATE_W - 2 * WALL, PLATE_H - 2 * WALL, FACE_T, PLATE_D + 1, PLATE_R - WALL))

    for sx in (-1, 1):
        for sy in (-1, 1):
            boolean(p, box("boss", sx * POCKET_HX, sx * (SKIRT_IN_HX + 0.5), sy * BOSS_Y - BOSS_LEN / 2,
                           sy * BOSS_Y + BOSS_LEN / 2, FACE_T - 0.5, TAB_BACK_Z), "UNION")
            boolean(p, box("lug", sx * LUG_X - LUG_W / 2, sx * LUG_X + LUG_W / 2, sy * POCKET_HY,
                           sy * (SKIRT_IN_HY + 0.5), FACE_T - 0.5, TAB_BACK_Z), "UNION")
    for b in [o for o in bpy.data.objects if o.name.startswith(("boss", "lug"))]:
        bpy.data.objects.remove(b)

    cx, cy = px(SCREEN_OFF_X), SCREEN_OFF_Y
    win_w, win_h = ACT_W - 2 * WIN_MARGIN_X, ACT_H / 2
    boolean(p, rrect("window", win_w, win_h, -1, FACE_T + 1, WIN_R, cx, cy))
    for sy in (-1, 1):
        y_in, y_out = cy + sy * (win_h / 2 - 0.5), cy + sy * ACT_H / 2
        boolean(p, box("band", cx - ACT_W / 2, cx + ACT_W / 2, min(y_in, y_out), max(y_in, y_out), BAND_T, FACE_T + 0.5))
    boolean(p, cyl("btn_band", CAP_D + 2, BAND_T, FACE_T + 0.5, px(BTN_X), BTN_Y))
    boolean(p, cyl("btn_hole", BTN_HOLE_D, -1, FACE_T + 1, px(BTN_X), BTN_Y))

    ux = px(USB_SIDE * PLATE_W / 2)
    uz = FACE_T + TAB_T / 2
    boolean(p, box("usb", ux - 2 * WALL - 2, ux + 2 * WALL + 2, USB_Y - USB_W / 2, USB_Y + USB_W / 2,
                   uz - USB_H / 2, PLATE_D + 1))

    for sx in (-1, 1):
        for sy in (-1, 1):
            boolean(p, box("slot", sx * SLOT_X - SLOT_W / 2, sx * SLOT_X + SLOT_W / 2, sy * BOSS_Y - SLOT_L / 2,
                           sy * BOSS_Y + SLOT_L / 2, TAB_BACK_Z - SLOT_DEPTH, PLATE_D + 1))
    return p


def build_clip(sx, sy, name="clip"):
    """Clip in plate frame for the boss at plate-frame (sx*SLOT_X, sy*BOSS_Y)."""
    x_slot = sx * SLOT_X
    x_in = sx * (POCKET_HX - CLIP_REACH)
    x_out = x_slot + sx * (SLOT_W / 2 + 2.0)
    c = box(name, min(x_in, x_out), max(x_in, x_out), sy * BOSS_Y - CLIP_ARM_W / 2, sy * BOSS_Y + CLIP_ARM_W / 2,
            TAB_BACK_Z + CLIP_GAP, TAB_BACK_Z + CLIP_GAP + CLIP_ARM_T)
    tw, tl = SLOT_W - 2 * CLIP_FIT, SLOT_L - 2 * CLIP_FIT
    boolean(c, box("tongue", x_slot - tw / 2, x_slot + tw / 2, sy * BOSS_Y - tl / 2, sy * BOSS_Y + tl / 2,
                   TAB_BACK_Z - SLOT_DEPTH + 0.3, TAB_BACK_Z + CLIP_GAP + 0.5), "UNION")
    return c


def build_cap():
    """Button cap in plate frame (outside the face is z < 0)."""
    cx, cy = px(BTN_X), BTN_Y
    head_bot = -FOAM_T
    head_top = head_bot - CAP_HEAD_T
    post_end = GLASS_Z - TIP_GAP - NIB_PROTRUDE
    c = cyl("button_cap", CAP_D, head_top, head_bot, cx, cy)
    bev = c.modifiers.new("chamfer", "BEVEL")
    bev.width, bev.segments, bev.limit_method = 1.0, 1, "ANGLE"
    bpy.context.view_layer.objects.active = c
    bpy.ops.object.modifier_apply(modifier=bev.name)

    sleeve = cyl("sleeve", BTN_HOLE_D - 1.0, head_bot - 0.5, 0.3, cx, cy)
    boolean(sleeve, cyl("sleeve_in", BTN_HOLE_D - 4.0, head_bot - 1, 1, cx, cy))
    boolean(sleeve, box("tape_gap", cx, cx + CAP_D, cy - TAPE_W / 2 - 0.3, cy + TAPE_W / 2 + 0.3, head_bot - 1, 1))
    boolean(c, sleeve, "UNION")
    boolean(c, cyl("post", POST_D, head_bot - 0.5, post_end, cx, cy), "UNION")
    boolean(c, cyl("socket", SOCKET_D, post_end - SOCKET_DEPTH, post_end + 1, cx, cy))
    # copper tape path: radial groove on the face, then down the side (toward plate-frame +x)
    boolean(c, box("groove_face", cx, cx + CAP_D, cy - TAPE_W / 2, cy + TAPE_W / 2, head_top - 1, head_top + TAPE_DEPTH))
    boolean(c, box("groove_side", cx + CAP_D / 2 - TAPE_DEPTH, cx + CAP_D, cy - TAPE_W / 2, cy + TAPE_W / 2,
                   head_top - 1, head_bot + 1))
    return c


def build_foot(name="foot", mirror=False):
    """Easel foot. Profile in (back, up), extruded FOOT_W. Rebate on the top layers takes the side skirt rim."""
    a = math.radians(LEAN_DEG)
    top_b = FOOT_H * math.tan(a)
    pts = [(0, 0), (FOOT_DEPTH, 0), (top_b + 6, FOOT_H), (top_b, FOOT_H)]
    f = prism(name, pts, FOOT_W)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(2 * FOOT_REBATE_D, FOOT_H * 3, FOOT_REBATE_W + 1), verts=bm.verts)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(-a, 3, "Z"))
    bmesh.ops.translate(bm, vec=(0, 0, FOOT_W - FOOT_REBATE_W + (FOOT_REBATE_W + 1) / 2), verts=bm.verts)
    boolean(f, link("rebate", bm))
    if mirror:  # right-hand foot: rebate on the bed side would overhang, so mirror the part instead
        bm = bmesh.new()
        bm.from_mesh(f.data)
        for v in bm.verts:
            v.co.z = FOOT_W - v.co.z
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(f.data)
        bm.free()
    return f


def to_print(o, m):
    """Apply matrix m, then drop the part onto z=0 at the origin."""
    o.data.transform(m)
    xs = [v.co.x for v in o.data.vertices]
    ys = [v.co.y for v in o.data.vertices]
    zs = [v.co.z for v in o.data.vertices]
    o.data.transform(Matrix.Translation((-(min(xs) + max(xs)) / 2, -(min(ys) + max(ys)) / 2, -min(zs))))
    o.data.update()


def build_all():
    """Assembly in plate frame (mm). Returns dict of objects."""
    parts = {"front_plate": build_plate(), "button_cap": build_cap()}
    for i, (sx, sy) in enumerate([(1, 1), (-1, 1), (1, -1), (-1, -1)]):
        parts[f"clip_{i}"] = build_clip(sx, sy, f"clip_{i}")
    return parts


def check(o):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    nm = sum(1 for e in bm.edges if not e.is_manifold)
    vol = bm.calc_volume(signed=False) / 1000.0
    bm.free()
    xs, ys, zs = ([v.co[i] for v in o.data.vertices] for i in range(3))
    size = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    return nm, vol, size


def export(o, path):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True, apply_modifiers=True, global_scale=1.0)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(STL_DIR, exist_ok=True)
    plate = build_plate()
    to_print(plate, Matrix.Identity(4))  # face already on the bed
    cap = build_cap()
    to_print(cap, Matrix.Rotation(math.pi, 4, "X"))  # head face down
    clip = build_clip(1, 1)
    to_print(clip, Matrix.Rotation(math.pi, 4, "X"))  # arm flat on the bed, tongue up
    foot_l = build_foot("foot_l")
    to_print(foot_l, Matrix.Identity(4))  # profile flat on the bed
    foot_r = build_foot("foot_r", mirror=True)
    to_print(foot_r, Matrix.Rotation(math.pi, 4, "X"))  # flip so the rebate is on top again
    rows = []
    for o, fname, qty in [(plate, "front_plate.stl", 1), (clip, "corner_clip.stl", 4),
                          (cap, "button_cap.stl", 1), (foot_l, "stand_foot_left.stl", 1),
                          (foot_r, "stand_foot_right.stl", 1)]:
        export(o, os.path.join(STL_DIR, fname))
        nm, vol, size = check(o)
        rows.append((fname, qty, nm, vol, size))
    for fname, qty, nm, vol, size in rows:
        fits = size[0] <= 250 and size[1] <= 250
        print(f"PART {fname} x{qty}: {size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} mm, "
              f"{vol:.2f} cm3, non-manifold edges {nm}, fits 250 bed {fits}")


if __name__ == "__main__":
    main()
