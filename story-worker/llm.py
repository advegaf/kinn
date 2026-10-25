import json
import os

import requests


def env(name, default=""):
    value = os.environ.get(name, "").strip()
    return value or default


def require_env(name):
    value = env(name)
    if not value:
        raise RuntimeError(f"Missing env {name}")
    return value


DEFAULT_MODELS = {
    "openai": "gpt-4o",
    "anthropic": "claude-opus-5-5",
    "meta": "muse-spark-1.3",
    "codex": "gpt-6-luna",
}


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
    if provider == "codex":
        # CODEX_RELAY_URL is the codex-relay base, for example https://<host>.ts.net/v1, same as the backend.
        base, key = require_env("CODEX_RELAY_URL").rstrip("/"), require_env("CODEX_RELAY_SECRET")
    elif is_meta:
        # META_API_URL is the base (https://api.meta.ai/v1), same as the backend.
        base, key = env("META_API_URL", "https://api.meta.ai/v1").rstrip("/"), require_env("META_API_KEY")
    else:
        base, key = "https://api.openai.com/v1", require_env("OPENAI_API_KEY")
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
