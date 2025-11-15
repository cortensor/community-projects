(() => {
  const els = {
    preloader: document.getElementById('preloader'),
    status: document.getElementById('statusText'),
    importInput: document.getElementById('importInput'),
    exportBtn: document.getElementById('exportBtn'),
  publishBtn: document.getElementById('publishBtn'),
    addNewBtn: document.getElementById('addNewBtn'),
  newAppBtn: document.getElementById('newAppBtn'),
  newBotBtn: document.getElementById('newBotBtn'),
  newPkgBtn: document.getElementById('newPkgBtn'),
  newResBtn: document.getElementById('newResBtn'),
    lockBtn: document.getElementById('lockBtn'),
    search: document.getElementById('searchAdmin'),
    type: document.getElementById('typeAdmin'),
    tableBody: document.querySelector('#itemsTable tbody'),
    form: document.getElementById('editorForm'),
    editorTitle: document.getElementById('editorTitle'),
    // fields
    f_id: document.getElementById('f_id'),
    f_type: document.getElementById('f_type'),
    f_name: document.getElementById('f_name'),
    f_clicks: document.getElementById('f_clicks'),
    f_url: document.getElementById('f_url'),
    f_image: document.getElementById('f_image'),
  f_image_file: document.getElementById('f_image_file'),
  f_image_embed: document.getElementById('f_image_embed'),
  f_image_preview: document.getElementById('f_image_preview'),
    f_created: document.getElementById('f_created'),
    f_tags: document.getElementById('f_tags'),
    f_highlight: document.getElementById('f_highlight'),
    f_desc: document.getElementById('f_desc'),
    extList: document.getElementById('externalList'),
    addExternalBtn: document.getElementById('addExternalBtn'),
  galleryList: document.getElementById('galleryList'),
  addGalleryBtn: document.getElementById('addGalleryBtn'),
    saveBtn: document.getElementById('saveBtn'),
    resetBtn: document.getElementById('resetBtn'),
    deleteBtn: document.getElementById('deleteBtn'),
  duplicateBtn: document.getElementById('duplicateBtn'),
  useDraftToggle: document.getElementById('useDraftToggle'),
  clearDraftBtn: document.getElementById('clearDraftBtn'),
  // deep editor (created dynamically)
  tabBar: null,
  tabForm: null,
  tabJSON: null,
  tabPreview: null,
  jsonArea: null,
  authOverlay: document.getElementById('authOverlay'),
  authForm: document.getElementById('authForm'),
  authId: document.getElementById('authId'),
  authPin: document.getElementById('authPin'),
  };

  const state = {
    data: { updatedAt: '', tags: [], items: [] },
    filtered: [],
    selIndex: -1,
  locked: true,
  passOk: false,
  persistKey: 'cortensor_admin_data',
  useDraft: true,
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
    els.saveBtn.disabled = val; els.deleteBtn.disabled = val;
  }

  // Deep editor tabs & helpers
  function ensureTabs(){
    if (els.tabBar || !els.form) return;
    const panel = els.form.closest('.panel'); if (!panel) return;
    const bar = document.createElement('div');
    bar.className = 'view-toggle';
    bar.style.marginTop = '-6px';
    bar.innerHTML = `
      <button type="button" class="btn ghost" data-tab="form">Form</button>
      <button type="button" class="btn ghost" data-tab="json">JSON</button>
      <button type="button" class="btn ghost" data-tab="preview">Preview</button>
      <label class="btn ghost" style="margin-left:auto; display:inline-flex; align-items:center; gap:8px">
        <input id="autoSlug" type="checkbox" checked style="accent-color:#6a7dff" /> Auto-slug ID
      </label>`;
    panel.querySelector('.panel-head')?.appendChild(bar);
    els.tabBar = bar;
    // Wrap form into Form tab container
    const formWrap = document.createElement('div'); formWrap.id = 'tabFormWrap';
    els.form.parentElement.insertBefore(formWrap, els.form);
    formWrap.appendChild(els.form);
    els.tabForm = formWrap;
    // JSON tab
    const jsonWrap = document.createElement('div'); jsonWrap.id = 'tabJSONWrap'; jsonWrap.style.display = 'none';
    jsonWrap.innerHTML = `<textarea id="jsonEditor" rows="16" style="width:100%; resize:vertical;" placeholder="{\n  \"id\": \"...\",\n  \"type\": \"app\",\n  ...\n}"></textarea>`;
    formWrap.parentElement.appendChild(jsonWrap);
    els.tabJSON = jsonWrap; els.jsonArea = jsonWrap.querySelector('#jsonEditor');
    // Preview tab
    const prev = document.createElement('div'); prev.id = 'tabPreviewWrap'; prev.style.display = 'none'; prev.innerHTML = `<div id="previewCard"></div>`;
    formWrap.parentElement.appendChild(prev); els.tabPreview = prev;
    // Tab switch wiring
    bar.querySelectorAll('[data-tab]').forEach(btn => btn.addEventListener('click', () => switchTab(btn.getAttribute('data-tab'))));
    switchTab('form');
  }

  function switchTab(name){
    const set = (el,on)=> el && (el.style.display = on? '' : 'none');
    set(els.tabForm, name==='form');
    set(els.tabJSON, name==='json');
    set(els.tabPreview, name==='preview');
    els.tabBar?.querySelectorAll('[data-tab]')?.forEach(b => b.classList.toggle('primary', b.getAttribute('data-tab')===name));
    if (name==='json') syncJSONFromForm();
    if (name==='preview') renderPreviewFromForm();
  }

  function syncJSONFromForm(){
    const it = readForm();
    try { if (els.jsonArea) els.jsonArea.value = JSON.stringify(it, null, 2); } catch {}
  }

  function applyJSONToForm(){
    try{
      const obj = JSON.parse(els.jsonArea.value);
      els.f_id.value = obj.id || '';
      els.f_type.value = obj.type || 'app';
      els.f_name.value = obj.name || '';
      els.f_clicks.value = obj.clicks || 0;
      els.f_url.value = obj.url || '';
      els.f_image.value = obj.image || '';
      els.f_created.value = obj.createdAt || '';
      els.f_tags.value = (obj.tags||[]).join(', ');
      els.f_highlight.value = obj.highlight || '';
      els.f_desc.value = obj.description || '';
      renderExternalList(obj.external||[]);
    }catch{ toast('Invalid JSON'); }
  }

  function renderPreviewFromForm(){
    const it = readForm();
    const host = document.getElementById('previewCard'); if (!host) return;
    host.innerHTML = `
      <article class="card" style="max-width:720px; margin:4px auto 0">
        <div class="thumb"><img src="${it.image}" alt="${it.name}" /><span class="badge">${it.type}</span></div>
        <div class="card-body">
          <h3>${it.name}</h3>
          <p class="highlight">${it.highlight||''}</p>
          <div class="tag-list">${(it.tags||[]).slice(0,4).map(t=>`<span class=\"tag small\">#${t}</span>`).join('')}</div>
          <div class="muted preview-desc" style="margin-top:6px">${(it.description||'').replace(/</g,'&lt;')}</div>
        </div>
      </article>`;
  }

  function renderList(){
    const q = (els.search.value||'').toLowerCase();
    const ty = els.type.value;
    const rows = state.data.items.filter(i => (!ty || i.type===ty) && (!q || `${i.id} ${i.name} ${(i.tags||[]).join(' ')}`.toLowerCase().includes(q)));
    state.filtered = rows;
    els.tableBody.innerHTML = '';
    const frag = document.createDocumentFragment();
  rows.forEach((i, idx) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
    <td><label style="display:flex; align-items:center; gap:8px"><input type="checkbox" data-sel="${i.id}" /> <code>${i.id}</code></label></td>
        <td>${i.name}</td>
        <td>${i.type}</td>
        <td>${(i.tags||[]).join(', ')}</td>
        <td>${i.clicks||0}</td>
        <td>${i.createdAt||''}</td>
        <td style="text-align:right">
          <button class="btn ghost" data-edit="${i.id}">Edit</button>
        </td>
      `;
      frag.appendChild(tr);
    });
    els.tableBody.appendChild(frag);

    els.tableBody.querySelectorAll('[data-edit]').forEach(b => b.addEventListener('click', () => {
      const id = b.getAttribute('data-edit');
      const idx = state.data.items.findIndex(x=>x.id===id);
      if (idx>-1) loadToForm(idx);
    }));
    // Row click (excluding interactive elements)
    els.tableBody.querySelectorAll('tr').forEach((tr, i) => {
      tr.addEventListener('click', (e)=>{
        if (e.target.closest('button') || e.target.tagName==='INPUT' || e.target.tagName==='LABEL' || e.target.closest('label')) return;
        const item = rows[i]; if (!item) return;
        const idx = state.data.items.findIndex(x=>x.id===item.id);
        if (idx>-1) loadToForm(idx);
      });
    });
  }

  function clearForm(){ els.form.reset(); els.extList.innerHTML=''; state.selIndex=-1; els.editorTitle.textContent = 'Editor'; }

  function renderExternalList(ext = []){
    els.extList.innerHTML = '';
    ext.forEach((e, i) => addExternalRow(e.label||'', e.url||''));
  }

  function addExternalRow(label='', url=''){
    const row = document.createElement('div');
    row.className = 'ext-row';
    row.innerHTML = `
      <input type="text" placeholder="Label" value="${label.replace(/"/g,'&quot;')}" />
      <input type="url" placeholder="https://..." value="${url.replace(/"/g,'&quot;')}" />
      <span style="display:inline-flex; gap:6px">
        <button class="btn ghost" type="button" data-move="up">▲</button>
        <button class="btn ghost" type="button" data-move="down">▼</button>
        <button class="btn ghost" type="button" data-remove>Remove</button>
      </span>
    `;
    row.querySelector('[data-remove]').addEventListener('click', ()=> row.remove());
    row.querySelectorAll('[data-move]').forEach(btn => btn.addEventListener('click', ()=> moveExtRow(row, btn.getAttribute('data-move'))));
    els.extList.appendChild(row);
  }

  function moveExtRow(row, dir){
    if (!row || !row.parentElement) return;
    if (dir === 'up' && row.previousElementSibling) row.parentElement.insertBefore(row, row.previousElementSibling);
    if (dir === 'down' && row.nextElementSibling) row.parentElement.insertBefore(row.nextElementSibling, row);
  }

  function getExternalFromForm(){
    return [...els.extList.querySelectorAll('.ext-row')].map(r => {
      const [l,u] = r.querySelectorAll('input');
      return { label: l.value.trim(), url: u.value.trim() };
    }).filter(x=>x.label && x.url);
  }

  function loadToForm(index){
    const it = state.data.items[index]; if (!it) return;
    state.selIndex = index; els.editorTitle.textContent = `Editing: ${it.name}`;
    els.f_id.value = it.id || '';
    els.f_type.value = it.type || 'app';
    els.f_name.value = it.name || '';
    els.f_clicks.value = it.clicks || 0;
    els.f_url.value = it.url || '';
  els.f_image.value = it.image || '';
  if (els.f_image_preview) els.f_image_preview.src = it.image || 'assets/placeholders/cover.svg';
    els.f_created.value = it.createdAt || '';
    els.f_tags.value = (it.tags||[]).join(', ');
    els.f_highlight.value = it.highlight || '';
    els.f_desc.value = it.description || '';
    renderExternalList(it.external||[]);
  renderGallery(it.gallery||[]);
  renderPreviewFromForm();
  }

  function readForm(){
    const name = els.f_name.value.trim();
    let id = els.f_id.value.trim();
    if (!id && name) id = slug(name);
    return {
      id,
      type: els.f_type.value,
      name,
      clicks: Number(els.f_clicks.value||0),
      url: els.f_url.value.trim(),
      image: els.f_image.value.trim() || 'assets/placeholders/cover.svg',
      createdAt: els.f_created.value || new Date().toISOString().slice(0,10),
      tags: els.f_tags.value.split(',').map(s=>s.trim()).filter(Boolean),
      highlight: els.f_highlight.value.trim(),
      description: els.f_desc.value.trim(),
      external: getExternalFromForm(),
  gallery: getGalleryFromForm(),
    };
  }

  function upsertItem(item){
    const exists = state.data.items.findIndex(x=>x.id===item.id);
    // Validate duplicate id
    if (exists === -1 && state.data.items.some(x=>x.id===item.id)){
      throw new Error('Duplicate ID');
    }
    if (exists>-1) state.data.items[exists] = item; else state.data.items.push(item);
    state.data.updatedAt = new Date().toISOString().slice(0,10);
    // grow tag universe
  const tset = new Set();
  // Rebuild from items to drop irrelevant tags
  state.data.items.forEach(it => (it.tags||[]).forEach(t => tset.add(t)));
  state.data.tags = [...tset].sort();
    autosave();
  }

  // --- Gallery Support (images 2-4) ---
  function renderGallery(arr = []){
    if (!els.galleryList) return; els.galleryList.innerHTML='';
    arr.slice(0,3).forEach(src => addGalleryRow(src));
  }
  function addGalleryRow(src=''){
    if (!els.galleryList) return; if (els.galleryList.children.length >= 3) { toast('Max 3 gallery images'); return; }
    const row = document.createElement('div'); row.className='gallery-row';
    row.innerHTML = `
      <div>
        <input type="text" placeholder="Image URL or data URL" value="${(src||'').replace(/"/g,'&quot;')}" />
        <img class="gallery-thumb" alt="Preview" />
        <div style="display:flex; gap:6px; flex-wrap:wrap; margin-top:6px">
          <input type="file" accept="image/*" data-up type="file" style="flex:1" />
          <label class="checkbox-inline" style="display:inline-flex; align-items:center; gap:6px; font-size:.75rem"><input data-embed type="checkbox" /> Embed</label>
        </div>
      </div>
      <div class="g-actions">
        <button type="button" class="btn ghost" data-g-move="up">▲</button>
        <button type="button" class="btn ghost" data-g-move="down">▼</button>
        <button type="button" class="btn ghost" data-g-del>✕</button>
      </div>`;
    const input = row.querySelector('input[type=text]');
    const img = row.querySelector('.gallery-thumb');
    const fileInput = row.querySelector('[data-up]');
    const embedChk = row.querySelector('[data-embed]');
    const updatePreview = () => { img.src = input.value || 'assets/placeholders/cover.svg'; };
    input.addEventListener('input', updatePreview); updatePreview();
    fileInput.addEventListener('change', ()=>{
      const f = fileInput.files?.[0]; if(!f) return;
      if (embedChk.checked){
        const r = new FileReader(); r.onload = ()=> { input.value = r.result||''; updatePreview(); }; r.readAsDataURL(f);
      } else {
        (async ()=>{
          try{
            const fd = new FormData(); fd.append('file', f);
            const pin = (window.APP_CONFIG?.ADMIN_PIN) || '';
            const resp = await fetch('/api/upload', { method:'POST', body: fd, headers: pin? {'x-admin-pin': pin}:{}});
            const out = await resp.json().catch(()=>null);
            if(!resp.ok || !out?.ok) throw new Error(out?.error||'Upload failed');
            input.value = out.url || (`/database/images/${out.filename}`); updatePreview(); toast('Uploaded');
          }catch(err){ console.error(err); toast('Upload failed'); }
        })();
      }
    });
    row.querySelector('[data-g-del]').addEventListener('click', ()=> row.remove());
    row.querySelectorAll('[data-g-move]').forEach(btn => btn.addEventListener('click', ()=> moveGalleryRow(row, btn.getAttribute('data-g-move'))));
    els.galleryList.appendChild(row);
  }
  function moveGalleryRow(row, dir){
    if (dir==='up' && row.previousElementSibling) row.parentElement.insertBefore(row, row.previousElementSibling);
    if (dir==='down' && row.nextElementSibling) row.parentElement.insertBefore(row.nextElementSibling, row);
  }
  function getGalleryFromForm(){
    if (!els.galleryList) return [];
    return [...els.galleryList.querySelectorAll('.gallery-row')].map(r=> r.querySelector('input[type=text]').value.trim()).filter(Boolean).slice(0,3);
  }

  function deleteItem(id){
    state.data.items = state.data.items.filter(x=>x.id!==id);
    state.data.updatedAt = new Date().toISOString().slice(0,10);
  autosave();
  }

  function exportJSON(){
    const blob = new Blob([JSON.stringify(state.data, null, 2)], {type:'application/json'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = 'data.json'; a.click(); URL.revokeObjectURL(a.href);
    toast('Exported data.json');
  }

  async function loadInitial(){
    try{
      // Respect draft toggle
      const preferDraft = (localStorage.getItem('cortensor_admin_use_draft')||'1') === '1';
      state.useDraft = preferDraft;
      if (els.useDraftToggle) els.useDraftToggle.checked = preferDraft;
      // Load autosaved first if enabled
      if (preferDraft){
        const cached = localStorage.getItem(state.persistKey);
        if (cached){
          state.data = JSON.parse(cached);
          els.status.textContent = `Loaded draft (${state.data.items?.length||0} items).`;
          renderList(); setTimeout(()=> els.preloader?.classList.add('hidden'), 200);
          return;
        }
      }
      const res = await fetch('assets/data.json', {cache:'no-cache'});
      const data = await res.json();
      state.data = data;
      els.status.textContent = `Loaded ${data.items?.length||0} items. Updated ${data.updatedAt||''}`;
      renderList();
      // Deep link to item editor via ?id=
      const p = new URLSearchParams(location.search);
      const wanted = p.get('id');
      if (wanted){
        const idx = state.data.items.findIndex(x=>x.id===wanted);
        if (idx>-1) loadToForm(idx);
      }
    }catch(err){
      console.error(err); els.status.textContent = 'Failed to load data.json';
    }finally{ setTimeout(()=> els.preloader?.classList.add('hidden'), 300); }
  }

  function autosave(){
  if (!state.useDraft) return;
  try { localStorage.setItem(state.persistKey, JSON.stringify(state.data)); } catch {}
  }

  function bulkDelete(){
    const ids = [...document.querySelectorAll('[data-sel]:checked')].map(el=> el.getAttribute('data-sel'));
    if (!ids.length) return toast('Select rows first');
    if (!confirm(`Delete ${ids.length} item(s)?`)) return;
    ids.forEach(id => deleteItem(id));
    renderList(); toast('Deleted');
  }

  // Events
  els.lockBtn.addEventListener('click', ()=> {
    if (!state.locked) return setLock(true);
    const code = prompt('Enter admin passcode');
    if (!code) return;
    // Simple client-side passcode check (replace with real auth in production)
    if (code.length >= 4) { state.passOk = true; setLock(false); toast('Unlocked'); } else { toast('Invalid passcode'); }
  });
  els.exportBtn.addEventListener('click', exportJSON);
  els.publishBtn?.addEventListener('click', async ()=> {
    if (state.locked) return toast('Unlock to publish');
    if (!confirm('Publish current draft to server? This overwrites assets/data.json.')) return;
    try {
      const pin = (window.APP_CONFIG?.ADMIN_PIN) || '';
      const res = await fetch('/api/publish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(pin? { 'x-admin-pin': pin }: {}) },
        body: JSON.stringify(state.data),
      });
      const out = await res.json().catch(()=>null);
      if (!res.ok || !out?.ok) throw new Error(out?.error||'Publish failed');
      toast('Published');
    } catch(err){ console.error(err); toast('Publish failed'); }
  });
  els.addNewBtn.addEventListener('click', ()=> { clearForm(); if (state.locked) toast('Unlock to edit'); els.editorTitle.textContent = 'New Item'; });
  els.newAppBtn?.addEventListener('click', ()=> { clearForm(); els.f_type.value='app'; els.f_highlight.value=''; els.f_desc.value=''; els.f_image.value='assets/placeholders/cover.svg'; renderPreviewFromForm(); els.editorTitle.textContent='New App'; });
  els.newBotBtn?.addEventListener('click', ()=> { clearForm(); els.f_type.value='bot'; els.f_highlight.value=''; els.f_desc.value=''; els.f_image.value='assets/placeholders/cover.svg'; renderPreviewFromForm(); els.editorTitle.textContent='New Bot'; });
  els.newPkgBtn?.addEventListener('click', ()=> { clearForm(); els.f_type.value='package'; els.f_highlight.value=''; els.f_desc.value=''; els.f_image.value='assets/placeholders/cover.svg'; renderPreviewFromForm(); els.editorTitle.textContent='New Package'; });
  els.newResBtn?.addEventListener('click', ()=> { clearForm(); els.f_type.value='resource'; els.f_highlight.value=''; els.f_desc.value=''; els.f_image.value='assets/placeholders/cover.svg'; renderPreviewFromForm(); els.editorTitle.textContent='New Resource'; });
  // Add bulk delete button next to Add New
  (function(){
    const btn = document.createElement('button'); btn.className='btn ghost'; btn.type='button'; btn.textContent='Bulk Delete';
    els.addNewBtn.parentElement.appendChild(btn); btn.addEventListener('click', ()=> { if (state.locked) return toast('Unlock to edit'); bulkDelete(); });
  })();
  els.addExternalBtn.addEventListener('click', ()=> addExternalRow());
  els.addGalleryBtn?.addEventListener('click', ()=> addGalleryRow());
  els.search.addEventListener('input', debounce(renderList, 120));
  els.type.addEventListener('change', renderList);
  els.resetBtn.addEventListener('click', clearForm);
  els.deleteBtn.addEventListener('click', ()=> {
    if (state.locked) return toast('Unlock to edit');
    const id = els.f_id.value.trim(); if (!id) return;
    if (confirm(`Delete ${id}?`)) { deleteItem(id); clearForm(); renderList(); toast('Deleted'); }
  });
  els.form.addEventListener('submit', (e)=>{
    e.preventDefault(); if (state.locked) return toast('Unlock to edit');
  const it = readForm();
  if (!it.id) { toast('ID is required'); return; }
  if (!/^https?:\/\//.test(it.url)) { toast('URL must start with http(s)'); return; }
  try{ upsertItem(it); renderList(); toast('Saved'); } catch(err){ toast(err.message||'Save failed'); }
  });
  els.duplicateBtn?.addEventListener('click', ()=>{
    if (state.selIndex<0) return toast('Open an item first');
    const src = state.data.items[state.selIndex]; if (!src) return;
    const clone = JSON.parse(JSON.stringify(src));
    clone.id = `${clone.id}-copy`;
    clone.name = `${clone.name} (Copy)`;
    state.data.items.push(clone);
    state.data.updatedAt = new Date().toISOString().slice(0,10);
    autosave(); renderList(); toast('Duplicated');
  });
  els.useDraftToggle?.addEventListener('change', (e)=>{
    state.useDraft = !!e.target.checked;
    localStorage.setItem('cortensor_admin_use_draft', state.useDraft ? '1' : '0');
    toast(state.useDraft? 'Draft mode ON' : 'Draft mode OFF');
  });
  els.clearDraftBtn?.addEventListener('click', ()=>{
    localStorage.removeItem(state.persistKey); toast('Draft cleared');
  });

  // Image upload handlers
  if (els.f_image_file){
    els.f_image_file.addEventListener('change', async (e)=>{
      const file = e.target.files?.[0]; if (!file) return;
      // If embed checked, still allow data URL embedding client-side
      if (els.f_image_embed?.checked){
        const reader = new FileReader();
        reader.onload = () => {
          const dataUrl = String(reader.result||'');
          els.f_image.value = dataUrl;
          if (els.f_image_preview) els.f_image_preview.src = dataUrl;
          renderPreviewFromForm();
        };
        reader.readAsDataURL(file);
        return;
      }
      // Otherwise upload to server -> /database/images
      try{
        const fd = new FormData();
        fd.append('file', file);
        const pin = (window.APP_CONFIG?.ADMIN_PIN) || '';
        const res = await fetch('/api/upload', { method: 'POST', body: fd, headers: pin? { 'x-admin-pin': pin } : {} });
        const out = await res.json().catch(()=>null);
        if (!res.ok || !out?.ok) throw new Error(out?.error||'Upload failed');
        els.f_image.value = out.url || (`/database/images/${out.filename}`);
        if (els.f_image_preview) els.f_image_preview.src = els.f_image.value;
        toast('Uploaded');
        renderPreviewFromForm();
      }catch(err){
        console.error(err); toast('Upload failed');
      }
    });
  }

  // Mirror manual image path edits to preview
  els.f_image.addEventListener('input', ()=> {
    if (els.f_image_preview) els.f_image_preview.src = els.f_image.value || 'assets/placeholders/cover.svg';
    renderPreviewFromForm();
  });
  els.importInput.addEventListener('change', async (e)=>{
    const file = e.target.files?.[0]; if (!file) return;
    try{
      const text = await file.text();
      const data = JSON.parse(text);
      if (!Array.isArray(data.items)) throw new Error('Invalid JSON: missing items[]');
      state.data = data; renderList(); toast('Imported');
    }catch(err){ console.error(err); toast('Import failed'); }
    finally { e.target.value=''; }
  });

  function requireAuth(){
    // If already authenticated this session, skip
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
  setLock(false);
    loadInitial();
    ensureTabs();
    // Restore auto-slug preference
    const auto = document.getElementById('autoSlug');
    if (auto){
      const pref = localStorage.getItem('cortensor_admin_autoslug');
      if (pref!=null) auto.checked = pref === '1';
      auto.addEventListener('change', ()=> localStorage.setItem('cortensor_admin_autoslug', auto.checked?'1':'0'));
    }
    // Auto-slug ID from name when enabled
    els.f_name.addEventListener('input', ()=> {
      const auto = document.getElementById('autoSlug');
      if (auto?.checked){ els.f_id.value = slug(els.f_name.value.trim()); }
      renderPreviewFromForm();
    });
    // Fields affecting preview
    [els.f_type, els.f_image, els.f_highlight, els.f_desc, els.f_tags].forEach(el => el.addEventListener('input', debounce(renderPreviewFromForm, 120)));
    // Apply JSON via Ctrl/Cmd+S when JSON tab is visible
    document.addEventListener('keydown', (ev)=>{
      if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase()==='s'){
        if (els.tabJSON && els.tabJSON.style.display !== 'none'){
          ev.preventDefault(); applyJSONToForm(); renderPreviewFromForm(); toast('Applied JSON');
        }
      }
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    // Make reveal panels visible on this page (no homepage observer here)
    document.querySelectorAll('.reveal').forEach(el => el.classList.add('in'));
    if (requireAuth()) initAfterAuth();
  });
})();
