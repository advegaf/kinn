import { callLLM } from "../_shared/llm.ts";
import { generateImage } from "../_shared/providers.ts";
import { adminClient, corsHeaders, errorText, json, timer } from "../_shared/util.ts";

const SYSTEM = `You turn a grandmother's spoken memory into a short illustrated story.
Write a short warm title in English (under 8 words) and exactly 3 image prompts that follow the memory in order, like three panels.
Every prompt must ask for: a warm, grainy, hand illustrated, nostalgic style with soft film grain and faded colors; no text, letters or words in the image; no real or recognizable faces (show people from behind, at a distance, or as simple stylized figures).
Describe concrete scenes, objects, light and setting from the memory.
Respond with only a JSON object: {"title": "...", "prompts": ["...", "...", "..."]}`;

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
  const t = timer(`make-story ${messageId}`);
  const { data: msg, error: loadErr } = await db.from("messages").select("*").eq("id", messageId).single();
  if (loadErr || !msg) return json({ error: `Message not found: ${loadErr?.message ?? messageId}` }, 404);

  try {
    if (!msg.transcript) throw new Error("Message has no transcript yet. Run process-message first.");

    const out = await callLLM(SYSTEM, `Memory (${msg.source_lang}):\n${msg.transcript}\n\nEnglish translation:\n${msg.translation ?? ""}`);
    const prompts = Array.isArray(out.prompts) ? out.prompts.slice(0, 3).map(String) : [];
    if (prompts.length === 0) throw new Error("LLM returned no image prompts");
    t.step("llm");

    const images = await Promise.all(prompts.map((p) => generateImage(p)));
    t.step("images");

    const imagePaths = await Promise.all(
      images.map(async (png, i) => {
        const path = `${msg.thread_id}/${messageId}-${i + 1}.png`;
        const up = await db.storage.from("images").upload(path, png, { contentType: "image/png", upsert: true });
        if (up.error) throw new Error(`Image upload failed: ${up.error.message}`);
        return `images/${path}`;
      }),
    );
    t.step("upload");

    const story = { title: String(out.title ?? "A memory"), image_paths: imagePaths };
    const { data: done, error } = await db.from("messages").update({ story }).eq("id", messageId).select().single();
    if (error) throw new Error(`Saving story failed: ${error.message}`);
    return json(done);
  } catch (e) {
    const message = errorText(e);
    console.error(`[make-story ${messageId}] error after ${t.total()} ms: ${message}`);
    // The voice message itself is still fine, so only the error text is recorded here.
    // Status stays as it was so a failed story never hides a ready message.
    const { data: failed } = await db
      .from("messages")
      .update({ error: `make-story: ${message}` })
      .eq("id", messageId)
      .select()
      .single();
    return json({ ...(failed ?? { id: messageId }), story_error: message }, 500);
  }
});
