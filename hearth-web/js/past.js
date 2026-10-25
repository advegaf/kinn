// Her way back to older stories and replies: one at a time, newest first. Large visible controls
// on the side of the strip replace the old hidden double press.
import { $, setText } from './dom.js';
import { dayLabel } from './clock.js';

const DAY_MS = 24 * 60 * 60 * 1000;

let list = [];
let at = 0;

export const inPast = () => list.length > 0;
export const pastItem = () => list[at];

// Weeks start on Monday, as on a Spanish calendar.
function weekStart(msg) {
  const d = new Date(msg.created_at);
  d.setHours(0, 0, 0, 0);
  return d.getTime() - ((d.getDay() + 6) % 7) * DAY_MS;
}

// Also called after each fetch with the fresh rows, so the card never shows an old film state.
export function openPast(items, keepId) {
  list = items;
  at = Math.max(0, list.findIndex((m) => m.id === keepId));
}

export function nextPast() {
  at = (at + 1) % list.length;
}

const olderWeek = () => list.findIndex((m, i) => i > at && weekStart(m) < weekStart(list[at]));

export function olderWeekPast() {
  const i = olderWeek();
  if (i >= 0) at = i;
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
  $('past').toggleAttribute('data-older', olderWeek() >= 0);
  const img = $('past-img');
  if (image) img.src = image;
  else img.removeAttribute('src');
}
