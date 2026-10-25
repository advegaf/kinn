// Words on the strip that come from the thread: story titles and the recording prompt.
import { answeredStory } from './scenes.js';

const PENDING = 'traducci\u00f3n pendiente';

// [Spanish, English] title of the story a message is about. A free note carries the worker's
// placeholder as its Spanish title until it is translated.
export function titles(msg, messages, isMine) {
  const own = msg.story?.title_es || msg.story?.title;
  const st = own ? msg.story : answeredStory(msg, messages, isMine);
  if (st?.title_es === PENDING) return [st.title, st.title];
  return [st?.title_es || st?.title || '', st?.title || st?.title_es || ''];
}

// The last question in her family's newest message, if it is short enough to read at a glance.
// The English line is the last question of that message's original, under the same limit.
export function recPrompt(name, messages, isMine) {
  const latest = messages.filter((m) => !isMine(m) && m.translation).at(-1);
  const q = latest?.translation.match(/\u00bf[^\u00bf?]*\?/g)?.at(-1)?.trim();
  if (!q || q.length > 60) return [`cu\u00e9ntale a ${name} lo que recuerdas`, `tell ${name} what you remember`];
  const en = latest.transcript?.match(/[^.!?]*\?/g)?.at(-1)?.trim();
  return [q, en && en.length <= 80 ? en : `tell ${name} what you remember`];
}
