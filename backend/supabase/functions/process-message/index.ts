import { elderFields, freeFields, pickReply, pickStory, REPLIES, replyFields, replyTarget } from "../_shared/demo.ts";
import { callLLM } from "../_shared/llm.ts";
import { speak, transcribe } from "../_shared/providers.ts";
import { adminClient, corsHeaders, env, errorText, json, langName, stripBucket, timer } from "../_shared/util.ts";

const LLM_KEY: Record<string, string> = { meta: "META_API_KEY", anthropic: "ANTHROPIC_API_KEY", openai: "OPENAI_API_KEY" };

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
title_en and title_es summarize the message in English and in Spanish, at most 6 words each.`;
}

type Row = { id: string; sender_id: string; transcript: string | null };
type Msg = { id: string; sender_id: string; source_lang: string };

function demoFields(msg: Msg, role: string, heard: string, existing: Row[]): Record<string, unknown> {
  const tag = `[process-message ${msg.id}] demo heard "${heard.slice(0, 80)}"`;
  if (role === "elder") {
    const story = pickStory(heard, existing);
    console.log(`${tag} -> ${story.id}`);
    return elderFields(story);
  }
  const { index, score, heard: words } = pickReply(heard, existing);
  console.log(`${tag} score ${score}/${words} -> index ${index}`);
  if (index < 0) return freeFields(heard, msg.source_lang);
  const others = existing.filter((m) => m.sender_id !== msg.sender_id);
  return { ...replyFields(REPLIES[index], index), reply_to: replyTarget(REPLIES[index], others) };
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });

  let messageId = "";
  try {
    messageId = (await req.json())?.message_id ?? "";
  } catch {
    // fall through to the check below
  }
  if (!messageId) return json({ error: "message_id is required" }, 400);

  const db = adminClient();
  const t = timer(`process-message ${messageId}`);

  const { data: msg, error: loadErr } = await db.from("messages").select("*").eq("id", messageId).single();
  if (loadErr || !msg) return json({ error: `Message not found: ${loadErr?.message ?? messageId}` }, 404);

  try {
    await db.from("messages").update({ status: "processing", error: null }).eq("id", messageId);

    const originalPath = stripBucket("audio", msg.original_path);
    const [sender, audio, history, thread] = await Promise.all([
      db.from("profiles").select("*").eq("id", msg.sender_id).single(),
      db.storage.from("audio").download(originalPath),
      db.from("messages")
        .select("transcript, sender_id, created_at")
        .eq("thread_id", msg.thread_id)
        .neq("id", messageId)
        .not("transcript", "is", null)
        .order("created_at", { ascending: false })
        .limit(10),
      db.from("threads").select("demo").eq("id", msg.thread_id).single(),
    ]);
    if (sender.error || !sender.data) throw new Error(`Sender profile not found: ${sender.error?.message}`);
    if (audio.error || !audio.data) throw new Error(`Could not download audio ${originalPath}: ${audio.error?.message}`);
    t.step("load");

    const filename = originalPath.split("/").pop() || "audio.m4a";
    const provider = env("LLM_PROVIDER", "meta").toLowerCase();
    const demo = thread.data?.demo === true || !env(LLM_KEY[provider] ?? "META_API_KEY");
    if (demo) {
      // Presenter mode: real Scribe for the logs, then map onto the canned stories. No LLM, no TTS.
      let heard = "";
      try {
        heard = await transcribe(audio.data, filename, msg.source_lang);
      } catch (e) {
        console.error(`[process-message ${messageId}] demo stt failed, continuing: ${errorText(e)}`);
      }
      t.step("stt");
      const { data: rows } = await db.from("messages")
        .select("id, sender_id, transcript")
        .eq("thread_id", msg.thread_id)
        .neq("id", messageId)
        .order("created_at", { ascending: false });
      const fields = demoFields(msg, sender.data.role, heard, rows ?? []);
      const { data: done, error: doneErr } = await db.from("messages").update(fields).eq("id", messageId).select()
        .single();
      if (doneErr) throw new Error(`Final update failed: ${doneErr.message}`);
      t.step("ready");
      return json(done);
    }
    const transcript = await transcribe(audio.data, filename, msg.source_lang);
    if (!transcript) throw new Error("Transcription was empty. Was anything said?");
    await db.from("messages").update({ transcript }).eq("id", messageId);
    t.step("stt");

    // ask_about is only for messages the family member receives, which means the elder sent them.
    const wantAsk = sender.data.role === "elder";
    const earlier = (history.data ?? [])
      .reverse()
      .map((m) => `${m.sender_id === msg.sender_id ? "Same speaker" : "Other person"}: ${m.transcript}`)
      .join("\n");
    const userPrompt = `${earlier ? `Earlier messages in this conversation, oldest first:\n${earlier}\n\n` : ""}Message to translate (${langName(msg.source_lang)}):\n${transcript}`;
    const out = await callLLM(systemPrompt(msg.source_lang, msg.target_lang, wantAsk), userPrompt);
    const translation = String(out.translation ?? "").trim();
    if (!translation) throw new Error("LLM returned an empty translation");
    const culturalNotes = Array.isArray(out.cultural_notes) ? out.cultural_notes : [];
    const askAbout = wantAsk && Array.isArray(out.ask_about) ? out.ask_about.slice(0, 3) : [];
    const story = {
      ...(msg.story ?? {}),
      title: String(out.title_en ?? "").trim() || null,
      title_es: String(out.title_es ?? "").trim() || null,
      status: "ready",
    };
    t.step("llm");

    const voiceId = sender.data.voice_id || env("FALLBACK_VOICE_ID");
    if (!voiceId) throw new Error("Sender has no voice_id and FALLBACK_VOICE_ID is not set");
    const mp3 = await speak(translation, voiceId);
    t.step("tts");

    const translatedPath = `${msg.thread_id}/${messageId}-tr.mp3`;
    const up = await db.storage.from("audio").upload(translatedPath, mp3, {
      contentType: "audio/mpeg",
      upsert: true,
    });
    if (up.error) throw new Error(`Upload of translated audio failed: ${up.error.message}`);
    t.step("upload");

    const { data: done, error: doneErr } = await db
      .from("messages")
      .update({
        transcript,
        translation,
        translated_path: translatedPath,
        cultural_notes: culturalNotes,
        ask_about: askAbout,
        story,
        status: "ready",
        error: null,
      })
      .eq("id", messageId)
      .select()
      .single();
    if (doneErr) throw new Error(`Final update failed: ${doneErr.message}`);
    t.step("ready");
    console.log(`[process-message ${messageId}] done in ${t.total()} ms`);
    return json(done);
  } catch (e) {
    const message = errorText(e);
    console.error(`[process-message ${messageId}] error after ${t.total()} ms: ${message}`);
    const { data: failed } = await db
      .from("messages")
      .update({ status: "error", error: message })
      .eq("id", messageId)
      .select()
      .single();
    // 200 with the row so the app can read status and error from the same shape.
    return json(failed ?? { id: messageId, status: "error", error: message });
  }
});
