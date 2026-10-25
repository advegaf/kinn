import requests

from llm import env, require_env

SUPABASE_URL = env("SUPABASE_URL", "http://127.0.0.1:54321").rstrip("/")


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


def upload(path, file_path, content_type, bucket="videos"):
    with open(file_path, "rb") as f:
        res = requests.post(
            f"{SUPABASE_URL}/storage/v1/object/{bucket}/{path}",
            data=f,
            headers=headers({"Content-Type": content_type, "x-upsert": "true"}),
            timeout=120,
        )
    if not res.ok:
        raise RuntimeError(f"Upload {path} failed ({res.status_code}): {res.text[:300]}")
    return f"{bucket}/{path}"


def download(bucket, path, dest):
    res = requests.get(f"{SUPABASE_URL}/storage/v1/object/{bucket}/{path}", headers=headers(), timeout=120)
    if not res.ok:
        raise RuntimeError(f"Download {path} failed ({res.status_code}): {res.text[:300]}")
    with open(dest, "wb") as f:
        f.write(res.content)
    return dest
