"""Image helpers for tools/make-docs-media.sh. Pillow + numpy only.

Subcommands:
  logo <icon.png> <out.png>
      Masks the app icon to an iOS rounded square (radius 22.37%), 512 px, transparent outside.
  hearth <frame-black.png> <frame-calib.png> <outdir> <shot.png>...
      Pastes each 1280x800 hearth-web screenshot into the Hearth front render. frame-black is the
      render with a black screen texture; frame-calib is the same camera with the calib texture
      (green field, four magenta markers at known texture pixels). The markers give an exact affine
      map from texture to render pixels, and the calib minus black difference gives the window mask
      (bezel occlusion and antialiasing included). Writes <outdir>/NN.png, cropped to the device.
  calib <out.png>
      Writes the calibration screen texture used above.
  crossfade <indir> <outdir> <steps> [loop_steps]
      Writes the frames of <indir> in order with <steps>-1 blended frames between neighbours,
      plus <loop_steps> blended frames from the last back to the first.
  hold <outdir> <hold> <fade> <png>...
      Each png held <hold> frames, then <fade> blended frames into the next (loops back to the first).
  phone <outdir> <height> <bg> <shot.png>...
      Draws an iPhone body around each simulator screenshot. bg is "none" (transparent) or a hex colour.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

MARKERS = [(160, 260), (1120, 260), (160, 540), (1120, 540)]  # texture pixels, see calib
CROP = (200, 130, 1400, 910)  # device crop in the 1600x1000 front render (1200x780)


def rounded_mask(size, radius, scale=4):
    w, h = size
    m = Image.new("L", (w * scale, h * scale), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * scale - 1, h * scale - 1], radius * scale, fill=255)
    return m.resize(size, Image.LANCZOS)


def logo(src, out):
    im = Image.open(src).convert("RGBA").resize((512, 512), Image.LANCZOS)
    im.putalpha(rounded_mask((512, 512), 512 * 0.2237))
    im.save(out, optimize=True)


def calib(out):
    im = Image.new("RGB", (1280, 800), (0, 255, 0))
    d = ImageDraw.Draw(im)
    for x, y in MARKERS:
        d.rectangle([x - 12, y - 12, x + 12, y + 12], fill=(255, 0, 255))
    im.save(out)


def blobs(mask):
    """Centroids of the four marker blobs, sorted like MARKERS (top-left, top-right, bottom-left, bottom-right)."""
    ys, xs = np.nonzero(mask)
    pts = np.stack([xs, ys], 1).astype(float)
    cx, cy = pts[:, 0].mean(), pts[:, 1].mean()
    out = []
    for top in (True, False):
        for left in (True, False):
            sel = pts[((pts[:, 1] < cy) == top) & ((pts[:, 0] < cx) == left)]
            out.append(sel.mean(0))
    return np.array(out)


def hearth(black_path, calib_path, outdir, shots):
    black = np.asarray(Image.open(black_path).convert("RGB")).astype(float) / 255
    cal = np.asarray(Image.open(calib_path).convert("RGB")).astype(float) / 255
    diff = np.clip(cal - black, 0, None)
    # magenta marker: red and blue both lifted well above green
    magenta = (diff[..., 0] - diff[..., 1] > 0.15) & (diff[..., 2] - diff[..., 1] > 0.15)
    dst = blobs(magenta)
    src = np.array(MARKERS, float)
    # least squares affine: render (x, y, 1) -> texture (u, v), what PIL's AFFINE transform wants
    A = np.hstack([dst, np.ones((4, 1))])
    coef_u, *_ = np.linalg.lstsq(A, src[:, 0], rcond=None)
    coef_v, *_ = np.linalg.lstsq(A, src[:, 1], rcond=None)
    err = np.abs(A @ np.stack([coef_u, coef_v], 1) - src).max()
    print(f"hearth: marker fit max error {err:.2f} texture px")
    level = diff.max(2)
    ref = np.median(level[level > level.max() * 0.5])
    alpha = np.clip(level / ref, 0, 1)[..., None]
    h, w = black.shape[:2]
    os.makedirs(outdir, exist_ok=True)
    for i, shot in enumerate(shots):
        tex = Image.open(shot).convert("RGB")
        warped = tex.transform((w, h), Image.AFFINE, tuple(coef_u) + tuple(coef_v), resample=Image.BICUBIC)
        scr = np.asarray(warped).astype(float) / 255
        comp = black + scr * alpha  # the black screen keeps its glass reflection, the screenshot adds on top
        comp = np.clip(comp, 0, 1)
        Image.fromarray((comp * 255 + 0.5).astype(np.uint8)).crop(CROP).save(os.path.join(outdir, f"{i:02d}.png"))


def blend(a, b, t):
    return Image.blend(a, b, t)


def crossfade(indir, outdir, steps, loop_steps=0):
    files = sorted(f for f in os.listdir(indir) if f.endswith(".png"))
    ims = [Image.open(os.path.join(indir, f)).convert("RGB") for f in files]
    os.makedirs(outdir, exist_ok=True)
    n = 0
    for i, im in enumerate(ims):
        im.save(os.path.join(outdir, f"{n:04d}.png"))
        n += 1
        last = i == len(ims) - 1
        k = loop_steps if last else steps
        nxt = ims[0] if last else ims[i + 1]
        for s in range(1, k):
            blend(im, nxt, s / k).save(os.path.join(outdir, f"{n:04d}.png"))
            n += 1
    print(f"crossfade: {n} frames")


def hold(outdir, nhold, fade, pngs):
    ims = [Image.open(p).convert("RGB") for p in pngs]
    os.makedirs(outdir, exist_ok=True)
    n = 0
    for i, im in enumerate(ims):
        nxt = ims[(i + 1) % len(ims)]
        for _ in range(nhold):
            im.save(os.path.join(outdir, f"{n:04d}.png"))
            n += 1
        for s in range(1, fade + 1):
            blend(im, nxt, s / (fade + 1)).save(os.path.join(outdir, f"{n:04d}.png"))
            n += 1
    print(f"hold: {n} frames")


def phone(outdir, height, bg, shots):
    """iPhone 17 Pro style body: black glass border, thin titanium rim, side buttons, Dynamic Island.
    Drawn at screenshot scale, then resized to <height>."""
    os.makedirs(outdir, exist_ok=True)
    first = Image.open(shots[0])
    sw, sh = first.size  # 1206x2622 on iPhone 17 Pro
    k = sw / 1206
    border = round(34 * k)      # black glass around the display
    rim = round(14 * k)         # titanium band
    pad = round(80 * k)         # canvas margin for buttons and shadow
    scr_r = round(170 * k)      # display corner radius
    bw, bh = sw + 2 * (border + rim), sh + 2 * (border + rim)
    W, H = bw + 2 * pad, bh + 2 * pad
    body_r = scr_r + border + rim
    bgcol = (0, 0, 0, 0) if bg == "none" else tuple(int(bg[i:i + 2], 16) for i in (0, 2, 4)) + (255,)

    base = Image.new("RGBA", (W, H), bgcol)
    # soft shadow
    sh_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh_layer).rounded_rectangle([pad, pad + round(24 * k), pad + bw, pad + bh + round(24 * k)],
                                               body_r, fill=(40, 30, 20, 70))
    sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(round(36 * k)))
    base = Image.alpha_composite(base, sh_layer)
    d = ImageDraw.Draw(base)
    # side buttons (left: action, volume up, volume down; right: power, camera control)
    ti, ti_dark = (168, 162, 154, 255), (120, 115, 108, 255)
    bt = round(10 * k)
    for y0, y1 in ((520, 640), (760, 960), (1010, 1210)):
        d.rounded_rectangle([pad - bt, pad + y0 * k, pad + rim, pad + y1 * k], bt, fill=ti_dark)
    for y0, y1 in ((860, 1160), (1640, 1840)):
        d.rounded_rectangle([pad + bw - rim, pad + y0 * k, pad + bw + bt, pad + y1 * k], bt, fill=ti_dark)
    # titanium rim, then black glass
    d.rounded_rectangle([pad, pad, pad + bw - 1, pad + bh - 1], body_r, fill=ti)
    d.rounded_rectangle([pad + round(3 * k), pad + round(3 * k), pad + bw - 1 - round(3 * k), pad + bh - 1 - round(3 * k)],
                        body_r - round(3 * k), fill=(196, 191, 184, 255))
    d.rounded_rectangle([pad + rim, pad + rim, pad + bw - 1 - rim, pad + bh - 1 - rim], body_r - rim, fill=(8, 8, 9, 255))
    smask = rounded_mask((sw, sh), scr_r)
    for i, shot in enumerate(shots):
        im = base.copy()
        x0, y0 = pad + rim + border, pad + rim + border
        im.paste(Image.open(shot).convert("RGB"), (x0, y0), smask)
        # simctl screenshots leave out the Dynamic Island: 126 x 37 pt, 11 pt from the top (3x)
        iw, ih, it = round(378 * k), round(111 * k), round(33 * k)
        ImageDraw.Draw(im).rounded_rectangle([x0 + (sw - iw) // 2, y0 + it, x0 + (sw + iw) // 2, y0 + it + ih],
                                             ih // 2, fill=(0, 0, 0, 255))
        out = im.resize((round(W * height / H), height), Image.LANCZOS)
        out.save(os.path.join(outdir, f"{i:02d}.png"))


def main():
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "logo":
        logo(*args)
    elif cmd == "calib":
        calib(*args)
    elif cmd == "hearth":
        hearth(args[0], args[1], args[2], args[3:])
    elif cmd == "crossfade":
        crossfade(args[0], args[1], int(args[2]), int(args[3]) if len(args) > 3 else 0)
    elif cmd == "hold":
        hold(args[0], int(args[1]), int(args[2]), args[3:])
    elif cmd == "phone":
        phone(args[0], int(args[1]), args[2], args[3:])
    else:
        sys.exit(f"unknown subcommand {cmd}")


if __name__ == "__main__":
    main()
