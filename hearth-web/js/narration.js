import { $ } from './dom.js';

const audio = $('audio');
const SPEECH_RATE = 0.95;
const SPEECH_WPM = 160; // Spanish at the demo rate, for the elapsed time estimate
const STALL_MS = 600;

let pendingPlay = null;
let raf = 0;
let progressTimer = 0;
let speechTimer = 0;

// Touch pointerdown is not a user activation in Chromium; pointerup and keydown are.
// A play blocked by autoplay policy waits here for the next one.
export function retryPending() {
  if (pendingPlay) { const fn = pendingPlay; pendingPlay = null; fn(); }
}

// Plays the narration from url, else speaks text. onProgress gets 0..1 of the narration;
// onEnd gets an optional linger delay in ms.
export function narrate(url, text, lang, onProgress, onEnd) {
  if (url) playUrl(url, text, lang, onProgress, onEnd);
  else if (text) speak(text, lang, onProgress, onEnd);
  else onEnd(6000);
}

function playUrl(url, text, lang, onProgress, onEnd) {
  audio.src = url;
  const tick = () => {
    const d = audio.duration;
    if (d > 0 && Number.isFinite(d)) onProgress(audio.currentTime / d);
    raf = requestAnimationFrame(tick);
  };
  cancelAnimationFrame(raf);
  raf = requestAnimationFrame(tick);
  audio.onended = () => { cancelAnimationFrame(raf); onProgress(1); onEnd(); };
  audio.onerror = () => {
    cancelAnimationFrame(raf);
    console.warn('audio failed', url);
    if (text) speak(text, lang, onProgress, onEnd);
    else onEnd(4000);
  };
  const attempt = () => audio.play().catch((err) => {
    if (err.name === 'NotAllowedError') pendingPlay = attempt;
    else console.warn('audio play', err.message);
  });
  attempt();
}

// Scenes follow the voice's word boundaries. When none have come for a while (some voices
// never send them, some stall), elapsed time over an estimated duration carries on from the last one.
function speak(text, lang, onProgress, onEnd) {
  const estMs = (text.split(/\s+/).length / SPEECH_WPM) * 60000 / SPEECH_RATE;
  let mark = { at: performance.now(), p: 0 };
  clearInterval(progressTimer);
  progressTimer = setInterval(() => {
    const since = performance.now() - mark.at;
    if (since > STALL_MS) onProgress(mark.p + since / estMs);
  }, 250);
  if (!('speechSynthesis' in window)) return onEnd(estMs + 1500);
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang === 'es' ? 'es-MX' : lang || 'es-MX';
  u.rate = SPEECH_RATE;
  const voice = speechSynthesis.getVoices().find((v) => v.lang.toLowerCase().startsWith((lang || 'es').toLowerCase()));
  if (voice) u.voice = voice;
  u.onboundary = (e) => {
    mark = { at: performance.now(), p: e.charIndex / text.length };
    onProgress(mark.p);
  };
  u.onend = () => { onProgress(1); onEnd(); };
  speechSynthesis.cancel();
  speechSynthesis.speak(u);
  // onend is unreliable in some WebViews, so cap the wait.
  speechTimer = setTimeout(() => onEnd(), Math.max(3000 + text.length * 90, estMs + 3000));
}

export function clearTimers() {
  cancelAnimationFrame(raf);
  clearTimeout(speechTimer);
  clearInterval(progressTimer);
}

export function stopAll() {
  clearTimers();
  pendingPlay = null;
  audio.onended = audio.onerror = null;
  audio.pause();
  if ('speechSynthesis' in window) speechSynthesis.cancel();
}
