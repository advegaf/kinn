// Touch and key input for the one-button Hearth, and the 3 s hold that starts a recording.
import config from '../config.js';
import { $ } from './dom.js';
import { inRect, toPct } from './calibrate.js';
import { resumeAudio } from './recorder.js';
import { retryPending } from './narration.js';

const HOLD_MS = 3000;
const PRESS_KEYS = new Set(['Enter', 'NumpadEnter', ' ', 'Spacebar', 'MediaPlayPause', 'AudioVolumeUp', 'VolumeUp']);

const root = $('hearth');
let holdTimer = 0;

// The ring in the middle of the strip fills while the hold runs (styles.css, [data-hold]).
export function startHold(onDone) {
  cancelHold();
  root.toggleAttribute('data-hold', true);
  holdTimer = setTimeout(() => {
    holdTimer = 0;
    root.removeAttribute('data-hold');
    onDone();
  }, HOLD_MS);
}

// True when a hold was still running, so the release counts as a short tap.
export function cancelHold() {
  if (!holdTimer) return false;
  clearTimeout(holdTimer);
  holdTimer = 0;
  root.removeAttribute('data-hold');
  return true;
}

// Touch pointerdown is not a user activation in Chromium; pointerup and keydown are.
// Anything that was blocked by autoplay policy gets retried on the next one.
export function unlock() {
  resumeAudio();
  retryPending();
}

// The kiosk app sends keydown and keyup together for a remote press, so a key cannot be held.
// press gets 'key' for it and treats it as a full hold.
export function bindInput(press, release, zone, strip) {
  addEventListener('keydown', (e) => {
    if (e.repeat || !PRESS_KEYS.has(e.key)) return;
    e.preventDefault();
    press('key', e.target.matches?.(':focus-visible') ? e.target.closest('[data-act]')?.dataset.act : undefined);
  });
  // A screen reader activates a button with a click that has no pointer before it (detail 0).
  addEventListener('click', (e) => {
    const act = e.target.closest?.('[data-act]')?.dataset.act;
    if (act && e.detail === 0) press('key', act);
  });
  addEventListener('pointerdown', (e) => {
    if (config.calibrate || !e.isPrimary) return;
    // A tapped control must not keep focus, or the remote's next Enter would press it again.
    if (e.target.closest?.('[data-act]')) e.preventDefault();
    document.activeElement?.blur?.();
    const p = toPct(e);
    if (inRect(zone, p.x, p.y)) press('button');
    else if (inRect(strip, p.x, p.y)) press('strip', e.target.closest?.('[data-act]')?.dataset.act);
  });
  for (const type of ['pointerup', 'pointercancel']) addEventListener(type, (e) => { if (e.isPrimary) release(); });
  addEventListener('contextmenu', (e) => e.preventDefault());
  for (const type of ['pointerup', 'touchend', 'keyup']) addEventListener(type, unlock, { passive: true });
}
