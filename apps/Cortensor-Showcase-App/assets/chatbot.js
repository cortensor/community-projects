// Simple bottom-right AI chatbot widget using Cortensor SSE API
// - POST /api/v1/completions/{sessionId}
// - Authorization: Bearer <api_key>
// - Body: { prompt, stream, timeout }

(async function () {
  if (window.waitForAppConfig) { try { await window.waitForAppConfig; } catch {} }
  const cfg = window.APP_CONFIG || {};
  const BASE_URL = cfg.API_BASE_URL || 'http://173.214.163.250:5010';
  const SESSION_ID = cfg.API_SESSION_ID || '21';
  let rawToken = (cfg.API_BEARER || '').trim();
  if (!rawToken) {
    const m = document.querySelector('meta[name="cortensor-api-key"]');
    if (m && m.content) rawToken = m.content.trim();
  }
  const AUTH = rawToken ? (rawToken.toLowerCase().startsWith('bearer ') ? rawToken : `Bearer ${rawToken}`) : '';
  const STREAM = !!cfg.CHAT_STREAM;
  const PERSONA_NAME = cfg.CHAT_PERSONA_NAME || 'Eureka';
  const MAX_CHARS = Number(cfg.CHAT_MAX_CHARS ?? 900);
  // If model hints at Llava, default to RAW prompt_type=1
  const MODEL = cfg.API_MODEL || cfg.CHAT_MODEL || '';
  let PROMPT_TYPE = cfg.CHAT_PROMPT_TYPE !== undefined ? Number(cfg.CHAT_PROMPT_TYPE) : 1; // default to RAW=1
  const IS_R1 = /deepseek|\br1\b/i.test(MODEL);
  if (IS_R1) PROMPT_TYPE = 1; // Always use RAW for DeepSeek R1

  if (window.__cortensorChatbotLoaded) return; window.__cortensorChatbotLoaded = true;

  const style = document.createElement('style');
  style.textContent = `
  .ct-chat { position: fixed; right: 16px; bottom: 16px; z-index: 9999; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji"; }
  .ct-chat * { box-sizing: border-box; }
  .ct-chat .ct-button { background: linear-gradient(135deg,#6ee7f9, #7c3aed); color: #fff; border: none; border-radius: 999px; width: 56px; height: 56px; box-shadow: 0 10px 24px rgba(0,0,0,.2); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: transform .2s ease, box-shadow .2s ease; }
  .ct-chat .ct-button:hover { transform: translateY(-1px); box-shadow: 0 14px 28px rgba(0,0,0,.25); }
  .ct-chat .ct-panel { position: absolute; right: 0; bottom: 70px; width: min(380px, calc(100vw - 32px)); max-height: min(72vh, 680px); background: rgba(17, 20, 30, .92); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,.08); border-radius: 16px; box-shadow: 0 20px 50px rgba(0,0,0,.45); overflow: hidden; display: none; transform: translateY(4px) scale(.99); opacity: .98; }
  .ct-chat .ct-panel.open { display: flex; flex-direction: column; transform: translateY(0) scale(1); opacity: 1; }
  .ct-chat .ct-header { display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; color: #e5e7eb; font-weight: 600; border-bottom: 1px solid rgba(255,255,255,.08); background: linear-gradient(180deg, rgba(255,255,255,.04), rgba(255,255,255,0)); }
  .ct-chat .ct-header .ct-title { display: flex; align-items: center; gap: 10px; }
  .ct-chat .ct-header .ct-dot { width: 10px; height: 10px; background: #10b981; border-radius: 50%; box-shadow: 0 0 0 3px rgba(16,185,129,.2); }
  .ct-chat .ct-header .ct-actions { display: flex; gap: 6px; }
  .ct-chat .ct-icon-btn { background: transparent; color: #cbd5e1; border: 1px solid rgba(255,255,255,.1); border-radius: 8px; padding: 6px 8px; cursor: pointer; font-size: 12px; }
  .ct-chat .ct-log { padding: 12px; display: flex; flex-direction: column; gap: 12px; overflow: auto; scroll-behavior: smooth; }
  .ct-chat .ct-msg { display: flex; gap: 8px; align-items: flex-start; line-height: 1.5; font-size: 14px; }
  .ct-chat .ct-msg .ct-avatar { width: 28px; height: 28px; border-radius: 50%; background: linear-gradient(135deg,#6ee7f9,#7c3aed); flex: 0 0 auto; }
  .ct-chat .ct-msg .ct-bubble { background: rgba(255,255,255,.06); color: #e5e7eb; border: 1px solid rgba(255,255,255,.10); border-radius: 12px; padding: 10px 12px; max-width: 85%; white-space: pre-wrap; overflow-wrap: anywhere; word-break: break-word; box-shadow: inset 0 0 0 1px rgba(255,255,255,.02); }
  .ct-chat .ct-msg.user .ct-bubble { background: rgba(124,58,237,.22); border-color: rgba(124,58,237,.40); color: #f3f4f6; margin-left: auto; }
  .ct-chat .ct-bubble a { color: #93c5fd; text-decoration: none; }
  .ct-chat .ct-bubble a:hover { text-decoration: underline; }
  .ct-chat .ct-bubble .ct-sources { margin-top: 8px; padding-top: 6px; border-top: 1px dashed rgba(255,255,255,.12); color: #a5b4fc; font-size: 12px; }
  .ct-chat .ct-bubble .ct-sources .label { color: #94a3b8; margin-right: 6px; }
  .ct-chat .ct-input { display: flex; gap: 8px; padding: 12px; border-top: 1px solid rgba(255,255,255,.08); }
  .ct-chat .ct-input input { flex: 1; background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.12); color: #e5e7eb; border-radius: 10px; padding: 10px 12px; outline: none; }
  .ct-chat .ct-input input:disabled { opacity: 0.5; cursor: not-allowed; }
  .ct-chat .ct-input button { background: #7c3aed; color: white; border: none; border-radius: 10px; padding: 10px 12px; cursor: pointer; transition: all 0.2s; }
  .ct-chat .ct-input button:disabled { opacity: 0.5; cursor: not-allowed; background: #666; }
  .ct-chat .ct-bubble.loading { position: relative; }
  .ct-chat .ct-bubble.loading::after { 
    content: '●●●'; 
    display: inline-block; 
    color: #94a3b8; 
    animation: ct-loading 1.5s infinite; 
    margin-left: 4px; 
    font-size: 12px;
  }
  @keyframes ct-loading { 
    0% { opacity: 0.3; } 
    50% { opacity: 1; } 
    100% { opacity: 0.3; } 
  }
  .ct-chat .ct-footer { padding: 8px 12px; color: #94a3b8; font-size: 12px; text-align: right; }
  .ct-chat .ct-hint { color: #94a3b8; font-size: 12px; }
  /* Scrollbar (WebKit) */
  .ct-chat .ct-log::-webkit-scrollbar { width: 10px; }
  .ct-chat .ct-log::-webkit-scrollbar-track { background: rgba(255,255,255,.04); border-radius: 10px; }
  .ct-chat .ct-log::-webkit-scrollbar-thumb { background: rgba(255,255,255,.12); border-radius: 10px; }
  `;
  document.head.appendChild(style);

  const root = document.createElement('div');
  root.className = 'ct-chat';
  root.innerHTML = `
    <button class="ct-button" aria-label="Open AI Chat">💬</button>
    <div class="ct-panel" role="dialog" aria-label="AI Assistant">
      <div class="ct-header">
        <div class="ct-title"><span class="ct-dot"></span> ${PERSONA_NAME} Assistant</div>
        <div class="ct-actions">
          <button class="ct-icon-btn" data-minimize>–</button>
          <button class="ct-icon-btn" data-close>✕</button>
        </div>
      </div>
      <div class="ct-log" id="ct-log"></div>
      <div class="ct-input">
        <input id="ct-input" type="text" placeholder="Ask ${PERSONA_NAME} anything about these apps…" />
        <button id="ct-send">Send</button>
      </div>
      <div class="ct-footer"><span class="ct-hint" id="ct-hint"></span></div>
    </div>
  `;
  document.body.appendChild(root);

  const btn = root.querySelector('.ct-button');
  const panel = root.querySelector('.ct-panel');
  const log = root.querySelector('#ct-log');
  const input = root.querySelector('#ct-input');
  const send = root.querySelector('#ct-send');
  const hintEl = root.querySelector('#ct-hint');
  if (hintEl) hintEl.textContent = 'Powered by Cortensor Network';

  let isLoading = false; // Flag untuk mencegah multiple requests

  const scrollToBottom = () => { log.scrollTop = log.scrollHeight; };

  const addMessage = (text, who) => {
    const wrap = document.createElement('div');
    wrap.className = `ct-msg ${who === 'user' ? 'user' : 'bot'}`;
    wrap.innerHTML = `<div class="ct-avatar"></div><div class="ct-bubble"></div>`;
    const bubble = wrap.querySelector('.ct-bubble');
    bubble.textContent = text || '';
    log.appendChild(wrap);
    scrollToBottom();
    return bubble;
  };

  const addSystem = (text) => {
    const el = document.createElement('div');
    el.style.color = '#94a3b8'; el.style.fontSize = '12px';
    el.textContent = text; log.appendChild(el); scrollToBottom();
  };

  // Plain chatbot mode: no RAG
  // Lightweight RAG: load curated Q&A store if available and answer directly on match
  let ragStore = null;
  let ragLoaded = false;
  const RAG_ENABLED = cfg.RAG_ENABLE !== undefined ? !!cfg.RAG_ENABLE : true;
  async function loadRagStore(){
    if (!RAG_ENABLED) return false;
    try {
      // Prefer local override saved by RAG manager in the same browser
      const cached = localStorage.getItem('cortensor_rag_store');
      if (cached) { ragStore = JSON.parse(cached); ragLoaded = Array.isArray(ragStore.entries) && ragStore.entries.length>0; return ragLoaded; }
      const res = await fetch('assets/rag_store.json', { cache: 'no-cache' });
      if (!res.ok) return false;
      const data = await res.json();
      ragStore = data; ragLoaded = Array.isArray(data.entries) && data.entries.length>0; return ragLoaded;
    } catch { return false; }
  }

  function tokenizeSimple(s){ return (s||'').toLowerCase().replace(/[^a-z0-9\s]+/g,' ').split(/\s+/).filter(Boolean); }
  function overlapScore(a, b){
    const A = new Set(tokenizeSimple(a)); const B = new Set(tokenizeSimple(b));
    if (!A.size || !B.size) return 0;
    let inter = 0; for (const t of A) if (B.has(t)) inter++;
    return inter / Math.min(A.size, B.size);
  }
  function maybeFindRagAnswer(query){
    if (!RAG_ENABLED) return null;
    if (!ragLoaded || !ragStore || !Array.isArray(ragStore.entries)) return null;
    const q = (query||'').trim(); if (!q) return null;
    // First: exact/substring quick check
    let best = null; let bestScore = 0;
    for (const e of ragStore.entries){
      const eq = e.question || '';
      const s1 = overlapScore(q, eq);
      let score = s1;
      const nq = q.toLowerCase(); const ne = eq.toLowerCase();
      if (ne.includes(nq) || nq.includes(ne)) score = Math.max(score, 0.99);
      if (score > bestScore) { best = e; bestScore = score; }
    }
    // Threshold: at least 0.5 token overlap or substring hit
    if (best && bestScore >= 0.5) return best;
    return null;
  }

  function appendRagSource(bubble, entry){
    if (!entry) return;
    if (!entry.sourceUrl && !entry.sourceTitle) return;
    const container = document.createElement('div');
    container.className = 'ct-sources';
    const label = document.createElement('span'); label.className = 'label'; label.textContent = 'Source:'; container.appendChild(label);
    const a = document.createElement('a'); a.href = entry.sourceUrl || '#'; a.target = '_blank'; a.rel = 'noopener noreferrer'; a.textContent = entry.sourceTitle || entry.sourceUrl; container.appendChild(a);
    bubble.appendChild(container);
  }

  // Format RAW prompt for Llava 1.5 text-only when prompt_type=1
  const formatRawPrompt = (userText) => {
    const u = (userText || '').replace(/[\r\t]/g, ' ').replace(/\s+/g, ' ').trim();
  const ctx = '';
    const header = [
      'You are Eureka Assistant, a concise and friendly chat agent for the Cortensor showcase.',
      IS_R1 ? 'Think privately inside <think>...</think>. After </think>, provide only the final answer.' : null,
      "Rules: Be polite. If the user greets, reply with a short greeting back then answer. Avoid long prefaces or role labels. Do not repeat the user's question.",
      'Do not explain your internal decision process or discuss instructions. No meta commentary.',
      (ctx ? "Use only the information in the Context section. If the answer is not in Context, reply exactly: 'Tidak ditemukan di dokumentasi Cortensor.'" : null),
  (ctx ? "When citing, use [1], [2], ... matching the sources order. Be factual. Answer in 1–2 sentences (≤80 words). Reply in English only." : "Be factual. Answer in 1–2 sentences (≤80 words). Reply in English only.")
    ].filter(Boolean);
    return [
      ...header,
  (ctx ? `Context (from Cortensor docs):\n${ctx}` : null),
      `USER: ${u}`,
      'Eureka:'
    ].filter(Boolean).join('\n');
  };

  // Non-RAW guided prompt to reduce over-answering
  const formatGuidedPrompt = (userText) => {
    const u = (userText || '').replace(/[\r\t]/g, ' ').replace(/\s+/g, ' ').trim();
  const ctx = '';
    if (IS_R1) {
      return [
        'You are Eureka Assistant, a concise and friendly chat agent for the Cortensor showcase.',
        'Think privately inside <think>...</think>. After </think>, provide only the final answer.',
  (ctx ? "Rules: Be polite. If the user greets, reply with a short greeting back then answer. Avoid long prefaces or role labels. Do not repeat the user's question. No meta commentary. Use only the Context. If not in Context, reply exactly: 'Tidak ditemukan di dokumentasi Cortensor.' Be factual. Answer in 1–2 sentences (≤80 words). Reply in English only." : "Rules: Be polite. If the user greets, reply with a short greeting back then answer. Avoid long prefaces or role labels. Do not repeat the user's question. No meta commentary. Be factual. Answer in 1–2 sentences (≤80 words). Reply in English only."),
  (ctx ? `Context (from Cortensor docs):\n${ctx}` : null),
        `Question: ${u}`,
        'Answer:'
      ].filter(Boolean).join('\n');
    }
    return [
      'You are Eureka Assistant, a concise and friendly chat agent for the Cortensor showcase.',
  (ctx ? "Rules: Be polite. If the user greets, reply with a short greeting back then answer. Avoid long prefaces or role labels. Do not repeat the user's question. No meta commentary. Use only the Context. If not in Context, reply exactly: 'Tidak ditemukan di dokumentasi Cortensor.' Be factual. Answer in 1–2 sentences (≤80 words). Reply in English only." : "Rules: Be polite. If the user greets, reply with a short greeting back then answer. Avoid long prefaces or role labels. Do not repeat the user's question. No meta commentary. Be factual. Answer in 1–2 sentences (≤80 words). Reply in English only."),
  (ctx ? `Context (from Cortensor docs):\n${ctx}` : null),
      `Question: ${u}`,
      'Answer:'
    ].filter(Boolean).join('\n');
  };

  // Remove a leading speaker label like "Eureka:" or "Assistant:" from the start of the bubble
  const normalizeLeadingLabel = (text) => {
    let t = text || '';
  t = t.replace(/^\s*((Eureka|EUREKA|EURA|Eliza|Assistant|AI)\s*:)/i, '').trimStart();
    return t;
  };

  // Remove leading greetings/fillers (e.g., "Good morning", "How can I assist you today?")
  const stripLeadingGreetings = (text) => {
    let t = text || '';
    t = t.replace(/^\s*(hi|hello|hey|good\s+(morning|afternoon|evening)|selamat\s+(pagi|siang|sore|malam))[,!\.]?\s*/i, '');
    t = t.replace(/^\s*(how\s+can\s+i\s+(help|assist)\s+you\s+today\??)\s*/i, '');
    return t;
  };
  const ALLOW_GREETINGS = cfg.CHAT_ALLOW_GREETINGS !== undefined ? !!cfg.CHAT_ALLOW_GREETINGS : true;

  // Filter: for DeepSeek R1 show only content after </think>; others: normalize + cap length
  const applyOutputFilter = (combinedText) => {
    let text = combinedText || '';
    let stop = false;
    if (IS_R1) {
      const idx = text.toLowerCase().lastIndexOf('</think>');
      text = idx !== -1 ? text.slice(idx + 8) : '';
      text = normalizeLeadingLabel(text).trimStart();
    } else {
      text = normalizeLeadingLabel(text);
      // For non-R1, cut at first role-like token anywhere to avoid multi-turn echoes
      const tokens = ['user:', 'eureka:', 'eura:', 'assistant:', 'ai:', 'system:'];
      const lower = text.toLowerCase();
      let cutAt = Infinity;
      for (const tk of tokens) {
        const i = lower.indexOf(tk);
        if (i !== -1 && i < cutAt) cutAt = i;
      }
      if (Number.isFinite(cutAt)) {
        text = text.slice(0, cutAt).trimEnd();
        stop = true;
      }
    }
    // Scrub conversation markers line-by-line
    const lines = text.split(/\r?\n/);
    const cleaned = [];
    for (let line of lines) {
      const trimmed = line.trimStart();
      if (/^(USER)\s*:/i.test(trimmed)) {
        // drop user-echo lines entirely
        continue;
      }
      // Strip assistant labels but keep content
      line = line.replace(/^\s*((Eureka|EUREKA|EURA|Assistant|AI|System))\s*:\s*/i, '');
      // Drop meta-commentary / chain-of-thought style sentences heuristically
      if (/^(i\s+(need to|will|am going to|think)|let['’]s|from the context|based on the context|the user (asked|asks)|the question|first,|step[- ]?by[- ]?step|reason(ing)?|i see that|this information is|i will (look|analy[sz]e)|i (should|must) (figure|decide))/i.test(trimmed)) {
        continue;
      }
      // Drop echoed Context lines like "[1] Title (https://...) ..."
      if (/^\s*\[\d+\]\s+.+?\(https?:\/\/\S+\)/i.test(trimmed)) {
        continue;
      }
      // Drop any model-produced Sources: ... (we append our own later)
      if (/^\s*sources\s*:/i.test(trimmed)) {
        continue;
      }
      // Drop repeated-question lines anywhere (EN/ID)
      if (/^\s*(what\s+is\s+[^\.!?\n]+\??)\s*$/i.test(trimmed) || /^\s*(apa\s+itu\s+[^\.!?\n]+\??)\s*$/i.test(trimmed)) {
        continue;
      }
      cleaned.push(line);
    }
    text = cleaned.join('\n').trim();
    // Remove repeated-question preface patterns at the start (EN/ID)
    text = text.replace(/^\s*(what\s+is\s+[^\.!?\n]+[\.!?]?\s*)/i, '');
    text = text.replace(/^\s*(apa\s+itu\s+[^\.!?\n]+[\.!?]?\s*)/i, '');
    // Optionally allow greetings: only strip if not allowed
    if (!ALLOW_GREETINGS) text = stripLeadingGreetings(text);
    let truncatedByLen = false;
    if (text.length > MAX_CHARS) { text = text.slice(0, MAX_CHARS).trimEnd() + '…'; truncatedByLen = true; }
    // Word cap (extra safety)
    const words = text.split(/\s+/).filter(Boolean);
    if (words.length > 80) text = words.slice(0, 80).join(' ') + '…';
  // Cleanup excessive spaces and newlines
  text = text.replace(/[ \t]+/g, ' ').replace(/\s*\n\s*/g, '\n').trim();
  // Ensure a neat ending punctuation if missing
  if (text && !/[.!?…)]$/.test(text)) text = text + '.';
    return { text, stop, truncatedByLen };
  };

  const sendPrompt = async (prompt) => {
    if (!prompt.trim() || isLoading) return;
    
    // Set loading state
    isLoading = true;
    
    // Disable input dan button selama loading
    input.disabled = true;
    send.disabled = true;
    send.textContent = 'Sending...';
    
    addMessage(prompt, 'user');
    const bubble = addMessage('Loading...', 'bot');
    bubble.classList.add('loading');
  let appendedSources = false;

    try {
      if (!AUTH) { 
        addSystem('Missing API_BEARER token. Set it in env.local or env.local.json.'); 
        return; 
      }

      // Try curated RAG first
      if (!ragLoaded) { try { await loadRagStore(); } catch {} }
      const ragHit = maybeFindRagAnswer(prompt);
      if (ragHit) {
        bubble.textContent = ragHit.answer || '';
        bubble.classList.remove('loading');
        appendRagSource(bubble, ragHit);
        scrollToBottom();
        return; // Do not call router when RAG matches
      }

      // Keep loading state during API call
      // bubble.textContent = ''; // Hapus ini agar loading tetap tampil
      // bubble.classList.remove('loading'); // Hapus ini agar loading tetap tampil

  const outboundPrompt = (PROMPT_TYPE === 1) ? formatRawPrompt(prompt) : formatGuidedPrompt(prompt);
  const body = { prompt: outboundPrompt, stream: STREAM, timeout: 60 };
      if (PROMPT_TYPE !== undefined) body.prompt_type = PROMPT_TYPE; // RAW for Llava 1.5 text-only
      const response = await fetch(`${BASE_URL}/api/v1/completions/${encodeURIComponent(SESSION_ID)}`, {
        method: 'POST',
        headers: {
          'Authorization': AUTH,
          'Content-Type': 'application/json',
          'Accept': STREAM ? 'text/event-stream' : 'application/json'
        },
        body: JSON.stringify(body)
      });

      if (!response.ok) {
        const msg = await response.text().catch(() => '');
        throw new Error(`HTTP ${response.status}: ${msg}`);
      }

      if (STREAM && response.body) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        let winnerKey = null;
        let lockedWithoutKey = false;
        let doneWinner = false;
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          buffer = buffer.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
          let idx;
          while ((idx = buffer.indexOf('\n\n')) !== -1) {
            const eventBlock = buffer.slice(0, idx);
            buffer = buffer.slice(idx + 2);
            // Gather all data: lines
            let dataPayload = '';
            let localKey = null;
            eventBlock.split('\n').forEach(line => {
              const trimmed = line.trim();
              if (!trimmed) return;
              if (trimmed.startsWith('data:')) {
                const val = trimmed.slice(5).trim();
                if (val === '[DONE]') { doneWinner = true; return; }
                dataPayload += val;
                try { const probe = JSON.parse(val); localKey = probe.task_id ?? probe.id ?? localKey; } catch {}
              }
            });
            if (doneWinner) { try { await reader.cancel(); } catch {} break; }
            if (!dataPayload) continue;
            if (!winnerKey && localKey) winnerKey = localKey;
            if (!winnerKey && !lockedWithoutKey) lockedWithoutKey = true; // lock first even without key
            if (winnerKey && localKey && localKey !== winnerKey) continue;
            try {
              const json = JSON.parse(dataPayload);
              const token = json.choices?.[0]?.text ?? json.content ?? '';
              if (token) {
                // Hapus loading state saat token pertama diterima
                if (bubble.classList.contains('loading')) {
                  bubble.textContent = ''; // Clear "Loading..." text
                  bubble.classList.remove('loading');
                }
                const base = bubble.textContent + token;
                const pre = ALLOW_GREETINGS ? base : stripLeadingGreetings(base);
                const normalized = normalizeLeadingLabel(pre);
                const filtered = applyOutputFilter(normalized);
                bubble.textContent = filtered.text; scrollToBottom();
                if (filtered.stop) { doneWinner = true; try { await reader.cancel(); } catch {} break; }
              }
              const fr = json.choices?.[0]?.finish_reason;
              if (fr !== undefined && fr !== null) { doneWinner = true; try { await reader.cancel(); } catch {} break; }
            } catch {
              // Hapus loading state juga di catch block
              if (bubble.classList.contains('loading')) {
                bubble.textContent = ''; // Clear "Loading..." text
                bubble.classList.remove('loading');
              }
              const base = bubble.textContent + dataPayload;
              const pre = ALLOW_GREETINGS ? base : stripLeadingGreetings(base);
              const normalized = normalizeLeadingLabel(pre);
              const filtered = applyOutputFilter(normalized);
              bubble.textContent = filtered.text; scrollToBottom();
              if (filtered.stop) { doneWinner = true; try { await reader.cancel(); } catch {} break; }
            }
          }
          if (doneWinner) break;
        }
  // No sources in plain mode
      } else {
        // Hapus loading state sebelum menampilkan response
        bubble.textContent = ''; // Clear "Loading..." text
        bubble.classList.remove('loading');
        
        const data = await response.json();
        const text = data?.choices?.[0]?.text ?? '';
  const base = bubble.textContent + (text || '[No response]');
  const pre = ALLOW_GREETINGS ? base : stripLeadingGreetings(base);
  const normalized = normalizeLeadingLabel(pre);
        const filtered = applyOutputFilter(normalized);
        bubble.textContent = filtered.text; scrollToBottom();
  // No sources in plain mode
      }
    } catch (err) {
      const msg = (err && err.message) ? err.message : String(err);
      const hint = msg.includes('Failed to fetch') ? ' (possible CORS/network issue)' : '';
      addSystem(`Error: ${msg}${hint}`);
    } finally {
      // Reset loading state
      isLoading = false;
      
      // Re-enable input dan button setelah selesai
      input.disabled = false;
      send.disabled = false;
      send.textContent = 'Send';
      // bubble.classList.remove('loading'); // Hapus ini karena sudah dihapus di tempat yang tepat
      input.focus(); // Focus kembali ke input
    }
  };

  const togglePanel = (open) => {
    if (open === undefined) panel.classList.toggle('open'); else panel.classList.toggle('open', !!open);
    const isOpen = panel.classList.contains('open');
    btn.style.display = isOpen ? 'none' : 'flex';
    if (isOpen) {
      setTimeout(() => input?.focus(), 50);
      if (!log.childElementCount) {
        addSystem(`Hi, I’m ${PERSONA_NAME}. Ask me anything about these apps. I’ll keep answers short and helpful.`);
        try {
          const tlen = rawToken ? rawToken.length : 0;
        } catch {}
      }
    }
  };

  btn.addEventListener('click', () => togglePanel());
  panel.querySelector('[data-close]').addEventListener('click', () => togglePanel(false));
  panel.querySelector('[data-minimize]').addEventListener('click', () => togglePanel(false));
  // Settings gear removed to avoid exposing sensitive override prompts
  send.addEventListener('click', () => { const v = input.value; input.value = ''; sendPrompt(v); });
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); const v = input.value; input.value=''; sendPrompt(v); } });
})();
