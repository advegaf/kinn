# Voices

Demo mode plays pre-generated ElevenLabs narration instead of the device speech voice. The real pipeline speaks every translation in the sender's own cloned voice.

## Account status (read this first)

The ElevenLabs key in `backend/.env` is on the **free tier**: 10,000 characters a month, resetting 2026-11-24. That has two consequences:

- The API refuses Voice Library voices for free users (HTTP 402, "Free users cannot use library voices via the API"). The demo files use premade voices for that reason.
- Instant voice cloning is off (`can_use_instant_voice_cloning: false`), so `enroll-voice` will fail on this key. Starter ($5/month) turns on both.

About 9,800 of the 10,000 characters are spent this cycle. Nothing more can be generated until the reset or an upgrade.

## Demo narration

Files live in `hearth-web/demo/audio/{id}-{es|en}.mp3` and are copied to `ios/MotherTongue/Resources/DemoAudio/`, which xcodegen bundles into the app root. Story ids are `s1` to `s6`, replies are `r1` and `r2`. `es` is Spanish, `en` is English.

| Role | Voice | Voice id | Used for |
| --- | --- | --- | --- |
| Rosa, Spanish and English | Sarah (premade) | `EXAVITQu4vr4xnSDxMaL` | `s1` to `s4`, both languages |
| Sofía, Spanish and English | Jessica (premade) | `cgSgspJ2msm6clMCkdW9` | `r1`, `r2`, both languages |

Rosa uses the same voice in both languages, which is the product promise: her own voice, translated.

Model `eleven_multilingual_v2`, `output_format=mp3_44100_128`, voice settings: stability 0.45, similarity_boost 0.85, style 0.15, use_speaker_boost true. The English text is the story `translation` with the `*italic*` markers stripped.

| File | Seconds | File | Seconds |
| --- | --- | --- | --- |
| s1-es | 70.5 | s1-en | 64.3 |
| s2-es | 80.6 | s2-en | 70.1 |
| s3-es | 76.4 | s3-en | 63.9 |
| s4-es | 70.6 | s4-en | 64.3 |
| r1-es | 11.1 | r1-en | 11.4 |
| r2-es | 9.8 | r2-en | 11.4 |

Characters sent: 9,107 (8 stories at about 1,050 each, 4 replies at about 175 each).

**Missing:** `s5-es`, `s5-en`, `s6-es`, `s6-en`. The full set needs about 13,300 characters and the free tier allows 10,000. Both apps fall back to speech synthesis when a file is missing: Hearth on the audio element's `error` event, iOS when `Bundle.main.url` returns nil.

### Better voices waiting on an upgrade

These library voices are already added to the account and work as soon as the plan is Starter or higher:

- Rosa: Azu, "Calm, Soft and Melodic", Mexican, old (`D3ws14YxTqcjPaXEOehR`).
- Sofía: Ale Rodriguez, "Natural Mexican", young (`yUdDEHhLHqO1mgoIOV5o`).

An A/B of the first beat of `s1` on `eleven_v3` (stability 0.35, with audio tags like `[softly]` and `[pause]`) is in `~/Desktop/voice-ab/`: A is Lily, B is Matilda, C is Sarah. Pick one there before regenerating. Strip the bracketed tags from anything shown on screen. Regenerating all 6 stories plus replies costs about 13,300 characters (v3 accepts at most 5,000 characters a request; each story is about 1,050).

## Real pipeline settings

`backend/supabase/functions/_shared/providers.ts` sends `voice_settings` on every TTS call. Each one comes from an env var, so tuning needs no code change:

| Env | Default | Notes |
| --- | --- | --- |
| `TTS_MODEL` | `eleven_multilingual_v2` | `eleven_flash_v2_5` is faster |
| `TTS_STABILITY` | 0.45 | Lower is more expressive. Raise it if a clone drifts |
| `TTS_SIMILARITY` | 0.85 | Sent as `similarity_boost` |
| `TTS_STYLE` | 0.15 | Higher adds emotion and latency |
| `TTS_SPEAKER_BOOST` | true | `false` turns it off |

Set them with `supabase secrets set TTS_STABILITY=0.4` and so on.

## What we need from you for perfect voices

The demo voices are stock. The real product speaks in each person's own voice, and the clone is only as good as the recording.

1. **Grandma, 2 to 3 minutes of Spanish.** Her speaking naturally, ideally telling a real story. Not reading a script.
2. **Sofía, 2 to 3 minutes of English**, same way.
3. **Quiet room.** No music, no TV, no fans or kitchen noise. Soft furnishings help.
4. **Phone 20 to 30 cm from the mouth**, held steady, not in a pocket or on the far side of a table.
5. **One session.** Same room, same phone, same day. Mixing sessions blurs the clone.
6. **Varied emotion.** Laughing, quiet, excited. A flat recording gives a flat clone.
7. **Signed consent** from each person before cloning (see `docs/CONSENT.md`).
8. **An ElevenLabs plan of Starter or higher.** Instant cloning is off on the free tier.
9. **Optional: Professional Voice Clone.** Needs the Creator tier and 30 or more minutes of clean audio per person. Noticeably closer to the real voice, takes a few hours to train.

### How to enroll

- **In the app:** open the voice page during onboarding (`VoiceEnrollView`), record the sample, and the app uploads it and calls `enroll-voice`.
- **By hand:** upload the sample to the `audio` bucket, then `POST functions/v1/enroll-voice` with `{ "profile_id": "...", "sample_path": "voices/<profile_id>.m4a" }` (the path defaults to that). It returns `{ "voice_id": "..." }` and writes `profiles.voice_id`. From then on `process-message` speaks that person's translations in their own voice.
