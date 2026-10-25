export const $ = (id) => document.getElementById(id);
export const setText = (id, text) => { const el = $(id); if (el.textContent !== text) el.textContent = text; };
