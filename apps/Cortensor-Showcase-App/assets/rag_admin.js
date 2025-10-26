(() => {
  const els = {
    status: document.getElementById('statusText'),
    importInput: document.getElementById('importInput'),
    exportBtn: document.getElementById('exportBtn'),
    addNewBtn: document.getElementById('addNewBtn'),
    tableBody: document.querySelector('#ragTable tbody'),
    form: document.getElementById('editorForm'),
    editorTitle: document.getElementById('editorTitle'),
    // fields
    f_id: document.getElementById('f_id'),
    f_question: document.getElementById('f_question'),
    f_answer: document.getElementById('f_answer'),
    f_tags: document.getElementById('f_tags'),
    f_created: document.getElementById('f_created'),
    f_sourceTitle: document.getElementById('f_sourceTitle'),
    f_sourceUrl: document.getElementById('f_sourceUrl'),
    // auth
    lockBtn: document.getElementById('lockBtn'),
    authOverlay: document.getElementById('authOverlay'),
    authForm: document.getElementById('authForm'),
    authId: document.getElementById('authId'),
    authPin: document.getElementById('authPin'),
  };

  const state = {
    data: { updatedAt: '', entries: [] },
    filtered: [], selIndex: -1, locked: true, passOk: false,
  };

  const toast = (msg) => {
    let t = document.querySelector('.toast'); if (!t) { t = document.createElement('div'); t.className = 'toast'; document.body.appendChild(t); }
    t.textContent = msg; t.classList.add('in'); clearTimeout(t._to); t._to = setTimeout(()=> t.classList.remove('in'), 1600);
  };

  const slug = (s) => (s||'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/(^-|-$)/g,'');
  const debounce = (fn, t=200) => { let to; return (...a)=>{ clearTimeout(to); to=setTimeout(()=>fn(...a),t); }; };

  function setLock(val){
    state.locked = val; els.lockBtn.textContent = val? 'Unlock' : 'Lock';
    [...els.form.elements].forEach(e=> e.disabled = val);
  }

  function renderList(){
    const q = (document.getElementById('searchRag').value||'').toLowerCase();
    const rows = state.data.entries.filter(e => !q || `${e.id} ${e.question} ${(e.tags||[]).join(' ')}`.toLowerCase().includes(q));
    state.filtered = rows;
    els.tableBody.innerHTML = '';
    const frag = document.createDocumentFragment();
    rows.forEach((e) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><code>${e.id}</code></td>
        <td>${e.question}</td>
        <td>${(e.tags||[]).join(', ')}</td>
        <td>${e.createdAt||''}</td>
        <td style="text-align:right"><button class="btn ghost" data-edit="${e.id}">Edit</button></td>
      `;
      frag.appendChild(tr);
    });
    els.tableBody.appendChild(frag);
    els.tableBody.querySelectorAll('[data-edit]').forEach(b => b.addEventListener('click', () => {
      const id = b.getAttribute('data-edit');
      const idx = state.data.entries.findIndex(x=>x.id===id);
      if (idx>-1) loadToForm(idx);
    }));
  }

  function clearForm(){ els.form.reset(); state.selIndex=-1; els.editorTitle.textContent = 'Editor'; }

  function loadToForm(index){
    const it = state.data.entries[index]; if (!it) return;
    state.selIndex = index; els.editorTitle.textContent = `Editing: ${it.id}`;
    els.f_id.value = it.id || '';
    els.f_question.value = it.question || '';
    els.f_answer.value = it.answer || '';
    els.f_tags.value = (it.tags||[]).join(', ');
    els.f_created.value = it.createdAt || '';
    els.f_sourceTitle.value = it.sourceTitle || '';
    els.f_sourceUrl.value = it.sourceUrl || '';
  }

  function readForm(){
    const q = els.f_question.value.trim();
    let id = els.f_id.value.trim();
    if (!id && q) id = slug(q);
    return {
      id,
      question: q,
      answer: els.f_answer.value.trim(),
      tags: els.f_tags.value.split(',').map(s=>s.trim()).filter(Boolean),
      createdAt: els.f_created.value || new Date().toISOString().slice(0,10),
      sourceTitle: els.f_sourceTitle.value.trim(),
      sourceUrl: els.f_sourceUrl.value.trim(),
    };
  }

  function upsertEntry(entry){
    const exists = state.data.entries.findIndex(x=>x.id===entry.id);
    if (exists === -1 && state.data.entries.some(x=>x.id===entry.id)) throw new Error('Duplicate ID');
    if (exists>-1) state.data.entries[exists] = entry; else state.data.entries.push(entry);
    state.data.updatedAt = new Date().toISOString().slice(0,10);
    autosave();
  }

  function deleteEntry(id){
    state.data.entries = state.data.entries.filter(x=>x.id!==id);
    state.data.updatedAt = new Date().toISOString().slice(0,10);
    autosave();
  }

  function exportJSON(){
    const blob = new Blob([JSON.stringify(state.data, null, 2)], {type:'application/json'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = 'rag_store.json'; a.click(); URL.revokeObjectURL(a.href);
    toast('Exported rag_store.json');
  }

  async function loadInitial(){
    try{
      const cached = localStorage.getItem('cortensor_rag_store');
      if (cached){
        state.data = JSON.parse(cached); renderList(); return;
      }
      const res = await fetch('assets/rag_store.json', {cache:'no-cache'});
      if (!res.ok) throw new Error('Missing rag_store.json');
      const data = await res.json();
      if (!Array.isArray(data.entries)) throw new Error('Invalid JSON: missing entries[]');
      state.data = data; renderList();
    }catch(err){ console.warn(err); state.data = { updatedAt: '', entries: [] }; renderList(); }
  }

  function autosave(){
    try { localStorage.setItem('cortensor_rag_store', JSON.stringify(state.data)); } catch {}
  }

  // Auth like Admin
  function requireAuth(){
    if (sessionStorage.getItem('cortensor_admin_auth') === '1') return true;
    els.authOverlay.classList.add('show');
    return false;
  }

  els.authForm.addEventListener('submit', async (e)=>{
    e.preventDefault();
    if (window.waitForAppConfig) { try { await window.waitForAppConfig; } catch {} }
    const cfg = window.APP_CONFIG || {};
    const id = els.authId.value.trim();
    const pin = els.authPin.value.trim();
    const expectedId = cfg.ADMIN_ID || 'admin';
    const expectedPin = cfg.ADMIN_PIN || '4718';
    if (id === expectedId && pin === expectedPin){
      sessionStorage.setItem('cortensor_admin_auth', '1');
      els.authOverlay.classList.remove('show');
      toast('Signed in');
      initAfterAuth();
    } else {
      toast('Invalid credentials');
    }
  });

  function initAfterAuth(){
    setLock(true);
    loadInitial();
  }

  // Events
  document.getElementById('lockBtn').addEventListener('click', ()=>{
    if (!state.locked) return setLock(true);
    const code = prompt('Enter admin passcode');
    if (!code) return;
    if (code.length >= 4) { state.passOk = true; setLock(false); toast('Unlocked'); } else { toast('Invalid passcode'); }
  });
  document.getElementById('addNewBtn').addEventListener('click', ()=> { clearForm(); if (state.locked) toast('Unlock to edit'); els.editorTitle.textContent = 'New Entry'; });
  document.getElementById('exportBtn').addEventListener('click', exportJSON);
  document.getElementById('resetBtn').addEventListener('click', clearForm);
  document.getElementById('deleteBtn').addEventListener('click', ()=>{
    if (state.locked) return toast('Unlock to edit');
    const id = els.f_id.value.trim(); if (!id) return;
    if (confirm(`Delete ${id}?`)) { deleteEntry(id); clearForm(); renderList(); toast('Deleted'); }
  });
  els.form.addEventListener('submit', (e)=>{
    e.preventDefault(); if (state.locked) return toast('Unlock to edit');
    const it = readForm(); if (!it.id) { toast('ID is required'); return; }
    try{ upsertEntry(it); renderList(); toast('Saved'); } catch(err){ toast(err.message||'Save failed'); }
  });
  els.importInput.addEventListener('change', async (e)=>{
    const file = e.target.files?.[0]; if (!file) return;
    try{
      const text = await file.text();
      const data = JSON.parse(text);
      if (!Array.isArray(data.entries)) throw new Error('Invalid JSON: missing entries[]');
      state.data = data; renderList(); toast('Imported');
    }catch(err){ console.error(err); toast('Import failed'); }
    finally { e.target.value=''; }
  });

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.reveal').forEach(el => el.classList.add('in'));
    if (requireAuth()) initAfterAuth();
  });
})();
