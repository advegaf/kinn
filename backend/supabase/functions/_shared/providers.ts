import { env, metaUrl, relayUrl, requireEnv } from "./util.ts";

async function check(res: Response, what: string): Promise<Response> {
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${what} failed (${res.status}): ${body.slice(0, 500)}`);
  }
  return res;
}

// Speech to text. STT_PROVIDER picks elevenlabs (default, Scribe) or openai.
// The filename extension tells the provider the audio format.
export async function transcribe(audio: Blob, filename: string, lang: string): Promise<string> {
  const provider = env("STT_PROVIDER", "elevenlabs").toLowerCase();
  const form = new FormData();
  const ext = (filename.split(".").pop() ?? "").toLowerCase();
  const type = ext === "webm" ? "audio/webm" : ext === "m4a" ? "audio/mp4" : audio.type;
  form.append("file", new File([audio], `audio.${ext || "m4a"}`, { type }));

  if (provider === "openai") {
    form.append("model", env("STT_MODEL", "gpt-4o-transcribe"));
    if (lang) form.append("language", lang);
    const res = await check(
      await fetch("https://api.openai.com/v1/audio/transcriptions", {
        method: "POST",
        headers: { Authorization: `Bearer ${requireEnv("OPENAI_API_KEY")}` },
        body: form,
      }),
      "Transcription (openai)",
    );
    const data = await res.json();
    return (data.text ?? "").trim();
  }

  // Scribe takes ISO 639-1 codes like "es" and "en" as is.
  // A leftover OpenAI STT_MODEL (gpt-4o-transcribe) is ignored here.
  const model = env("STT_MODEL");
  form.append("model_id", model.startsWith("scribe") ? model : "scribe_v2");
  if (lang) form.append("language_code", lang);
  form.append("tag_audio_events", "false");
  const res = await check(
    await fetch("https://api.elevenlabs.io/v1/speech-to-text", {
      method: "POST",
      headers: { "xi-api-key": requireEnv("ELEVENLABS_API_KEY") },
      body: form,
    }),
    "Transcription (elevenlabs)",
  );
  const data = await res.json();
  return (data.text ?? "").trim();
}

// Voice settings, tunable without a deploy. Lower stability sounds more natural and varied;
// high similarity keeps a cloned voice close to the sample.
function voiceSettings() {
  const num = (name: string, fallback: number) => {
    const v = Number.parseFloat(env(name));
    return Number.isFinite(v) ? v : fallback;
  };
  return {
    stability: num("TTS_STABILITY", 0.45),
    similarity_boost: num("TTS_SIMILARITY", 0.85),
    style: num("TTS_STYLE", 0.15),
    use_speaker_boost: env("TTS_SPEAKER_BOOST", "true").toLowerCase() !== "false",
  };
}

// ElevenLabs text to speech, returns mp3 bytes.
export async function speak(text: string, voiceId: string): Promise<Uint8Array> {
  const res = await check(
    await fetch(
      `https://api.elevenlabs.io/v1/text-to-speech/${encodeURIComponent(voiceId)}?output_format=mp3_44100_128`,
      {
        method: "POST",
        headers: {
          "xi-api-key": requireEnv("ELEVENLABS_API_KEY"),
          "Content-Type": "application/json",
          Accept: "audio/mpeg",
        },
        body: JSON.stringify({
          text,
          model_id: env("TTS_MODEL", "eleven_multilingual_v2"),
          voice_settings: voiceSettings(),
        }),
      },
    ),
    "Text to speech",
  );
  return new Uint8Array(await res.arrayBuffer());
}

// ElevenLabs Instant Voice Clone, returns the new voice_id.
export async function cloneVoice(name: string, sample: Blob, filename: string): Promise<string> {
  const form = new FormData();
  form.append("name", name);
  form.append("files", new File([sample], filename));
  const res = await check(
    await fetch("https://api.elevenlabs.io/v1/voices/add", {
      method: "POST",
      headers: { "xi-api-key": requireEnv("ELEVENLABS_API_KEY") },
      body: form,
    }),
    "Voice clone",
  );
  const data = await res.json();
  if (!data.voice_id) throw new Error(`Voice clone returned no voice_id: ${JSON.stringify(data)}`);
  return data.voice_id;
}

function b64ToBytes(b64: string): Uint8Array {
  return Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
}

// Image generation, returns PNG bytes. IMAGE_PROVIDER picks meta (default, Muse Image), openai or codex.
export async function generateImage(prompt: string): Promise<Uint8Array> {
  const provider = env("IMAGE_PROVIDER", "meta").toLowerCase();
  const name = provider === "openai" || provider === "codex" ? provider : "meta";
  const routes = {
    meta: {
      url: () => metaUrl("/images/generations"),
      key: "META_API_KEY",
      body: {
        model: env("IMAGE_MODEL").startsWith("muse") ? env("IMAGE_MODEL") : "muse-image-1.0",
        prompt,
        n: 1,
        size: "1024x1024",
        response_format: "b64_json",
        output_format: "png",
        reasoning_strength: "low",
      },
    },
    openai: {
      url: () => "https://api.openai.com/v1/images/generations",
      key: "OPENAI_API_KEY",
      body: { model: env("IMAGE_MODEL", "gpt-image-1"), prompt, n: 1, size: "1024x1024", quality: "low" },
    },
    codex: { url: () => relayUrl("/images/generations"), key: "CODEX_RELAY_SECRET", body: { prompt } },
  };
  const route = routes[name];
  const res = await check(
    await fetch(route.url(), {
      method: "POST",
      headers: { Authorization: `Bearer ${requireEnv(route.key)}`, "Content-Type": "application/json" },
      body: JSON.stringify(route.body),
    }),
    `Image generation (${name})`,
  );
  const data = await res.json();
  const item = data.data?.[0] ?? {};
  if (item.b64_json) return b64ToBytes(item.b64_json);
  if (item.url) {
    const img = await check(await fetch(item.url), "Image download");
    return new Uint8Array(await img.arrayBuffer());
  }
  throw new Error("Image generation returned no image data");
}
