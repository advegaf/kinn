// Data layer. SupabaseBackend follows docs/CONTRACT.md and mirrors the iOS client
// (ios/MotherTongue/Services/SupabaseService.swift). DemoBackend uses canned data and no network.

const SUPABASE_ESM = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.117.2/+esm';
const POLL_MS = 3000;
// Demo mode has no Supabase config, so the pre-made stage clips (videos/demo/...) load from public storage.
const DEMO_CLIPS = 'https://gxyeoawqjzgxubfvayjs.supabase.co/storage/v1/object/public/';

function uuid() {
  if (crypto.randomUUID) return crypto.randomUUID();
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = [...b].map((x) => x.toString(16).padStart(2, '0')).join('');
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

// story paths carry a bucket prefix ("videos/...", "images/..."); audio paths do not.
const stripBucket = (bucket, path) => path.replace(new RegExp(`^/?${bucket}/`), '');

export class SupabaseBackend {
  constructor(config) {
    this.config = config;
    this.profile = null;
    this.partner = null;
    this.thread = null;
  }

  async init() {
    const { createClient } = await import(SUPABASE_ESM);
    const { supabaseUrl, anonKey, profileId, threadId } = this.config;
    this.client = createClient(supabaseUrl, anonKey, {
      auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
    });

    const [profile, thread] = await Promise.all([
      this.client.from('profiles').select().eq('id', profileId).maybeSingle(),
      this.client.from('threads').select().eq('id', threadId).maybeSingle(),
    ]);
    if (profile.error) throw profile.error;
    if (thread.error) throw thread.error;
    if (!thread.data) throw new Error(`Thread ${threadId} not found`);
    this.profile = profile.data || { id: profileId, role: 'elder', lang: 'es', name: '' };
    this.thread = thread.data;

    const partnerId = this.profile.role === 'family' ? this.thread.elder_id : this.thread.family_id;
    if (partnerId) {
      const { data } = await this.client.from('profiles').select().eq('id', partnerId).maybeSingle();
      this.partner = data || null;
    }
  }

  async fetchMessages() {
    const { data, error } = await this.client.from('messages')
      .select()
      .eq('thread_id', this.thread.id)
      .order('created_at', { ascending: true })
      .limit(200);
    if (error) throw error;
    return data;
  }

  subscribe(onChange) {
    this.channel = this.client.channel(`hearth-${this.thread.id}`)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'messages', filter: `thread_id=eq.${this.thread.id}` }, () => onChange())
      .subscribe((status) => { if (status !== 'SUBSCRIBED') console.info('realtime', status); });
    this.poll = setInterval(onChange, POLL_MS);
  }

  async send(rec) {
    const id = uuid();
    const path = `${this.thread.id}/${id}.${rec.ext}`;
    const up = await this.client.storage.from('audio').upload(path, rec.blob, { contentType: rec.contentType, upsert: true });
    if (up.error) throw up.error;

    const row = {
      id,
      thread_id: this.thread.id,
      sender_id: this.profile.id,
      source_lang: this.profile.lang || 'es',
      target_lang: this.partner?.lang || 'en',
      original_path: path,
      status: 'uploaded',
    };
    const ins = await this.client.from('messages').insert(row);
    if (ins.error) throw ins.error;

    const res = await this.client.functions.invoke('process-message', { body: { message_id: id } });
    if (res.data && res.data.status) return res.data;
    // The function did not answer with a row. Read it back so the caller sees the real status.
    const { data } = await this.client.from('messages').select().eq('id', id).maybeSingle();
    if (res.error) console.warn('process-message', res.error);
    return data || { ...row, status: 'error', error: res.error?.message || 'process-message failed' };
  }

  async markHeard(id) {
    const { error } = await this.client.from('messages').update({ heard_at: new Date().toISOString() }).eq('id', id);
    if (error) console.warn('heard_at update failed', error.message);
  }

  publicUrl(bucket, path) {
    if (!path) return '';
    if (/^(https?:|data:|blob:)/.test(path)) return path;
    return this.client.storage.from(bucket).getPublicUrl(stripBucket(bucket, path)).data.publicUrl;
  }

  audioUrl(message) {
    return this.publicUrl('audio', message.translated_path);
  }

  // Her own voice, for replaying a story she told.
  originalUrl(message) {
    return this.publicUrl('audio', message.original_path);
  }

  media(story) {
    if (!story) return { video: '', images: [], scenes: [] };
    const scenes = (story.scenes || []).map((sc) => ({
      ...sc,
      image: sc.image_path ? this.publicUrl('images', sc.image_path) : this.publicUrl('videos', sc.thumb_path),
      video: this.publicUrl('videos', sc.video_path),
    }));
    // video_path and thumb_path carry the "videos/" prefix; publicUrl strips it.
    const images = (story.image_paths || []).map((p) => this.publicUrl('images', p));
    if (!images.length && story.thumb_path) images.push(this.publicUrl('videos', story.thumb_path));
    return { video: this.publicUrl('videos', story.video_path), images, scenes };
  }
}

export class DemoBackend {
  constructor(config) {
    this.config = config;
    this.profile = { id: 'demo-elder', name: 'Margaret', role: 'elder', lang: 'es' };
    this.partner = { id: 'demo-family', name: 'Angel', role: 'family', lang: 'en' };
    this.thread = { id: 'demo-thread', elder_id: 'demo-elder', family_id: 'demo-family' };
    this.messages = [];
    this.listeners = [];
    this.replyIndex = 0;
  }

  // Canned thread from demo/demo-stories.json (the same 6 stories as the iPhone demo).
  // Margaret's stories carry story.scenes with stills in demo/scenes/. Family replies carry what
  // Margaret hears (translation_es), reply_to, the story they answer (demo only, not in the contract),
  // and story.scenes for the reply's own beats when the JSON has them.
  // Audio is pre-generated ElevenLabs narration in demo/audio/{id}-{es|en}.mp3. A missing file
  // fails to load and main.js falls back to speechSynthesis.
  async init() {
    const res = await fetch('demo/demo-stories.json');
    if (!res.ok) throw new Error(`demo-stories.json ${res.status}`);
    const data = await res.json();
    this.partner.name = data.family?.name || this.partner.name;
    this.profile.name = data.elder?.name || this.profile.name;
    const t = Date.now();
    const iso = (minAgo) => new Date(t - minAgo * 60000).toISOString();
    const storyAgo = {};
    const stories = data.stories.map((st) => {
      const ago = st.days_ago * 1440 + 60;
      storyAgo[st.id] = ago;
      const scenes = st.scenes.map((sc) => ({
        text_es: sc.text_es, text_en: sc.text_en, t_es: sc.t_es, t_en: sc.t_en, prompt: sc.prompt,
        image_path: `demo/scenes/${sc.image}.jpg`,
        ...(sc.start != null ? { start: sc.start, end: sc.end } : {}),
        ...(sc.video_path ? { video_path: sc.video_path } : {}),
      }));
      return this.row(st.id, 'demo-elder', iso(ago), {
        transcript: st.transcript, translation: st.translation, ask_about: st.ask_about || [],
        original_path: `demo/audio/${st.id}-es.mp3`, translated_path: `demo/audio/${st.id}-en.mp3`,
        story: { title: st.title, title_es: st.title_es, scenes, image_paths: scenes.map((sc) => sc.image_path) },
      });
    });
    this.pending = data.replies.map((r, i) => this.row(`r${i + 1}`, 'demo-family', iso(storyAgo[r.after_story] - r.minutes_after), {
      transcript: r.text_en, translation: r.translation_es, reply_to: r.after_story,
      original_path: `demo/audio/r${i + 1}-en.mp3`, translated_path: `demo/audio/r${i + 1}-es.mp3`,
      // Beats of the reply itself, so each frame matches what she hears. scenes.js times them by
      // t_es span, else by text_es offset within translation_es.
      story: {
        title: r.title, title_es: r.title_es,
        ...(r.scenes?.length ? { scenes: r.scenes.map((sc) => ({
          text_es: sc.text_es, text_en: sc.text_en, t_es: sc.t_es, t_en: sc.t_en, image_path: `demo/scenes/${sc.image}.jpg`,
          ...(sc.video_path ? { video_path: sc.video_path } : {}),
        })) } : {}),
      },
    }));
    // The newest reply (r1, after today's story) is the one that arrives. The rest are already heard.
    const [fresh, ...older] = this.pending;
    older.forEach((m) => { m.heard_at = m.created_at; });
    this.messages = [...stories, ...older].sort((a, b) => a.created_at.localeCompare(b.created_at));
    this.pending = [fresh];
    const seedUnheard = ['waiting', 'playing'].includes(this.config.startState);
    if (seedUnheard) this.addReply(fresh.created_at);
    else if (!this.config.startState) setTimeout(() => this.addReply(), 6000);
  }

  row(id, sender, created, extra = {}) {
    return {
      id, thread_id: this.thread.id, sender_id: sender, status: 'ready',
      source_lang: sender === 'demo-elder' ? 'es' : 'en', target_lang: sender === 'demo-elder' ? 'en' : 'es',
      original_path: '', translated_path: null, story: null, heard_at: null, created_at: created, ...extra,
    };
  }

  // Delivers the next canned reply. Once the list runs out it repeats the last one with a new id.
  addReply(created = new Date().toISOString()) {
    const base = this.pending[Math.min(this.replyIndex++, this.pending.length - 1)];
    const id = this.replyIndex === 1 ? base.id : `${base.id}-${Date.now()}`;
    this.messages.push({ ...base, id, created_at: created, heard_at: null });
    this.emit();
  }

  emit() { this.listeners.forEach((fn) => fn()); }
  async fetchMessages() { return this.messages.map((m) => ({ ...m })); }
  subscribe(onChange) { this.listeners.push(onChange); }

  async send() {
    await new Promise((r) => setTimeout(r, 2600));
    const last = this.messages.filter((x) => x.sender_id === 'demo-elder').at(-1);
    const m = this.row(`e${Date.now()}`, 'demo-elder', new Date().toISOString(), { transcript: last?.transcript, translation: last?.translation, story: last?.story, original_path: last?.original_path, translated_path: last?.translated_path });
    this.messages.push(m);
    setTimeout(() => this.addReply(), 9000);
    this.emit();
    return m;
  }

  async markHeard(id) {
    const m = this.messages.find((x) => x.id === id);
    if (m) m.heard_at = new Date().toISOString();
  }

  audioUrl(message) { return message.translated_path || ''; }
  originalUrl(message) { return message.original_path || ''; }
  media(story) {
    const scenes = (story?.scenes || []).map((sc) => ({ ...sc, image: sc.image_path || sc.thumb_path || '', video: sc.video_path ? DEMO_CLIPS + sc.video_path : '' }));
    return { video: story?.video_path || '', images: story?.image_paths || [], scenes };
  }
}
