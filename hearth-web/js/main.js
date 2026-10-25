// Hearth state machine and input. The state set and the one-button flow are adapted from
// Dream Recorder's state-manager.js by Modem, github.com/modem-works/dream-recorder (MIT).

import config from '../config.js';
import { SupabaseBackend, DemoBackend } from './backend.js';
import { MicRecorder, FakeRecorder, resumeAudio } from './recorder.js';
import { loadRect, applyRect, loadStrip, applyStrip, inRect, toPct, startCalibration, startTemplate } from './calibrate.js';

const S = { CLOCK: 'clock', WAITING: 'waiting', RECORDING: 'recording', SENDING: 'sending', PLAYING: 'playing', ERROR: 'error' };

const DEBOUNCE_MS = 250;
const DOUBLE_MS = 650; // a second press this soon after the first counts as a double press
const MIN_RECORD_MS = 900;
const MAX_RECORD_MS = 3 * 60 * 1000;
const MIN_SENDING_MS = 1400;
const READY_TIMEOUT_MS = 90 * 1000;
const ERROR_MS = 3500;
const LINGER_MS = 1500;
const HISTORY = 7;
const HEARD_KEY = 'hearth.heard';

const $ = (id) => document.getElementById(id);
const root = $('hearth');
const html = document.documentElement;
const audio = $('audio');
const video = $('video');
const media = $('media');
const imgs = [$('img-a'), $('img-b')];

const backend = config.demo ? new DemoBackend(config) : new SupabaseBackend(config);
const recorder = config.demo ? new FakeRecorder() : new MicRecorder();
const zone = loadRect();
applyRect(zone);
const strip = loadStrip();
applyStrip(strip);

let state = 'boot';
let enteredAt = 0;
let lastPress = -Infinity;
let messages = [];
const heardLocal = loadHeard();

// ---------- state ----------

function setState(next) {
  if (state === next) return;
  state = next;
  enteredAt = performance.now();
  root.dataset.state = next;
  if (config.debug) console.info('state', next);
}

const partnerName = () => backend.partner?.name || 'tu familia';
const isMine = (m) => m.sender_id === backend.profile?.id;
const unheard = () => messages.filter((m) => !isMine(m) && m.status === 'ready' && !m.heard_at && !heardLocal.has(m.id));
const history = () => messages.filter((m) => !isMine(m) && m.status === 'ready').slice(-HISTORY).reverse();
const idleState = () => (unheard().length ? S.WAITING : S.CLOCK);
const wait = (ms) => new Promise((r) => setTimeout(r, Math.max(0, ms)));

const fmtWd = new Intl.DateTimeFormat('es', { weekday: 'long' });
const fmtMo = new Intl.DateTimeFormat('es', { month: 'long' });
const hm = (d) => `${d.getHours() % 12 || 12}:${String(d.getMinutes()).padStart(2, '0')}`;
const dayLabel = (d) => `${fmtWd.format(d)} ${d.getDate()}`;
const setText = (id, text) => { const el = $(id); if (el.textContent !== text) el.textContent = text; };

// The last question in her family's newest message, if it is short enough to read at a glance.
function recPrompt(name) {
  const latest = messages.filter((m) => !isMine(m) && m.translation).at(-1);
  const q = latest?.translation.match(/¿[^¿?]*\?/g)?.at(-1)?.trim();
  return q && q.length <= 60 ? q : `cuéntale a ${name} lo que recuerdas`;
}

function renderText() {
  const name = partnerName();
  const latest = unheard().at(-1);
  if (latest) {
    const d = new Date(latest.created_at);
    setText('waiting-label', `${dayLabel(d)}, ${hm(d)}`);
    setText('waiting-line', `${name} te escribió`);
    const title = storyFor(latest)?.title_es;
    setText('waiting-sub', title ? `sobre «${title}»` : 'presiona el botón para escucharla');
  }
  setText('rec-prompt', recPrompt(name));
  setText('send-line', 'guardando tu historia');
  setText('send-sub', `se la mando a ${name}`);
}

function setStatus(text) {
  $('status').textContent = text;
}

// Demo mode keeps nothing between loads, so the canned reply is new every time.
function loadHeard() {
  if (config.demo) return new Set();
  try { return new Set(JSON.parse(localStorage.getItem(HEARD_KEY) || '[]')); } catch { return new Set(); }
}

function saveHeard() {
  if (config.demo) return;
  try { localStorage.setItem(HEARD_KEY, JSON.stringify([...heardLocal].slice(-200))); } catch {}
}

// ---------- sync ----------

let refreshing = false;
let refreshAgain = false;
let failures = 0;

async function refresh() {
  if (refreshing) { refreshAgain = true; return; }
  refreshing = true;
  try {
    messages = await backend.fetchMessages();
    failures = 0;
    setStatus('');
  } catch (err) {
    failures += 1;
    if (failures >= 3) setStatus('sin conexión');
    console.warn('refresh failed', err?.message || err);
  } finally {
    refreshing = false;
  }
  renderText();
  if (state === S.CLOCK || state === S.WAITING) setState(idleState());
  if (refreshAgain) { refreshAgain = false; refresh(); }
}

// ---------- input ----------

function press(source) {
  const now = performance.now();
  if (now - lastPress < DEBOUNCE_MS) return;
  lastPress = now;
  unlock();
  const age = now - enteredAt;
  if (config.debug) console.info('press', source, state);

  switch (state) {
    case S.CLOCK:
      return startRecording();
    case S.WAITING:
      return play(unheard().at(-1));
    case S.RECORDING:
      if (age < DOUBLE_MS) { cancelRecording(); return replay(); }
      return stopAndSend();
    case S.PLAYING:
      if (age < DOUBLE_MS) return; // bounce guard, and keeps a double press from stopping its own replay
      return stopPlayback();
    case S.ERROR:
      clearTimeout(errorTimer);
      return setState(idleState());
    default:
      return; // sending and boot ignore presses
  }
}

const PRESS_KEYS = new Set(['Enter', 'NumpadEnter', ' ', 'Spacebar', 'MediaPlayPause', 'AudioVolumeUp', 'VolumeUp']);

addEventListener('keydown', (e) => {
  if (e.repeat || !PRESS_KEYS.has(e.key)) return;
  e.preventDefault();
  press('key');
});

addEventListener('pointerdown', (e) => {
  if (config.calibrate || !e.isPrimary) return;
  const p = toPct(e);
  if (inRect(zone, p.x, p.y)) press('button');
  else if (inRect(strip, p.x, p.y)) press('strip');
});

addEventListener('contextmenu', (e) => e.preventDefault());

// Touch pointerdown is not a user activation in Chromium; pointerup and keydown are.
// Anything that was blocked by autoplay policy gets retried on the next one.
let pendingPlay = null;
function unlock() {
  resumeAudio();
  if (pendingPlay) { const fn = pendingPlay; pendingPlay = null; fn(); }
}
for (const type of ['pointerup', 'touchend', 'keyup']) addEventListener(type, unlock, { passive: true });

// ---------- recording ----------

let recToken = 0;
let recReady = null;
let recTick = 0;
let recMax = 0;
let level = 0;

function setLevel(raw) {
  const target = Math.min(1, raw * 3.2);
  level = target > level ? level * 0.45 + target * 0.55 : level * 0.85 + target * 0.15;
  html.style.setProperty('--level', level.toFixed(3));
}

function startRecording() {
  setState(S.RECORDING);
  const token = ++recToken;
  level = 0;
  html.style.setProperty('--level', '0');
  const started = performance.now();
  const cells = ['c0', 'c1', 'c2', 'c3'].map($);
  const show = (s) => {
    const t = `${String(Math.min(99, Math.floor(s / 60))).padStart(2, '0')}${String(s % 60).padStart(2, '0')}`;
    cells.forEach((el, i) => { if (el.textContent !== t[i]) el.textContent = t[i]; });
  };
  show(0);
  recTick = setInterval(() => show(Math.floor((performance.now() - started) / 1000)), 250);
  recMax = setTimeout(() => state === S.RECORDING && stopAndSend(), MAX_RECORD_MS);

  recReady = recorder.start(setLevel).then(
    () => { if (token !== recToken) recorder.cancel(); },
    (err) => {
      console.error('microphone', err);
      if (token !== recToken) return;
      clearRecTimers();
      showError('No encuentro el micrófono');
      throw err;
    },
  );
  recReady.catch(() => {});
}

function clearRecTimers() {
  clearInterval(recTick);
  clearTimeout(recMax);
}

function cancelRecording() {
  recToken += 1;
  clearRecTimers();
  recorder.cancel();
  html.style.setProperty('--level', '0');
}

async function stopAndSend() {
  clearRecTimers();
  const token = recToken;
  setState(S.SENDING);
  try { await recReady; } catch { return; }
  if (token !== recToken) return;
  const rec = await recorder.stop();
  html.style.setProperty('--level', '0');

  if (rec.durationMs < MIN_RECORD_MS || (!config.demo && !rec.blob.size)) return setState(idleState());

  const started = performance.now();
  try {
    let row = await backend.send(rec);
    if (row.status === 'uploaded' || row.status === 'processing') row = await waitReady(row.id);
    await wait(MIN_SENDING_MS - (performance.now() - started));
    if (row.status !== 'ready') throw new Error(row.error || `status ${row.status}`);
    if (state === S.SENDING) setState(idleState());
  } catch (err) {
    console.error('send failed', err);
    showError('No se pudo enviar. Intenta otra vez.');
  }
  refresh();
}

async function waitReady(id) {
  const deadline = performance.now() + READY_TIMEOUT_MS;
  while (performance.now() < deadline) {
    await wait(2000);
    await refresh();
    const m = messages.find((x) => x.id === id);
    if (m && (m.status === 'ready' || m.status === 'error')) return m;
  }
  return { id, status: 'error', error: 'timed out waiting for process-message' };
}

// ---------- error ----------

let errorTimer = 0;
function showError(text, hold = false) {
  $('err-line').textContent = text;
  setState(S.ERROR);
  clearTimeout(errorTimer);
  if (!hold) errorTimer = setTimeout(() => state === S.ERROR && setState(idleState()), ERROR_MS);
}

// ---------- playback ----------

let playingId = null;
let lingerTimer = 0;
let speechTimer = 0;
let progressTimer = 0;
let cleanupTimer = 0;
let replayCursor = 0;
let lastReplayAt = -Infinity;

// Scenes of the story now playing: [{ start, end, image, video, text }], start and end as
// fractions 0..1 of the narration. The current scene is the last one with start <= progress.
let scenes = [];
let sceneIndex = -1;
let progress = 0;

const SPEECH_RATE = 0.95;
const SPEECH_WPM = 160; // Spanish at the demo rate, for the elapsed time estimate

// The story worker writes story = { status: 'generating' | 'error' } while working, so only a
// story with scenes, a video or images counts. A family reply uses the story it answers when the
// row says so (demo reply_to), otherwise the newest real story in the thread.
const hasStory = (st) => Boolean(st && (st.scenes?.length || st.video_path || st.image_paths?.length));

function storyFor(msg) {
  if (hasStory(msg.story)) return msg.story;
  const related = msg.reply_to && messages.find((m) => m.id === msg.reply_to);
  if (hasStory(related?.story)) return related.story;
  for (let i = messages.length - 1; i >= 0; i--) if (hasStory(messages[i].story)) return messages[i].story;
  return null;
}

function replay() {
  const list = history();
  if (!list.length) return setState(idleState());
  const now = performance.now();
  replayCursor = now - lastReplayAt < 60000 ? (replayCursor + 1) % list.length : 0;
  lastReplayAt = now;
  play(list[replayCursor], true);
}

// Her own story is timed against her Spanish words: each beat's text_es offset within the
// transcript. Otherwise the worker's start/end (timed on the translation), otherwise even spacing.
// A family reply spreads the related story's scenes evenly over its own length.
function buildScenes(story, msg, mine) {
  const m = backend.media(story);
  let list = m.scenes?.length ? m.scenes : m.images.map((image) => ({ image }));
  if (!m.scenes?.length && m.video) list = [{ image: m.images[0] || '', video: m.video }];
  if (!list.length) list = [{}];
  const n = list.length;
  const transcript = mine ? msg.transcript || '' : '';
  let spans = null;
  if (transcript && list.every((s) => s.text_es)) {
    const at = [];
    let cursor = 0;
    for (const s of list) {
      const i = transcript.indexOf(s.text_es, cursor);
      if (i < 0) break;
      at.push(i);
      cursor = i + s.text_es.length;
    }
    if (at.length === n) spans = at.map((a, i) => [i ? a / transcript.length : 0, i < n - 1 ? at[i + 1] / transcript.length : 1]);
  }
  if (!spans && mine && list.every((s) => Number.isFinite(s.start))) spans = list.map((s) => [s.start, s.end]);
  if (!spans) spans = list.map((_, i) => [i / n, (i + 1) / n]);
  const fallbackText = mine ? story?.title_es || story?.title || '' : msg.translation || '';
  return list.map((s, i) => ({
    image: s.image || '',
    video: s.video || '',
    text: mine ? s.text_es || fallbackText : fallbackText,
    start: spans[i][0],
    end: spans[i][1],
  }));
}

function play(msg, isReplay = false) {
  if (!msg) return setState(idleState());
  clearPlayTimers();
  playingId = msg.id;
  const mine = isMine(msg);
  const story = storyFor(msg);
  // Her own story plays back in her own voice and words; a reply plays its Spanish translation.
  const spoken = mine ? msg.transcript || '' : msg.translation || '';
  const lang = mine ? msg.source_lang || 'es' : msg.target_lang || 'es';
  scenes = buildScenes(story, msg, mine);
  sceneIndex = -1;
  progress = 0;

  const day = dayLabel(new Date(msg.created_at));
  $('play-stamp').textContent = mine ? `tu historia, ${day}` : `de ${partnerName()}, ${day}`;
  renderText();
  setState(S.PLAYING);

  if (!isReplay) {
    heardLocal.add(msg.id);
    saveHeard();
    backend.markHeard(msg.id).catch((err) => console.warn('markHeard', err));
  }

  // DEBUG ?at=0..1 freezes the strip at that point of the narration, with no sound.
  setProgress(config.at ?? 0);
  // Fetch the later stills only after the current one has its request in.
  scenes.forEach((s, i) => { if (s.image && i !== sceneIndex) new Image().src = s.image; });
  if (config.at != null) return;

  const id = msg.id;
  const url = mine ? backend.originalUrl(msg) : backend.audioUrl(msg);
  if (url) {
    audio.src = url;
    audio.ontimeupdate = () => {
      const d = audio.duration;
      if (playingId === id && d > 0 && Number.isFinite(d)) setProgress(audio.currentTime / d);
    };
    audio.onended = () => { setProgress(1); finish(id); };
    audio.onerror = () => {
      console.warn('audio failed', url);
      if (spoken) speak(spoken, lang, id);
      else finish(id, 4000);
    };
    const attempt = () => audio.play().catch((err) => {
      if (err.name === 'NotAllowedError') pendingPlay = attempt;
      else console.warn('audio play', err.message);
    });
    attempt();
  } else if (spoken) {
    speak(spoken, lang, id);
  } else {
    finish(id, 6000);
  }
}

// Scenes follow the voice's word boundaries. When none have come for a while (some voices
// never send them, some stall), elapsed time over an estimated duration carries on from the last one.
function speak(text, lang, id) {
  const estMs = (text.split(/\s+/).length / SPEECH_WPM) * 60000 / SPEECH_RATE;
  let mark = { at: performance.now(), p: 0 };
  clearInterval(progressTimer);
  progressTimer = setInterval(() => {
    const since = performance.now() - mark.at;
    if (playingId === id && since > 1500) setProgress(mark.p + since / estMs);
  }, 250);
  if (!('speechSynthesis' in window)) return finish(id, estMs + 1500);
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang === 'es' ? 'es-MX' : lang || 'es-MX';
  u.rate = SPEECH_RATE;
  const voice = speechSynthesis.getVoices().find((v) => v.lang.toLowerCase().startsWith((lang || 'es').toLowerCase()));
  if (voice) u.voice = voice;
  u.onboundary = (e) => {
    if (playingId !== id) return;
    mark = { at: performance.now(), p: e.charIndex / text.length };
    setProgress(mark.p);
  };
  u.onend = () => { setProgress(1); finish(id); };
  speechSynthesis.cancel();
  speechSynthesis.speak(u);
  // onend is unreliable in some WebViews, so cap the wait.
  speechTimer = setTimeout(() => finish(id), Math.max(3000 + text.length * 90, estMs + 3000));
}

function finish(id, delay = LINGER_MS) {
  if (state !== S.PLAYING || playingId !== id) return;
  clearTimeout(lingerTimer);
  lingerTimer = setTimeout(() => { if (state === S.PLAYING && playingId === id) stopPlayback(); }, delay);
}

function clearPlayTimers() {
  clearTimeout(lingerTimer);
  clearTimeout(speechTimer);
  clearInterval(progressTimer);
  clearTimeout(cleanupTimer);
}

function stopPlayback() {
  clearPlayTimers();
  playingId = null;
  pendingPlay = null;
  audio.onended = audio.onerror = audio.ontimeupdate = null;
  audio.pause();
  if ('speechSynthesis' in window) speechSynthesis.cancel();
  setState(idleState());
  // Let the strip fade before tearing the media down.
  cleanupTimer = setTimeout(() => {
    if (state === S.PLAYING) return;
    video.pause();
    video.removeAttribute('src');
    video.load();
    imgs.forEach((img) => img.classList.remove('on'));
    scenes = [];
    sceneIndex = -1;
  }, 900);
}

// ---------- media ----------

function setProgress(p) {
  if (!Number.isFinite(p) || !scenes.length) return;
  progress = Math.max(progress, Math.min(1, Math.max(0, p)));
  let i = 0;
  for (let k = 1; k < scenes.length; k++) if (scenes[k].start <= progress) i = k;
  if (i !== sceneIndex) showScene(i);
}

let kbFlip = 0;
let videoSwap = 0;

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
  setCaption(sc.text, !first && config.at == null);
}

video.addEventListener('playing', () => {
  if (state === S.PLAYING && scenes[sceneIndex]?.video) media.dataset.kind = 'video';
});
video.addEventListener('error', () => {
  if (state !== S.PLAYING || !video.getAttribute('src')) return;
  console.warn('video failed', video.src);
  media.dataset.kind = scenes[sceneIndex]?.image ? 'images' : 'warm';
});

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

// The caption fades out, takes the new beat, and fades back in with the scene.
let capFade = null;
function setCaption(text, fade) {
  const cap = $('play-cap');
  const apply = () => { cap.textContent = text; fitCaption(cap); };
  if (capFade) { capFade.cancel(); capFade = null; }
  if (!fade || !cap.animate || cap.textContent === text) { apply(); return; }
  const out = cap.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 700, easing: 'ease-in', fill: 'forwards' });
  capFade = out;
  out.onfinish = () => {
    apply();
    capFade = cap.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 1600, easing: 'ease-out' });
    out.cancel();
  };
}

// Largest caption size that keeps the beat to 2 lines (large) or 3 lines (smaller tiers).
// CSS also clamps to 3 lines, so nothing spills off the strip even before fonts load.
const CAP_TIERS = [['', 2], ['m', 3], ['s', 3], ['xs', 3]];
function fitCaption(cap) {
  for (const [tier, maxLines] of CAP_TIERS) {
    if (tier) cap.dataset.size = tier; else delete cap.dataset.size;
    const lineH = parseFloat(getComputedStyle(cap).fontSize) * 1.1;
    if (cap.scrollHeight <= lineH * maxLines + 2) return;
  }
}
document.fonts?.ready.then(() => { if (state === S.PLAYING) fitCaption($('play-cap')); });

// ---------- clock (Dream Recorder clock.js, 12 hour) ----------

let colonOn = true;
function tickClock() {
  const now = new Date();
  setText('clock-h', String(now.getHours() % 12 || 12));
  setText('clock-m', String(now.getMinutes()).padStart(2, '0'));
  colonOn = !colonOn;
  $('clock-colon').classList.toggle('off', !colonOn);
  setText('day-num', String(now.getDate()));
  setText('day-wd', fmtWd.format(now).toLowerCase());
  setText('day-mo', fmtMo.format(now).toLowerCase());
}

// ---------- boot ----------

async function keepAwake() {
  try { await navigator.wakeLock?.request('screen'); } catch {}
}

document.addEventListener('visibilitychange', () => {
  if (document.hidden) return;
  keepAwake();
  if (backend.thread) refresh();
});

async function connect() {
  try {
    await backend.init();
  } catch (err) {
    console.error('backend init failed', err);
    setStatus('sin conexión');
    setTimeout(connect, 10000);
    return;
  }
  setStatus('');
  await refresh();
  backend.subscribe(refresh);
  setState(idleState());
  if (config.demo && config.startState) enterDemoState(config.startState);
}

// ?demo=1&state=... jumps straight into a state for screenshots (&msg= and &at= for playing).
function enterDemoState(s) {
  if (s === S.RECORDING) startRecording();
  else if (s === S.SENDING) setState(S.SENDING);
  else if (s === S.PLAYING) {
    // &msg=<id> plays that row. With &at and no msg, her newest story, so frozen frames show its beats.
    const pick = messages.find((m) => m.id === config.startMsg)
      || (config.at != null ? messages.filter((m) => isMine(m) && hasStory(m.story)).at(-1) : null);
    if (pick) play(pick, true);
    else play(unheard().at(-1) || history()[0]);
  }
  else if (s === S.ERROR) showError('No se pudo enviar. Intenta otra vez.', true);
}

tickClock();
setInterval(tickClock, 1000);
keepAwake();
if (config.calibrate) startCalibration(zone, strip, () => state);

if (config.template) {
  startTemplate(zone, strip);
} else if (!config.demo && !config.configured) {
  setState(S.CLOCK);
  setStatus('falta configurar');
  console.warn('Hearth is not configured. Set config.local.js or pass ?thread= and ?profile=.');
} else {
  setState(S.CLOCK);
  connect();
}

window.hearth = { press, get state() { return state; }, refresh };
