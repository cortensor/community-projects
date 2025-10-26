(() => {
  // Simple in-memory cache so if user returns from detail/admin we skip refetch/parsing
  let dataCache = null;
  const state = {
    items: [],
    filtered: [],
    tags: [],
    tagCounts: {},
    activeTags: new Set(),
    query: '',
    type: '',
    sort: 'featured',
  view: 'grid', // locked to grid (list removed)
    preview: false,
    onlyFavs: false,
  };

  const els = {
    preloader: document.getElementById('preloader'),
    search: document.getElementById('searchInput'),
    type: document.getElementById('typeFilter'),
    sort: document.getElementById('sortSelect'),
    tagBar: document.getElementById('tagBar'),
    grid: document.getElementById('cardsGrid'),
    empty: document.getElementById('emptyState'),
    featuredPanel: document.getElementById('featuredSection'),
    featuredGrid: document.getElementById('featuredGrid'),
    catalogTitle: document.getElementById('catalogTitle'),
    catalogSubtitle: document.getElementById('catalogSubtitle'),
    sidebar: document.getElementById('catalogSidebar'),
  // view toggle elements removed
  };

  const storageKey = (id) => `cortensor_clicks_${id}`;
  const getLocalClicks = (id) => {
    try { return JSON.parse(localStorage.getItem(storageKey(id)) || '0') || 0; } catch { return 0; }
  };
  const addLocalClick = (id) => {
    const n = getLocalClicks(id) + 1;
    localStorage.setItem(storageKey(id), JSON.stringify(n));
  };

  const debounce = (fn, t = 200) => { let to; return (...a) => { clearTimeout(to); to = setTimeout(() => fn(...a), t); }; };

  function computeScores(items) {
    return items.map(it => {
      const baseClicks = Number(it.clicks || 0);
      const local = getLocalClicks(it.id);
      return {
        ...it,
        localClicks: local,
        scoreFeatured: baseClicks + local * 3,
        scorePopular: baseClicks + local,
      };
    });
  }

  function computeBadges(it){
    const now = Date.now();
    const created = new Date(it.createdAt||0).getTime();
    const updated = new Date(it.updatedAt||it.createdAt||0).getTime();
    const isNew = created && (now - created) <= 7*24*3600*1000;
    const isUpdated = updated>created && (now - updated) <= 3*24*3600*1000;
    return { isNew, isUpdated };
  }

  function applyFilters() {
    const q = state.query.trim().toLowerCase();
    const tags = state.activeTags;
    let res = state.items.filter(it => {
      if (state.type && it.type !== state.type) return false;
      if (tags.size && !it.tags?.some(t => tags.has(t))) return false;
      if (!q) return true;
      return it.__hay?.includes(q);
    });
    if (state.onlyFavs){
      const favSet = loadFavSet();
      res = res.filter(it => favSet.has(it.id));
    }

    const scored = computeScores(res);
    switch (state.sort) {
      case 'popular':
        scored.sort((a,b) => b.scorePopular - a.scorePopular); break;
      case 'alpha':
        scored.sort((a,b) => a.name.localeCompare(b.name)); break;
      case 'newest':
        scored.sort((a,b) => new Date(b.createdAt) - new Date(a.createdAt)); break;
      case 'recent':
        scored.sort((a,b) => new Date(b.updatedAt || b.createdAt || 0) - new Date(a.updatedAt || a.createdAt || 0)); break;
      case 'featured':
      default:
        scored.sort((a,b) => b.scoreFeatured - a.scoreFeatured); break;
    }
    state.filtered = scored;
    renderGrid();
    renderFeatured();
    syncURL();
  }

  function createTagPill(tag, active=false) {
    const s = document.createElement('button');
    s.className = `tag${active? ' active': ''}`;
    const count = state.tagCounts[tag] || 0;
    s.innerHTML = `#${tag} <span class="count">${count}</span>`;
    s.setAttribute('data-tag', tag);
    s.setAttribute('role', 'switch');
    s.setAttribute('aria-checked', active? 'true':'false');
    s.addEventListener('click', () => {
      if (state.activeTags.has(tag)) state.activeTags.delete(tag); else state.activeTags.add(tag);
      [...els.tagBar.querySelectorAll('.tag')].forEach(t => {
        const on = state.activeTags.has(t.dataset.tag);
        t.classList.toggle('active', on); t.setAttribute('aria-checked', on? 'true':'false');
      });
      applyFilters();
    });
    return s;
  }

  function renderTagsBar() {
    if (!els.tagBar) return;
    els.tagBar.innerHTML = '';
    const tags = state.tags.slice(0, 30);
    if (!tags.length) {
      const note = document.createElement('p');
      note.className = 'muted sidebar-empty';
      note.textContent = 'Tags will appear here once items include them.';
      els.tagBar.appendChild(note);
      return;
    }
    tags.forEach(t => els.tagBar.appendChild(createTagPill(t, state.activeTags.has(t))));
  }

  function tryLabelFor(it){
    if (it.type === 'bot') return 'Open Bot';
    if (it.type === 'package') return 'Open Package';
    if (it.type === 'resource') return 'Open Link';
    return 'Try Now';
  }

  function buildCard(it, index, opts = {}){
    const options = opts || {};
    const favSet = options.favSet || loadFavSet();
    const featured = Boolean(options.featured);
    const card = document.createElement('article');
    card.className = `card reveal${featured ? ' featured-card' : ''}`;
    const detailURL = `detail.html?id=${encodeURIComponent(it.id)}${state.preview ? '&preview=1' : ''}`;
    const fetchPriority = index <= 8 ? 'high' : 'low';
    const imageSrc = (typeof it.image === 'string' && it.image) ? it.image : 'assets/placeholders/cover.svg';
    const lowSrc = imageSrc.startsWith('data:') ? imageSrc : `${imageSrc}${imageSrc.includes('?') ? '&' : '?'}w=24&auto=compress&preview=1`;
    const favOn = favSet.has(it.id);
    const nameMarked = highlightQuery(it.name || '', state.query);
    const highlightMarked = highlightQuery(it.highlight || '', state.query);
    const { isNew, isUpdated } = computeBadges(it);
    const recBadge = isNew ? '<span class="badge fresh">NEW</span>' : (isUpdated ? '<span class="badge updated">UPDATED</span>' : '');
    const typeRaw = (it.type || 'app').toString();
    const typeLabel = typeRaw.charAt(0).toUpperCase() + typeRaw.slice(1);
    const featuredBadge = featured ? '<span class="badge badge-featured">Featured</span>' : '';
    card.innerHTML = `<div class="thumb">
        <img data-full="${imageSrc}" src="${lowSrc}" alt="${it.name || 'Catalog item'} preview" loading="lazy" decoding="async" fetchpriority="${fetchPriority}" class="blur-up" />
        <span class="badge badge-type">${typeLabel}</span>
        ${featuredBadge}
        ${recBadge}
        <button class="fav-toggle ${favOn ? 'active' : ''}" data-fav="${it.id}" title="Favorite">${favOn ? '★' : '☆'}</button>
      </div>
      <div class="card-body">
        <h3>${nameMarked}</h3>
        <p class="highlight">${highlightMarked}</p>
        <div class="tag-list">${(it.tags || []).slice(0,4).map(t=>`<span class=\"tag small\">#${t}</span>`).join('')}</div>
        <div class="card-actions">
          <a class="btn primary" href="${it.url}" target="_blank" rel="noopener" data-try="${it.id}">${tryLabelFor(it)}</a>
          <a class="btn ghost" data-detail="${detailURL}">Details</a>
          <button class="btn ghost" type="button" data-share="${it.id}">Share</button>
          <button class="btn ghost hidden" type="button" data-edit="${it.id}">Edit</button>
        </div>
        ${state.preview ? '<span class="preview-badge">DRAFT</span>' : ''}
      </div>`;
    card.addEventListener('pointerenter', () => schedulePrefetch(detailURL));
    return card;
  }

  function renderGrid(){
    const list = state.filtered;
    els.grid.innerHTML = '';
    updateCatalogMeta();
    if (!list.length) {
      els.empty.classList.remove('hidden');
      return;
    }
    els.empty.classList.add('hidden');

    let index = 0;
    const PAGE = 36;
    const sentinel = document.createElement('div');
    sentinel.id = 'scrollSentinel';
    sentinel.style.height = '1px';
    const favSet = loadFavSet();

    const renderChunk = () => {
      const frag = document.createDocumentFragment();
      let count = 0;
      while (index < list.length && count < PAGE) {
        const card = buildCard(list[index], index, { favSet });
        frag.appendChild(card);
        index++;
        count++;
      }
      els.grid.appendChild(frag);
      attachCardEvents(els.grid);
      upgradeBlurImages();
      els.grid.appendChild(sentinel);
      if (index >= list.length) {
        sentinel.remove();
        setupReveals();
      }
    };

    renderChunk();
    if ('IntersectionObserver' in window) {
      const io = new IntersectionObserver((entries) => {
        if (entries.some(e => e.isIntersecting)) {
          io.unobserve(sentinel);
          renderChunk();
          if (document.body.contains(sentinel)) io.observe(sentinel);
        }
      }, { rootMargin: '600px' });
      io.observe(sentinel);
    } else {
      const btn = document.createElement('button');
      btn.textContent = 'Load More';
      btn.className = 'btn ghost';
      btn.style.margin = '30px auto';
      btn.addEventListener('click', () => renderChunk());
      els.grid.appendChild(btn);
    }
  }

  function renderFeatured(){
    if (!els.featuredPanel || !els.featuredGrid) return;
    const hasFilters = Boolean(state.query || state.activeTags.size || state.type || state.onlyFavs);
    if (hasFilters) {
      els.featuredPanel.classList.add('hidden');
      els.featuredGrid.innerHTML = '';
      return;
    }
    const picks = computeScores(state.items)
      .sort((a,b) => b.scoreFeatured - a.scoreFeatured)
      .slice(0, 6);
    if (!picks.length) {
      els.featuredPanel.classList.add('hidden');
      els.featuredGrid.innerHTML = '';
      return;
    }
    els.featuredPanel.classList.remove('hidden');
    els.featuredGrid.innerHTML = '';
    const favSet = loadFavSet();
    const frag = document.createDocumentFragment();
    picks.forEach((it, idx) => {
      const card = buildCard(it, idx, { favSet, featured: true });
      frag.appendChild(card);
    });
    els.featuredGrid.appendChild(frag);
    attachCardEvents(els.featuredGrid);
    upgradeBlurImages();
    setupReveals();
  }

  function updateCatalogMeta(){
    if (!els.catalogTitle || !els.catalogSubtitle) return;
    const count = state.filtered.length;
    const countText = `${count} ${count === 1 ? 'item' : 'items'}`;
    const filters = [];
    if (state.onlyFavs) filters.push('favorites');
    if (state.type) {
      const typeNames = { app: 'web apps', bot: 'bots', package: 'packages', resource: 'resources' };
      filters.push(typeNames[state.type] || state.type);
    }
    if (state.activeTags.size) filters.push([...state.activeTags].map(t => `#${t}`).join(', '));
    if (state.query) filters.push(`matching "${state.query}"`);
    const filterText = filters.length ? `Filtered by ${filters.join(' · ')}` : 'All categories';
    const sortLabels = {
      featured: 'Featured order',
      popular: 'Most popular',
      alpha: 'Alphabetical',
      newest: 'Newest first',
      recent: 'Recently updated',
    };
    const sortKey = state.sort === 'trending' ? 'featured' : state.sort;
    const sortText = sortLabels[sortKey] || 'Featured order';
    els.catalogTitle.textContent = filters.length ? 'Filtered Results' : 'All Catalog Items';
    els.catalogSubtitle.textContent = `${countText} — ${filterText}. Sorted by ${sortText}.`;
  }

  function fallbackCopy(text){
    const ta = document.createElement('textarea');
    ta.value = text; document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); showToast('Link copied'); } catch {}
    ta.remove();
  }

  function copyToClipboard(text){
    if(navigator.clipboard?.writeText){ navigator.clipboard.writeText(text).then(()=> showToast('Copied')).catch(()=> fallbackCopy(text)); }
    else fallbackCopy(text);
  }

  function showToast(msg){
    let t = document.querySelector('.toast');
    if (!t) {
      t = document.createElement('div');
      t.className = 'toast';
      document.body.appendChild(t);
    }
    t.textContent = msg;
    t.classList.add('in');
    clearTimeout(t._to);
    t._to = setTimeout(()=> t.classList.remove('in'), 1600);
  }

  function setupReveals(){
    const obs = new IntersectionObserver((entries, ob) => {
      entries.forEach(e => { if (e.isIntersecting){ e.target.classList.add('in'); ob.unobserve(e.target); } });
    }, { threshold: 0.06 });
    document.querySelectorAll('.reveal').forEach(el => obs.observe(el));
  }

  async function init(){
    try {
      readURL();
      detectPreviewMode();
      const data = await loadData();
      state.items = data.items || [];
      state.items.forEach(it => { it.__hay = `${it.name||''} ${it.highlight||''} ${it.description||''} ${(it.tags||[]).join(' ')}`.toLowerCase(); });
      const tset = new Set([...(data.tags||[])]);
      const counts = {};
      state.items.forEach(i => (i.tags||[]).forEach(t => { tset.add(t); counts[t] = (counts[t]||0)+1; }));
      state.tagCounts = counts;
      state.tags = [...tset].sort((a,b)=> (counts[b]||0)-(counts[a]||0) || a.localeCompare(b));
      renderTagsBar();
      injectFavoritesToggle();
      applyFilters();
      injectPreviewUI();
    } catch(err){
      console.error('Failed to load data.json', err);
      els.grid.innerHTML = '<div class="muted">Failed to load data. Please refresh.</div>';
    } finally { setTimeout(()=> els.preloader?.classList.add('hidden'), 350); }
  }

  els.search?.addEventListener('input', debounce(e => { state.query = e.target.value; applyFilters(); }, 120));
  els.type?.addEventListener('change', e => { state.type = e.target.value; applyFilters(); });
  els.sort?.addEventListener('change', e => { state.sort = e.target.value; applyFilters(); });
  // view toggle removed

  document.addEventListener('DOMContentLoaded', init);

  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'A' || e.key === 'a')) {
      e.preventDefault();
      location.href = 'admin.html';
    }
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'E' || e.key === 'e')) {
      document.querySelectorAll('[data-edit]').forEach(b => b.classList.toggle('hidden'));
      showToast('Edit toggles on this page');
    }
  });

  function updateViewButtons(){} // noop

  function syncURL(){
    const params = new URLSearchParams();
    if (state.query) params.set('q', state.query);
    if (state.type) params.set('type', state.type);
    if (state.sort && state.sort!=='featured') params.set('sort', state.sort);
  // view param omitted (locked grid)
    if (state.activeTags.size) params.set('tags', [...state.activeTags].join(','));
    const qs = params.toString();
    const base = location.pathname;
    history.replaceState(null, '', qs? `${base}?${qs}` : base);
  }

  function readURL(){
    const p = new URLSearchParams(location.search);
    state.query = p.get('q')||'';
    state.type = p.get('type')||'';
    const sortParam = p.get('sort');
    if (sortParam === 'trending') state.sort = 'featured';
    else state.sort = sortParam || 'featured';
    if (!['featured','popular','alpha','newest','recent'].includes(state.sort)) state.sort = 'featured';
    state.view = 'grid';
    const t = (p.get('tags')||'').split(',').map(s=>s.trim()).filter(Boolean);
    state.activeTags = new Set(t);
    if (els.search) els.search.value = state.query;
    if (els.type) els.type.value = state.type;
    if (els.sort) els.sort.value = state.sort;
  }

  function detectPreviewMode(){
    const p = new URLSearchParams(location.search);
    const qPrev = p.get('preview');
    const stored = localStorage.getItem('cortensor_preview_mode') === '1';
    const authed = sessionStorage.getItem('cortensor_admin_auth') === '1';
    if (qPrev === '1') {
      if (authed){
        state.preview = true; localStorage.setItem('cortensor_preview_mode','1');
      } else {
        p.delete('preview'); history.replaceState(null,'', p.toString()? `${location.pathname}?${p}`: location.pathname);
        state.preview = false; localStorage.removeItem('cortensor_preview_mode');
      }
    } else if (qPrev === '0') { state.preview = false; localStorage.removeItem('cortensor_preview_mode'); }
    else {
      state.preview = stored && authed; if (!authed) localStorage.removeItem('cortensor_preview_mode');
    }
  }

  async function loadData(){
    if (dataCache) return dataCache;
    if (state.preview){
      try { const raw = localStorage.getItem('cortensor_admin_data'); if (raw){ const draft = JSON.parse(raw); draft.__preview = true; dataCache = draft; return draft; } } catch(e){ console.warn('Draft parse failed', e); }
    }
    try {
      const cached = localStorage.getItem('cortensor_data_cache');
      if (cached){ const parsed = JSON.parse(cached); dataCache = parsed; backgroundRefresh(); return parsed; }
    } catch {}
    const res = await fetch('assets/data.json', {cache:'no-cache'}); dataCache = await res.json();
    try { localStorage.setItem('cortensor_data_cache', JSON.stringify(dataCache)); } catch {}
    return dataCache;
  }
  async function backgroundRefresh(){
    try {
      const res = await fetch('assets/data.json', {cache:'no-cache'});
      if (!res.ok) return; const fresh = await res.json();
      if (JSON.stringify(fresh.updatedAt) !== JSON.stringify(dataCache?.updatedAt)){
        dataCache = fresh;
        try { localStorage.setItem('cortensor_data_cache', JSON.stringify(fresh)); } catch {}
      }
    } catch {}
  }

  const prefetchSet = new Set();
  function schedulePrefetch(url){
    if (prefetchSet.has(url)) return; prefetchSet.add(url);
    const link = document.createElement('link'); link.rel='prefetch'; link.href=url; document.head.appendChild(link);
  }

  function showShareMenu(btn, id){
    const existing = btn.parentElement.querySelector('.share-menu');
    if(existing){ existing.remove(); return; }
    const it = state.items.find(i=> i.id===id) || state.filtered.find(i=> i.id===id);
    const menu = document.createElement('div'); menu.className='share-menu';
    const base = location.origin + location.pathname.replace(/[^/]*$/, '');
    const url = `${base}detail.html?id=${encodeURIComponent(id)}`;
    const md = `[${it?.name||'Item'}](${url})`;
    const actions = [
      ['Copy Link', () => copyToClipboard(url)],
      ['Copy Markdown', () => copyToClipboard(md)],
      ['Copy Title', () => copyToClipboard(it?.name||'')],
      ['Tweet', () => window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent((it?.name||'')+' '+url)}`,'_blank')]
    ];
    actions.forEach(([label, fn])=>{ const b=document.createElement('button'); b.textContent=label; b.addEventListener('click', e=>{ e.stopPropagation(); fn(); menu.remove(); }); menu.appendChild(b); });
    document.addEventListener('click', function handler(ev){ if(!menu.contains(ev.target) && ev.target!==btn){ menu.remove(); document.removeEventListener('click', handler, true);} }, true);
    btn.parentElement.style.position='relative';
    btn.parentElement.appendChild(menu);
  }

  function ensurePreviewModal(){
    if (document.querySelector('.preview-modal')) return;
    const wrap = document.createElement('div');
    wrap.className='preview-modal';
    wrap.innerHTML='<div class="preview-backdrop"></div><div class="preview-card"><button class="preview-close" aria-label="Close">✕</button><div class="preview-body"></div></div>';
    document.body.appendChild(wrap);
    wrap.querySelector('.preview-backdrop').addEventListener('click', closePreviewModal);
    wrap.querySelector('.preview-close').addEventListener('click', closePreviewModal);
    document.addEventListener('keydown', e=>{ if(e.key==='Escape') closePreviewModal(); });
  }
  function openPreviewModal(it){
    ensurePreviewModal();
    const modal = document.querySelector('.preview-modal');
    const body = modal.querySelector('.preview-body');
    const cover = it.image? `<img class="preview-thumb" src="${it.image}" alt="${(it.name||'').replace(/"/g,'&quot;')}">` : '';
    const tags = (it.tags||[]).map(t=> '#'+t).join(' ');
    const links = (it.external||[]).map(ex=> `<a target="_blank" rel="noopener" href="${ex.url}">${ex.label||ex.url}</a>`).join(' ');
    body.innerHTML = `${cover}<h2>${it.name||''}</h2><p>${it.highlight||''}</p><div class="prev-tags">${tags}</div><div class="prev-links">${links}</div><div class="prev-actions"><button class="btn primary" data-open-detail="${it.id}">Open Detail</button></div>`;
    body.querySelector('[data-open-detail]')?.addEventListener('click', ()=> { location.href = `detail.html?id=${encodeURIComponent(it.id)}${state.preview?'&preview=1':''}`; });
    modal.classList.add('show');
    setTimeout(()=> modal.querySelector('.preview-close')?.focus(), 30);
  }
  function closePreviewModal(){ document.querySelector('.preview-modal')?.classList.remove('show'); }

  function attachCardEvents(scope){
    scope.querySelectorAll('[data-try]:not([data-bound])').forEach(btn => {
      btn.setAttribute('data-bound','1');
      btn.addEventListener('click', () => addLocalClick(btn.getAttribute('data-try')));
    });
    scope.querySelectorAll('[data-share]:not([data-bound])').forEach(btn => {
      btn.setAttribute('data-bound','1');
      btn.addEventListener('click', (e) => { e.stopPropagation(); const id = btn.getAttribute('data-share'); showShareMenu(btn, id); });
    });
  // preview removed
    scope.querySelectorAll('[data-edit]:not([data-bound])').forEach(btn => {
      btn.setAttribute('data-bound','1');
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-edit');
        location.href = `admin.html?id=${encodeURIComponent(id)}`;
      });
    });
    scope.querySelectorAll('[data-detail]:not([data-bound])').forEach(a => {
      a.setAttribute('data-bound','1');
      a.addEventListener('click', (e)=> { e.preventDefault(); location.href = a.getAttribute('data-detail'); });
    });
    scope.querySelectorAll('[data-fav]:not([data-fav-bound])').forEach(btn => {
      btn.setAttribute('data-fav-bound','1');
      btn.addEventListener('click', (e)=> { e.stopPropagation(); const id = btn.getAttribute('data-fav'); toggleFavorite(id, btn); });
    });
  }

  function upgradeBlurImages(){
    const imgs = [...document.querySelectorAll('img.blur-up:not(.ready)')];
    const io = new IntersectionObserver((entries)=>{
      entries.forEach(en => {
        if (en.isIntersecting){
          const img = en.target;
          const full = img.getAttribute('data-full');
          if (full){
            const hi = new Image();
            hi.onload = () => { img.src = full; img.classList.add('ready'); };
            hi.src = full;
          } else {
            img.classList.add('ready');
          }
          io.unobserve(img);
        }
      });
    }, { rootMargin: '120px' });
    imgs.forEach(im => io.observe(im));
  }

  function injectPreviewUI(){
    const authed = sessionStorage.getItem('cortensor_admin_auth') === '1';
    if (!authed) return;
    if (!state.preview && !localStorage.getItem('cortensor_admin_data')) return;
    let banner = document.getElementById('previewBanner');
    if (!banner){ banner = document.createElement('div'); banner.id='previewBanner'; banner.className='preview-banner'; document.body.appendChild(banner); }
    banner.innerHTML = state.preview ? `<strong>Preview Mode:</strong> Showing local draft. <button type="button" class="btn ghost small" id="exitPreviewBtn">Exit Preview</button>` : `<strong>Draft Available:</strong> Unsaved local changes. <button type="button" class="btn ghost small" id="enterPreviewBtn">Preview Draft</button>`;
    banner.querySelector('#exitPreviewBtn')?.addEventListener('click', ()=> { localStorage.removeItem('cortensor_preview_mode'); const p=new URLSearchParams(location.search); p.set('preview','0'); location.search=p.toString(); });
    banner.querySelector('#enterPreviewBtn')?.addEventListener('click', ()=> { localStorage.setItem('cortensor_preview_mode','1'); const p=new URLSearchParams(location.search); p.set('preview','1'); location.search=p.toString(); });
  }

  // Favorites helpers & UI
  function favStorageKey(){ return 'cortensor_favorites_v1'; }
  function loadFavSet(){ try { return new Set(JSON.parse(localStorage.getItem(favStorageKey())||'[]')); } catch { return new Set(); } }
  function saveFavSet(set){ try { localStorage.setItem(favStorageKey(), JSON.stringify([...set])); } catch {} }
  function toggleFavorite(id, btn){ const set = loadFavSet(); if (set.has(id)) set.delete(id); else set.add(id); saveFavSet(set); if (btn){ btn.classList.toggle('active', set.has(id)); btn.textContent = set.has(id)? '★':'☆'; } }
  function injectFavoritesToggle(){ if (document.getElementById('favToggleBtn')) return; const filters = document.querySelector('.filters'); if (!filters) return; const b=document.createElement('button'); b.id='favToggleBtn'; b.type='button'; b.className='btn ghost'; b.textContent='Favorites'; b.setAttribute('aria-pressed','false'); b.addEventListener('click', ()=> { state.onlyFavs = !state.onlyFavs; b.setAttribute('aria-pressed', state.onlyFavs?'true':'false'); b.classList.toggle('primary', state.onlyFavs); applyFilters(); }); filters.appendChild(b); }

  function highlightQuery(text,q){ if (!q) return text; try { const safe=q.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'); return text.replace(new RegExp('('+safe+')','ig'), '<mark>$1</mark>'); } catch { return text; } }
})();
