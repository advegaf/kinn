"""Kinn story worker.

Watches Supabase for ready messages from either side, splits each story into SCENES beats
with one LLM call, renders one Dream Recorder style Luma clip per beat (ffmpeg
look plus a gentle slow-down), uploads them and writes messages.story with
story.scenes. Retries Luma on failure; the make-story images fallback is off
unless STORY_FALLBACK=images.

  python main.py                     poll forever
  python main.py --once <message_id> process one message now
  python main.py --look <input.mp4>  apply the ffmpeg look to a local file
  python main.py --luma-check        one real Luma clip, no Supabase
  python main.py --scenes-check      LLM beats plus SCENES real Luma clips on a sample story, no Supabase
  python main.py --demo-clips s1 r1  Luma clips for canned demo scenes, uploaded to videos/demo/<id>-<n>
"""

import argparse
import json
import logging
import os
import socket
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import ffmpeg
import requests

from audio import fix_webm
from llm import env
from luma import LUMA_API_STYLE, LUMA_ASPECT_RATIO, LUMA_DURATION, LUMA_MODEL, LUMA_RESOLUTION, generate_with_retry
from scenes import make_scenes
from supa import SUPABASE_URL, headers, rest, upload

log = logging.getLogger("story-worker")

POLL_SECONDS = float(env("POLL_SECONDS", "5"))
STALE_MINUTES = float(env("CLAIM_STALE_MINUTES", "10"))
WORKER_ID = f"{socket.gethostname()}:{os.getpid()}"

# The Luma Agents account allows 4 concurrent generations; a 5th gets HTTP 429 and waits for a slot.
LUMA_CONCURRENCY = int(env("LUMA_CONCURRENCY", "4"))
LUMA_SLOWDOWN = float(env("LUMA_SLOWDOWN", "2.0"))  # setpts factor, 2.0 turns a 5 s clip into about 10 s
STORY_FALLBACK = env("STORY_FALLBACK", "none")  # "images" calls make-story when Luma fails

FFMPEG_BRIGHTNESS = float(env("FFMPEG_BRIGHTNESS", "0.03"))
FFMPEG_VIBRANCE = float(env("FFMPEG_VIBRANCE", "0.25"))
FFMPEG_DENOISE_THRESHOLD = float(env("FFMPEG_DENOISE_THRESHOLD", "20"))
FFMPEG_BILATERAL_SIGMA = float(env("FFMPEG_BILATERAL_SIGMA", "12"))
FFMPEG_NOISE_STRENGTH = float(env("FFMPEG_NOISE_STRENGTH", "34"))


class Timer:
    def __init__(self, label):
        self.label = label
        self.start = self.last = time.monotonic()

    def step(self, name):
        now = time.monotonic()
        log.info("[%s] %s %d ms", self.label, name, (now - self.last) * 1000)
        self.last = now

    def total(self):
        return int((time.monotonic() - self.start) * 1000)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


READY = [
    ("select", "*,sender:profiles(role)"),
    ("status", "eq.ready"),
    ("transcript", "not.is.null"),
    ("order", "created_at.asc"),
    ("limit", "5"),
]


def find_work():
    fresh = rest("GET", READY + [("story", "is.null")]) + rest("GET", READY + [("story->>status", "eq.pending")])
    stale_before = (datetime.now(timezone.utc) - timedelta(minutes=STALE_MINUTES)).isoformat()
    stale = rest(
        "GET",
        READY + [("story->>status", "eq.generating"), ("story->>claimed_at", "lt." + stale_before)],
    )
    return fresh + stale


def get_message(message_id):
    rows = rest("GET", [("select", "*"), ("id", "eq." + message_id)])
    if not rows:
        raise RuntimeError(f"Message {message_id} not found")
    return rows[0]


def claim(msg, force=False):
    """Atomically mark a row as generating. Returns the row, or None if another worker won."""
    params = [READY[0], ("id", "eq." + msg["id"])]
    story = msg.get("story")
    if not force:
        if story is None:
            params.append(("story", "is.null"))
        elif story.get("status") == "pending":
            params.append(("story->>status", "eq.pending"))
        else:
            params.append(("story->>claimed_at", "eq." + str(story.get("claimed_at"))))
    marker = {"status": "generating", "claimed_at": now_iso(), "worker": WORKER_ID}
    rows = rest("PATCH", params, {"story": marker})
    return rows[0] if rows else None


def write_story(message_id, story, only_if_generating=False):
    params = [("id", "eq." + message_id)]
    if only_if_generating:
        params.append(("story->>status", "eq.generating"))
    return rest("PATCH", params, {"story": story})


# ffmpeg look, ported from Dream Recorder functions/video.py (Copyright 2025 Modem, MIT)


def process_video(src, dest):
    stream = ffmpeg.input(src)
    stream = ffmpeg.filter(stream, "eq", brightness=FFMPEG_BRIGHTNESS)
    stream = ffmpeg.filter(stream, "vibrance", intensity=FFMPEG_VIBRANCE)
    stream = ffmpeg.filter(stream, "vaguedenoiser", threshold=FFMPEG_DENOISE_THRESHOLD)
    stream = ffmpeg.filter(stream, "bilateral", sigmaS=FFMPEG_BILATERAL_SIGMA)
    stream = ffmpeg.filter(stream, "noise", all_strength=FFMPEG_NOISE_STRENGTH)
    stream = ffmpeg.output(stream, dest, vcodec="libx264", pix_fmt="yuv420p", movflags="+faststart")
    try:
        ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
    except ffmpeg.Error as e:
        raise RuntimeError(f"ffmpeg look failed: {e.stderr.decode()[-500:]}")
    return dest


def process_thumbnail(video, dest):
    """21:9 center crop of the frame at 1 s (Dream Recorder crops square)."""
    info = next(s for s in ffmpeg.probe(video)["streams"] if s["codec_type"] == "video")
    width, height = int(info["width"]), int(info["height"])
    h = min(height, round(width * 9 / 21))
    w = min(width, round(h * 21 / 9))
    stream = ffmpeg.input(video, ss=1)
    stream = ffmpeg.filter(stream, "crop", w, h, (width - w) // 2, (height - h) // 2)
    stream = ffmpeg.output(stream, dest, vframes=1, **{"q:v": 2})
    try:
        ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
    except ffmpeg.Error as e:
        raise RuntimeError(f"ffmpeg thumbnail failed: {e.stderr.decode()[-500:]}")
    return dest


def slow_video(src, dest):
    """Gentle slow-down so a 5 s clip holds about 10 s. Keeps the look, re-encodes for Safari."""
    if LUMA_SLOWDOWN <= 1:
        return src
    stream = ffmpeg.filter(ffmpeg.input(src), "setpts", f"{LUMA_SLOWDOWN}*PTS")
    stream = ffmpeg.output(stream, dest, vcodec="libx264", pix_fmt="yuv420p", movflags="+faststart")
    try:
        ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
    except ffmpeg.Error as e:
        raise RuntimeError(f"ffmpeg slow-down failed: {e.stderr.decode()[-500:]}")
    return dest




def call_make_story(message_id):
    res = requests.post(
        f"{SUPABASE_URL}/functions/v1/make-story",
        json={"message_id": message_id},
        headers=headers({"Content-Type": "application/json"}),
        timeout=180,
    )
    try:
        detail = res.json().get("story_error") or res.json().get("error") or res.text
    except ValueError:
        detail = res.text
    return res.status_code, str(detail)[:500]



def render_scene(label, n, prompt, out_dir, raw_dir):
    """Luma, look, slow-down and thumbnail for one beat. Returns (video, thumb) or None on failure."""
    start = time.monotonic()
    try:
        raw = generate_with_retry(prompt, os.path.join(raw_dir, f"raw-{n}.mp4"))
        look = process_video(raw, os.path.join(raw_dir, f"look-{n}.mp4"))
        video = slow_video(look, os.path.join(out_dir, f"scene-{n}.mp4"))
        thumb = process_thumbnail(video, os.path.join(out_dir, f"scene-{n}.jpg"))
        log.info("[%s] scene %d done in %d ms", label, n, (time.monotonic() - start) * 1000)
        return video, thumb
    except Exception as e:
        log.error("[%s] scene %d failed: %s", label, n, " ".join(str(e).split())[:300])
        return None


def render_scenes(label, scenes, out_dir, raw_dir):
    """Render every beat in parallel. Returns [(video, thumb, ok)], reusing a neighbour's media for failed beats."""
    with ThreadPoolExecutor(max_workers=max(1, min(5, LUMA_CONCURRENCY, len(scenes)))) as pool:
        jobs = [pool.submit(render_scene, label, i + 1, sc["prompt"], out_dir, raw_dir) for i, sc in enumerate(scenes)]
        results = [j.result() for j in jobs]
    if not any(results):
        raise RuntimeError(f"all {len(scenes)} Luma scenes failed")
    first = next(r for r in results if r)
    media, last = [], first
    for r in results:
        last = r or last
        media.append((last[0], last[1], r is not None))
    return media


def fallback(msg, reason, meta):
    reason = " ".join(reason.split())[:300]
    if STORY_FALLBACK != "images":
        log.error("[%s] video failed, no fallback configured: %s", msg["id"], reason)
        write_story(msg["id"], {**meta, "status": "error", "error": f"video: {reason}"}, only_if_generating=True)
        return
    log.warning("[%s] video failed, falling back to make-story: %s", msg["id"], reason)
    code, text = call_make_story(msg["id"])
    if code == 200:
        story = get_message(msg["id"]).get("story") or {}
        story.update({k: v for k, v in meta.items() if k in ("world", "title_es")})
        story["video_error"] = reason
        write_story(msg["id"], story)
        log.info("[%s] make-story fallback done", msg["id"])
        return
    log.error("[%s] make-story failed (%s): %s", msg["id"], code, text)
    write_story(
        msg["id"],
        {"status": "error", "error": f"video: {reason}; make-story ({code}): {text[:200]}"},
        only_if_generating=True,
    )


def process(msg, prior_story=None):
    mid, thread = msg["id"], msg["thread_id"]
    t = Timer(mid)
    meta = {}
    try:
        plan = make_scenes(msg, (msg.get("sender") or {}).get("role", "elder"))
        meta = {k: (prior_story or {}).get(k) or plan[k] for k in ("title", "title_es")}
        meta["world"] = plan["world"]
        t.step("llm")
        log.info("[%s] world: %s", mid, plan["world"])
        with tempfile.TemporaryDirectory() as tmp:
            media = render_scenes(mid, plan["scenes"], tmp, tmp)
            t.step("luma+ffmpeg")
            uploaded = {}
            for n, (video, thumb, ok) in enumerate(media, 1):
                if ok:
                    uploaded[video] = (
                        upload(f"{thread}/{mid}-{n}.mp4", video, "video/mp4"),
                        upload(f"{thread}/{mid}-{n}.jpg", thumb, "image/jpeg"),
                    )
            t.step("upload")
        scenes = []
        for sc, (video, _, ok) in zip(plan["scenes"], media):
            scenes.append({**sc, "video_path": uploaded[video][0], "thumb_path": uploaded[video][1]})
        reused = sum(1 for m in media if not m[2])
        if reused:
            log.warning("[%s] %d scene(s) reuse the previous clip", mid, reused)
        story = {**meta, "scenes": scenes, "video_path": scenes[0]["video_path"], "thumb_path": scenes[0]["thumb_path"]}
        if prior_story and prior_story.get("image_paths"):
            story["image_paths"] = prior_story["image_paths"]
        write_story(mid, story)
        log.info("[%s] story done in %d ms", mid, t.total())
    except Exception as e:
        try:
            fallback(msg, str(e), meta)
        except Exception as fe:
            log.error("[%s] fallback crashed: %s", mid, fe)
            try:
                write_story(mid, {"status": "error", "error": f"video: {e}; fallback: {fe}"[:500]}, only_if_generating=True)
            except Exception as we:
                log.error("[%s] could not record error: %s", mid, we)
        log.info("[%s] finished with fallback in %d ms", mid, t.total())


def run_forever():
    log.info("Worker %s polling %s every %.0f s", WORKER_ID, SUPABASE_URL, POLL_SECONDS)
    while True:
        try:
            fix_webm()
            for msg in find_work():
                prior = msg.get("story")
                row = claim(msg)
                if row is None:
                    log.info("[%s] claimed by another worker", msg["id"])
                    continue
                log.info("[%s] claimed%s", msg["id"], " (stale)" if prior else "")
                process(row, prior if prior and prior.get("status") != "generating" else None)
        except Exception as e:
            log.error("Poll failed: %s", e)
        time.sleep(POLL_SECONDS)


def run_once(message_id):
    msg = get_message(message_id)
    if not msg.get("transcript"):
        raise SystemExit(f"Message {message_id} has no transcript")
    prior = msg.get("story")
    row = claim(msg, force=True)
    process(row, prior)
    print(json.dumps(get_message(message_id).get("story"), indent=2))


def run_look(src):
    base = os.path.splitext(src)[0]
    out, thumb = base + ".look.mp4", base + ".jpg"
    if os.path.abspath(out) == os.path.abspath(src):
        raise SystemExit("Refusing to overwrite the input")
    t = Timer("look")
    process_video(src, out)
    process_thumbnail(out, thumb)
    t.step("ffmpeg")
    print(out)
    print(thumb)


def run_luma_check():
    """One real Luma generation plus the look, no Supabase needed. Run this first when the key arrives."""
    prompt = ("A warm 1960s kitchen in Monterrey at dawn, steam rising from a clay pot of tamales, "
              "flour on a worn wooden table, soft window light, nostalgic, painterly, no text, no faces")
    t = Timer("luma-check")
    out_dir = os.path.abspath("luma-check")
    os.makedirs(out_dir, exist_ok=True)
    raw = generate_with_retry(prompt, os.path.join(out_dir, "raw.mp4"))
    t.step("luma")
    look = process_video(raw, os.path.join(out_dir, "look.mp4"))
    thumb = process_thumbnail(look, os.path.join(out_dir, "thumb.jpg"))
    t.step("ffmpeg")
    print(f"OK style={LUMA_API_STYLE} model={LUMA_MODEL} aspect={LUMA_ASPECT_RATIO} resolution={LUMA_RESOLUTION} duration={LUMA_DURATION}")
    print(look)
    print(thumb)


# About 60 s of narration at a calm pace, for --scenes-check.
SAMPLE_STORY = {
    "source_lang": "es",
    "transcript": (
        "Cuando yo tenía nueve años, vivíamos en una casita de adobe en las afueras de Monterrey. "
        "Cada diciembre, mi mamá se levantaba antes del sol para hacer tamales. "
        "Yo la ayudaba a untar la masa en las hojas, y siempre me regañaba porque ponía demasiada. "
        "La cocina se llenaba de vapor y olía a chile y a canela. "
        "Mi papá llegaba del campo con las manos frías y se las calentaba sobre la olla. "
        "En la tarde, todos los vecinos venían con sus platos, y mi mamá le daba a cada uno lo que tenía, "
        "aunque a nosotros nos quedara poco. "
        "Una vez le pregunté por qué regalaba tanto, y me dijo que la comida que se comparte nunca se acaba. "
        "Esa noche nos sentamos afuera, bajo un cielo lleno de estrellas, con las manos todavía oliendo a masa. "
        "Mi papá tocó la guitarra y mi mamá cantó bajito una canción de su pueblo. "
        "Ya no tengo esa casa, ni a ellos, pero cada diciembre hago tamales y pongo demasiada masa, "
        "y me acuerdo de que lo que se comparte nunca se acaba."
    ),
    "translation": (
        "When I was nine years old, we lived in a little adobe house on the edge of Monterrey. "
        "Every December, my mother got up before the sun to make tamales. "
        "I helped her spread the masa on the husks, and she always scolded me because I used too much. "
        "The kitchen filled with steam and smelled of chile and cinnamon. "
        "My father came in from the fields with cold hands and warmed them over the pot. "
        "In the afternoon, all the neighbors came with their plates, and my mother gave each one what she had, "
        "even if there was little left for us. "
        "Once I asked her why she gave so much away, and she told me that food you share never runs out. "
        "That night we sat outside, under a sky full of stars, our hands still smelling of masa. "
        "My father played the guitar and my mother sang a song from her village, very softly. "
        "I don't have that house anymore, or them, but every December I make tamales and I use too much masa, "
        "and I remember that what you share never runs out."
    ),
}


def run_scenes_check():
    """make_scenes plus SCENES real Luma clips on the sample story, no Supabase. Costs SCENES clips."""
    t = Timer("scenes-check")
    plan = make_scenes(SAMPLE_STORY, "elder")
    t.step("llm")
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    out_dir = os.path.abspath("luma-check")
    os.makedirs(out_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        media = render_scenes("scenes-check", plan["scenes"], out_dir, tmp)
    t.step("luma+ffmpeg")
    print(f"OK {sum(1 for m in media if m[2])}/{len(media)} scenes rendered, model={LUMA_MODEL} style={LUMA_API_STYLE}")
    for video, thumb, ok in media:
        print(video if ok else f"{video} (reused)")


def run_demo_clips(ids):
    """Renders and uploads one clip per scene of the given canned stories (s1) or replies (r1)."""
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "demo-stories.json")) as f:
        data = json.load(f)
    canned = {st["id"]: st["scenes"] for st in data["stories"]}
    canned.update({f"r{i + 1}": r["scenes"] for i, r in enumerate(data["replies"])})
    # Reply scenes have no prompt; each one shows a story scene's image, so it takes that scene's prompt.
    by_image = {sc["image"]: sc["prompt"] for scenes in canned.values() for sc in scenes if sc.get("prompt")}
    jobs = [(f"{cid}-{n}", sc.get("prompt") or by_image[sc["image"]]) for cid in ids for n, sc in enumerate(canned[cid], 1)]
    with tempfile.TemporaryDirectory() as tmp:
        media = render_scenes("demo-clips", [{"prompt": p} for _, p in jobs], tmp, tmp)
        if not all(ok for _, _, ok in media):
            raise SystemExit("Some clips failed, nothing uploaded")
        for (name, _), (video, thumb, _) in zip(jobs, media):
            print(upload(f"demo/{name}.mp4", video, "video/mp4"), upload(f"demo/{name}.jpg", thumb, "image/jpeg"))


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
    parser = argparse.ArgumentParser(description="Kinn story worker")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--once", metavar="MESSAGE_ID", help="process one message now, even if it already has a story")
    group.add_argument("--look", metavar="INPUT_MP4", help="apply the Dream Recorder look to a local video")
    group.add_argument("--luma-check", action="store_true", help="one real Luma generation plus the look, to verify the key and settings")
    group.add_argument("--scenes-check", action="store_true", help="LLM beats plus SCENES real Luma clips on a sample story, no Supabase")
    group.add_argument("--demo-clips", nargs="+", metavar="ID", help="Luma clips for canned demo scenes (s1, r1), uploaded to videos/demo/")
    args = parser.parse_args()
    if args.demo_clips:
        run_demo_clips(args.demo_clips)
    elif args.scenes_check:
        run_scenes_check()
    elif args.luma_check:
        run_luma_check()
    elif args.look:
        run_look(args.look)
    elif args.once:
        run_once(args.once)
    else:
        run_forever()


if __name__ == "__main__":
    main()
