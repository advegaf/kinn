import DEMO from "./demo-stories.json" with { type: "json" };

// t_en, t_es: measured [start, end] of the beat as fractions of the English and Spanish narration mp3.
export type DemoScene = {
  image: string;
  text_es: string;
  text_en: string;
  prompt?: string;
  t_en?: number[];
  t_es?: number[];
  video_path?: string;
  thumb_path?: string;
};
export type DemoStory = {
  id: string;
  days_ago: number;
  title: string;
  title_es: string;
  transcript: string;
  translation: string;
  ask_about: string[];
  scenes: DemoScene[];
};
export type DemoReply = {
  after_story: string;
  minutes_after: number;
  title: string;
  title_es: string;
  translation_es: string;
  text_en: string;
  scenes: DemoScene[];
};

export const STORIES = DEMO.stories as DemoStory[];
export const REPLIES = DEMO.replies as DemoReply[];
export const replyId = (i: number) => `r${i + 1}`;

// seed-demo uploads these narration mp3s to audio/demo/. s5 and s6 have none.
export const DEMO_AUDIO = new Set(["s1", "s2", "s3", "s4", "r1", "r2"]);

const unmark = (s: string) => s.replace(/\*/g, "");

function tokens(s: string): Set<string> {
  return new Set(
    s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().split(/[^a-z]+/).filter((w) => w.length >= 4),
  );
}

// The 70% rule stops a long free note that shares a few common words from matching a canned one.
export function scoreMatch(heard: string, candidates: string[]): { index: number; score: number; heard: number } {
  const h = tokens(heard);
  const scores = candidates.map((c) => {
    const t = tokens(c);
    let n = 0;
    for (const w of h) if (t.has(w)) n++;
    return n;
  });
  const best = Math.max(-1, ...scores);
  const i = scores.indexOf(best);
  const tied = scores.filter((s) => s === best).length > 1;
  const strong = best >= 3 && best >= 0.7 * h.size && !tied;
  return { index: strong ? i : -1, score: Math.max(0, best), heard: h.size };
}

// Same rule as the story worker: first start 0, last end 1, each end is the next start.
function timed(full: string, beats: string[]): { start: number; end: number }[] {
  const text = unmark(full);
  const len = Math.max(1, text.length);
  let cursor = 0;
  const starts = beats.map((b, i) => {
    const idx = text.indexOf(unmark(b), cursor);
    if (idx < 0) return i / beats.length;
    cursor = idx + unmark(b).length;
    return idx / len;
  });
  starts[0] = 0;
  return starts.map((start, i) => ({ start, end: i + 1 < starts.length ? starts[i + 1] : 1 }));
}

function spans(scenes: DemoScene[], key: "t_en" | "t_es", full: string, beats: string[]) {
  if (scenes.every((sc) => sc[key]?.length === 2)) return scenes.map((sc) => ({ start: sc[key]![0], end: sc[key]![1] }));
  return timed(full, beats);
}

// The phone times English by t_en. The Hearth times the Spanish by t_es.
const measured = (sc: DemoScene) => ({ ...(sc.t_en ? { t_en: sc.t_en } : {}), ...(sc.t_es ? { t_es: sc.t_es } : {}) });
const clip = (sc: DemoScene) => (sc.video_path ? { video_path: sc.video_path, thumb_path: sc.thumb_path } : {});

// start and end follow the English mp3, which is what the family hears.
export function elderFields(s: DemoStory) {
  const times = spans(s.scenes, "t_en", s.translation, s.scenes.map((sc) => sc.text_en));
  const scenes = s.scenes.map((sc, i) => ({
    ...times[i],
    ...measured(sc),
    ...clip(sc),
    text_es: sc.text_es,
    text_en: sc.text_en,
    image_path: `demo/${sc.image}.jpg`,
  }));
  return {
    transcript: s.transcript,
    translation: s.translation,
    ask_about: s.ask_about,
    cultural_notes: [],
    translated_path: DEMO_AUDIO.has(s.id) ? `demo/${s.id}-en.mp3` : null,
    story: {
      title: s.title,
      title_es: s.title_es,
      status: "ready",
      scenes,
      image_paths: scenes.map((sc) => `images/${sc.image_path}`),
    },
    status: "ready",
    error: null,
  };
}

// start and end follow the Spanish mp3, which is what the elder hears.
export function replyFields(r: DemoReply, i: number) {
  const times = spans(r.scenes, "t_es", r.translation_es, r.scenes.map((sc) => sc.text_es));
  const scenes = r.scenes.map((sc, k) => ({
    ...times[k],
    ...measured(sc),
    ...clip(sc),
    text_es: sc.text_es,
    text_en: sc.text_en,
    image_path: `demo/${sc.image}.jpg`,
  }));
  const id = replyId(i);
  return {
    transcript: r.text_en,
    translation: r.translation_es,
    ask_about: [],
    cultural_notes: [],
    translated_path: DEMO_AUDIO.has(id) ? `demo/${id}-es.mp3` : null,
    story: {
      title: r.title,
      title_es: r.title_es,
      status: "ready",
      scenes,
      image_paths: scenes.map((sc) => `images/${sc.image_path}`),
    },
    status: "ready",
    error: null,
  };
}

type Row = { id: string; transcript: string | null };

export function pickStory(heard: string, existing: Row[]): DemoStory | null {
  const used = new Set(existing.map((m) => m.transcript));
  const i = scoreMatch(heard, STORIES.map((s) => s.transcript)).index;
  if (i >= 0) return STORIES[i];
  if (heard.trim()) return null;
  return STORIES.find((s) => !used.has(s.transcript)) ?? STORIES[0];
}

// When Scribe heard nothing (failure or no quota), take the next unused reply so the scripted demo
// still runs. Heard words that match no reply give index -1, a free note.
export function pickReply(heard: string, existing: Row[]): { index: number; score: number; heard: number } {
  const m = scoreMatch(heard, REPLIES.map((r) => r.text_en));
  if (m.index >= 0 || heard.trim()) return m;
  const used = new Set(existing.map((r) => r.transcript));
  const next = REPLIES.findIndex((r) => !used.has(r.text_en));
  return { ...m, index: next >= 0 ? next : 0 };
}

const PENDING: Record<string, string> = { en: "(translation pending)", es: "traducci\u00f3n pendiente" };

export function headline(text: string): string {
  const words = text.trim().split(/\s+/).filter(Boolean).slice(0, 6);
  return words.join(" ").replace(/[\s.,;:!?\u00bf\u00a1"'\u2026]+$/u, "");
}

// No LLM in demo mode, so she hears the original audio and the other language title says
// the translation is pending.
export function freeFields(heard: string, sourceLang: string) {
  const own = headline(heard) || (sourceLang === "es" ? "Un mensaje" : "A note");
  const title = sourceLang === "es" ? PENDING.en : own;
  const title_es = sourceLang === "es" ? own : PENDING.es;
  return {
    transcript: heard,
    translation: null,
    translated_path: null,
    ask_about: [],
    cultural_notes: [],
    story: { title, title_es, status: "ready", scenes: [], image_paths: [] },
    status: "ready",
    error: null,
  };
}

// elderRows must be newest first.
export function replyTarget(r: DemoReply, elderRows: Row[]): string | null {
  const story = STORIES.find((s) => s.id === r.after_story);
  return (elderRows.find((m) => m.transcript === story?.transcript) ?? elderRows[0])?.id ?? null;
}
