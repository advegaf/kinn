import logging
import re

from llm import call_llm, env

log = logging.getLogger("story-worker")

SCENES = int(env("SCENES", "3"))

# speaker, then the world line rule, per sender role
SPEAKERS = {
    "elder": (
        "a grandmother's spoken memory",
        "First write one world line that fixes the characters (described without faces), the place, the era and the color palette. ",
    ),
    "family": (
        "a grandson's spoken note to his grandmother about his life now",
        "First write one world line from his point of view that fixes a young man's day, his place, his era (the present day) and the color palette; "
        "keep every face out of frame. ",
    ),
}

# Adapted from Dream Recorder's GPT_SYSTEM_PROMPT (Copyright 2025 Modem, MIT), dreams turned into memories.
SYSTEM_PROMPT = (
    "You are a creative video prompt engineer specializing in Luma Dream Machine. "
    "You receive {speaker} as an English text and a Spanish text that say the same thing. "
    "Split it into exactly {n} consecutive beats, in order. "
    "For each beat, text_en is copied word for word from the English text and text_es is copied word for word "
    "from the Spanish text. Do not paraphrase, fix or skip anything: the {n} text_en excerpts joined together "
    "must equal the whole English text, and the {n} text_es excerpts joined together must equal the whole Spanish text. "
    "{world}"
    "Then for each beat write a video prompt: a single, succinct cinematic sentence for a wide 21:9 frame that restates "
    "the world line and shows what happens in that beat, so all {n} clips feel like one film. "
    "Be specific about useful visual elements and emotional tone: the place, the light, the objects, "
    "the textures, the weather and the feeling of the moment. "
    "The look is warm, nostalgic and painterly, soft and grainy like a dream or a faded memory. "
    "Never include on-screen text, letters or signs, and never show close-up faces "
    "(show people from behind, at a distance, or as small figures in the scene). "
    "Also write a short warm title in English (under 8 words) and the same title in Spanish. "
    'Respond with only a JSON object: {{"title": "...", "title_es": "...", "world": "...", '
    '"scenes": [{{"text_en": "...", "text_es": "...", "prompt": "..."}}]}}'
)


def find_beats(text, excerpts):
    """Start offsets of each excerpt in text, searched in order with flexible whitespace. None if any is missing."""
    offsets, cursor = [], 0
    for excerpt in excerpts:
        words = str(excerpt or "").split()
        if not words:
            return None
        m = re.compile(r"\s+".join(map(re.escape, words)), re.I).search(text, cursor)
        if not m:
            return None
        offsets.append(m.start())
        cursor = m.end()
    return offsets


def split_beats(text, n):
    """Fallback: n roughly equal groups of sentences (words if too few). Returns (offsets, excerpts)."""
    pieces = [m for m in re.finditer(r"\S.*?(?:[.!?]+(?=\s|$)|$)", text, re.S)]
    if len(pieces) < n:
        pieces = list(re.finditer(r"\S+", text))
    if len(pieces) < n:
        raise RuntimeError(f"Story too short for {n} scenes")
    offsets, j = [0], 0
    for k in range(1, n):
        target = len(text) * k / n
        # the piece start nearest the target, leaving at least one piece for each remaining beat
        j = min(range(j + 1, len(pieces) - (n - k) + 1), key=lambda i: abs(pieces[i].start() - target))
        offsets.append(pieces[j].start())
    bounds = offsets + [len(text)]
    return offsets, [text[bounds[i] : bounds[i + 1]].strip() for i in range(n)]


def beat_texts(text, excerpts, n, label):
    offsets = find_beats(text, excerpts)
    if offsets is None:
        log.warning("%s excerpts did not match the text, splitting evenly", label)
        return split_beats(text, n)
    # each beat runs to the next beat's start, so words the model skipped are not lost
    offsets[0] = 0
    bounds = offsets[1:] + [len(text)]
    return offsets, [text[offsets[i] : bounds[i]].strip() for i in range(n)]


def ask_beats(system, user, n):
    for attempt in range(2):
        out = call_llm(system, user)
        beats = out.get("scenes") if isinstance(out.get("scenes"), list) else []
        prompts = [str((b or {}).get("prompt") or "").strip() if isinstance(b, dict) else "" for b in beats]
        if len(beats) == n and all(prompts):
            return out, beats, prompts
        log.warning("LLM returned %d beats (want %d), attempt %d", len(beats), n, attempt + 1)
    raise RuntimeError(f"LLM did not return {n} scenes with prompts")


def make_scenes(msg, role, n=None):
    """Beats for one message. start and end are fractions of the translation, the text the receiver hears."""
    n = n or SCENES
    transcript = (msg.get("transcript") or "").strip()
    translation = (msg.get("translation") or "").strip() or transcript
    spanish_source = str(msg.get("source_lang") or "es").startswith("es")
    en_text, es_text = (translation, transcript) if spanish_source else (transcript, translation)
    speaker, world_rule = SPEAKERS.get(role, SPEAKERS["family"])
    system = SYSTEM_PROMPT.format(n=n, speaker=speaker, world=world_rule)
    user = f"English text:\n{en_text}\n\nSpanish text:\n{es_text}"
    out, beats, prompts = ask_beats(system, user, n)
    world = str(out.get("world") or "").strip()
    en_off, en = beat_texts(en_text, [b.get("text_en") for b in beats], n, "English")
    es_off, es = beat_texts(es_text, [b.get("text_es") for b in beats], n, "Spanish")
    heard_off = en_off if spanish_source else es_off
    total = max(len(translation), 1)
    starts = [round(o / total, 3) for o in heard_off] + [1.0]
    starts[0] = 0.0
    scenes = [
        {"start": starts[i], "end": starts[i + 1], "text_es": es[i], "text_en": en[i], "prompt": prompts[i]}
        for i in range(n)
    ]
    title = str(out.get("title") or "A memory").strip()
    return {"title": title, "title_es": str(out.get("title_es") or title).strip(), "world": world, "scenes": scenes}
