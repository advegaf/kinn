// Seeds the presenter mode thread on a hosted project. Safe to run again: uploads upsert,
// profiles, thread and messages are reused when they already exist.
// Usage: SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... deno run -A scripts/seed-demo.ts
import { createClient } from "jsr:@supabase/supabase-js@2";
import { DEMO_AUDIO, elderFields, STORIES } from "../supabase/functions/_shared/demo.ts";

const url = Deno.env.get("SUPABASE_URL");
const key = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
if (!url || !key) throw new Error("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY");
const db = createClient(url, key, { auth: { persistSession: false } });
const demoDir = new URL("../../hearth-web/demo/", import.meta.url);

function must<T>(res: { data: T; error: { message: string } | null }, what: string): NonNullable<T> {
  if (res.error) throw new Error(`${what}: ${res.error.message}`);
  return res.data as NonNullable<T>;
}

async function uploadDir(sub: string, bucket: string, type: string) {
  const dir = new URL(sub, demoDir);
  let n = 0;
  for await (const f of Deno.readDir(dir)) {
    if (!f.isFile || !f.name.endsWith(type === "image/jpeg" ? ".jpg" : ".mp3")) continue;
    const body = await Deno.readFile(new URL(f.name, dir));
    must(await db.storage.from(bucket).upload(`demo/${f.name}`, body, { contentType: type, upsert: true }), f.name);
    n++;
  }
  console.log(`uploaded ${n} files to ${bucket}/demo/`);
}

async function profile(name: string, role: string, lang: string): Promise<string> {
  const found = must(await db.from("profiles").select("id").eq("name", name).eq("role", role).limit(1), "profiles");
  if (found.length) return found[0].id;
  return must(await db.from("profiles").insert({ name, role, lang }).select("id").single(), "insert profile").id;
}

await uploadDir("scenes/", "images", "image/jpeg");
await uploadDir("audio/", "audio", "audio/mpeg");

const margaret = await profile("Margaret", "elder", "es");
const angel = await profile("Angel", "family", "en");

const threads = must(
  await db.from("threads").select("id").eq("demo", true).eq("elder_id", margaret).order("created_at").limit(1),
  "threads",
);
const threadId: string = threads.length
  ? threads[0].id
  : must(await db.from("threads").insert({ elder_id: margaret, family_id: angel, demo: true }).select("id").single(), "insert thread").id;

// s1 is left out on purpose: Margaret tells it live.
for (const s of STORIES.filter((s) => s.id !== "s1")) {
  const fields = elderFields(s);
  const row = {
    thread_id: threadId,
    sender_id: margaret,
    source_lang: "es",
    target_lang: "en",
    original_path: DEMO_AUDIO.has(s.id) ? `demo/${s.id}-es.mp3` : "",
    created_at: new Date(Date.now() - s.days_ago * 86400000).toISOString(),
    ...fields,
  };
  const found = must(
    await db.from("messages").select("id").eq("thread_id", threadId).eq("transcript", s.transcript).limit(1),
    "messages",
  );
  if (found.length) {
    const { created_at: _keep, ...update } = row;
    must(await db.from("messages").update(update).eq("id", found[0].id), `update ${s.id}`);
    console.log(`${s.id}: updated ${found[0].id}`);
  } else {
    const ins = must(await db.from("messages").insert(row).select("id").single(), `insert ${s.id}`);
    console.log(`${s.id}: inserted ${ins.id}`);
  }
}

const code = threadId.slice(0, 6).toUpperCase();
console.log(`\nthread   ${threadId}\nmargaret ${margaret}\nangel    ${angel}\ncode     ${code}`);
console.log(`hearth   https://mothertongue-hearth.netlify.app/?thread=${threadId}&profile=${margaret}&subs=en`);
