# Codex relay

The LLM step (translation, cultural notes, "Ask her about" prompts, story beats, summaries) and the make-story images can run on a ChatGPT subscription instead of a paid API key. `relay.py` is a small HTTP server on a machine where the Codex CLI is logged in. For each request it runs one `codex exec` in an empty read-only folder and returns the reply in the OpenAI shape that the clients already use:

- `POST /v1/chat/completions` returns the JSON object that the system prompt asks for, as `choices[0].message.content`.
- `POST /v1/images/generations` returns one PNG as `data[0].b64_json`.
- `GET /health` returns `{"ok": true}`.

Each POST must send `Authorization: Bearer $RELAY_SECRET`. The relay never reads `~/.codex/auth.json`; only the Codex CLI does.

Measured on 2026-10-25 with `gpt-6-luna` at low effort: translation of a 30 s clip in about 4 s, 5 story beats in about 10 s, one image in about 25 to 40 s.

## Run it as a user service (Linux)

Needs Python 3, the Codex CLI on `PATH` (`codex login` done) and Tailscale with Funnel.

```sh
install -D -m 644 relay.py ~/.local/share/kinn-codex-relay/relay.py
install -D -m 644 kinn-codex-relay.service ~/.config/systemd/user/kinn-codex-relay.service
(umask 077; printf 'RELAY_SECRET=%s\n' "$(openssl rand -hex 32)" > ~/.config/kinn-codex-relay.env)
systemctl --user daemon-reload
systemctl --user enable --now kinn-codex-relay
loginctl enable-linger "$USER"     # keeps it running after logout
tailscale funnel --bg 8790         # public https://<host>.<tailnet>.ts.net/ to 127.0.0.1:8790
curl https://<host>.<tailnet>.ts.net/health
```

systemd restarts the relay 2 s after a crash. Logs: `journalctl --user -u kinn-codex-relay -f`. After you change `relay.py`, run the `install` line again and `systemctl --user restart kinn-codex-relay`.

## Point the backend and the story worker at it

```sh
supabase secrets set LLM_PROVIDER=codex IMAGE_PROVIDER=codex \
  CODEX_RELAY_URL=https://<host>.<tailnet>.ts.net/v1 CODEX_RELAY_SECRET=<RELAY_SECRET>
```

Use the same `LLM_PROVIDER`, `CODEX_RELAY_URL` and `CODEX_RELAY_SECRET` in `story-worker/.env`. `LLM_MODEL` picks another Codex model, for example `gpt-6.1-sol` (better prose, about 2 to 3 times slower).

## Settings

All are optional except `RELAY_SECRET`.

| Name | Default | Use |
|---|---|---|
| `RELAY_SECRET` | none | Shared bearer secret, at least 32 characters |
| `RELAY_PORT`, `RELAY_HOST` | `8790`, `127.0.0.1` | Listen address. Funnel reaches it on localhost |
| `CODEX_MODEL` | `gpt-6-luna` | Model when the request has none, and for images |
| `CODEX_EFFORT` | `low` | Reasoning effort |
| `RELAY_TEXT_TIMEOUT`, `RELAY_IMAGE_TIMEOUT` | `75`, `140` s | The relay stops `codex exec` after this. The clients give up after 90 s |
| `RELAY_CONCURRENCY` | `4` | Codex runs at the same time. More requests wait for a free slot |

## When the relay is down

Demo mode (`hearth-web ?demo=1`, `DemoBackend.swift`) does not call the backend, so it still works. A live message gets `status = error` with the relay error text, and the Hearth shows "No se pudo enviar. Intenta otra vez."
