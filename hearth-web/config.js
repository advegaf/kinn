// Loads config.local.js when present, then lets URL params override it.
// Params: ?thread= ?profile= ?demo=1 ?calibrate=1 ?template=1 ?state= ?msg= (demo only) ?at=0..1 ?debug=1 ?subs=en

const params = new URLSearchParams(location.search);
const flag = (name) => params.has(name) && params.get(name) !== '0';

const demo = flag('demo');
let local = {};
if (!demo) {
  try {
    local = (await import('./config.local.js')).default || {};
  } catch {
    console.warn('config.local.js not found. Copy config.example.js to config.local.js.');
  }
}

const config = {
  supabaseUrl: (local.SUPABASE_URL || '').replace(/\/+$/, ''),
  anonKey: local.SUPABASE_ANON_KEY || '',
  profileId: (params.get('profile') || local.PROFILE_ID || '').toLowerCase(),
  threadId: (params.get('thread') || local.THREAD_ID || '').toLowerCase(),
  demo,
  calibrate: flag('calibrate'),
  template: flag('template'),
  debug: flag('debug'),
  // English line under every Spanish line, for people who do not read Spanish.
  subs: params.get('subs') === 'en',
  startState: params.get('state') || '',
  startMsg: params.get('msg') || '',
  // DEBUG: freeze playback at this fraction of the narration (0..1), with no audio. For screenshots.
  at: params.has('at') && Number.isFinite(parseFloat(params.get('at'))) ? Math.min(1, Math.max(0, parseFloat(params.get('at')))) : null,
};

config.configured = Boolean(config.supabaseUrl && config.anonKey && config.profileId && config.threadId);

export default config;
