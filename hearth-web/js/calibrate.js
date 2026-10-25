// Button zone and strip (mat window) storage, the ?calibrate=1 overlay and the ?template=1 mat guide.
// Rects are in percent of the full screen.

const KEY = 'hearth.buttonRect';
const STRIP_KEY = 'hearth.stripRect';
const DEFAULT = { x: 82, y: 81, w: 12, h: 13 };
const STRIP_DEFAULT = { x: 0, y: 25, w: 100, h: 50 };
const MAX_Y = 94; // Android gesture nav owns the bottom edge.
const MM = { w: 190.1, h: 113.5 }; // Alexa Tablet 8 (2026) active area, 1340 x 800 at 179 ppi
const HOLE_MM = 25;

function load(key, fallback, fix) {
  try {
    const r = JSON.parse(localStorage.getItem(key) || 'null');
    if (r && [r.x, r.y, r.w, r.h].every(Number.isFinite)) return fix(r);
  } catch {}
  return { ...fallback };
}

function save(key, r) {
  try { localStorage.setItem(key, JSON.stringify(r)); } catch {}
}

function clear(key) {
  try { localStorage.removeItem(key); } catch {}
}

export const loadRect = () => load(KEY, DEFAULT, clamp);
export const loadStrip = () => load(STRIP_KEY, STRIP_DEFAULT, clampStrip);

function clampStrip(r) {
  const w = Math.min(100, Math.max(20, r.w));
  const h = Math.min(90, Math.max(10, r.h));
  return { w, h, x: Math.min(100 - w, Math.max(0, r.x)), y: Math.min(100 - h, Math.max(0, r.y)) };
}

export function applyStrip(r) {
  const s = document.documentElement.style;
  s.setProperty('--sx', r.x);
  s.setProperty('--sy', r.y);
  s.setProperty('--sw', r.w);
  s.setProperty('--sh', r.h);
}

const cm = (pct, axis) => ((pct / 100) * MM[axis] / 10).toFixed(1);
const holePct = () => ({ w: (HOLE_MM / MM.w) * 100, h: (HOLE_MM / MM.h) * 100 });

function clamp(r) {
  const w = Math.min(60, Math.max(3, r.w));
  const h = Math.min(30, Math.max(3, r.h));
  return {
    w, h,
    x: Math.min(100 - w, Math.max(0, r.x)),
    y: Math.min(MAX_Y - h, Math.max(0, r.y)),
  };
}

export function applyRect(r) {
  const s = document.documentElement.style;
  s.setProperty('--bx', r.x);
  s.setProperty('--by', r.y);
  s.setProperty('--bw', r.w);
  s.setProperty('--bh', r.h);
}

export function inRect(r, xPct, yPct) {
  return xPct >= r.x && xPct <= r.x + r.w && yPct >= r.y && yPct <= r.y + r.h;
}

export const toPct = (e) => ({ x: (e.clientX / innerWidth) * 100, y: (e.clientY / innerHeight) * 100 });

// zone and strip are the live rect objects shared with main.js; they are mutated in place.
export function startCalibration(zone, strip, getState) {
  document.documentElement.classList.add('calibrating');
  const root = document.createElement('div');
  root.className = 'calib';
  root.innerHTML = `
    <div class="calib-line" style="top:${MAX_Y}%"></div>
    <div class="calib-strip"><span class="calib-tag"></span><div class="calib-handle"></div></div>
    <div class="calib-rect"><div class="calib-circle"></div><span class="calib-tag"></span><div class="calib-handle"></div></div>
    <div class="calib-panel">
      <div data-k="strip"></div>
      <div data-k="rect"></div>
      <div data-k="touch">last touch: none</div>
      <div data-k="hits">hits in zone: 0 / 0</div>
      <div data-k="screen"></div>
      <button data-a="center">Center on last touch</button><button data-a="count">Reset count</button><button data-a="reset">Default button</button><button data-a="reset-strip">Default strip</button>
    </div>`;
  document.body.appendChild(root);
  const rectEl = root.querySelector('.calib-rect');
  const stripEl = root.querySelector('.calib-strip');
  const circleEl = root.querySelector('.calib-circle');
  const panel = root.querySelector('.calib-panel');
  const out = (k, text) => { panel.querySelector(`[data-k="${k}"]`).textContent = text; };
  let last = null;
  let hits = 0;
  let total = 0;

  const render = () => {
    Object.assign(rectEl.style, { left: `${zone.x}%`, top: `${zone.y}%`, width: `${zone.w}%`, height: `${zone.h}%` });
    Object.assign(stripEl.style, { left: `${strip.x}%`, top: `${strip.y}%`, width: `${strip.w}%`, height: `${strip.h}%` });
    const hole = holePct();
    Object.assign(circleEl.style, { width: `${(hole.w / zone.w) * 100}%`, height: `${(hole.h / zone.h) * 100}%`, inset: '-100%' });
    applyRect(zone);
    applyStrip(strip);
    const stripText = `strip ${strip.w.toFixed(1)}% x ${strip.h.toFixed(1)}%, ${cm(strip.w, 'w')} x ${cm(strip.h, 'h')} cm`;
    stripEl.firstElementChild.textContent = stripText;
    rectEl.querySelector('.calib-tag').textContent = `button ${zone.w.toFixed(1)}% x ${zone.h.toFixed(1)}%, hole ${(HOLE_MM / 10).toFixed(1)} cm`;
    out('strip', `${stripText}, top ${strip.y.toFixed(1)}% (${cm(strip.y, 'h')} cm)`);
    out('rect', `zone x ${zone.x.toFixed(1)}% y ${zone.y.toFixed(1)}% w ${zone.w.toFixed(1)}% h ${zone.h.toFixed(1)}%`);
    out('screen', `${innerWidth}x${innerHeight} css px, dpr ${devicePixelRatio}, state ${getState()}`);
  };
  const round = (c) => { for (const k in c) c[k] = Math.round(c[k] * 10) / 10; return c; };
  const commit = () => {
    Object.assign(zone, round(clamp(zone)));
    Object.assign(strip, round(clampStrip(strip)));
    save(KEY, { ...zone });
    save(STRIP_KEY, { ...strip });
    render();
  };

  panel.addEventListener('pointerdown', (e) => {
    e.stopPropagation();
    const a = e.target.dataset?.a;
    if (a === 'center' && last) { Object.assign(zone, { x: last.x - zone.w / 2, y: last.y - zone.h / 2 }); commit(); }
    if (a === 'count') { hits = 0; total = 0; out('hits', 'hits in zone: 0 / 0'); }
    if (a === 'reset') { clear(KEY); Object.assign(zone, DEFAULT); render(); }
    if (a === 'reset-strip') { clear(STRIP_KEY); Object.assign(strip, STRIP_DEFAULT); render(); }
  });

  let drag = null;
  root.addEventListener('pointerdown', (e) => {
    const p = toPct(e);
    const handle = e.target.classList.contains('calib-handle') ? e.target.parentElement : null;
    const target = handle || (e.target === rectEl ? rectEl : e.target === stripEl ? stripEl : null);
    const obj = target === stripEl ? strip : target === rectEl ? zone : null;
    drag = obj && { start: p, obj, rect: { ...obj }, fix: obj === strip ? clampStrip : clamp, mode: handle ? 'size' : 'move', moved: false };
    root.setPointerCapture?.(e.pointerId);

    last = p;
    total += 1;
    const hit = inRect(zone, p.x, p.y);
    if (hit) hits += 1;
    out('touch', `last touch: x ${p.x.toFixed(1)}% y ${p.y.toFixed(1)}% ${hit ? '(in zone)' : ''}`);
    out('hits', `hits in zone: ${hits} / ${total}`);
    const dot = document.createElement('div');
    dot.className = `calib-dot${hit ? ' hit' : ''}`;
    Object.assign(dot.style, { left: `${p.x}%`, top: `${p.y}%` });
    root.appendChild(dot);
    requestAnimationFrame(() => requestAnimationFrame(() => dot.classList.add('fade')));
    setTimeout(() => dot.remove(), 2200);
  });
  root.addEventListener('pointermove', (e) => {
    if (!drag) return;
    const p = toPct(e);
    const dx = p.x - drag.start.x;
    const dy = p.y - drag.start.y;
    drag.moved = true;
    const r = drag.rect;
    Object.assign(drag.obj, drag.fix(drag.mode === 'move' ? { ...r, x: r.x + dx, y: r.y + dy } : { ...r, w: r.w + dx, h: r.h + dy }));
    render();
  });
  const end = () => { if (drag?.moved) commit(); drag = null; };
  root.addEventListener('pointerup', end);
  root.addEventListener('pointercancel', end);
  addEventListener('resize', render);
  setInterval(render, 1000);
  render();
}

// Full screen mat guide: hold the mat board against the glass and trace the white shapes.
export function startTemplate(zone, strip) {
  const root = document.createElement('div');
  root.className = 'template';
  const hole = holePct();
  const cx = zone.x + zone.w / 2;
  const cy = zone.y + zone.h / 2;
  const sb = strip.y + strip.h;
  const el = (cls, css, text = '') => {
    const d = document.createElement('div');
    d.className = cls;
    Object.assign(d.style, css);
    d.textContent = text;
    root.appendChild(d);
  };
  const pct = (v) => `${v}%`;
  el('t-title', {}, `mat template: active area ${cm(100, 'w')} x ${cm(100, 'h')} cm. trace the white lines.`);
  el('t-strip', { left: pct(strip.x), top: pct(strip.y), width: pct(strip.w), height: pct(strip.h) });
  el('t-label', { left: pct(strip.x + strip.w / 2), top: pct(strip.y + strip.h / 2) },
    `strip window ${cm(strip.w, 'w')} x ${cm(strip.h, 'h')} cm`);
  el('t-v', { left: '50%', top: '0', height: pct(strip.y) });
  el('t-label', { left: '50%', top: pct(strip.y / 2) }, `${cm(strip.y, 'h')} cm from top`);
  el('t-v', { left: '30%', top: pct(sb), height: pct(100 - sb) });
  el('t-label', { left: '30%', top: pct(sb + (100 - sb) / 2) }, `${cm(100 - sb, 'h')} cm to bottom`);
  el('t-hole', { left: pct(cx - hole.w / 2), top: pct(cy - hole.h / 2), width: pct(hole.w), height: pct(hole.h) });
  el('t-h', { left: pct(cx - hole.w * 0.7), top: pct(cy), width: pct(hole.w * 1.4) });
  el('t-v', { left: pct(cx), top: pct(cy - hole.h * 0.7), height: pct(hole.h * 1.4) });
  el('t-h', { left: pct(cx), top: pct(cy), width: pct(100 - cx) });
  el('t-v', { left: pct(cx), top: pct(cy), height: pct(100 - cy) });
  el('t-label t-end', { left: pct(cx - hole.w * 0.75), top: pct(cy - hole.h * 0.2) }, `button hole ${HOLE_MM / 10} cm`);
  el('t-label t-end', { left: pct(cx - hole.w * 0.75), top: pct(cy + hole.h * 0.2) },
    `center ${cm(100 - cx, 'w')} cm from right, ${cm(100 - cy, 'h')} cm from bottom`);
  document.body.appendChild(root);
}
