// Hearth state machine and input. The state set and the one-button flow are adapted from
// Dream Recorder's state-manager.js by Modem, github.com/modem-works/dream-recorder (MIT).

import config from '../config.js';
import { SupabaseBackend, DemoBackend } from './backend.js';
import { MicRecorder, FakeRecorder, resumeAudio } from './recorder.js';
import { loadRect, applyRect, loadStrip, applyStrip, inRect, toPct, startCalibration, startTemplate } from './calibrate.js';
import { $, setText } from './dom.js';
import { dayLabel, sentAt, tickClock, setFamilyCode } from './clock.js';
import { hasStory, storyFor, buildScenes, startScenes, setProgress, teardown } from './scenes.js';
import { narrate, retryPending, clearTimers, stopAll } from './narration.js';
import { showToast, hideToast } from './toast.js';
import { titles as titlesFor, recPrompt } from './text.js';
import { inPast, pastItem, openPast, nextPast, closePast, renderPast } from './past.js';

const S = { CLOCK: 'clock', WAITING: 'waiting', RECORDING: 'recording', SENDING: 'sending', SAVED: 'saved', PLAYING: 'playing', ERROR: 'error', PAST: 'past' };

const DEBOUNCE_MS = 250;
const BOUNCE_MS = 650; // a press this soon after a state change is a bounce or a shaky double tap
const MIN_RECORD_MS = 900;
const MAX_RECORD_MS = 3 * 60 * 1000;
const MIN_SENDING_MS = 1400;
const READY_TIMEOUT_MS = 90 * 1000;
const ERROR_MS = 3500;
const SAVED_MS = 4000;
const LINGER_MS = 1500;
const PAST_IDLE_MS = 60 * 1000;
const HEARD_KEY = 'hearth.heard';
const SAVED_STATUS = 'tu historia est\u00e1 guardada';

const root = $('hearth');
const html = document.documentElement;
if (config.subs) root.dataset.subs = 'en';

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

function setState(next) {
  if (state === next) return;
  if (state === S.SAVED && $('status').textContent.startsWith(SAVED_STATUS)) setStatus('');
  state = next;
  enteredAt = performance.now();
  root.dataset.state = next;
  if (config.debug) console.info('state', next);
}

const partnerName = () => backend.partner?.name || 'tu familia';
const isMine = (m) => m.sender_id === backend.profile?.id;
const unheard = () => messages.filter((m) => !isMine(m) && m.status === 'ready' && !m.heard_at && !heardLocal.has(m.id));
const past = () => messages.filter((m) => m.status === 'ready').reverse();
const idleState = () => (unheard().length ? S.WAITING : S.CLOCK);
const wait = (ms) => new Promise((r) => setTimeout(r, Math.max(0, ms)));

const titles = (msg) => titlesFor(msg, messages, isMine);

function renderText() {
  const name = partnerName();
  const latest = unheard().at(-1);
  if (latest) {
    const [when, whenEn] = sentAt(new Date(latest.created_at));
    setText('waiting-line', `${name} te escribi\u00f3`);
    setText('waiting-line-en', `${name} wrote to you`);
    const [es, en] = titles(latest);
    setText('waiting-sub', es ? `${when}, sobre \u00ab${es}\u00bb` : when);
    setText('waiting-sub-en', en ? `${whenEn}, about \u00ab${en}\u00bb` : whenEn);
  }
  root.toggleAttribute('data-past', past().length > 0);
  const [prompt, promptEn] = recPrompt(messages, isMine, name);
  setText('rec-prompt', prompt);
  setText('rec-prompt-en', promptEn);
  setText('send-line', 'guardando tu historia');
  setText('send-sub', `se la mando a ${name}`);
  setText('send-sub-en', `sending it to ${name}`);
}

const STATUS_EN = { 'sin conexi\u00f3n': 'offline', 'falta configurar': 'not set up', [SAVED_STATUS]: 'your story is saved' };
function setStatus(text) {
  $('status').textContent = config.subs && STATUS_EN[text] ? `${text} \u00b7 ${STATUS_EN[text]}` : text;
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

let refreshing = false;
let refreshAgain = false;
let failures = 0;
let primed = false;
const toasted = new Set();

async function refresh() {
  if (refreshing) { refreshAgain = true; return; }
  refreshing = true;
  try {
    messages = await backend.fetchMessages();
    if (failures >= 3) setStatus('');
    failures = 0;
    toastNew();
  } catch (err) {
    failures += 1;
    if (failures >= 3) setStatus('sin conexi\u00f3n');
    console.warn('refresh failed', err?.message || err);
  } finally {
    refreshing = false;
  }
  renderText();
  if (state === S.CLOCK || state === S.WAITING) setState(idleState());
  if (refreshAgain) { refreshAgain = false; refresh(); }
}

function press(source, act) {
  const now = performance.now();
  if (now - lastPress < DEBOUNCE_MS) return;
  lastPress = now;
  unlock();
  const age = now - enteredAt;
  if (config.debug) console.info('press', source, state);

  switch (state) {
    case S.CLOCK:
      if (act === 'past' && past().length) return showPast();
      return startRecording();
    case S.PAST:
      if (age < BOUNCE_MS) return;
      if (act === 'back') return leavePast();
      if (act === 'next') { nextPast(); return showPast(); }
      return play(pastItem(), !unheard().some((m) => m.id === pastItem().id));
    case S.WAITING:
      return play(unheard().at(-1));
    case S.RECORDING:
    case S.PLAYING:
      if (age < BOUNCE_MS) return;
      return state === S.RECORDING ? stopAndSend() : stopPlayback();
    case S.ERROR:
      clearTimeout(errorTimer);
      return startRecording();
    case S.SAVED:
      clearTimeout(savedTimer);
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
  else if (inRect(strip, p.x, p.y)) press('strip', e.target.closest?.('[data-act]')?.dataset.act);
});

addEventListener('contextmenu', (e) => e.preventDefault());

// Touch pointerdown is not a user activation in Chromium; pointerup and keydown are.
// Anything that was blocked by autoplay policy gets retried on the next one.
function unlock() {
  resumeAudio();
  retryPending();
}
for (const type of ['pointerup', 'touchend', 'keyup']) addEventListener(type, unlock, { passive: true });

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
      showError('No encuentro el micr\u00f3fono', "Can't find the microphone");
      throw err;
    },
  );
  recReady.catch(() => {});
}

function clearRecTimers() {
  clearInterval(recTick);
  clearTimeout(recMax);
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
    if (state === S.SENDING) showSaved(row);
  } catch (err) {
    console.error('send failed', err);
    showError(SEND_FAILED, SEND_FAILED_EN);
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

const SEND_FAILED = 'No se pudo enviar. Intenta otra vez.';
const SEND_FAILED_EN = "Couldn't send. Try again.";

let errorTimer = 0;
function showError(text, en, hold = false) {
  $('err-line').textContent = text;
  $('err-line-en').textContent = en;
  setState(S.ERROR);
  clearTimeout(errorTimer);
  if (!hold) errorTimer = setTimeout(() => state === S.ERROR && setState(idleState()), ERROR_MS);
}

const busy = () => state === S.RECORDING || state === S.SENDING;

// The first fetch only records what is already there; later arrivals get a toast.
// During playback the newest arrival waits and shows once the story ends.
let queuedToast = null;
function toastNew() {
  const fresh = messages.filter((m) => !isMine(m) && m.status === 'ready' && !toasted.has(m.id));
  for (const m of fresh) toasted.add(m.id);
  if (primed && fresh.length) {
    queuedToast = fresh.at(-1).id;
    if (state !== S.PLAYING) flushToast();
  }
  primed = true;
}

function flushToast() {
  const id = queuedToast;
  queuedToast = null;
  const msg = messages.find((m) => m.id === id);
  if (!msg || heardLocal.has(id) || busy()) return;
  showToast(partnerName(), titles(msg), () => {
    const now = messages.find((m) => m.id === id);
    if (now && !busy()) play(now);
  });
}

// Her story is in. The title shows when the story worker has already named it.
let savedTimer = 0;
function showSaved(row, hold = false) {
  const st = row?.story;
  setText('saved-sub', st?.title_es ? `\u00ab${st.title_es}\u00bb` : '');
  setText('saved-sub-en', st?.title ? `\u00ab${st.title}\u00bb` : '');
  setState(S.SAVED);
  setStatus(SAVED_STATUS);
  clearTimeout(savedTimer);
  if (!hold) savedTimer = setTimeout(() => state === S.SAVED && setState(idleState()), SAVED_MS);
}

let playingId = null;
let lingerTimer = 0;
let cleanupTimer = 0;
let pastTimer = 0;

function showPast() {
  if (!inPast()) openPast(past());
  const msg = pastItem();
  const m = backend.media(storyFor(msg, messages));
  renderPast({ mine: isMine(msg), name: partnerName(), titles: titles(msg), image: m.scenes[0]?.image || m.images[0] });
  setState(S.PAST);
  clearTimeout(pastTimer);
  pastTimer = setTimeout(() => state === S.PAST && leavePast(), PAST_IDLE_MS);
}

function leavePast() {
  clearTimeout(pastTimer);
  closePast();
  setState(idleState());
}

function play(msg, isReplay = false) {
  hideToast();
  clearTimeout(pastTimer);
  if (msg?.id !== pastItem()?.id) closePast();
  if (!msg) return setState(idleState());
  clearPlayTimers();
  playingId = msg.id;
  const mine = isMine(msg);
  const story = storyFor(msg, messages);
  // Her own story plays back in her own voice and words; a reply plays its Spanish translation,
  // or its original while the translation is still pending.
  const untranslated = !mine && !msg.translation;
  const original = mine || untranslated;
  const spoken = (original ? msg.transcript : msg.translation) || '';
  const lang = original ? msg.source_lang || 'es' : msg.target_lang || 'es';
  const list = buildScenes(backend.media(story), story, msg, mine, untranslated);
  $('play-cap').toggleAttribute('data-pending', untranslated);

  const day = dayLabel(new Date(msg.created_at));
  const stamp = $('play-stamp');
  stamp.textContent = mine ? `tu historia, ${day}` : `de ${partnerName()}, ${day}`;
  if (config.subs) {
    const en = document.createElement('span');
    en.className = 'en';
    en.textContent = mine ? 'your story' : `from ${partnerName()}`;
    stamp.append(en);
  }
  renderText();
  setState(S.PLAYING);

  if (!isReplay) {
    heardLocal.add(msg.id);
    saveHeard();
    backend.markHeard(msg.id).catch((err) => console.warn('markHeard', err));
  }

  startScenes(list);
  if (config.at != null) return;

  const id = msg.id;
  const url = original ? backend.originalUrl(msg) : backend.audioUrl(msg);
  narrate(url, spoken, lang, (p) => { if (playingId === id) setProgress(p); }, (delay) => finish(id, delay));
}

function finish(id, delay = LINGER_MS) {
  if (state !== S.PLAYING || playingId !== id) return;
  clearTimeout(lingerTimer);
  lingerTimer = setTimeout(() => { if (state === S.PLAYING && playingId === id) stopPlayback(); }, delay);
}

function clearPlayTimers() {
  clearTimeout(lingerTimer);
  clearTimeout(cleanupTimer);
  clearTimers();
}

function stopPlayback() {
  clearPlayTimers();
  playingId = null;
  stopAll();
  if (inPast()) showPast();
  else setState(idleState());
  flushToast();
  // Let the strip fade before tearing the media down.
  cleanupTimer = setTimeout(() => {
    if (state !== S.PLAYING) teardown();
  }, 900);
}

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
    if (!config.demo) setFamilyCode(backend.thread.id.slice(0, 6).toUpperCase());
  } catch (err) {
    console.error('backend init failed', err);
    setStatus('sin conexi\u00f3n');
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
    else play(unheard().at(-1) || past().find((m) => !isMine(m)));
  }
  else if (s === S.PAST) showPast();
  else if (s === S.ERROR) showError(SEND_FAILED, SEND_FAILED_EN, true);
  else if (s === S.SAVED) showSaved(messages.filter((m) => isMine(m) && hasStory(m.story)).at(-1), true);
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
