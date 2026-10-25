// H0 smoke test: profiles + thread + audio upload + message row + process-message.
// Uses only the anon key, the same access the app has, so it also exercises RLS and storage policies.
//
// Usage:
//   SUPABASE_URL=... SUPABASE_ANON_KEY=... deno run -A scripts/smoke.ts path/to/audio.m4a [elder|family]
// The sender defaults to the elder (Spanish to English). Pass "family" to send English to Spanish.

const url = (Deno.env.get("SUPABASE_URL") ?? "").replace(/\/$/, "");
const key = Deno.env.get("SUPABASE_ANON_KEY") ?? "";
const [audioFile, senderRole = "elder"] = Deno.args;

if (!url || !key || !audioFile) {
  console.error("Usage: SUPABASE_URL=... SUPABASE_ANON_KEY=... deno run -A scripts/smoke.ts <audio file> [elder|family]");
  Deno.exit(1);
}

const headers = { apikey: key, Authorization: `Bearer ${key}` };

async function insert(table: string, row: Record<string, unknown>) {
  const res = await fetch(`${url}/rest/v1/${table}`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json", Prefer: "return=representation" },
    body: JSON.stringify(row),
  });
  if (!res.ok) throw new Error(`insert ${table} failed (${res.status}): ${await res.text()}`);
  return (await res.json())[0];
}

const started = performance.now();

const elder = await insert("profiles", { name: "Abuela Smoke", role: "elder", lang: "es" });
const family = await insert("profiles", { name: "Grandkid Smoke", role: "family", lang: "en" });
const thread = await insert("threads", { elder_id: elder.id, family_id: family.id });
const sender = senderRole === "family" ? family : elder;
const receiver = senderRole === "family" ? elder : family;
console.log(`thread ${thread.id}, sender ${sender.role} ${sender.id}`);

const messageId = crypto.randomUUID();
const ext = audioFile.split(".").pop()?.toLowerCase() || "m4a";
const originalPath = `${thread.id}/${messageId}.${ext}`;
const contentType = ext === "mp3" ? "audio/mpeg" : ext === "wav" ? "audio/wav" : "audio/mp4";
const up = await fetch(`${url}/storage/v1/object/audio/${originalPath}`, {
  method: "POST",
  headers: { ...headers, "Content-Type": contentType, "x-upsert": "true" },
  body: await Deno.readFile(audioFile),
});
if (!up.ok) throw new Error(`upload failed (${up.status}): ${await up.text()}`);

await insert("messages", {
  id: messageId,
  thread_id: thread.id,
  sender_id: sender.id,
  source_lang: sender.lang,
  target_lang: receiver.lang,
  original_path: originalPath,
  status: "uploaded",
});
const setupMs = Math.round(performance.now() - started);

const fnStart = performance.now();
const res = await fetch(`${url}/functions/v1/process-message`, {
  method: "POST",
  headers: { ...headers, "Content-Type": "application/json" },
  body: JSON.stringify({ message_id: messageId }),
});
const fnMs = Math.round(performance.now() - fnStart);
const text = await res.text();
let row: Record<string, unknown> = {};
try {
  row = JSON.parse(text);
} catch {
  console.error(`process-message returned non JSON (${res.status}): ${text}`);
  Deno.exit(1);
}

console.log("");
console.log(`HTTP:         ${res.status}`);
console.log(`status:       ${row.status}`);
if (row.error) console.log(`error:        ${row.error}`);
console.log(`transcript:   ${row.transcript ?? ""}`);
console.log(`translation:  ${row.translation ?? ""}`);
console.log(`notes:        ${JSON.stringify(row.cultural_notes ?? [])}`);
console.log(`ask_about:    ${JSON.stringify(row.ask_about ?? [])}`);
if (row.translated_path) {
  console.log(`audio URL:    ${url}/storage/v1/object/public/audio/${row.translated_path}`);
}
console.log(`setup:        ${setupMs} ms`);
console.log(`process:      ${fnMs} ms (target under 8000)`);
console.log(`total:        ${Math.round(performance.now() - started)} ms`);
Deno.exit(row.status === "ready" ? 0 : 2);
