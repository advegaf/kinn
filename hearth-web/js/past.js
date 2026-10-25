// Her way back to older stories and replies: one at a time, newest first. Large visible controls
// on the side of the strip replace the old hidden double press.
import { $, setText } from './dom.js';
import { dayLabel } from './clock.js';

let list = [];
let at = 0;

export const inPast = () => list.length > 0;
export const pastItem = () => list[at];

export function openPast(items) {
  list = items;
  at = 0;
}

export function nextPast() {
  at = (at + 1) % list.length;
}

export function closePast() {
  list = [];
}

export function renderPast({ mine, name, titles: [es, en], image }) {
  const day = dayLabel(new Date(pastItem().created_at));
  setText('past-title', es || (mine ? 'tu historia' : `mensaje de ${name}`));
  setText('past-title-en', en || (mine ? 'your story' : `note from ${name}`));
  setText('past-stamp', mine ? `tu historia, ${day}` : `de ${name}, ${day}`);
  setText('past-stamp-en', mine ? 'your story' : `from ${name}`);
  setText('past-count', `${at + 1} de ${list.length}`);
  setText('past-count-en', `${at + 1} of ${list.length}`);
  const img = $('past-img');
  if (image) img.src = image;
  else img.removeAttribute('src');
}
