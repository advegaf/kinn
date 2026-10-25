"""Painterly 21:9 story stills for the design iterations, finished with Dream Recorder's ffmpeg look."""
import os, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter

W, H = 1260, 540
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)

def grad(d, top, bot, y0=0, y1=H):
    for y in range(y0, y1):
        t = (y - y0) / max(1, y1 - y0)
        d.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))

def blobs(d, rng, n, box, colors, rmin, rmax):
    x0, y0, x1, y1 = box
    for _ in range(n):
        x, y, r = rng.uniform(x0, x1), rng.uniform(y0, y1), rng.uniform(rmin, rmax)
        d.ellipse([x - r, y - r * 0.7, x + r, y + r * 0.7], fill=rng.choice(colors))

def kitchen(rng):
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    grad(d, (196, 120, 70), (90, 52, 34))
    d.rectangle([760, 60, 1100, 300], fill=(250, 214, 150))
    d.rectangle([0, 380, W, H], fill=(110, 70, 44))
    d.ellipse([380, 250, 640, 420], fill=(150, 72, 40))
    blobs(d, rng, 40, (420, 60, 620, 260), [(240, 220, 200), (220, 200, 180)], 20, 60)
    return im

def street(rng):
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    grad(d, (150, 190, 230), (240, 200, 160), 0, 250)
    x = 0
    for c in [(214, 90, 70), (240, 190, 80), (90, 150, 170), (230, 140, 120), (130, 170, 90), (220, 110, 150)]:
        w = rng.randint(180, 260); d.rectangle([x, rng.randint(120, 200), x + w, 470], fill=c); x += w
    d.rectangle([0, 470, W, H], fill=(150, 130, 110))
    return im

def garden(rng):
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    grad(d, (120, 170, 230), (200, 220, 230), 0, 300)
    d.rectangle([0, 260, W, H], fill=(60, 110, 60))
    blobs(d, rng, 160, (0, 260, W, H), [(210, 40, 40), (230, 70, 60), (90, 140, 70), (250, 180, 60)], 10, 30)
    return im

def sea(rng):
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    grad(d, (250, 190, 150), (180, 150, 200), 0, 260)
    grad(d, (70, 110, 150), (30, 60, 90), 260, H)
    d.ellipse([560, 170, 700, 310], fill=(255, 225, 170))
    return im

def bakery(rng):
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    grad(d, (60, 40, 30), (30, 20, 15))
    d.rectangle([200, 80, 1060, 420], fill=(240, 190, 110))
    blobs(d, rng, 60, (240, 280, 1020, 400), [(200, 130, 60), (230, 170, 90), (180, 100, 50)], 25, 55)
    return im

def plaza(rng):
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    grad(d, (240, 170, 120), (250, 220, 180), 0, 300)
    d.polygon([(520, 380), (630, 60), (740, 380)], fill=(230, 210, 190))
    d.rectangle([380, 220, 880, 420], fill=(225, 200, 175))
    d.rectangle([0, 420, W, H], fill=(190, 160, 130))
    return im

def train(rng):
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    grad(d, (170, 200, 220), (230, 230, 210), 0, 280)
    d.rectangle([0, 280, W, H], fill=(170, 150, 80))
    d.rectangle([120, 220, 1140, 360], fill=(60, 80, 110))
    for x in range(160, 1120, 110):
        d.rectangle([x, 245, x + 70, 300], fill=(240, 220, 160))
    return im

scenes = [("tamales", kitchen), ("calle", street), ("jardin", garden), ("mar", sea), ("panaderia", bakery), ("plaza", plaza), ("tren", train)]
for i, (name, fn) in enumerate(scenes):
    rng = random.Random(i + 3)
    im = fn(rng).filter(ImageFilter.GaussianBlur(9))
    raw = os.path.join(OUT, f"_{name}.png")
    im.save(raw)
    out = os.path.join(OUT, f"{i + 1}-{name}.jpg")
    vf = "eq=brightness=0.06,vibrance=intensity=1.2,vaguedenoiser=threshold=300,bilateral=sigmaS=100,noise=alls=40:allf=u"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-vf", vf, "-q:v", "3", out], check=True)
    os.remove(raw)
    print(out)
