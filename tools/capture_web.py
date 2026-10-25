"""Headless Chrome screenshots of hearth-web for the docs media kit.

Usage: python3 tools/capture_web.py <outdir>
Serves hearth-web on a free local port (never 8765), then writes:
  story/NN.png   ?demo=1&state=playing&at=<NN/35>   (36 frames of story 1)
  state-<s>.png  ?demo=1&state=<s>   for clock, waiting, recording, playing (at=0.35)
  template.png   ?template=1
The server root is a temp mirror of hearth-web (symlinks) plus capture.html, a copy of index.html
with layer transitions off. Headless Chrome leaves the clock layer stuck part way through its fade
when ?state=recording jumps straight from clock to recording, so states are shot from capture.html.
Existing files are skipped, so reruns are cheap. Delete the outdir to force a fresh capture.
"""
import os
import shutil
import socket
import tempfile
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
FRAMES = 36


def free_port():
    while True:
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        if port != 8765:
            return port


def shot(url, out):
    if os.path.exists(out):
        return
    subprocess.run([CHROME, "--headless", "--hide-scrollbars", "--run-all-compositor-stages-before-draw",
                    "--virtual-time-budget=6000", "--screenshot=" + out, "--window-size=1280,800", url],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    outdir = os.path.abspath(sys.argv[1])
    os.makedirs(os.path.join(outdir, "story"), exist_ok=True)
    port = free_port()
    web = os.path.join(ROOT, "hearth-web")
    mirror = tempfile.mkdtemp(prefix="hearth-capture-")
    for name in os.listdir(web):
        os.symlink(os.path.join(web, name), os.path.join(mirror, name))
    with open(os.path.join(web, "index.html")) as f:
        page = f.read().replace("</head>", "<style>.layer{transition:none!important}</style></head>", 1)
    with open(os.path.join(mirror, "capture.html"), "w") as f:
        f.write(page)
    server = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
                              cwd=mirror, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(1)
        base = f"http://127.0.0.1:{port}/index.html"
        for i in range(FRAMES):
            at = i / (FRAMES - 1)
            shot(f"{base}?demo=1&state=playing&at={at:.3f}", os.path.join(outdir, "story", f"{i:02d}.png"))
        for s in ("clock", "waiting", "recording", "playing"):
            extra = "&at=0.35" if s == "playing" else ""
            shot(f"http://127.0.0.1:{port}/capture.html?demo=1&state={s}{extra}", os.path.join(outdir, f"state-{s}.png"))
        shot(f"{base}?template=1", os.path.join(outdir, "template.png"))
    finally:
        server.terminate()
        server.wait()
        shutil.rmtree(mirror)


if __name__ == "__main__":
    main()
