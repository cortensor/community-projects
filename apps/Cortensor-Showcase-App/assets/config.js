// Loads runtime config from env.local.json or .env.local (dotenv style)
// Exposes window.APP_CONFIG and window.waitForAppConfig (Promise)

(function(){
  const defaults = {
    API_BASE_URL: 'http://173.214.163.250:5010',
  API_BEARER: '', // token only; code will prefix Bearer
    API_SESSION_ID: '21',
    CHAT_STREAM: false,
    CHAT_PERSONA_NAME: 'Eureka',
    CHAT_SYSTEM_PERSONA: 'You are Eureka, a friendly, concise support assistant for the Cortensor apps showcase. Answer like a helpful support agent: be clear, professional, and actionable. Prefer short paragraphs and bullets. If a key detail is missing, ask one clarifying question before concluding.',
    ADMIN_ID: 'admin',
  ADMIN_PIN: '4718',
  RAG_ENABLE: true
  };

  function merge(target, src) {
    Object.keys(src || {}).forEach(k => {
      target[k] = src[k];
    });
    return target;
  }

  function parseDotenv(txt){
    const out = {};
    if (!txt) return out;
    // Strip BOM if present
    if (txt.charCodeAt(0) === 0xFEFF) txt = txt.slice(1);
    txt.split(/\r?\n/).forEach(line => {
      if (!line) return;
      // Allow comments; but preserve # inside quotes
      let raw = line;
      // Trim leading/trailing whitespace
      raw = raw.replace(/^\s+|\s+$/g, '');
      if (!raw || raw.startsWith('#')) return;
      const eq = raw.indexOf('=');
      if (eq === -1) return;
      const key = raw.slice(0, eq).trim();
      let val = raw.slice(eq+1).trim();
      if (!key) return;
      // If quoted, remove surrounding quotes and keep inner #
      const isSq = val.startsWith("'") && val.endsWith("'");
      const isDq = val.startsWith('"') && val.endsWith('"');
      if (isSq || isDq) {
        val = val.slice(1, -1);
      } else {
        // Remove inline comments starting with # (unquoted)
        const hash = val.indexOf('#');
        if (hash !== -1) val = val.slice(0, hash);
      }
      out[key] = val.trim();
    });
    return out;
  }

  async function load(){
    let debugFlag = false;
    try {
      const dp = new URLSearchParams(window.location.search);
      const d = (dp.get('debug')||'').toLowerCase();
      debugFlag = d === '1' || d === 'true' || d === 'config';
    } catch {}
    const maybeLog = (cfg) => { if (debugFlag) { try { console.log('[APP_CONFIG]', cfg); } catch {} } };
    // Allow override via inline script: window.__APP_CONFIG__ = {...}
    let overrides = {};
    try {
      const raw = localStorage.getItem('APP_CONFIG_OVERRIDE');
      if (raw) overrides = JSON.parse(raw);
    } catch {}
    // Query params override as well (e.g., ?API_BEARER=... or ?api_bearer=...)
    try {
      const p = new URLSearchParams(window.location.search);
      const pickAny = (...keys) => {
        for (const k of keys) { const v = p.get(k); if (v !== null) return v; }
        for (const k of keys) { const v = p.get(k.toLowerCase()); if (v !== null) return v; }
        return null;
      };
      const qOverrides = {};
      const apiBase = pickAny('API_BASE_URL','baseUrl','base_url'); if (apiBase !== null) qOverrides.API_BASE_URL = apiBase;
      const apiBearer = pickAny('API_BEARER','API_KEY','api_key','key','token'); if (apiBearer !== null) qOverrides.API_BEARER = apiBearer;
      const apiSess = pickAny('API_SESSION_ID','SESSION_ID','sessionId','sid'); if (apiSess !== null) qOverrides.API_SESSION_ID = apiSess;
      const chatStream = pickAny('CHAT_STREAM','stream'); if (chatStream !== null) qOverrides.CHAT_STREAM = chatStream;
      const persona = pickAny('CHAT_PERSONA_NAME','persona'); if (persona !== null) qOverrides.CHAT_PERSONA_NAME = persona;
      const sys = pickAny('CHAT_SYSTEM_PERSONA','system'); if (sys !== null) qOverrides.CHAT_SYSTEM_PERSONA = sys;
      const adminId = pickAny('ADMIN_ID','admin'); if (adminId !== null) qOverrides.ADMIN_ID = adminId;
      const adminPin = pickAny('ADMIN_PIN','pin'); if (adminPin !== null) qOverrides.ADMIN_PIN = adminPin;
  if (typeof qOverrides.CHAT_STREAM === 'string') {
        qOverrides.CHAT_STREAM = qOverrides.CHAT_STREAM.toLowerCase() === 'true';
      }
  const ragEnable = pickAny('RAG_ENABLE','rag'); if (ragEnable !== null) qOverrides.RAG_ENABLE = (/^(1|true|yes)$/i).test(ragEnable);
      overrides = { ...overrides, ...qOverrides };
    } catch {}
    const cfg = merge({},{...defaults, ...overrides, ...(window.__APP_CONFIG__||{})});
    // Helper: fetch with cache-busting and relative path (works under subpaths)
    const j = Date.now();
    const fetchTxt = async (path) => {
      try {
        const res = await fetch(`${path}?_=${j}`, { cache: 'no-store' });
        if (!res.ok) return null;
        return await res.text();
      } catch { return null; }
    };
    const fetchJSON = async (path) => {
      try {
        const res = await fetch(`${path}?_=${j}`, { cache: 'no-store' });
        if (!res.ok) return null;
        return await res.json();
      } catch { return null; }
    };
    const fetchTxtPaths = async (paths) => {
      for (const p of paths) { const t = await fetchTxt(p); if (t) return t; }
      return null;
    };
    const fetchJSONPaths = async (paths) => {
      for (const p of paths) { const jv = await fetchJSON(p); if (jv) return jv; }
      return null;
    };
    // Prefer JSON
    try {
  const json = await fetchJSONPaths(['env.local.json','/env.local.json']);
  if (json) { merge(cfg, json); cfg.__source = 'env.local.json'; window.APP_CONFIG = cfg; maybeLog(cfg); window.dispatchEvent(new CustomEvent('app:config-ready', { detail: cfg })); return cfg; }
    } catch {}
    // Try dotenv without dot (some hosts block dotfiles)
    try {
  const txt = await fetchTxtPaths(['env.local','/env.local']);
      if (txt) {
        const env = parseDotenv(txt);
        // Map common keys (either exact or prefixed with VITE_/NEXT_PUBLIC_)
        const pick = (k) => env[k] ?? env['VITE_'+k] ?? env['NEXT_PUBLIC_'+k];
        merge(cfg, {
          API_BASE_URL: pick('API_BASE_URL') ?? cfg.API_BASE_URL,
          API_BEARER: pick('API_BEARER') ?? cfg.API_BEARER,
          API_SESSION_ID: pick('API_SESSION_ID') ?? cfg.API_SESSION_ID,
          CHAT_STREAM: (pick('CHAT_STREAM') ?? cfg.CHAT_STREAM).toString().toLowerCase() === 'true',
          CHAT_PERSONA_NAME: pick('CHAT_PERSONA_NAME') ?? cfg.CHAT_PERSONA_NAME,
          CHAT_SYSTEM_PERSONA: pick('CHAT_SYSTEM_PERSONA') ?? cfg.CHAT_SYSTEM_PERSONA,
          ADMIN_ID: pick('ADMIN_ID') ?? cfg.ADMIN_ID,
          ADMIN_PIN: pick('ADMIN_PIN') ?? cfg.ADMIN_PIN,
          RAG_ENABLE: ((pick('RAG_ENABLE') ?? cfg.RAG_ENABLE)+'').toLowerCase() === 'true',
        });
  cfg.__source = 'env.local';
  window.APP_CONFIG = cfg; maybeLog(cfg); window.dispatchEvent(new CustomEvent('app:config-ready', { detail: cfg })); return cfg;
      }
    } catch {}
    // Try dotfile (works on many static servers, but not all)
    try {
  const txt = await fetchTxtPaths(['.env.local','/.env.local']);
      if (txt) {
        const env = parseDotenv(txt);
        const pick = (k) => env[k] ?? env['VITE_'+k] ?? env['NEXT_PUBLIC_'+k];
        merge(cfg, {
          API_BASE_URL: pick('API_BASE_URL') ?? cfg.API_BASE_URL,
          API_BEARER: pick('API_BEARER') ?? cfg.API_BEARER,
          API_SESSION_ID: pick('API_SESSION_ID') ?? cfg.API_SESSION_ID,
          CHAT_STREAM: (pick('CHAT_STREAM') ?? cfg.CHAT_STREAM).toString().toLowerCase() === 'true',
          CHAT_PERSONA_NAME: pick('CHAT_PERSONA_NAME') ?? cfg.CHAT_PERSONA_NAME,
          CHAT_SYSTEM_PERSONA: pick('CHAT_SYSTEM_PERSONA') ?? cfg.CHAT_SYSTEM_PERSONA,
          ADMIN_ID: pick('ADMIN_ID') ?? cfg.ADMIN_ID,
          ADMIN_PIN: pick('ADMIN_PIN') ?? cfg.ADMIN_PIN,
          RAG_ENABLE: ((pick('RAG_ENABLE') ?? cfg.RAG_ENABLE)+'').toLowerCase() === 'true',
        });
  cfg.__source = '.env.local';
  window.APP_CONFIG = cfg; maybeLog(cfg); window.dispatchEvent(new CustomEvent('app:config-ready', { detail: cfg })); return cfg;
      }
    } catch {}
  cfg.__source = 'defaults/overrides';
  window.APP_CONFIG = cfg; maybeLog(cfg); window.dispatchEvent(new CustomEvent('app:config-ready', { detail: cfg })); return cfg;
  }

  window.waitForAppConfig = load();
})();
