import { env, metaUrl, relayUrl, requireEnv } from "./util.ts";

const DEFAULT_MODELS: Record<string, string> = {
  openai: "gpt-4o",
  anthropic: "claude-opus-5-5",
  meta: "muse-spark-1.3",
  codex: "gpt-6-luna",
};

// Pulls the first JSON object out of a model reply, tolerating code fences or stray prose.
export function parseJSON(text: string): Record<string, unknown> {
  const cleaned = text.replace(/```(?:json)?/gi, "").trim();
  try {
    return JSON.parse(cleaned);
  } catch {
    const start = cleaned.indexOf("{");
    const end = cleaned.lastIndexOf("}");
    if (start >= 0 && end > start) return JSON.parse(cleaned.slice(start, end + 1));
    throw new Error(`LLM did not return JSON: ${text.slice(0, 300)}`);
  }
}

async function post(url: string, headers: Record<string, string>, body: unknown, what: string) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(90_000),
  });
  if (!res.ok) {
    throw new Error(`${what} failed (${res.status}): ${(await res.text()).slice(0, 500)}`);
  }
  return await res.json();
}

// One LLM call that returns parsed JSON. The system prompt must ask for JSON.
export async function callLLM(system: string, user: string): Promise<Record<string, unknown>> {
  const provider = env("LLM_PROVIDER", "meta").toLowerCase();
  const model = env("LLM_MODEL", DEFAULT_MODELS[provider] ?? DEFAULT_MODELS.meta);

  if (provider === "anthropic") {
    const data = await post(
      "https://api.anthropic.com/v1/messages",
      {
        "x-api-key": requireEnv("ANTHROPIC_API_KEY"),
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "server-side-fallback-2026-07-01",
      },
      {
        model,
        max_tokens: 16000,
        output_config: { effort: "low" },
        fallbacks: "default",
        system,
        messages: [{ role: "user", content: user }],
      },
      "Anthropic LLM",
    );
    if (data.stop_reason === "refusal") throw new Error("Anthropic LLM declined the request");
    const text = (data.content ?? [])
      .filter((b: { type: string }) => b.type === "text")
      .map((b: { text: string }) => b.text)
      .join("");
    return parseJSON(text);
  }

  const isMeta = provider === "meta";
  const isCodex = provider === "codex";
  const url = isMeta
    ? metaUrl("/chat/completions")
    : isCodex
    ? relayUrl("/chat/completions")
    : "https://api.openai.com/v1/chat/completions";
  const key = requireEnv(isMeta ? "META_API_KEY" : isCodex ? "CODEX_RELAY_SECRET" : "OPENAI_API_KEY");
  const body: Record<string, unknown> = {
    model,
    messages: [
      { role: "system", content: system },
      { role: "user", content: user },
    ],
    response_format: { type: "json_object" },
  };
  // Muse Spark is a reasoning model; low effort keeps latency down.
  if (isMeta) body.reasoning_effort = env("META_REASONING_EFFORT", "low");
  const data = await post(url, { Authorization: `Bearer ${key}` }, body, `${provider} LLM`);
  const message = data.choices?.[0]?.message ?? {};
  if (message.refusal) throw new Error(`${provider} LLM refused: ${String(message.refusal).slice(0, 300)}`);
  if (!message.content) throw new Error(`${provider} LLM returned no content`);
  return parseJSON(message.content);
}
