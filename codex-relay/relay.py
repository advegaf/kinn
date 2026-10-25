"""Kinn codex relay.

Gives the edge functions and the story worker LLM text and images from a ChatGPT
subscription, with no API key. It speaks the two OpenAI routes the clients use
and runs `codex exec` for each request:

  POST /v1/chat/completions   {"model", "messages"}  -> {"choices": [{"message": {"content"}}]}
  POST /v1/images/generations {"prompt"}             -> {"data": [{"b64_json"}]}
  GET  /health                                       -> {"ok": true}

Every POST must send "Authorization: Bearer $RELAY_SECRET". The token in
~/.codex/auth.json stays with the Codex CLI; the relay never reads it.
"""

import base64
import glob
import hmac
import json
import logging
import os
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger("codex-relay")


def env(name, default=""):
    return os.environ.get(name, "").strip() or default


SECRET = env("RELAY_SECRET")
HOST = env("RELAY_HOST", "127.0.0.1")
PORT = int(env("RELAY_PORT", "8790"))
CODEX = env("CODEX_BIN", "codex")
CODEX_HOME = env("CODEX_HOME", os.path.expanduser("~/.codex"))
MODEL = env("CODEX_MODEL", "gpt-6-luna")
EFFORT = env("CODEX_EFFORT", "low")
# The clients give up after 90 s, so a text call must end before that.
TEXT_TIMEOUT = float(env("RELAY_TEXT_TIMEOUT", "75"))
IMAGE_TIMEOUT = float(env("RELAY_IMAGE_TIMEOUT", "140"))
MAX_BODY = 1_000_000
SLOTS = threading.BoundedSemaphore(int(env("RELAY_CONCURRENCY", "4")))

TEXT_RULES = "Reply with only the JSON object the instructions ask for. Do not run commands, read files or use tools."
IMAGE_RULES = (
    "Make exactly one image with your built in image generation tool, from the prompt below. "
    "Do not run commands, write code or read files. When the image is made, reply with only the word done.\n\nPrompt:\n"
)


class RelayError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def run_codex(prompt, model, timeout):
    """Runs one ephemeral codex exec in an empty read-only folder. Returns (thread_id, last agent message)."""
    with tempfile.TemporaryDirectory(prefix="codex-relay-") as work:
        cmd = [
            CODEX, "exec", "--json", "--ephemeral", "--ignore-user-config", "--ignore-rules",
            "--skip-git-repo-check", "-s", "read-only", "-C", work,
            "-m", model, "-c", f"model_reasoning_effort={EFFORT}", "-",
        ]
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True
        )
        try:
            out, err = proc.communicate(prompt, timeout=timeout)
        except subprocess.TimeoutExpired:
            # codex starts child processes, so stop the whole group
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
            raise RelayError(504, f"codex exec timed out after {int(timeout)} s")
    thread_id, reply, failure = "", "", ""
    for line in out.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        item = event.get("item") or {}
        if event.get("type") == "thread.started":
            thread_id = event.get("thread_id", "")
        elif event.get("type") == "item.completed" and item.get("type") == "agent_message":
            reply = item.get("text", "")
        elif event.get("type") in ("error", "turn.failed"):
            failure = json.dumps(event)[:500]
    if proc.returncode != 0 or failure:
        raise RelayError(502, f"codex exec failed ({proc.returncode}): {failure or err.strip()[-500:]}")
    return thread_id, reply


def chat(body):
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        raise RelayError(400, "messages is required")
    parts = [str(m.get("content") or "") for m in messages if isinstance(m, dict)]
    _, reply = run_codex("\n\n".join(parts + [TEXT_RULES]), str(body.get("model") or MODEL), TEXT_TIMEOUT)
    if not reply.strip():
        raise RelayError(502, "codex returned no reply")
    return {"object": "chat.completion", "choices": [{"index": 0, "message": {"role": "assistant", "content": reply}}]}


def image(body):
    prompt = str(body.get("prompt") or "").strip()
    if not prompt:
        raise RelayError(400, "prompt is required")
    thread_id, _ = run_codex(IMAGE_RULES + prompt, MODEL, IMAGE_TIMEOUT)
    folder = os.path.join(CODEX_HOME, "generated_images", thread_id)
    try:
        files = sorted(glob.glob(os.path.join(folder, "*.png")), key=os.path.getmtime) if thread_id else []
        if not files:
            raise RelayError(502, "codex made no image")
        with open(files[-1], "rb") as f:
            data = base64.b64encode(f.read()).decode()
    finally:
        if thread_id:
            shutil.rmtree(folder, ignore_errors=True)
    return {"data": [{"b64_json": data}]}


ROUTES = {"/v1/chat/completions": (chat, TEXT_TIMEOUT), "/v1/images/generations": (image, IMAGE_TIMEOUT)}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def send(self, status, payload):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        if status != 200:
            # the request body may be unread, so it must not be parsed as the next request
            self.send_header("Connection", "close")
            self.close_connection = True
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            self.send(200, {"ok": True})
        else:
            self.send(404, {"error": {"message": "not found"}})

    def do_POST(self):
        start = time.monotonic()
        route = ROUTES.get(self.path)
        status = 200
        try:
            if not route:
                raise RelayError(404, "not found")
            token = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            if not hmac.compare_digest(token.encode(), SECRET.encode()):
                raise RelayError(401, "bad relay secret")
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY:
                raise RelayError(413, "body is empty or too large")
            body = json.loads(self.rfile.read(length))
            handler, timeout = route
            if not SLOTS.acquire(timeout=timeout):
                raise RelayError(503, "relay is busy")
            try:
                payload = handler(body)
            finally:
                SLOTS.release()
        except RelayError as e:
            status, payload = e.status, {"error": {"message": str(e)}}
        except (ValueError, AttributeError) as e:
            status, payload = 400, {"error": {"message": f"bad request: {e}"}}
        except Exception as e:
            log.exception("relay crashed")
            status, payload = 500, {"error": {"message": f"relay error: {e}"}}
        self.send(status, payload)
        log.info("%s %s %d in %d ms", self.command, self.path, status, (time.monotonic() - start) * 1000)

    def log_message(self, *args):
        pass


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if len(SECRET) < 32:
        raise SystemExit("Set RELAY_SECRET to at least 32 characters (openssl rand -hex 32)")
    if not shutil.which(CODEX):
        raise SystemExit(f"{CODEX} not found on PATH")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.daemon_threads = True
    log.info("codex relay on http://%s:%d, model %s, effort %s", HOST, PORT, MODEL, EFFORT)
    server.serve_forever()


if __name__ == "__main__":
    main()
