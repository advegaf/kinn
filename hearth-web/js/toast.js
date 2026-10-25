// A banner over the strip: a new family message, or a note about one. Tapping it runs onTap.
import { $, setText } from './dom.js';

const HOLD_MS = 5000;

let timer = 0;
let onTapNow = null;
let bound = false;

export function showToast([line, lineEn], [es, en], onTap) {
  const el = $('toast');
  if (!bound) {
    bound = true;
    // The strip treats any press as the button; a tap on the banner is only for the banner.
    el.addEventListener('pointerdown', (e) => e.stopPropagation());
    el.addEventListener('click', () => {
      const tap = onTapNow;
      hideToast();
      tap?.();
    });
  }
  onTapNow = onTap;
  setText('toast-es', line);
  setText('toast-sum-es', es || '');
  setText('toast-en', lineEn);
  setText('toast-sum-en', en || '');
  el.classList.add('on');
  clearTimeout(timer);
  timer = setTimeout(hideToast, HOLD_MS);
}

export function hideToast() {
  clearTimeout(timer);
  onTapNow = null;
  $('toast')?.classList.remove('on');
}
