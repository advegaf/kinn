# Hearth story worker

Turns grandma's spoken memories into short Dream Recorder style films: 5 scenes that change as the story is told. The Hearth (`../hearth-web/`) plays the scenes in time with her voice, and the iOS app shows them too.

It polls Supabase every 5 s for elder messages with `status = 'ready'`, a transcript and `story is null`. For each one it:

1. Claims the row by writing `story = {"status": "generating", "claimed_at": ...}` only where `story is null`, so two workers never take the same message. Claims older than 10 min are taken over.
2. Makes one LLM call that splits the story into 5 beats. Each beat gets a verbatim excerpt of the English translation (`text_en`), the matching excerpt of the Spanish transcript (`text_es`) and a 21:9 cinematic prompt. Every prompt restates one shared `world` line (characters, place, era, palette) so the clips feel like one film. If the excerpts do not match the text, the worker splits the text into 5 roughly equal sentence groups and keeps the prompts.
3. Computes each scene's `start` and `end` as 0..1 fractions of the narration from the character offset of `text_en` in the translation.
4. Sends the 5 prompts to Luma in parallel (Luma Agents API, `ray-3.2`, 21:9, 540p, 5s), at most `LUMA_CONCURRENCY` (default 4) at once because the account allows 4 concurrent generations. Each clip is polled for up to 4 min and downloaded.
5. Applies the Dream Recorder ffmpeg look, slows each clip down by `LUMA_SLOWDOWN` (default 2.0, so about 10 s) and cuts a 21:9 jpg thumbnail at 1 s.
6. Uploads `videos/{thread_id}/{message_id}-{n}.mp4` and `.jpg` (`n` from 1), then writes `story = {title, title_es, world, scenes: [{start, end, text_es, text_en, prompt, video_path, thumb_path}], video_path, thumb_path}`. The top-level paths are the first scene. Existing `image_paths` are kept.

A beat whose clip fails after `LUMA_RETRIES` retries reuses the previous scene's clip. If every clip fails, `story` becomes `{"status": "error", "error": "..."}`, unless `STORY_FALLBACK=images`, which calls the `make-story` edge function (3 images) and adds `video_error`. The message `status` column is never touched, so a failed story never hides a ready voice message.

Cost: about 5 Luma clips per story, roughly $2 to 3.50. Set `SCENES` lower to save money while testing.

Clients should treat a story with `status` of `generating` or `error` as "no story yet".

## Local

Needs Python 3.12 and ffmpeg (`brew install ffmpeg`).

```sh
cd story-worker
uv venv -p 3.12 .venv && source .venv/bin/activate   # or python3.12 -m venv .venv
pip install -r requirements.txt
cp .env.example .env    # fill in keys
set -a; source .env; set +a
```

For the local Supabase stack, use `SUPABASE_URL=http://127.0.0.1:54321` and the `SERVICE_ROLE_KEY` from `cd ../backend && supabase status -o env`. The `videos` bucket comes from `backend/supabase/migrations/20261024230000_videos.sql`.

```sh
python main.py                         # poll forever
python main.py --once <message_id>     # process one message now, even if it has a story
python main.py --look clip.mp4         # writes clip.look.mp4 and clip.jpg, no keys needed
python main.py --luma-check            # one real Luma clip, needs LUMA_API_KEY only
python main.py --scenes-check          # LLM beats plus 5 real Luma clips on a built-in 60 s story
```

`--look` is the quick way to compare the grain against Dream Recorder press stills. A test clip:

```sh
ffmpeg -f lavfi -i testsrc=size=960x410:rate=24 -t 3 test.mp4 && python main.py --look test.mp4
```

Every step logs its time in ms, for example `[<id>] scene 3 done in 45105 ms`. A 5 scene story takes about 1.5 to 2 min (4 clips at once, then the 5th).

## Running it for the demo

The worker runs on a teammate's laptop, pointed at the hosted Supabase project. Keep the Mac awake while it polls:

```sh
set -a; source .env; set +a
caffeinate -i python main.py
```

The LLM defaults to Meta `muse-spark-1.3` (`LLM_PROVIDER=meta`, `META_API_KEY`). Set `LLM_PROVIDER=openai` or `anthropic` with the matching key to switch, or `LLM_PROVIDER=codex` with `CODEX_RELAY_URL` and `CODEX_RELAY_SECRET` to use the ChatGPT subscription through `../codex-relay`.

## Fly.io (optional)

Only if nobody can keep a laptop running.

```sh
brew install flyctl && fly auth login
cd story-worker
fly launch --no-deploy --copy-config --yes    # change app name in fly.toml first if it is taken
fly secrets set \
  SUPABASE_URL=https://YOUR-PROJECT.supabase.co \
  SUPABASE_SERVICE_ROLE_KEY=... \
  META_API_KEY=... \
  LUMA_API_KEY=...
fly deploy
fly scale count worker=1 --yes
fly logs
```

The app has no HTTP service; it is a single `worker` process on a shared-cpu-1x with 1 GB. Optional secrets: `LLM_PROVIDER` (`meta`, `openai`, `anthropic`, `codex`), `CODEX_RELAY_URL`, `CODEX_RELAY_SECRET`, `LLM_MODEL`, `META_API_URL`, `META_REASONING_EFFORT`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and any `SCENES`, `LUMA_*` or `FFMPEG_*` value from `.env.example`.

Running more than one machine is safe because of the claim step, but one is enough.

## Credit

The Luma request and polling flow, the prompt and the ffmpeg look (`process_video`, `process_thumbnail`) are adapted from [Dream Recorder](https://github.com/modem-works/dream-recorder) by Modem. The thumbnail here is a 21:9 crop instead of a square, and the output adds `yuv420p` and `+faststart` so it plays in Safari and starts streaming right away.

MIT License:

```
Copyright 2025 Modem

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Check Luma

Run this after changing the Luma key or settings. It needs only `LUMA_API_KEY` (no Supabase) and makes one real 5 s clip, then applies the Dream Recorder look:

```sh
export LUMA_API_KEY=...
python main.py --luma-check      # writes luma-check/raw.mp4, look.mp4 and thumb.jpg
```

The key is for the Luma Agents API (`luma-api-...`, `LUMA_API_STYLE=agents`, `https://agents.lumalabs.ai/v1`, model `ray-3.2`). For an older Dream Machine key set `LUMA_API_STYLE=dream_machine`, which switches the URL to `https://api.lumalabs.ai/dream-machine/v1` and the model to `ray-flash-2`. If Luma rejects `21:9`, set `LUMA_ASPECT_RATIO=16:9` and rerun.

Then check a whole story. This needs the LLM key too and costs 5 clips:

```sh
python main.py --scenes-check    # prints the scenes JSON, writes luma-check/scene-{n}.mp4 and .jpg
```

Luma failures are retried `LUMA_RETRIES` times (default 2, 30 s apart after a concurrency 429). A failed story can be rerun with `--once <message_id>`.
