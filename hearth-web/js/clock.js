// Clock adapted from Dream Recorder's clock.js by Modem, 12 hour.
import config from '../config.js';
import { $, setText } from './dom.js';

const fmtWd = new Intl.DateTimeFormat('es', { weekday: 'long' });
const fmtMo = new Intl.DateTimeFormat('es', { month: 'long' });
const fmtWdEn = new Intl.DateTimeFormat('en', { weekday: 'long' });
const fmtMoEn = new Intl.DateTimeFormat('en', { month: 'long' });
export const hm = (d) => `${d.getHours() % 12 || 12}:${String(d.getMinutes()).padStart(2, '0')}`;
export const dayLabel = (d) => `${fmtWd.format(d)} ${d.getDate()}`;

let colonOn = true;
export function tickClock() {
  const now = new Date();
  setText('clock-h', String(now.getHours() % 12 || 12));
  setText('clock-m', String(now.getMinutes()).padStart(2, '0'));
  colonOn = !colonOn;
  $('clock-colon').classList.toggle('off', !colonOn);
  setText('day-num', String(now.getDate()));
  setText('day-wd', fmtWd.format(now).toLowerCase());
  setText('day-mo', fmtMo.format(now).toLowerCase());
  if (config.subs) setText('day-en', `${fmtWdEn.format(now)} \u00b7 ${fmtMoEn.format(now)}`);
}

export function setFamilyCode(code) {
  setText('fam-code-es', `c\u00f3digo familiar ${code}`);
  setText('fam-code-en', 'family code');
}
