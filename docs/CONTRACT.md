# Kinn: app and backend contract

Both the iOS app (`ios/`) and the Supabase backend (`backend/supabase/`) code against this file. Change it here first if anything moves.

## Roles

- `elder`: grandma. Uses the Hearth (taps the screen). Speaks `es`.
- `family`: grandkid. Uses the thread app. Speaks `en`.

Each elder and family pair shares one thread.

## Tables (Postgres, schema `public`)

```sql
profiles (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  role text not null check (role in ('elder','family')),
  lang text not null,              -- BCP-47 short code: 'es', 'en'
  voice_id text,                   -- ElevenLabs voice id after enrollment, null before
  created_at timestamptz default now()
)

threads (
  id uuid primary key default gen_random_uuid(),
  elder_id uuid references profiles(id),
  family_id uuid references profiles(id),
  created_at timestamptz default now()
)

messages (
  id uuid primary key default gen_random_uuid(),
  thread_id uuid references threads(id) not null,
  sender_id uuid references profiles(id) not null,
  source_lang text not null,
  target_lang text not null,
  original_path text not null,     -- storage path in bucket 'audio'
  transcript text,
  translation text,
  translated_path text,            -- storage path in bucket 'audio'
  cultural_notes jsonb default '[]', -- [{ "term": "mija", "note": "..." }]
  ask_about jsonb default '[]',      -- ["Ask her about ...", ...] only for messages the family receives
  story jsonb,                       -- { "title", "title_es", "world", "scenes": [...], "video_path": "videos/...", "thumb_path": "videos/...", "image_paths": ["images/..."] } (all optional, see Story worker)
  heard_at timestamptz,              -- set by the receiving device when the translated audio is played
  status text not null default 'uploaded' check (status in ('uploaded','processing','ready','error')),
  error text,
  created_at timestamptz default now()
)
```

Realtime is enabled on `messages`. Hackathon mode: no auth, the anon key can read and write. RLS is permissive. This is a demo, not production.

## Storage

- Bucket `audio` (public): `{thread_id}/{message_id}.m4a` holds the original, `{thread_id}/{message_id}-tr.mp3` holds the translation. Voice samples go in `voices/{profile_id}.m4a`.
- Bucket `images` (public): `{thread_id}/{message_id}-{n}.png`. Note: `story.image_paths` entries include the bucket prefix (`images/{thread_id}/{message_id}-{n}.png`). Strip `images/` before building a public URL from the `images` bucket. `original_path` and `translated_path` do not include a bucket prefix.

- Bucket `videos` (public): `{thread_id}/{message_id}-{n}.mp4` and `{thread_id}/{message_id}-{n}.jpg`, one pair per scene, `n` from 1. Older stories use `{thread_id}/{message_id}.mp4` and `.jpg`. Every `video_path` and `thumb_path` in `story` includes the `videos/` prefix, same rule as images.
- Original audio may be `.m4a` (iOS) or `.webm` (web Hearth, opus). `process-message` derives the MIME type from the extension.

## Story worker

A separate service (`story-worker/`) watches for elder messages with `status = 'ready'` and `story is null`. One LLM call splits the story into 5 beats, Luma renders one Dream Recorder style clip per beat (ffmpeg grain, slowed to about 10 s), and the worker uploads them and writes `story`. The `make-story` images fallback runs only when the worker sets `STORY_FALLBACK=images` (off by default).

Success:

```json
{
  "title": "...", "title_es": "...",
  "world": "one line: characters, place, era, palette, shared by every scene prompt",
  "scenes": [
    { "start": 0.0, "end": 0.18, "text_es": "...", "text_en": "...", "prompt": "...",
      "video_path": "videos/{thread_id}/{message_id}-1.mp4", "thumb_path": "videos/{thread_id}/{message_id}-1.jpg" }
  ],
  "video_path": "videos/{thread_id}/{message_id}-1.mp4",
  "thumb_path": "videos/{thread_id}/{message_id}-1.jpg"
}
```

- `scenes` has 5 entries in story order. `start` and `end` are fractions 0..1 of the narration (the translated audio). They come from the character offset of each beat's `text_en` within `translation`, divided by its length, because speech is close to linear in characters. The first `start` is 0, the last `end` is 1, and each `end` equals the next `start`, so the scenes tile the whole narration. The current scene at playback fraction `p` is the last one with `start <= p`.
- `text_en` is a consecutive excerpt of `translation` and `text_es` of `transcript`. Joined in order they cover the whole text. A client that times against the Spanish original can compute its own fractions from `text_es` offsets within `transcript`.
- If a beat's clip fails, that scene reuses the previous scene's `video_path` and `thumb_path` (the first scene borrows the next good one). The story is an error only if every clip fails.
- Top-level `video_path` and `thumb_path` are always the first scene, for backward compatibility. Clients use `scenes` when present and otherwise fall back to the single video or `image_paths`. Existing `image_paths` are kept.

While working, `story = {"status":"generating","claimed_at":...}`. If everything fails, `story = {"status":"error","error":"..."}`. Clients treat a story without `video_path` or `image_paths` as "no story yet". The image fallback includes `video_error`.

`process-message` always returns HTTP 200 with the row. Read `status` and `error` to tell success from failure. `enroll-voice` returns HTTP 500 with `{ "error": "..." }` on failure.

## Edge functions

All take JSON via POST and return JSON. The app calls them with the anon key as `Authorization: Bearer <anon>`.

### `process-message`
Request: `{ "message_id": "<uuid>" }`
The app first uploads the original audio and inserts the row with `status = 'uploaded'`, then calls this function.
Steps: set `processing`, transcribe, then run the LLM (translation, cultural notes, ask_about), then TTS in the sender's `voice_id` (fallback stock voice), then upload `-tr.mp3`, then set `ready`. On failure, set `error` with a message.
Response: the updated message row.

### `enroll-voice`
Request: `{ "profile_id": "<uuid>", "sample_path": "voices/<profile_id>.m4a" }`
Creates an ElevenLabs Instant Voice Clone and writes `profiles.voice_id`.
Response: `{ "voice_id": "..." }`

### `make-story` (stretch, below the cut line)
Request: `{ "message_id": "<uuid>" }`. Generates 3 images for a ready elder message and writes `story`.

## Secrets (Supabase function env, never committed)

`ELEVENLABS_API_KEY`, `META_API_KEY`, `FALLBACK_VOICE_ID`. Optional: `STT_PROVIDER` (`elevenlabs` default | `openai`), `STT_MODEL` (default `scribe_v2`, or `gpt-4o-transcribe` for openai), `LLM_PROVIDER` (`meta` default | `openai` | `anthropic` | `codex`), `LLM_MODEL` (default `muse-spark-1.3`), `IMAGE_PROVIDER` (`meta` default | `openai` | `codex`), `IMAGE_MODEL` (default `muse-image-1.0`), `META_API_URL` (base URL, default `https://api.meta.ai/v1`), `META_REASONING_EFFORT` (default `low`), `TTS_MODEL` (default `eleven_multilingual_v2`), `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` (only when a provider is switched to them), `CODEX_RELAY_URL` and `CODEX_RELAY_SECRET` (only for `codex`, see codex-relay/README.md).
