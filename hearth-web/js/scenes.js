import config from '../config.js';
import { $ } from './dom.js';
import { setCaption } from './captions.js';

const root = $('hearth');
const video = $('video');
const media = $('media');
const imgs = [$('img-a'), $('img-b')];
const playing = () => root.dataset.state === 'playing';

// Scenes of the story now playing: [{ start, end, image, video, text, textEn }], start and end as
// fractions 0..1 of the narration. The current scene is the last one with start <= progress.
let scenes = [];
let sceneIndex = -1;
let progress = 0;
let kbFlip = 0;
let videoSwap = 0;

// The story worker writes story = { status: 'generating' | 'error' } while working, so only a
// story with scenes, a video or images counts. A family reply uses the story it answers when the
// row says so (demo reply_to), otherwise the newest real story in the thread.
export const hasStory = (st) => Boolean(st && (st.scenes?.length || st.video_path || st.image_paths?.length));

export function storyFor(msg, messages) {
  if (hasStory(msg.story)) return msg.story;
  const related = msg.reply_to && messages.find((m) => m.id === msg.reply_to);
  if (hasStory(related?.story)) return related.story;
  for (let i = messages.length - 1; i >= 0; i--) if (hasStory(messages[i].story)) return messages[i].story;
  return null;
}

// The story a family reply answers: its reply_to, else her newest story before it.
export function answeredStory(msg, messages, isMine) {
  const related = msg.reply_to && messages.find((m) => m.id === msg.reply_to);
  if (hasStory(related?.story)) return related.story;
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i];
    if (isMine(m) && hasStory(m.story) && m.created_at <= msg.created_at) return m.story;
  }
  return storyFor(msg, messages);
}

// Each beat's text_es offset within the transcript, as spans, or null if any beat is missing.
function textSpans(list, transcript) {
  const at = [];
  let cursor = 0;
  for (const s of list) {
    const i = transcript.indexOf(s.text_es, cursor);
    if (i < 0) return null;
    at.push(i);
    cursor = i + s.text_es.length;
  }
  const n = list.length;
  return at.map((a, i) => [i ? a / transcript.length : 0, i < n - 1 ? at[i + 1] / transcript.length : 1]);
}

// A family reply with its own scenes uses the worker's start/end. A story's own beats use their
// t_es spans in the Spanish audio, else text_es offsets within the Spanish she hears.
// Otherwise even spacing.
function spansFor(list, transcript, mine, own) {
  const timed = list.every((s) => Number.isFinite(s.start));
  if (!mine && own && timed) return list.map((s) => [s.start, s.end]);
  if (own && list.every((s) => Array.isArray(s.t_es))) return list.map((s) => s.t_es);
  const byText = transcript && list.every((s) => s.text_es) ? textSpans(list, transcript) : null;
  if (byText) return byText;
  if (own && timed) return list.map((s) => [s.start, s.end]);
  return list.map((_, i) => [i / list.length, (i + 1) / list.length]);
}

// The worker marks emphasis as *words*; the strip shows them plain.
const plain = (t) => t.replace(/\*([^*]+)\*/g, '$1');

// m is backend.media(story). A family reply without its own scenes spreads the related story's
// scenes evenly over its length.
export function buildScenes(m, story, msg, mine, untranslated) {
  let list = m.scenes?.length ? m.scenes : m.images.map((image) => ({ image }));
  if (!m.scenes?.length && m.video) list = [{ image: m.images[0] || '', video: m.video }];
  if (!list.length) list = [{}];
  const own = mine || story === msg.story;
  const transcript = own ? (mine ? msg.transcript : msg.translation) || '' : '';
  const spans = spansFor(list, transcript, mine, own);
  const title = story?.title_es || story?.title || '';
  const fallbackText = (mine ? title : untranslated ? msg.transcript : msg.translation) || '';
  const fallbackEn = mine ? story?.title || '' : msg.transcript || '';
  return list.map((s, i) => {
    const en = untranslated ? 'traducci\u00f3n pendiente' : plain(own ? s.text_en || fallbackEn : fallbackEn);
    return {
      image: s.image || '',
      video: s.video || '',
      text: plain(own ? s.text_es || fallbackText : fallbackText),
      textEn: config.subs || untranslated ? en : '',
      start: spans[i][0],
      end: spans[i][1],
    };
  });
}

export function startScenes(list) {
  scenes = list;
  sceneIndex = -1;
  progress = 0;
  // DEBUG ?at=0..1 freezes the strip at that point of the narration, with no sound.
  setProgress(config.at ?? 0);
  // Fetch the later stills only after the current one has its request in.
  scenes.forEach((s, i) => { if (s.image && i !== sceneIndex) new Image().src = s.image; });
}

export function setProgress(p) {
  if (!Number.isFinite(p) || !scenes.length) return;
  progress = Math.max(progress, Math.min(1, Math.max(0, p)));
  let i = 0;
  for (let k = 1; k < scenes.length; k++) if (scenes[k].start <= progress) i = k;
  if (i !== sceneIndex) showScene(i);
}

// Crossfade to scene i: the incoming still fades in over 2s, the outgoing one out a bit faster.
// A scene clip plays over its still once it is running.
function showScene(i) {
  const first = sceneIndex < 0;
  sceneIndex = i;
  const sc = scenes[i];
  clearTimeout(videoSwap);
  if (sc.image) {
    media.dataset.kind = 'images';
    crossfadeImage(sc.image);
  } else if (!sc.video) {
    media.dataset.kind = 'warm';
    imgs.forEach((img) => img.classList.remove('on'));
  }
  if (sc.video) {
    // Wait for the previous clip to fade out before swapping the source.
    const swap = () => { video.src = sc.video; video.play().catch((err) => console.warn('video play', err.message)); };
    if (first || !video.getAttribute('src')) swap(); else videoSwap = setTimeout(swap, 700);
    if (!sc.image) media.dataset.kind = 'video';
  } else if (video.getAttribute('src')) {
    video.pause();
  }
  setCaption(sc.text, sc.textEn, !first && config.at == null);
}

function crossfadeImage(src) {
  const img = imgs[kbFlip];
  const other = imgs[1 - kbFlip];
  kbFlip = 1 - kbFlip;
  img.classList.remove('on');
  img.style.setProperty('--kx', `${(Math.random() * 4 - 2).toFixed(2)}%`);
  img.style.setProperty('--ky', `${(Math.random() * 3 - 1.5).toFixed(2)}%`);
  img.src = src;
  const show = () => requestAnimationFrame(() => requestAnimationFrame(() => {
    if (img.getAttribute('src') !== src) return;
    img.classList.add('on');
    other.classList.remove('on');
  }));
  (img.decode ? img.decode() : Promise.resolve()).then(show, show);
}

video.addEventListener('playing', () => {
  if (playing() && scenes[sceneIndex]?.video) media.dataset.kind = 'video';
});
video.addEventListener('error', () => {
  if (!playing() || !video.getAttribute('src')) return;
  console.warn('video failed', video.src);
  media.dataset.kind = scenes[sceneIndex]?.image ? 'images' : 'warm';
});

export function teardown() {
  video.pause();
  video.removeAttribute('src');
  video.load();
  imgs.forEach((img) => img.classList.remove('on'));
  scenes = [];
  sceneIndex = -1;
}
