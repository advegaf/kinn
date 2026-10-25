import { cloneVoice } from "../_shared/providers.ts";
import { adminClient, corsHeaders, env, errorText, json, stripBucket, timer } from "../_shared/util.ts";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });

  const body = await req.json().catch(() => null);
  const profileId: string = body?.profile_id ?? "";
  let samplePath: string = body?.sample_path ?? "";
  if (!profileId) return json({ error: "profile_id is required" }, 400);
  if (!samplePath) samplePath = `voices/${profileId}.m4a`;

  const db = adminClient();
  const t = timer(`enroll-voice ${profileId}`);
  try {
    const path = stripBucket("audio", samplePath);
    const [profile, sample] = await Promise.all([
      db.from("profiles").select("id, name").eq("id", profileId).single(),
      db.storage.from("audio").download(path),
    ]);
    if (profile.error || !profile.data) throw new Error(`Profile not found: ${profile.error?.message}`);
    if (sample.error || !sample.data) throw new Error(`Could not download sample ${path}: ${sample.error?.message}`);
    t.step("load");

    // ElevenLabs free tier cannot do Instant Voice Clone. When the clone fails, use the
    // shared fallback voice so onboarding still finishes and messages still get spoken.
    let voiceId: string;
    let fallback = false;
    try {
      voiceId = await cloneVoice(
        `${profile.data.name} (Hearth)`,
        sample.data,
        path.split("/").pop() || "sample.m4a",
      );
      t.step("clone");
    } catch (e) {
      voiceId = env("FALLBACK_VOICE_ID");
      if (!voiceId) throw e;
      fallback = true;
      console.warn(`[enroll-voice ${profileId}] clone failed, using FALLBACK_VOICE_ID: ${errorText(e)}`);
    }

    const { error } = await db.from("profiles").update({ voice_id: voiceId }).eq("id", profileId);
    if (error) throw new Error(`Saving voice_id failed: ${error.message}`);
    t.step("save");
    return json(fallback ? { voice_id: voiceId, fallback: true } : { voice_id: voiceId });
  } catch (e) {
    const message = errorText(e);
    console.error(`[enroll-voice ${profileId}] error after ${t.total()} ms: ${message}`);
    return json({ error: message }, 500);
  }
});
