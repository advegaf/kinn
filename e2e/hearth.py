"""End to end suite for the Hearth (hearth-web) in demo mode, headless at 1340x800.

Usage: python3 e2e/hearth.py
Needs agent-browser (npm i -g agent-browser && agent-browser install). No API keys.
Serves hearth-web on a free local port and drives it with real key and pointer presses.
Screenshots of each state go to e2e/out/hearth/. Exit code 1 when a check fails.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "e2e", "out", "hearth")
SESSION = "kinn-e2e-hearth"
W, H = 1340, 800

# The layer that must show in each state, and the elements in it that must hold text.
LAYERS = {
    "clock": (".clock", ["#clock-h", "#clock-m", "#day-num"]),
    "waiting": (".waiting", ["#waiting-line", "#waiting-sub"]),
    "recording": (".rec", ["#rec-prompt"]),
    "sending": (".send", ["#send-line", "#send-sub"]),
    "saved": (".saved", []),
    "playing": (".play-cap", ["#play-cap", "#play-stamp"]),
    "error": (".err", ["#err-line"]),
}

# Runs in the page. Returns a list of problems for the current state, empty when the screen is right.
CHECK_JS = """
((layer, texts, all) => {
  const bad = [];
  const shown = (el) => {
    if (!el) return false;
    const s = getComputedStyle(el), r = el.getBoundingClientRect();
    return s.display !== 'none' && s.visibility === 'visible' && parseFloat(s.opacity) > 0.95 && r.width > 0 && r.height > 0;
  };
  const active = document.querySelector(layer);
  if (!shown(active)) bad.push(`${layer} is not shown`);
  for (const sel of all) {
    if (sel === layer) continue;
    const el = document.querySelector(sel);
    if (el && parseFloat(getComputedStyle(el).opacity) > 0.05 && !active.contains(el)) bad.push(`${sel} shows over ${layer}`);
  }
  for (const sel of texts) {
    const el = document.querySelector(sel);
    if (!el || !el.textContent.trim()) bad.push(`${sel} has no text`);
    else if (!shown(el)) bad.push(`${sel} is not shown`);
  }
  const scope = active.matches('.play-cap') ? [active, document.querySelector('#play-stamp')] : [active];
  for (const box of scope) {
    for (const el of [box, ...box.querySelectorAll('*')]) {
      if (!el.textContent.trim() || el.children.length && el.matches('div')) continue;
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      if (r.left < -1 || r.top < -1 || r.right > innerWidth + 1 || r.bottom > innerHeight + 1)
        bad.push(`${el.id || el.className || el.tagName} is outside the screen`);
      if (el.scrollWidth > el.clientWidth + 2 && getComputedStyle(el).display !== 'inline')
        bad.push(`${el.id || el.className || el.tagName} clips its text`);
    }
  }
  const spot = document.querySelector('#spot').getBoundingClientRect();
  if (spot.width < 44 || spot.height < 44) bad.push(`button zone is ${spot.width}x${spot.height}, less than 44`);
  return bad;
})(%s, %s, %s)
"""


class Fail(Exception):
    pass


def ab(*args, check=True):
    p = subprocess.run(["agent-browser", "--session", SESSION, "--json", *args], capture_output=True, text=True, check=False)
    try:
        out = json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        out = {"success": False, "error": p.stderr.strip() or p.stdout.strip()}
    if check and not out.get("success"):
        raise Fail(f"agent-browser {' '.join(args[:1])}: {out.get('error')}")
    return out.get("data") or {}


def js(expr):
    return ab("eval", expr).get("result")


def state():
    return js("window.hearth?.state")


def wait_state(want, timeout):
    wants = want if isinstance(want, (list, tuple)) else [want]
    end = time.time() + timeout
    seen = state()
    while time.time() < end:
        if seen in wants:
            return seen
        time.sleep(0.2)
        seen = state()
    raise Fail(f"state is {seen}, expected {' or '.join(wants)} within {timeout}s")


def check_screen(name, timeout=4):
    layer, texts = LAYERS[name]
    others = [v[0] for v in LAYERS.values()]
    expr = CHECK_JS % (json.dumps(layer), json.dumps(texts), json.dumps(others))
    end = time.time() + timeout
    bad = js(expr)
    while bad and time.time() < end:
        time.sleep(0.3)
        bad = js(expr)
    if bad:
        raise Fail(f"{name} screen: " + "; ".join(bad))


def shot(name):
    ab("screenshot", os.path.join(OUT, f"{name}.png"))


def press_key():
    ab("press", "Enter")


def button_down(target="#spot"):
    """Presses the button zone (#spot) or the visible strip (#strip) at its centre."""
    x, y = js(f"(() => {{ const r = document.querySelector('{target}').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }})()")
    ab("mouse", "move", str(round(x)), str(round(y)))
    ab("mouse", "down")


def press_button(target="#spot"):
    button_down(target)
    ab("mouse", "up")


def holding():
    return js("document.querySelector('#hearth').hasAttribute('data-hold')")


def hold_to_record():
    """A hold on the strip records only after 3 s, and the ring shows while the hold runs."""
    button_down("#strip")
    time.sleep(1)
    if not holding():
        raise Fail("no hold ring while the button is held")
    if state() != "clock":
        raise Fail(f"state is {state()} after a 1 s hold, expected clock")
    wait_state("recording", 4)
    ab("mouse", "up")
    time.sleep(0.5)
    if state() != "recording":
        raise Fail(f"letting go after the hold left recording: {state()}")


def open_page(base, query):
    ab("open", f"{base}?{query}")
    ab("set", "viewport", str(W), str(H))
    ab("errors", "--clear")
    wait_state(["clock", "waiting", "recording", "sending", "playing", "error"], 10)


def no_page_errors():
    errors = ab("errors").get("errors") or []
    if errors:
        raise Fail("page errors: " + "; ".join(str(e.get("message", e)) for e in errors))


def media_shows_scene():
    ok = js("[...document.querySelectorAll('.kb img.on')].some((i) => i.complete && i.naturalWidth > 0)"
            " && parseFloat(getComputedStyle(document.querySelector('#media')).opacity) > 0.5")
    if not ok:
        raise Fail("playing screen shows no story scene")


def toast_plays():
    """The arrival banner names the sender, fits the strip, and a tap on it plays the new message."""
    end = time.time() + 3
    while not js("document.querySelector('#toast').classList.contains('on')"):
        if time.time() > end:
            raise Fail("no banner when the family reply arrives")
        time.sleep(0.2)
    time.sleep(0.4)
    text, inside, opacity = js("(() => { const t = document.querySelector('#toast'); const r = t.getBoundingClientRect();"
                               " return [document.querySelector('#toast-es').textContent.trim(),"
                               " r.right <= innerWidth + 1 && r.bottom <= innerHeight + 1, parseFloat(getComputedStyle(t).opacity)]; })()")
    if opacity < 0.95:
        raise Fail(f"banner is not shown (opacity {opacity})")
    if not text:
        raise Fail("banner has no text")
    if not inside:
        raise Fail("banner is outside the screen")
    shot("toast")
    ab("click", "#toast")
    wait_state("playing", 3)
    check_screen("playing", timeout=6)
    press_key()
    wait_state(["clock", "waiting"], 3)


# ---------- scenarios ----------

def demo_path(base):
    """Clock, the family reply arrives, Margaret plays it, then records and sends a story."""
    open_page(base, "demo=1")
    wait_state("clock", 5)
    check_screen("clock")
    shot("clock")

    wait_state("waiting", 12)
    check_screen("waiting")
    shot("waiting")

    press_button("#strip")
    wait_state("playing", 3)
    check_screen("playing", timeout=6)
    media_shows_scene()
    shot("playing")
    time.sleep(1)
    press_key()
    wait_state("clock", 3)
    check_screen("clock")

    hold_to_record()
    check_screen("recording")
    time.sleep(2.2)
    counter = js("['c0','c1','c2','c3'].map((id) => document.getElementById(id).textContent).join('')")
    if counter in ("0000", None):
        raise Fail(f"recording counter does not run: {counter}")
    shot("recording")

    press_button("#strip")
    wait_state("sending", 3)
    check_screen("sending")
    shot("sending")
    # Demo send takes 2.6 s and the screen holds at least 1.4 s.
    if wait_state(["saved", "error"], 10) == "error":
        raise Fail("send ended in the error screen")
    check_screen("saved")
    shot("saved")
    check_screen(wait_state(["clock", "waiting"], 6))
    # The demo backend answers a sent story with a new family reply 9 s later.
    wait_state("waiting", 15)
    check_screen("waiting")
    toast_plays()
    no_page_errors()


def subtitles(base):
    """With English subtitles on, the story caption shows both languages and fits the screen."""
    open_page(base, "demo=1&subs=en&state=playing")
    wait_state("playing", 5)
    check_screen("playing", timeout=6)
    if not js("document.querySelector('#cap-en').textContent.trim()"):
        raise Fail("playing screen has no English subtitle")
    shot("playing-subs")
    no_page_errors()


def short_tap(base):
    """A tap shorter than the 3 s hold does not record, and the ring goes away."""
    open_page(base, "demo=1&state=clock")
    wait_state("clock", 5)
    button_down()
    time.sleep(1)
    ab("mouse", "up")
    if holding():
        raise Fail("the hold ring stays after a short tap")
    time.sleep(2.5)
    if state() != "clock":
        raise Fail(f"a short tap changed the state to {state()}")
    check_screen("clock")
    no_page_errors()


def short_press(base):
    """A press shorter than the minimum length does not send anything."""
    open_page(base, "demo=1&state=clock")
    wait_state("clock", 5)
    # The second press must land after the 650 ms double press window and before the 900 ms minimum.
    # Tool calls are not that exact, so the page times both key presses.
    js("(() => { const key = () => dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));"
       " key(); setTimeout(key, 775); })()")
    wait_state("recording", 1)
    time.sleep(1)
    wait_state("clock", 4)
    check_screen("clock")


def error_screen(base):
    """The error screen shows, and a remote key press starts a new recording."""
    open_page(base, "demo=1&state=error")
    wait_state("error", 5)
    check_screen("error")
    shot("error")
    press_key()
    wait_state("recording", 3)
    check_screen("recording")
    no_page_errors()


def error_tap(base):
    """A short tap on the error screen goes back."""
    open_page(base, "demo=1&state=error")
    wait_state("error", 5)
    press_button()
    wait_state(["clock", "waiting"], 3)
    no_page_errors()


SCENARIOS = [demo_path, short_tap, short_press, error_screen, error_tap, subtitles]


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    port = free_port()
    server = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
                              cwd=os.path.join(ROOT, "hearth-web"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}/index.html"
    failed = 0
    try:
        time.sleep(0.5)
        for scenario in SCENARIOS:
            started = time.time()
            try:
                scenario(base)
                print(f"ok    {scenario.__name__} ({time.time() - started:.1f}s)")
            except Fail as e:
                failed += 1
                print(f"FAIL  {scenario.__name__}: {e}")
                ab("screenshot", os.path.join(OUT, f"fail-{scenario.__name__}.png"), check=False)
    finally:
        ab("close", check=False)
        server.terminate()
        server.wait()
    print(f"\n{len(SCENARIOS) - failed} passed, {failed} failed. Screenshots in {os.path.relpath(OUT, ROOT)}/")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
