import { elderFields, freeFields, pickReply, pickStory, REPLIES, replyFields, replyTarget } from "../_shared/demo.ts";
import { callLLM } from "../_shared/llm.ts";
import { speak, transcribe } from "../_shared/providers.ts";
import { adminClient, corsHeaders, env, errorText, json, langName, stripBucket, timer } from "../_shared/util.ts";

const LLM_KEY: Record<string, string> = { meta: "META_API_KEY", anthropic: "ANTHROPIC_API_KEY", openai: "OPENAI_API_KEY", codex: "CODEX_RELAY_SECRET" };

function systemPrompt(sourceLang: string, targetLang: string, wantAsk: boolean): string {
  const src = langName(sourceLang);
  const tgt = langName(targetLang);
  return `You translate voice messages between a grandmother and her grandchild in one family.
Translate from ${src} to ${tgt} the way a loving bilingual grandchild would: keep the warmth, the endearments, the humor and the idioms. Do not translate word for word. Keep the speaker's voice and rhythm so it sounds natural when spoken aloud.
Keep endearments like "mija", "mijo", "coraz\u00f3n", "abuelita" in place when that sounds natural in ${tgt}, and explain each one you keep in cultural_notes. Also add a cultural note for any idiom, dish, saint, place or tradition a ${tgt} speaker might not know. Keep notes to one short sentence each. Use an empty list if there is nothing worth explaining.
${
    wantAsk
      ? `Also write exactly 3 short follow-up prompts for the grandchild, each starting with "Ask her about", drawn from this message and the earlier conversation. Make them specific and warm, things that invite a story.`
      : `Return an empty list for ask_about.`
  }
The translation will be read aloud by text to speech, so do not add brackets, notes or stage directions inside it.
Respond with only a JSON object in this exact shape:
{"translation": "...", "title_en": "...", "title_es": "...", "cultural_notes": [{"term": "...", "note": "..."}], "ask_about": ["Ask her about ...", "Ask her about ...", "Ask her about ..."]}
title_en and title_es summarize the message in English and in Spanish, at most 6 words each, in sentence case (only the first word and names capitalized), no final period.`;
}

type Row = { id: string; sender_id: string; transcript: string | null };
type Msg = { id: string; sender_id: string; source_lang: string };

function demoFields(msg: Msg, role: string, heard: string, existing: Row[]): Record<string, unknown> | null {
  const tag = `[process-message ${msg.id}] demo heard "${heard.slice(0, 80)}"`;
  if (role === "elder") {
    const story = pickStory(heard, existing);
    console.log(`${tag} -> ${story?.id ?? "free"}`);
    return story ? elderFields(story) : null;
  }
  const { index, score, heard: words } = pickReply(heard, existing);
  console.log(`${tag} score ${score}/${words} -> index ${index}`);
  if (index < 0) return null;
  const others = existing.filter((m) => m.sender_id !== msg.sender_id);
  return { ...replyFields(REPLIES[index], index), reply_to: replyTarget(REPLIES[index], others) };
}

type Db = ReturnType<typeof adminClient>;
type Timer = ReturnType<typeof timer>;
type Hist = { transcript: string | null; sender_id: string };
type Job = { db: Db; t: Timer; id: string; msg: any; role: string; voiceId: string; audio: Blob; filename: string };

async function readMessageId(req: Request): Promise<string> {
  try {
    return (await req.json())?.message_id ?? "";
  } catch {
    return "";
  }
}

async function loadJob(db: Db, t: Timer, msg: any): Promise<{ job: Job; history: Hist[]; demo: boolean; llm: boolean }> {
  await db.from("messages").update({ status: "processing", error: null }).eq("id", msg.id);
  const originalPath = stripBucket("audio", msg.original_path);
  const [sender, audio, history, thread] = await Promise.all([
    db.from("profiles").select("*").eq("id", msg.sender_id).single(),
    db.storage.from("audio").download(originalPath),
    db.from("messages")
      .select("transcript, sender_id, created_at")
      .eq("thread_id", msg.thread_id)
      .neq("id", msg.id)
      .not("transcript", "is", null)
      .order("created_at", { ascending: false })
      .limit(10),
    db.from("threads").select("demo").eq("id", msg.thread_id).single(),
  ]);
  if (sender.error || !sender.data) throw new Error(`Sender profile not found: ${sender.error?.message}`);
  if (audio.error || !audio.data) throw new Error(`Could not download audio ${originalPath}: ${audio.error?.message}`);
  t.step("load");
  const provider = env("LLM_PROVIDER", "meta").toLowerCase();
  const job: Job = {
    db,
    t,
    id: msg.id,
    msg,
    role: sender.data.role,
    voiceId: sender.data.voice_id,
    audio: audio.data,
    filename: originalPath.split("/").pop() || "audio.m4a",
  };
  const llm = Boolean(env(LLM_KEY[provider] ?? "META_API_KEY"));
  return { job, history: history.data ?? [], demo: thread.data?.demo === true || !llm, llm };
}

async function saveReady(job: Job, fields: Record<string, unknown>): Promise<unknown> {
  const { data: done, error } = await job.db.from("messages").update(fields).eq("id", job.id).select().single();
  if (error) throw new Error(`Final update failed: ${error.message}`);
  job.t.step("ready");
  return done;
}

async function saveError(db: Db, t: Timer, id: string, e: unknown): Promise<Response> {
  const message = errorText(e);
  console.error(`[process-message ${id}] error after ${t.total()} ms: ${message}`);
  const { data: failed } = await db
    .from("messages")
    .update({ status: "error", error: message })
    .eq("id", id)
    .select()
    .single();
  // 200 with the row so the app can read status and error from the same shape.
  return json(failed ?? { id, status: "error", error: message });
}

// Presenter mode: real Scribe for the logs, then map onto the canned stories. No LLM, no TTS.
async function runDemo(job: Job, history: Hist[], llm: boolean): Promise<unknown> {
  let heard = "";
  try {
    heard = await transcribe(job.audio, job.filename, job.msg.source_lang);
  } catch (e) {
    console.error(`[process-message ${job.id}] demo stt failed, continuing: ${errorText(e)}`);
  }
  job.t.step("stt");
  const { data: rows } = await job.db.from("messages")
    .select("id, sender_id, transcript")
    .eq("thread_id", job.msg.thread_id)
    .neq("id", job.id)
    .order("created_at", { ascending: false });
  const canned = demoFields(job.msg, job.role, heard, rows ?? []);
  if (canned) return saveReady(job, canned);
  if (!llm || !heard) return saveReady(job, freeFields(heard, job.msg.source_lang));
  return finishReal(job, heard, history);
}

async function transcribeOrFail(job: Job): Promise<string> {
  const transcript = await transcribe(job.audio, job.filename, job.msg.source_lang);
  if (!transcript) throw new Error("Transcription was empty. Was anything said?");
  await job.db.from("messages").update({ transcript }).eq("id", job.id);
  job.t.step("stt");
  return transcript;
}

async function translate(job: Job, transcript: string, history: Hist[]): Promise<Record<string, unknown>> {
  const msg = job.msg;
  // ask_about is only for messages the family member receives, which means the elder sent them.
  const wantAsk = job.role === "elder";
  const earlier = history
    .reverse()
    .map((m) => `${m.sender_id === msg.sender_id ? "Same speaker" : "Other person"}: ${m.transcript}`)
    .join("\n");
  const userPrompt = `${earlier ? `Earlier messages in this conversation, oldest first:\n${earlier}\n\n` : ""}Message to translate (${langName(msg.source_lang)}):\n${transcript}`;
  const out = await callLLM(systemPrompt(msg.source_lang, msg.target_lang, wantAsk), userPrompt);
  const translation = String(out.translation ?? "").trim();
  if (!translation) throw new Error("LLM returned an empty translation");
  const story = {
    ...(msg.story ?? {}),
    title: String(out.title_en ?? "").trim() || null,
    title_es: String(out.title_es ?? "").trim() || null,
    status: job.role === "elder" ? "pending" : "ready",
  };
  job.t.step("llm");
  return {
    translation,
    cultural_notes: Array.isArray(out.cultural_notes) ? out.cultural_notes : [],
    ask_about: wantAsk && Array.isArray(out.ask_about) ? out.ask_about.slice(0, 3) : [],
    story,
  };
}

async function speakAndUpload(job: Job, translation: string): Promise<string> {
  const voiceId = job.voiceId || env("FALLBACK_VOICE_ID");
  if (!voiceId) throw new Error("Sender has no voice_id and FALLBACK_VOICE_ID is not set");
  const mp3 = await speak(translation, voiceId);
  job.t.step("tts");
  const translatedPath = `${job.msg.thread_id}/${job.id}-tr.mp3`;
  const up = await job.db.storage.from("audio").upload(translatedPath, mp3, { contentType: "audio/mpeg", upsert: true });
  if (up.error) throw new Error(`Upload of translated audio failed: ${up.error.message}`);
  job.t.step("upload");
  return translatedPath;
}

async function runReal(job: Job, history: Hist[]): Promise<unknown> {
  return finishReal(job, await transcribeOrFail(job), history);
}

async function finishReal(job: Job, transcript: string, history: Hist[]): Promise<unknown> {
  const out = await translate(job, transcript, history);
  const translatedPath = await speakAndUpload(job, out.translation as string);
  const done = await saveReady(job, {
    transcript,
    ...out,
    translated_path: translatedPath,
    status: "ready",
    error: null,
  });
  console.log(`[process-message ${job.id}] done in ${job.t.total()} ms`);
  return done;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  const messageId = await readMessageId(req);
  if (!messageId) return json({ error: "message_id is required" }, 400);

  const db = adminClient();
  const t = timer(`process-message ${messageId}`);
  const { data: msg, error: loadErr } = await db.from("messages").select("*").eq("id", messageId).single();
  if (loadErr || !msg) return json({ error: `Message not found: ${loadErr?.message ?? messageId}` }, 404);

  try {
    const { job, history, demo, llm } = await loadJob(db, t, msg);
    return json(demo ? await runDemo(job, history, llm) : await runReal(job, history));
  } catch (e) {
    return saveError(db, t, messageId, e);
  }
});
