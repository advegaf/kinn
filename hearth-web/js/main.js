// Hearth state machine and input. The state set and the one-button flow are adapted from
// Dream Recorder's state-manager.js by Modem, github.com/modem-works/dream-recorder (MIT).

import config from '../config.js';
import { SupabaseBackend, DemoBackend } from './backend.js';
import { MicRecorder, FakeRecorder, resumeAudio } from './recorder.js';
import { loadRect, applyRect, loadStrip, applyStrip, inRect, toPct, startCalibration, startTemplate } from './calibrate.js';
import { $, setText } from './dom.js';
import { hm, dayLabel, tickClock, setFamilyCode } from './clock.js';
import { hasStory, storyFor, answeredStory, buildScenes, startScenes, setProgress, teardown } from './scenes.js';
import { narrate, retryPending, clearTimers, stopAll } from './narration.js';
import { showToast, hideToast } from './toast.js';

const S = { CLOCK: 'clock', WAITING: 'waiting', RECORDING: 'recording', SENDING: 'sending', SAVED: 'saved', PLAYING: 'playing', ERROR: 'error' };

const DEBOUNCE_MS = 250;
const DOUBLE_MS = 650; // a second press this soon after the first counts as a double press
const MIN_RECORD_MS = 900;
const MAX_RECORD_MS = 3 * 60 * 1000;
const MIN_SENDING_MS = 1400;
const READY_TIMEOUT_MS = 90 * 1000;
const ERROR_MS = 3500;
const SAVED_MS = 4000;
const LINGER_MS = 1500;
const HISTORY = 7;
const HEARD_KEY = 'hearth.heard';
const SAVED_STATUS = 'tu historia est\u00e1 guardada';
const PENDING = 'traducci\u00f3n pendiente';

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
const history = () => messages.filter((m) => !isMine(m) && m.status === 'ready').slice(-HISTORY).reverse();
const idleState = () => (unheard().length ? S.WAITING : S.CLOCK);
const wait = (ms) => new Promise((r) => setTimeout(r, Math.max(0, ms)));

// [Spanish, English] title of the story a message is about. A free note carries the worker's
// placeholder as its Spanish title until it is translated.
function titles(msg) {
  const own = msg.story?.title_es || msg.story?.title;
  const st = own ? msg.story : answeredStory(msg, messages, isMine);
  if (st?.title_es === PENDING) return [st.title, st.title];
  return [st?.title_es || st?.title || '', st?.title || st?.title_es || ''];
}

// The last question in her family's newest message, if it is short enough to read at a glance.
// The English line is the last question of that message's original, under the same limit.
function recPrompt(name) {
  const latest = messages.filter((m) => !isMine(m) && m.translation).at(-1);
  const q = latest?.translation.match(/\u00bf[^\u00bf?]*\?/g)?.at(-1)?.trim();
  if (!q || q.length > 60) return [`cu\u00e9ntale a ${name} lo que recuerdas`, `tell ${name} what you remember`];
  const en = latest.transcript?.match(/[^.!?]*\?/g)?.at(-1)?.trim();
  return [q, en && en.length <= 80 ? en : `tell ${name} what you remember`];
}

function renderText() {
  const name = partnerName();
  const latest = unheard().at(-1);
  if (latest) {
    const d = new Date(latest.created_at);
    setText('waiting-label', `${dayLabel(d)}, ${hm(d)}`);
    setText('waiting-line', `${name} te escribi\u00f3`);
    setText('waiting-line-en', `${name} wrote to you`);
    const [es, en] = titles(latest);
    setText('waiting-sub', es ? `sobre \u00ab${es}\u00bb` : '');
    setText('waiting-sub-en', en ? `about \u00ab${en}\u00bb` : '');
  }
  const [prompt, promptEn] = recPrompt(name);
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
  else if (inRect(strip, p.x, p.y)) press('strip');
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
let replayCursor = 0;
let lastReplayAt = -Infinity;

function replay() {
  const list = history();
  if (!list.length) return setState(idleState());
  const now = performance.now();
  replayCursor = now - lastReplayAt < 60000 ? (replayCursor + 1) % list.length : 0;
  lastReplayAt = now;
  play(list[replayCursor], true);
}

function play(msg, isReplay = false) {
  hideToast();
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
  setState(idleState());
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
    else play(unheard().at(-1) || history()[0]);
  }
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
