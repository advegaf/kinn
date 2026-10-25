"""Draws the Hearth's wide-strip screen texture used by the Blender mockup."""
import random
import sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 800
STRIP_TOP, STRIP_H = 152, 496  # roughly 21:9 window inside the 16:10 panel
out = sys.argv[1]

img = Image.new("RGB", (W, H), (20, 14, 10))
strip = Image.new("RGB", (W, STRIP_H))
d = ImageDraw.Draw(strip)

top, mid, bot = (243, 197, 139), (229, 142, 94), (110, 60, 42)
for y in range(STRIP_H):
    t = y / STRIP_H
    a, b, u = (top, mid, t / 0.55) if t < 0.55 else (mid, bot, (t - 0.55) / 0.45)
    d.line([(0, y), (W, y)], fill=tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(3)))

d.ellipse([170, 70, 290, 190], fill=(252, 231, 194))
for base, amp, color in [(0.58, 40, (122, 90, 58)), (0.70, 30, (91, 74, 44)), (0.82, 22, (63, 58, 34))]:
    pts = [(0, STRIP_H)]
    for x in range(0, W + 1, 8):
        import math
        pts.append((x, STRIP_H * base + amp * math.sin(x / 210 + base * 9)))
    pts.append((W, STRIP_H))
    d.polygon(pts, fill=color)

glow = Image.new("RGB", (W, STRIP_H), (0, 0, 0))
gd = ImageDraw.Draw(glow)
cx, cy, r = 930, STRIP_H // 2, 150
gd.ellipse([cx - r - 60, cy - r - 60, cx + r + 60, cy + r + 60], fill=(150, 105, 50))
glow = glow.filter(ImageFilter.GaussianBlur(50))
strip = ImageChops.screen(strip, glow).convert("RGBA")
d = ImageDraw.Draw(strip)
d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(242, 190, 120), outline=(255, 226, 180), width=3)

serif = "/System/Library/Fonts/NewYork.ttf"
serif_i = "/System/Library/Fonts/NewYorkItalic.ttf"
sans = "/System/Library/Fonts/SFNS.ttf"
f_big = ImageFont.truetype(serif, 64)
f_it = ImageFont.truetype(serif_i, 34)
f_btn = ImageFont.truetype(serif, 54)
f_sm = ImageFont.truetype(sans, 30)

d.text((cx, cy + 6), "Escuchar", font=f_btn, fill=(80, 34, 22), anchor="mm")
d.text((90, 250), "Buenas tardes, Rosa", font=f_big, fill=(252, 240, 222))
d.text((92, 330), "Tamales en Monterrey", font=f_it, fill=(240, 214, 186))
d.text((92, 400), "Mensaje nuevo de Sofia", font=f_sm, fill=(245, 232, 214))

rng = random.Random(4)
px = strip.load()
for _ in range(26000):
    x, y = rng.randrange(W), rng.randrange(STRIP_H)
    p = px[x, y]
    k = rng.choice((-22, 22))
    px[x, y] = (max(0, min(255, p[0] + k)), max(0, min(255, p[1] + k)), max(0, min(255, p[2] + k)), 255)

if len(sys.argv) > 2 and sys.argv[2] == "v2":
    # v2 shell: strip fills the middle 50% only; top and bottom bands stay black (glow is lit separately)
    img = Image.new("RGB", (W, H), (0, 0, 0))
    strip, STRIP_TOP = strip.crop((0, (STRIP_H - H // 2) // 2, W, (STRIP_H + H // 2) // 2)), H // 4
img.paste(strip.convert("RGB"), (0, STRIP_TOP))
img.save(out)
print("wrote", out)
