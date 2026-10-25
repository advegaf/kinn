import { $ } from './dom.js';

const cap = $('play-cap');
const es = $('cap-es');
const en = $('cap-en');

// The caption fades out, takes the new beat, and fades back in with the scene.
// data-two marks a caption with an English line; CSS lays the two languages out separately.
let capFade = null;
export function setCaption(text, textEn = '', fade = false) {
  const apply = () => {
    es.textContent = text;
    en.textContent = textEn;
    cap.toggleAttribute('data-two', Boolean(textEn));
    fitCaption();
  };
  if (capFade) { capFade.cancel(); capFade = null; }
  if (!fade || !cap.animate || (es.textContent === text && en.textContent === textEn)) { apply(); return; }
  const out = cap.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 200, easing: 'ease-out', fill: 'forwards' });
  capFade = out;
  out.onfinish = () => {
    apply();
    capFade = cap.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 450, easing: 'ease-out' });
    out.cancel();
  };
}

// Largest caption size that keeps the beat to 2 lines (large) or 3 lines (smaller tiers).
// CSS also clamps to 3 lines, so nothing spills off the strip even before fonts load.
// With two lines, the Spanish is measured alone (half a line of slack for the clamped box's
// rounding), and both lines together must fit the room under the stamp (CAP_ROOM strip units).
const CAP_TIERS = [['', 2], ['m', 3], ['s', 3], ['xs', 3], ['xxs', 3]];
const CAP_ROOM = 56;
export function fitCaption() {
  const two = cap.hasAttribute('data-two');
  const room = (CAP_ROOM * $('strip').clientHeight) / 100;
  // xxs is only for the two-language caption; with Spanish alone the smallest tier stays xs.
  for (const [tier, maxLines] of two ? CAP_TIERS : CAP_TIERS.slice(0, -1)) {
    if (tier) cap.dataset.size = tier; else delete cap.dataset.size;
    const lineH = parseFloat(getComputedStyle(cap).fontSize) * 1.1;
    if (!two) {
      if (cap.scrollHeight <= lineH * maxLines + 2) return;
    } else if (es.scrollHeight <= lineH * (maxLines + 0.5) && es.scrollHeight + en.scrollHeight + lineH * 0.3 <= room) {
      return;
    }
  }
}
document.fonts?.ready.then(() => { if ($('hearth').dataset.state === 'playing') fitCaption(); });
