"""Kinn story worker.

Watches Supabase for ready elder messages, splits each story into SCENES beats
with one LLM call, renders one Dream Recorder style Luma clip per beat (ffmpeg
look plus a gentle slow-down), uploads them and writes messages.story with
story.scenes. Retries Luma on failure; the make-story images fallback is off
unless STORY_FALLBACK=images.

  python main.py                     poll forever
  python main.py --once <message_id> process one message now
  python main.py --look <input.mp4>  apply the ffmpeg look to a local file
  python main.py --luma-check        one real Luma clip, no Supabase
  python main.py --scenes-check      LLM beats plus SCENES real Luma clips on a sample story, no Supabase
"""

import argparse
import json
import logging
import os
import re
import socket
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import ffmpeg
import requests

log = logging.getLogger("story-worker")


def env(name, default=""):
    value = os.environ.get(name, "").strip()
    return value or default


def require_env(name):
    value = env(name)
    if not value:
        raise RuntimeError(f"Missing env {name}")
    return value


SUPABASE_URL = env("SUPABASE_URL", "http://127.0.0.1:54321").rstrip("/")
POLL_SECONDS = float(env("POLL_SECONDS", "5"))
STALE_MINUTES = float(env("CLAIM_STALE_MINUTES", "10"))
WORKER_ID = f"{socket.gethostname()}:{os.getpid()}"

# "agents" is the Luma Agents API (luma-api- keys); "dream_machine" is the older API.
LUMA_API_STYLE = env("LUMA_API_STYLE", "agents")
_AGENTS = LUMA_API_STYLE == "agents"
LUMA_API_URL = env(
    "LUMA_API_URL", "https://agents.lumalabs.ai/v1" if _AGENTS else "https://api.lumalabs.ai/dream-machine/v1"
).rstrip("/")
LUMA_GENERATIONS_ENDPOINT = env("LUMA_GENERATIONS_ENDPOINT", f"{LUMA_API_URL}/generations")
LUMA_MODEL = env("LUMA_MODEL", "ray-3.2" if _AGENTS else "ray-flash-2")
LUMA_ASPECT_RATIO = env("LUMA_ASPECT_RATIO", "21:9")
LUMA_RESOLUTION = env("LUMA_RESOLUTION", "540p")
LUMA_DURATION = env("LUMA_DURATION", "5s")
LUMA_POLL_INTERVAL = float(env("LUMA_POLL_INTERVAL", "5"))
LUMA_TIMEOUT = float(env("LUMA_TIMEOUT", "240"))
LUMA_RETRIES = int(env("LUMA_RETRIES", "2"))
SCENES = int(env("SCENES", "5"))
# The Luma Agents account allows 4 concurrent generations; a 5th gets HTTP 429 and waits for a slot.
LUMA_CONCURRENCY = int(env("LUMA_CONCURRENCY", "4"))
LUMA_SLOWDOWN = float(env("LUMA_SLOWDOWN", "2.0"))  # setpts factor, 2.0 turns a 5 s clip into about 10 s
STORY_FALLBACK = env("STORY_FALLBACK", "none")  # "images" calls make-story when Luma fails

FFMPEG_BRIGHTNESS = float(env("FFMPEG_BRIGHTNESS", "0.03"))
FFMPEG_VIBRANCE = float(env("FFMPEG_VIBRANCE", "0.25"))
FFMPEG_DENOISE_THRESHOLD = float(env("FFMPEG_DENOISE_THRESHOLD", "20"))
FFMPEG_BILATERAL_SIGMA = float(env("FFMPEG_BILATERAL_SIGMA", "12"))
FFMPEG_NOISE_STRENGTH = float(env("FFMPEG_NOISE_STRENGTH", "34"))

DEFAULT_MODELS = {
    "openai": "gpt-4o",
    "anthropic": "claude-opus-5-5",
    "meta": "muse-spark-1.3",
}

# Adapted from Dream Recorder's GPT_SYSTEM_PROMPT (Copyright 2025 Modem, MIT), dreams turned into memories.
SYSTEM_PROMPT = (
    "You are a creative video prompt engineer specializing in Luma Dream Machine. "
    "You receive a grandmother's spoken memory (the original transcript) and its English translation. "
    "Split the story into exactly {n} consecutive beats, in order. "
    "For each beat, text_en is copied word for word from the English translation and text_es is copied word for word "
    "from the original transcript. Do not paraphrase, fix or skip anything: the {n} text_en excerpts joined together "
    "must equal the whole translation, and the {n} text_es excerpts joined together must equal the whole transcript. "
    "First write one world line that fixes the characters (described without faces), the place, the era and the color palette. "
    "Then for each beat write a video prompt: a single, succinct cinematic sentence for a wide 21:9 frame that restates "
    "the world line and shows what happens in that beat, so all {n} clips feel like one film. "
    "Be specific about useful visual elements and emotional tone: the place, the light, the objects, "
    "the textures, the weather and the feeling of the moment. "
    "The look is warm, nostalgic and painterly, like a faded memory. "
    "Never include on-screen text, letters or signs, and never show close-up faces "
    "(show people from behind, at a distance, or as small figures in the scene). "
    "Also write a short warm title in English (under 8 words) and the same title in Spanish. "
    'Respond with only a JSON object: {{"title": "...", "title_es": "...", "world": "...", '
    '"scenes": [{{"text_en": "...", "text_es": "...", "prompt": "..."}}]}}'
)


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


# Supabase REST and storage


def headers(extra=None):
    key = require_env("SUPABASE_SERVICE_ROLE_KEY")
    h = {"apikey": key, "Authorization": f"Bearer {key}"}
    h.update(extra or {})
    return h


def rest(method, params, body=None):
    res = requests.request(
        method,
        f"{SUPABASE_URL}/rest/v1/messages",
        params=params,
        json=body,
        headers=headers({"Prefer": "return=representation"}),
        timeout=30,
    )
    if not res.ok:
        raise RuntimeError(f"Supabase {method} failed ({res.status_code}): {res.text[:300]}")
    return res.json()


ELDER_READY = [
    ("select", "*,sender:profiles!inner(role)"),
    ("sender.role", "eq.elder"),
    ("status", "eq.ready"),
    ("transcript", "not.is.null"),
    ("order", "created_at.asc"),
    ("limit", "5"),
]


def find_work():
    fresh = rest("GET", ELDER_READY + [("story", "is.null")])
    stale_before = (datetime.now(timezone.utc) - timedelta(minutes=STALE_MINUTES)).isoformat()
    stale = rest(
        "GET",
        ELDER_READY + [("story->>status", "eq.generating"), ("story->>claimed_at", "lt." + stale_before)],
    )
    return fresh + stale


def get_message(message_id):
    rows = rest("GET", [("select", "*"), ("id", "eq." + message_id)])
    if not rows:
        raise RuntimeError(f"Message {message_id} not found")
    return rows[0]


def claim(msg, force=False):
    """Atomically mark a row as generating. Returns the row, or None if another worker won."""
    params = [("id", "eq." + msg["id"])]
    story = msg.get("story")
    if not force:
        if story is None:
            params.append(("story", "is.null"))
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


def upload(path, file_path, content_type):
    with open(file_path, "rb") as f:
        res = requests.post(
            f"{SUPABASE_URL}/storage/v1/object/videos/{path}",
            data=f,
            headers=headers({"Content-Type": content_type, "x-upsert": "true"}),
            timeout=120,
        )
    if not res.ok:
        raise RuntimeError(f"Upload {path} failed ({res.status_code}): {res.text[:300]}")
    return f"videos/{path}"


# LLM


def parse_json(text):
    cleaned = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except ValueError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise RuntimeError(f"LLM did not return JSON: {text[:300]}")


def post_json(url, hdrs, body, what):
    res = requests.post(url, headers={"Content-Type": "application/json", **hdrs}, json=body, timeout=90)
    if not res.ok:
        raise RuntimeError(f"{what} failed ({res.status_code}): {res.text[:500]}")
    return res.json()


def call_llm(system, user):
    provider = env("LLM_PROVIDER", "meta").lower()
    model = env("LLM_MODEL", DEFAULT_MODELS.get(provider, DEFAULT_MODELS["meta"]))

    if provider == "anthropic":
        data = post_json(
            "https://api.anthropic.com/v1/messages",
            {
                "x-api-key": require_env("ANTHROPIC_API_KEY"),
                "anthropic-version": "2023-06-01",
                "anthropic-beta": "server-side-fallback-2026-07-01",
            },
            {
                "model": model,
                "max_tokens": 16000,
                "output_config": {"effort": "low"},
                "fallbacks": "default",
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            "Anthropic LLM",
        )
        if data.get("stop_reason") == "refusal":
            raise RuntimeError("Anthropic LLM declined the request")
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        return parse_json(text)

    is_meta = provider == "meta"
    # META_API_URL is the base (https://api.meta.ai/v1), same as the backend.
    base = env("META_API_URL", "https://api.meta.ai/v1").rstrip("/") if is_meta else "https://api.openai.com/v1"
    key = require_env("META_API_KEY") if is_meta else require_env("OPENAI_API_KEY")
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {"type": "json_object"},
    }
    # Muse Spark is a reasoning model; low effort keeps latency down.
    if is_meta:
        body["reasoning_effort"] = env("META_REASONING_EFFORT", "low")
    data = post_json(f"{base}/chat/completions", {"Authorization": f"Bearer {key}"}, body, f"{provider} LLM")
    message = ((data.get("choices") or [{}])[0] or {}).get("message") or {}
    if message.get("refusal"):
        raise RuntimeError(f"{provider} LLM refused: {str(message['refusal'])[:300]}")
    if not message.get("content"):
        raise RuntimeError(f"{provider} LLM returned no content")
    return parse_json(message["content"])


def find_beats(text, excerpts):
    """Start offsets of each excerpt in text, searched in order with flexible whitespace. None if any is missing."""
    offsets, cursor = [], 0
    for excerpt in excerpts:
        words = str(excerpt or "").split()
        if not words:
            return None
        m = re.compile(r"\s+".join(map(re.escape, words)), re.I).search(text, cursor)
        if not m:
            return None
        offsets.append(m.start())
        cursor = m.end()
    return offsets


def split_beats(text, n):
    """Fallback: n roughly equal groups of sentences (words if too few). Returns (offsets, excerpts)."""
    pieces = [m for m in re.finditer(r"\S.*?(?:[.!?]+(?=\s|$)|$)", text, re.S)]
    if len(pieces) < n:
        pieces = list(re.finditer(r"\S+", text))
    if len(pieces) < n:
        raise RuntimeError(f"Story too short for {n} scenes")
    offsets, j = [0], 0
    for k in range(1, n):
        target = len(text) * k / n
        # the piece start nearest the target, leaving at least one piece for each remaining beat
        j = min(range(j + 1, len(pieces) - (n - k) + 1), key=lambda i: abs(pieces[i].start() - target))
        offsets.append(pieces[j].start())
    bounds = offsets + [len(text)]
    return offsets, [text[bounds[i] : bounds[i + 1]].strip() for i in range(n)]


def beat_texts(text, excerpts, n, label):
    offsets = find_beats(text, excerpts)
    if offsets is None:
        log.warning("%s excerpts did not match the text, splitting evenly", label)
        return split_beats(text, n)
    # each beat runs to the next beat's start, so words the model skipped are not lost
    offsets[0] = 0
    bounds = offsets[1:] + [len(text)]
    return offsets, [text[offsets[i] : bounds[i]].strip() for i in range(n)]


def make_scenes(msg, n=None):
    n = n or SCENES
    transcript = (msg.get("transcript") or "").strip()
    translation = (msg.get("translation") or "").strip() or transcript
    user = f"Memory ({msg.get('source_lang', '')}):\n{transcript}\n\nEnglish translation:\n{translation}"
    for attempt in range(2):
        out = call_llm(SYSTEM_PROMPT.format(n=n), user)
        beats = out.get("scenes") if isinstance(out.get("scenes"), list) else []
        prompts = [str((b or {}).get("prompt") or "").strip() if isinstance(b, dict) else "" for b in beats]
        if len(beats) == n and all(prompts):
            break
        log.warning("LLM returned %d beats (want %d), attempt %d", len(beats), n, attempt + 1)
    else:
        raise RuntimeError(f"LLM did not return {n} scenes with prompts")
    world = str(out.get("world") or "").strip()
    en_off, en = beat_texts(translation, [b.get("text_en") for b in beats], n, "English")
    _, es = beat_texts(transcript, [b.get("text_es") for b in beats], n, "Spanish")
    total = max(len(translation), 1)
    starts = [round(o / total, 3) for o in en_off] + [1.0]
    starts[0] = 0.0
    scenes = [
        {"start": starts[i], "end": starts[i + 1], "text_es": es[i], "text_en": en[i], "prompt": prompts[i]}
        for i in range(n)
    ]
    title = str(out.get("title") or "A memory").strip()
    return {"title": title, "title_es": str(out.get("title_es") or title).strip(), "world": world, "scenes": scenes}


# Luma, adapted from Dream Recorder functions/video.py


def luma_headers():
    return {"accept": "application/json", "authorization": f"Bearer {require_env('LUMA_API_KEY')}"}


def luma_body(prompt):
    if _AGENTS:
        return {
            "model": LUMA_MODEL,
            "type": "video",
            "prompt": prompt,
            "aspect_ratio": LUMA_ASPECT_RATIO,
            "video": {"resolution": LUMA_RESOLUTION, "duration": LUMA_DURATION},
        }
    return {
        "prompt": prompt,
        "model": LUMA_MODEL,
        "resolution": LUMA_RESOLUTION,
        "duration": LUMA_DURATION,
        "aspect_ratio": LUMA_ASPECT_RATIO,
    }


def luma_video_url(data):
    if _AGENTS:
        for item in data.get("output") or []:
            if isinstance(item, dict) and item.get("type") == "video" and item.get("url"):
                return item["url"]
        return None
    assets = data.get("assets") or {}
    return assets.get("video") or assets.get("url") or (data.get("result") or {}).get("url")


def generate_video(prompt, dest):
    res = requests.post(
        LUMA_GENERATIONS_ENDPOINT,
        headers={**luma_headers(), "content-type": "application/json"},
        json=luma_body(prompt),
        timeout=60,
    )
    if res.status_code not in (200, 201):
        raise RuntimeError(f"Luma API error ({res.status_code}): {res.text[:500]}")
    gen_id = res.json().get("id")
    if not gen_id:
        raise RuntimeError("Luma returned no generation id")
    log.info("Luma generation %s started", gen_id)

    deadline = time.monotonic() + LUMA_TIMEOUT
    video_url = None
    while time.monotonic() < deadline:
        time.sleep(LUMA_POLL_INTERVAL)
        status = requests.get(f"{LUMA_API_URL}/generations/{gen_id}", headers=luma_headers(), timeout=30)
        if status.status_code not in (200, 201):
            log.warning("Luma status check %s: %s", status.status_code, status.text[:200])
            continue
        data = status.json()
        state = data.get("state")
        if state in ("completed", "succeeded"):
            video_url = luma_video_url(data)
            if not video_url:
                raise RuntimeError("Luma completed without a video url")
            break
        if state in ("failed", "error"):
            reason = data.get("failure_reason") or data.get("error") or "unknown"
            code = f" [{data['failure_code']}]" if data.get("failure_code") else ""
            raise RuntimeError(f"Luma generation failed{code}: {reason}")
        # any other state (queued, dreaming, processing...) is still pending
    if not video_url:
        raise RuntimeError(f"Luma timed out after {int(LUMA_TIMEOUT)} s")

    with requests.get(video_url, stream=True, timeout=120) as dl:
        dl.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in dl.iter_content(chunk_size=65536):
                f.write(chunk)
    return dest


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


# Pipeline


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


def generate_with_retry(prompt, dest):
    for attempt in range(LUMA_RETRIES + 1):
        try:
            return generate_video(prompt, dest)
        except Exception as e:
            if attempt == LUMA_RETRIES:
                raise
            log.warning("Luma attempt %d failed, retrying: %s", attempt + 1, e)
            # a concurrency 429 clears when another clip finishes, about 30 to 45 s
            time.sleep(30 if "(429)" in str(e) else 5)


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
        plan = make_scenes(msg)
        meta = {k: plan[k] for k in ("title", "title_es", "world")}
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
    plan = make_scenes(SAMPLE_STORY)
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


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
    parser = argparse.ArgumentParser(description="Kinn story worker")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--once", metavar="MESSAGE_ID", help="process one message now, even if it already has a story")
    group.add_argument("--look", metavar="INPUT_MP4", help="apply the Dream Recorder look to a local video")
    group.add_argument("--luma-check", action="store_true", help="one real Luma generation plus the look, to verify the key and settings")
    group.add_argument("--scenes-check", action="store_true", help="LLM beats plus SCENES real Luma clips on a sample story, no Supabase")
    args = parser.parse_args()
    if args.scenes_check:
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
