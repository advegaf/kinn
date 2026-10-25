// Microphone capture with a live level meter. Level math follows Dream Recorder's
// recorder.js (RMS of time domain data), github.com/modem-works/dream-recorder (MIT).

const CANDIDATES = [
  ['audio/mp4', 'm4a'],
  ['audio/webm;codecs=opus', 'webm'],
  ['audio/webm', 'webm'],
  ['audio/ogg;codecs=opus', 'ogg'],
];

export function pickFormat() {
  if (typeof MediaRecorder === 'undefined') return null;
  for (const [mime, ext] of CANDIDATES) {
    if (MediaRecorder.isTypeSupported?.(mime)) {
      if (ext === 'ogg') console.warn('Recording as ogg. The contract expects webm or m4a.');
      return { mime, ext, contentType: mime.split(';')[0] };
    }
  }
  return { mime: '', ext: 'webm', contentType: 'audio/webm' };
}

let ctx = null;

export function resumeAudio() {
  if (ctx && ctx.state === 'suspended') ctx.resume().catch(() => {});
}

export class MicRecorder {
  constructor() {
    this.stream = null;
    this.rec = null;
    this.chunks = [];
    this.raf = 0;
    this.format = null;
  }

  async start(onLevel) {
    this.format = pickFormat();
    if (!this.format) throw new Error('MediaRecorder unsupported');
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    this.chunks = [];
    this.rec = new MediaRecorder(this.stream, this.format.mime ? { mimeType: this.format.mime } : undefined);
    this.rec.ondataavailable = (e) => { if (e.data && e.data.size) this.chunks.push(e.data); };
    this.rec.start(250);
    this.startedAt = performance.now();

    try {
      ctx = ctx || new (window.AudioContext || window.webkitAudioContext)();
      resumeAudio();
      const source = ctx.createMediaStreamSource(this.stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 512;
      source.connect(analyser);
      this.source = source;
      const buf = new Uint8Array(analyser.fftSize);
      const tick = () => {
        analyser.getByteTimeDomainData(buf);
        let sum = 0;
        for (let i = 0; i < buf.length; i++) {
          const v = (buf[i] - 128) / 128;
          sum += v * v;
        }
        onLevel(Math.sqrt(sum / buf.length));
        this.raf = requestAnimationFrame(tick);
      };
      tick();
    } catch (err) {
      console.warn('Level meter unavailable', err);
    }
  }

  stop() {
    return new Promise((resolve) => {
      const rec = this.rec;
      const done = () => {
        const type = this.format.contentType;
        const blob = new Blob(this.chunks, { type });
        const durationMs = performance.now() - this.startedAt;
        this.release();
        resolve({ blob, durationMs, ...this.format });
      };
      if (!rec || rec.state === 'inactive') return done();
      rec.onstop = done;
      rec.stop();
    });
  }

  cancel() {
    if (this.rec && this.rec.state !== 'inactive') {
      this.rec.onstop = null;
      try { this.rec.stop(); } catch {}
    }
    this.release();
  }

  release() {
    cancelAnimationFrame(this.raf);
    try { this.source?.disconnect(); } catch {}
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
    this.rec = null;
    this.source = null;
  }
}

// Demo mode never touches the mic. It fakes a speaking voice so the glow reacts.
export class FakeRecorder {
  async start(onLevel) {
    this.startedAt = performance.now();
    const tick = (t) => {
      const syllables = Math.max(0, Math.sin(t / 140)) * (0.55 + 0.45 * Math.sin(t / 900));
      onLevel(Math.min(1, 0.05 + syllables * 0.45 + Math.random() * 0.08));
      this.raf = requestAnimationFrame(tick);
    };
    this.raf = requestAnimationFrame(tick);
  }

  async stop() {
    cancelAnimationFrame(this.raf);
    return { blob: new Blob([], { type: 'audio/webm' }), durationMs: performance.now() - this.startedAt, mime: 'audio/webm', ext: 'webm', contentType: 'audio/webm' };
  }

  cancel() { cancelAnimationFrame(this.raf); }
}
