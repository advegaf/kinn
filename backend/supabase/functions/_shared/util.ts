import { createClient } from "jsr:@supabase/supabase-js@2";

export const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

export function env(name: string, fallback = ""): string {
  return Deno.env.get(name) || fallback;
}

export function requireEnv(name: string): string {
  const v = Deno.env.get(name);
  if (!v) throw new Error(`Missing secret ${name}`);
  return v;
}

// Meta Model API base (OpenAI compatible). META_API_URL overrides it.
export function metaUrl(path: string): string {
  return env("META_API_URL", "https://api.meta.ai/v1").replace(/\/+$/, "") + path;
}

export function adminClient() {
  return createClient(requireEnv("SUPABASE_URL"), requireEnv("SUPABASE_SERVICE_ROLE_KEY"), {
    auth: { persistSession: false },
  });
}

// Accept paths with or without a leading "<bucket>/" prefix.
export function stripBucket(bucket: string, path: string): string {
  return path.startsWith(bucket + "/") ? path.slice(bucket.length + 1) : path;
}

export function errorText(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

// Logs time spent per step and in total, for the under 8 s latency target.
export function timer(label: string) {
  const start = performance.now();
  let last = start;
  return {
    step(name: string) {
      const now = performance.now();
      console.log(`[${label}] ${name}: ${Math.round(now - last)} ms (total ${Math.round(now - start)} ms)`);
      last = now;
    },
    total(): number {
      return Math.round(performance.now() - start);
    },
  };
}

export const LANG_NAMES: Record<string, string> = {
  es: "Spanish",
  en: "English",
};

export function langName(code: string): string {
  return LANG_NAMES[code] ?? code;
}
