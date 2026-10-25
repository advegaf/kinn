import logging
import time

import requests

from llm import env, require_env

log = logging.getLogger("story-worker")

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
