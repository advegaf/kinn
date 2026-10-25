# Hearth backend

Supabase project for Hearth. Schema, storage and edge functions follow `../docs/CONTRACT.md`.

```
backend/
  supabase/config.toml                  project config (verify_jwt off for all 3 functions)
  supabase/migrations/*_init.sql        tables, permissive RLS, realtime on messages, audio + images buckets
  supabase/functions/process-message    STT, LLM translation + notes, TTS in sender's voice
  supabase/functions/enroll-voice       ElevenLabs instant voice clone, writes profiles.voice_id
  supabase/functions/make-story         3 still images, optional fallback for the story worker
  supabase/functions/_shared            CORS, timing, callLLM, provider fetch helpers
  scripts/smoke.sh, scripts/smoke.ts    H0 end to end test
  .env.example                          every secret name
```

All commands below run from `backend/`.

## Prereqs

- Supabase CLI (`brew install supabase/tap/supabase`), Deno 2.
- For local: Docker running (`colima start` on this machine, or Docker Desktop).
- `[analytics]` is disabled in `config.toml` because its log container fails to mount the Docker socket under colima. Turn it back on if you use Docker Desktop and want local function logs in Studio. `supabase functions serve` still prints logs in its terminal.

## Secrets

```sh
cp .env.example .env
# fill in ELEVENLABS_API_KEY, META_API_KEY, FALLBACK_VOICE_ID at minimum
```

`FALLBACK_VOICE_ID` is any stock ElevenLabs voice id (copy one from the ElevenLabs Voices page). It is used until a profile has enrolled its own voice.

## Local

```sh
supabase start                 # first run pulls images, takes a few minutes
supabase db reset              # applies migrations from scratch
supabase status                # prints API URL, anon key, service role key, Studio URL
```

`supabase start` serves the edge functions too, but to be sure they get your secrets, run them yourself in a second terminal:

```sh
supabase functions serve --env-file .env
```

Smoke test (second terminal):

```sh
scripts/smoke.sh path/to/spanish.m4a           # elder speaks Spanish, family hears English
scripts/smoke.sh path/to/english.m4a family    # family speaks English, elder hears Spanish
```

With no `SUPABASE_URL` set, `smoke.sh` reads the local URL and anon key from `supabase status`. It prints transcript, translation, cultural notes, ask_about, the public URL of the translated mp3 and the latency. Exit code 0 means status `ready`.

No test audio handy? On a Mac:

```sh
say -v Paulina "Hola mija, ¿cómo estás? Hoy hice tamales." -o /tmp/hola.m4a --file-format=m4af --data-format=aac
scripts/smoke.sh /tmp/hola.m4a
```

## Hosted project

```sh
supabase login
supabase link --project-ref <project-ref>      # from the dashboard URL
supabase db push                               # applies migrations
grep -v '^#' .env | grep -v '=$' | grep . > .env.secrets   # drop comments and empty values
supabase secrets set --env-file .env.secrets
rm .env.secrets
supabase functions deploy process-message --no-verify-jwt
supabase functions deploy enroll-voice --no-verify-jwt
supabase functions deploy make-story --no-verify-jwt
```

`supabase secrets set` rejects names starting with `SUPABASE_`. Those are provided to functions automatically. Only the function secrets go in `.env`.

Smoke test against hosted (anon key or `sb_publishable_` key from Project Settings, API Keys):

```sh
SUPABASE_URL=https://<project-ref>.supabase.co SUPABASE_ANON_KEY=<anon or publishable key> \
  scripts/smoke.sh path/to/spanish.m4a
```

Logs with the per step timings: Dashboard, Edge Functions, process-message, Logs. Each run prints lines like `[process-message <id>] stt: 1450 ms (total 1720 ms)`.

## How the app uses it

1. Upload original audio to bucket `audio` at `{thread_id}/{message_id}.m4a`.
2. Insert the `messages` row with that `id`, `status = 'uploaded'`.
3. POST `functions/v1/process-message` with `{ "message_id": "..." }`. Response is the updated row. On failure the response is still HTTP 200 with `status = 'error'` and `error` set, and the same row is broadcast over realtime.
4. Play `audio/{translated_path}` from `/storage/v1/object/public/audio/<translated_path>`.

`enroll-voice` returns `{ "voice_id": "..." }` on success and `{ "error": "..." }` with HTTP 500 on failure (profiles has no status column).

`make-story` is optional. The story worker (`../story-worker/`) makes the 5 scene Luma films; it calls `make-story` only when every clip fails and `STORY_FALLBACK=images` is set. `make-story` writes `story = { title, image_paths }`. Each image path is stored as `images/{thread_id}/{message_id}-{n}.png`, following the `"images/..."` example in the contract, so the public URL is `/storage/v1/object/public/<image_path>`. On failure it writes `error` but leaves `status` alone so a ready message stays playable.

## Providers

Defaults: ElevenLabs Scribe for STT, Meta Muse Spark for the LLM, Meta Muse Image for make-story, ElevenLabs for TTS. OpenAI and Anthropic stay as options; they only need a key if you switch to them. `OPENAI_API_KEY` is not required.

- STT, `STT_PROVIDER=elevenlabs` (default): `POST https://api.elevenlabs.io/v1/speech-to-text` with header `xi-api-key`, multipart fields `file`, `model_id` (default `scribe_v2`) and `language_code`. The transcript is in `text`. `STT_PROVIDER=openai` uses `gpt-4o-transcribe`.
- LLM, `LLM_PROVIDER=meta` (default): OpenAI compatible `POST {META_API_URL}/chat/completions` with `Authorization: Bearer $META_API_KEY`. `META_API_URL` is the base URL, default `https://api.meta.ai/v1`. Model `muse-spark-1.3`, `response_format: {"type": "json_object"}`, and `reasoning_effort` from `META_REASONING_EFFORT` (default `low`, for latency). A null `content` or a `refusal` in the reply becomes a clear error.
- LLM, `openai`: chat completions with `response_format: json_object`, default `gpt-4o`. `anthropic`: Messages API, default `claude-opus-5-5` at `effort: low`, with server side refusal fallback (`fallbacks: "default"`).
- Images, `IMAGE_PROVIDER=meta` (default): `POST {META_API_URL}/images/generations` with model `muse-image-1.0`, PNG returned as base64. `IMAGE_PROVIDER=openai` uses `gpt-image-1`.
- TTS: ElevenLabs, `TTS_MODEL` default `eleven_multilingual_v2`. `voice_settings` come from `TTS_STABILITY` (0.45), `TTS_SIMILARITY` (0.85, sent as `similarity_boost`), `TTS_STYLE` (0.15) and `TTS_SPEAKER_BOOST` (true). Lower stability sounds more natural; raise it if a cloned voice drifts. See `docs/VOICES.md`.

`STT_MODEL`, `LLM_MODEL` and `IMAGE_MODEL` override the model; empty means the provider default.

Sources:

- Meta overview, base URL and auth: https://dev.meta.ai/docs/
- Meta models: https://dev.meta.ai/docs/models
- Meta chat completions schema: https://dev.meta.ai/docs/api-reference/chat-completions/schemas
- Meta images schema: https://dev.meta.ai/docs/api-reference/images/schemas
- Meta structured output: https://dev.meta.ai/docs/structured-output
- ElevenLabs speech to text: https://elevenlabs.io/docs/api-reference/speech-to-text/convert
- ElevenLabs models: https://elevenlabs.io/docs/overview/models

## Verify

Verified:

- ElevenLabs Scribe STT on the hosted Supabase project, and on the local stack with m4a and webm clips.

Not yet verified:

- Meta LLM (`muse-spark-1.3`) and image calls with a real `META_API_KEY`. The request shapes follow the docs above but have not run end to end, because we do not have a Meta key yet.
- Real ElevenLabs TTS through the whole `process-message` pipeline (it runs after the LLM step, so it waits on the Meta key too). Also the `output_format=mp3_44100_128` query param and the `voices/add` multipart fields `name` and `files`. Instant voice cloning needs a paid ElevenLabs tier.
- `gpt-image-1` with `quality: "low"` and `size: "1024x1024"`, only used with `IMAGE_PROVIDER=openai`.
- Whether `supabase start` alone loads `.env` into functions. The README uses `supabase functions serve --env-file .env` to be explicit.
- End to end latency. The 8 s target has not been measured. Biggest levers: `META_REASONING_EFFORT=low`, `TTS_MODEL=eleven_flash_v2_5`, shorter clips.
