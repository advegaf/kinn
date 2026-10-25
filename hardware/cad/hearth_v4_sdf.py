"""Hearth v4 case: front bezel and back shell as signed distance fields, meshed with marching cubes.

Run: uv run --python python3 --with numpy --with scikit-image python cad/hearth_v4_sdf.py
Writes cad/build/{front_bezel,back_shell}_raw.stl in print orientation (mm).
Then run cad/hearth_v4.py in Blender to clean, check and export to cad/stl/.

Frame. Build coords are the front view: X right, Y up, Z depth toward the back (face at Z=0).
Output mesh frame is the plate frame of hearth_parts.py: x = -X, y = Y, z = Z (bezel) or Z - FACE_T (shell).
"""
import math
import os
import struct
import sys

import numpy as np

# Measure these values first. hearth_parts.py, hearth_v4.py and the renders import them.
TAB_W, TAB_H, TAB_T = 208.94, 132.64, 7.95   # Alexa Tablet 8 (2026): 208.94 x 132.64 x 7.95. Calipers, case off.
TAB_CORNER_R = 9.0                          # guess
ACT_W, ACT_H = 190.14, 113.52               # lit area: 1340 x 800 px at 179 ppi (8.7 in). Measure the offset.
SCREEN_OFF_X, SCREEN_OFF_Y = 0.0, 0.0       # active area centre offset from body centre (front view). Measure.
CLR = 0.6                                   # gap per side between tablet and the bezel ribs

W, H = 228.0, 152.0      # footprint seen from the front
R_PLAN = 20.0            # corner radius seen from the front
FACE_T = 1.6             # bezel face
T = 1.6                  # shell wall
BACK_GAP = 0.8           # tablet back to shell ceiling, take up with 1 mm foam pads
Z_B = FACE_T + TAB_T + BACK_GAP + T   # back of the base slab
R_E = 8.0                # soft back edge of the slab
K_SEAM = 0.8             # soft seam where bezel meets shell
R_F = 5.0                # soft front edge, like DR's pillowy face
FACE_CH = 2 * R_F * (1 - 1 / math.sqrt(2))   # 45 degree line tangent to R_F: prints clean face down

# The hump values use front view coordinates.
HUMP_X0, HUMP_X1 = -84.0, 46.0      # base extent across
HUMP_Y0, HUMP_Y1 = -H / 2 - 30, 56.0  # base extent up; runs well past the bottom so the back meets the ground clean
HUMP_R = 26.0            # plan corner radius
Z_TOP = 36.0             # total depth, face to hump top
HUMP_ROUND = 14.0        # top edge round
HUMP_TAPER = 30.0        # side lean from vertical, degrees
K_BLEND = 12.0           # fillet between slab and hump

# The bottom is one flat face, tilted so the case leans back.
LEAN_DEG = 9.0
K_FOOT = 1.5

WIN_MARGIN_X = 3.0
WIN_R = 3.0
WIN_CH = 0.8
BAND_T = 1.0             # face thickness over the hidden display bands; FACE_T turns them off
BUTTON = False         # False: no button hole, grandma taps the screen window directly
GLOW_BANDS = False     # thin glow panels only matter with a translucent shell
BTN_X, BTN_Y = 64.0, -43.0
BTN_HOLE_D = 20.0
RING_D, RING_W = 33.0, 1.6   # DR style touch ring: 45 degree V groove around the cap
CAP_D = 28.0

LUG_FIT = 0.15           # gap per side between lug and shell wall; 0.0 to 0.1 for tighter
LUG_T, LUG_H = 1.8, 5.0
LUGS_LONG_X = (-75.0, -25.0, 25.0, 75.0)   # on the top wall
LUGS_BOTTOM_X = (-78.0, -55.0, 55.0, 78.0) # on the bottom wall, clear of the speaker vents
LUGS_SHORT_Y = (-44.0, 44.0)               # on left and right walls
LUG_LEN_LONG, LUG_LEN_SHORT = 22.0, 16.0
RIB_T, RIB_H, RIB_LEG = 1.2, 5.0, 16.0     # corner L ribs that locate the tablet

USB_SIDE = -1            # -1 = left short edge seen from the front, +1 = right
USB_Y, USB_W = 0.0, 60.0  # notch centre and width along the edge
USB_H = 9.0              # notch height from the bezel back
SPK_X, SPK_Y = -19.0, 20.0   # centre of the 19 hole grid (front view). Fire speaker spot unknown.
SPK_D, SPK_PITCH = 3.0, 6.0
PILL_L, PILL_H = 20.0, 3.6   # two vent slots on the hump's top face
PILL_GAP = 4.0
PILL_Z = Z_B + 6.0
# Speaker vents in the bottom wall, under the tablet's bottom edge (Fire HD 8 speakers fire out of it in landscape).
# The bottom wall sits on the counter, so a shallow channel lifts it off there and opens to the front.
VENT_X = (-40.0, 40.0)   # first and last slot centre, front view X
VENT_N = 13
VENT_W = 2.4             # slot width across X
VENT_Z = (FACE_T + 1.0, FACE_T + TAB_T)   # slot extent in depth: the tablet's edge band
VENT_CH_D = 1.5          # channel depth into the bottom face
VENT_CH_PAD = 4.0        # channel runs this far past the outer slots in X and past the slots' back end in Z

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "build")


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b + (a - b) * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def rrect(x, y, hx, hy, r):
    qx = np.abs(x) - (hx - r)
    qy = np.abs(y) - (hy - r)
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r


def round_top(d2, z, ztop, r):
    """Extrude a 2D field toward +z with a round of radius r on the top edge."""
    qx, qz = d2 + r, z - (ztop - r)
    return np.minimum(np.maximum(qx, qz), 0) + np.hypot(np.maximum(qx, 0), np.maximum(qz, 0)) - r


def envelope(X, Y, Z):
    plan = rrect(X, Y, W / 2, H / 2, R_PLAN)
    slab = round_top(plan, Z, Z_B, R_E)
    shrink = np.maximum(Z - Z_B, 0) * math.tan(math.radians(HUMP_TAPER))
    hx, hy = (HUMP_X1 - HUMP_X0) / 2 - shrink, (HUMP_Y1 - HUMP_Y0) / 2 - shrink
    d2 = rrect(X - (HUMP_X0 + HUMP_X1) / 2, Y - (HUMP_Y0 + HUMP_Y1) / 2, hx, hy, np.maximum(HUMP_R - shrink, 4.0))
    hump = round_top(d2, Z, Z_TOP, HUMP_ROUND)
    body = np.maximum(smin(slab, hump, K_BLEND), round_top(plan, -Z, 0.0, R_F))
    a = math.radians(LEAN_DEG)
    ground = ((-H / 2 + Z * math.tan(a)) - Y) * math.cos(a)
    return smax(body, ground, K_FOOT)


def lug_mask(X, Y):
    m = np.full(X.shape, np.inf, dtype=np.float32)
    for x in LUGS_LONG_X:
        m = np.minimum(m, np.maximum(np.abs(X - x) - LUG_LEN_LONG / 2, H / 2 - 12 - Y))
    for x in LUGS_BOTTOM_X:
        m = np.minimum(m, np.maximum(np.abs(X - x) - LUG_LEN_LONG / 2, H / 2 - 12 + Y))
    for y in LUGS_SHORT_Y:
        m = np.minimum(m, np.maximum(np.abs(Y - y) - LUG_LEN_SHORT / 2, W / 2 - 12 - np.abs(X)))
    return m


def side(X, Y, Z):
    """Plan outline with the tilted ground cut, no rounds."""
    a = math.radians(LEAN_DEG)
    return np.maximum(rrect(X, Y, W / 2, H / 2, R_PLAN), ((-H / 2 + Z * math.tan(a)) - Y) * math.cos(a))


SEAM_INSET = R_F - math.sqrt(R_F ** 2 - (R_F - FACE_T) ** 2)   # front round inset at the seam


def inner(X, Y, Z):
    """Envelope with the front round taken out: vertical from the seam until the back round, so lugs slide in."""
    return np.maximum(envelope(X, Y, Z), side(X, Y, Z) + SEAM_INSET)


def bezel(X, Y, Z):
    e = envelope(X, Y, Z)
    ef = side(X, Y, Z) + SEAM_INSET
    d = np.maximum.reduce([e, (side(X, Y, Z) - Z + FACE_CH) / math.sqrt(2), -Z])
    d = smax(d, Z - FACE_T, K_SEAM)
    # glow bands: thin the face from the back over the hidden top and bottom of the display
    cx, cy = SCREEN_OFF_X, SCREEN_OFF_Y
    win_w, win_h = ACT_W - 2 * WIN_MARGIN_X, ACT_H / 2
    band = np.maximum(rrect(X - cx, np.abs(Y - cy) - (win_h / 2 + ACT_H / 2) / 2, ACT_W / 2, (ACT_H / 2 - win_h / 2) / 2 - 0.5, 1.0),
                      BAND_T - Z)
    if GLOW_BANDS:
        d = np.maximum(d, -band)
    win = rrect(X - cx, Y - cy, win_w / 2, win_h / 2, WIN_R) - np.maximum(WIN_CH - Z, 0)
    d = np.maximum(d, -win)
    if BUTTON:
        rb = np.hypot(X - BTN_X, Y - BTN_Y)
        d = np.maximum(d, -(rb - BTN_HOLE_D / 2))
        groove = (np.abs(rb - RING_D / 2) - RING_W / 2 + Z) / math.sqrt(2)
        d = np.maximum(d, -groove)
    # lugs ride just inside the shell wall
    lug = np.abs(ef + T + LUG_FIT + LUG_T / 2) - LUG_T / 2
    lug = smax(smax(lug, lug_mask(X, Y), 0.8), Z - (FACE_T + LUG_H), 0.8)
    lug = np.maximum(lug, FACE_T - 0.4 - Z)
    d = np.minimum(d, lug)
    px_, py_ = TAB_W / 2 + CLR, TAB_H / 2 + CLR
    pocket = rrect(X, Y, px_, py_, TAB_CORNER_R + CLR)
    corner = np.maximum(px_ - RIB_LEG - np.abs(X), py_ - RIB_LEG - np.abs(Y))
    rib = np.maximum.reduce([np.abs(pocket - RIB_T / 2) - RIB_T / 2, corner, Z - (FACE_T + RIB_H), FACE_T - 0.4 - Z])
    return np.maximum(np.minimum(d, rib), -vent_channel(X, Y, Z))


def shell(X, Y, Z):
    e = envelope(X, Y, Z)
    d = np.maximum.reduce([smax(e, FACE_T - Z, K_SEAM), -(inner(X, Y, Z) + T), FACE_T - Z])
    ux = USB_SIDE * W / 2
    notch = np.maximum.reduce([W / 2 - 14 - USB_SIDE * X, np.abs(Y - USB_Y) - USB_W / 2 + np.maximum(Z - FACE_T, 0),
                               Z - (FACE_T + USB_H)])
    d = np.maximum(d, -notch)
    k = 0
    for row, n in zip(range(-2, 3), (3, 4, 5, 4, 3)):
        for i in range(n):
            hx = SPK_X + (i - (n - 1) / 2) * SPK_PITCH
            hy = SPK_Y + row * SPK_PITCH * math.sqrt(3) / 2
            hole = np.maximum(np.hypot(X - hx, Y - hy) - SPK_D / 2, Z_B + 3 - Z)
            d = np.maximum(d, -hole)
            k += 1
    assert k == 19
    for s in (-1, 1):
        cx = (HUMP_X0 + HUMP_X1) / 2 + s * (PILL_L / 2 + PILL_GAP / 2)
        qx = np.maximum(np.abs(X - cx) - (PILL_L - PILL_H) / 2, 0)
        pill = np.maximum(np.hypot(qx, Z - PILL_Z) - PILL_H / 2, 20 - Y)
        d = np.maximum(d, -pill)
    return vents(d, X, Y, Z)


def vent_channel(X, Y, Z):
    """Relief in the tilted bottom face over the vents, open to the front, 45 degree ramp at the back so it prints."""
    a = math.radians(LEAN_DEG)
    g = ((-H / 2 + Z * math.tan(a)) - Y) * math.cos(a)   # > 0 below the ground plane
    z_end = VENT_Z[1] + VENT_CH_PAD
    return np.maximum(-VENT_CH_D + np.maximum(Z - z_end, 0) - g,
                      np.abs(X - (VENT_X[0] + VENT_X[1]) / 2) - (VENT_X[1] - VENT_X[0]) / 2 - VENT_W / 2 - VENT_CH_PAD)


def vents(d, X, Y, Z):
    d = np.maximum(d, -vent_channel(X, Y, Z))
    zc, hl = (VENT_Z[0] + VENT_Z[1]) / 2, (VENT_Z[1] - VENT_Z[0] - VENT_W) / 2
    qz = np.maximum(np.abs(Z - zc) - hl, 0)
    pitch = (VENT_X[1] - VENT_X[0]) / (VENT_N - 1)
    for i in range(VENT_N):
        slot = np.maximum(np.hypot(X - (VENT_X[0] + i * pitch), qz) - VENT_W / 2, Y - (-H / 2 + 15))
        d = np.maximum(d, -slot)
    return d


def mesh(fn, lo, hi, step, name):
    xs = np.arange(lo[0], hi[0] + step, step, dtype=np.float32) + step * 0.37
    ys = np.arange(lo[1], hi[1] + step, step, dtype=np.float32) + step * 0.29
    zs = np.arange(lo[2], hi[2] + step, step, dtype=np.float32) + step * 0.41
    vol = np.empty((len(xs), len(ys), len(zs)), dtype=np.float32)
    Y, Z = np.meshgrid(ys, zs, indexing="ij")
    for i, x in enumerate(xs):
        vol[i] = fn(np.full_like(Y, x), Y, Z)
    vol[[0, -1], :, :] = vol[:, [0, -1], :] = 1.0
    vol[:, :, [0, -1]] = 1.0
    from skimage.measure import marching_cubes  # here so Blender can import the constants without scikit-image
    v, f, _, _ = marching_cubes(vol, 0.0, spacing=(step, step, step), allow_degenerate=False)
    v += np.array([xs[0], ys[0], zs[0]])
    inside = (vol < 0).sum() * step ** 3 / 1000.0
    print(f"{name}: grid {vol.shape}, {len(f)} tris, voxel volume {inside:.1f} cm3")
    return v, f


def write_stl(path, v, f):
    tri = v[f].astype(np.float32)
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    rec = np.zeros(len(f), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"], rec["v"] = n, tri
    with open(path, "wb") as fh:
        fh.write(b"hearth v4".ljust(80, b" "))
        fh.write(struct.pack("<I", len(f)))
        fh.write(rec.tobytes())


def to_plate(v, f, dz):
    p = np.column_stack([-v[:, 0], v[:, 1], v[:, 2] - dz])
    return p, f[:, ::-1]  # mirroring x flips winding


def main():
    os.makedirs(OUT, exist_ok=True)
    step = float(sys.argv[1]) if len(sys.argv) > 1 else 0.35
    pad = 2.0
    v, f = mesh(bezel, (-W / 2 - pad, -H / 2 - pad, -pad), (W / 2 + pad, H / 2 + pad, FACE_T + LUG_H + pad), step * 0.75, "front_bezel")
    write_stl(os.path.join(OUT, "front_bezel_raw.stl"), *to_plate(v, f, 0.0))
    v, f = mesh(shell, (-W / 2 - pad, -H / 2 - pad, FACE_T - pad), (W / 2 + pad, H / 2 + pad, Z_TOP + pad), step, "back_shell")
    write_stl(os.path.join(OUT, "back_shell_raw.stl"), *to_plate(v, f, FACE_T))


if __name__ == "__main__":
    main()
