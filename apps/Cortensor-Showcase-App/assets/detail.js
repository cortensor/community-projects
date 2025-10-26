(() => {
  const els = {
    preloader: document.getElementById('preloader'),
    title: document.getElementById('title'),
    subtitle: document.getElementById('subtitle'),
    typeBadge: document.getElementById('typeBadge'),
    tags: document.getElementById('tags'),
    name: document.getElementById('name'),
    highlight: document.getElementById('highlight'),
    desc: document.getElementById('description'),
    cover: document.getElementById('coverImage'),
    try1: document.getElementById('tryBtn'),
    try2: document.getElementById('tryBtn2'),
  externalWrap: document.getElementById('externalLinks'),
  copyLink: document.getElementById('copyLinkBtn'),
  stats: document.getElementById('stats'),
  galleryStrip: document.getElementById('galleryStrip'),
    imageMeta: document.getElementById('imageMeta'),
    lightbox: document.getElementById('lightbox'),
    lbImg: document.getElementById('lbImage'),
    lbPrev: document.getElementById('lbPrev'),
    lbNext: document.getElementById('lbNext'),
    lbCounter: document.getElementById('lbCounter'),
    lbClose: document.getElementById('lbClose'),
  lbReset: document.getElementById('lbReset'),
  lbHint: document.getElementById('lbHint'),
  };
  let gallerySources = [];
  let galleryIndex = 0;
  let zoom = { active:false, scale:1, x:0, y:0, originX:0, originY:0 };
  let touchState = { x:0, y:0, t:0 };

  const params = new URLSearchParams(location.search);
  const id = params.get('id');
  const previewParam = params.get('preview') === '1';
  const authed = sessionStorage.getItem('cortensor_admin_auth') === '1';
  const storedPreview = localStorage.getItem('cortensor_preview_mode') === '1';
  let preview = false;
  if (previewParam) {
    if (authed){ preview = true; localStorage.setItem('cortensor_preview_mode','1'); }
    else {
      // remove unauthorized param
      params.delete('preview'); const p = new URLSearchParams(params); history.replaceState(null,'', p.toString()? `${location.pathname}?${p}`: location.pathname);
    }
  } else if (storedPreview && authed){ preview = true; }
  else { localStorage.removeItem('cortensor_preview_mode'); }

  const storageKey = (id) => `cortensor_clicks_${id}`;
  const addLocalClick = (id) => {
    try {
      const n = JSON.parse(localStorage.getItem(storageKey(id)) || '0') + 1;
      localStorage.setItem(storageKey(id), JSON.stringify(n));
    } catch {}
  };

  const tryLabelFor = (it) => {
    if (it.type === 'bot') return 'Open Bot';
    if (it.type === 'package') return 'Open Package';
    if (it.type === 'resource') return 'Open Link';
    return 'Try App / Demo';
  };

  async function init(){
    if (!id) {
      els.name.textContent = 'Not found';
      els.highlight.textContent = '';
      els.desc.textContent = 'Missing id parameter.';
      els.preloader.classList.add('hidden');
      return;
    }
    try{
      let data;
      if (preview){
        try { const raw = localStorage.getItem('cortensor_admin_data'); if (raw) data = JSON.parse(raw); } catch{}
      }
      if (!data){
        const res = await fetch('assets/data.json', {cache:'no-cache'});
        data = await res.json();
      }
  const items = data.items||[];
  const it = items.find(i => i.id === id);
      if (!it) throw new Error('Item not found');
      document.title = `${it.name} — Cortensor Showcase`;
      els.title.textContent = 'App Detail';
      els.subtitle.textContent = 'Powered by Cortensor';
      els.typeBadge.textContent = it.type.charAt(0).toUpperCase() + it.type.slice(1);
      els.name.textContent = it.name;
      els.highlight.textContent = it.highlight || '';
  // Preserve line breaks; already styled with white-space:pre-line
  els.desc.textContent = it.description || '—';
      els.cover.src = it.image || 'assets/placeholders/cover.svg';
      els.cover.alt = `${it.name} preview`;
      if (els.galleryStrip){
        const arr = (it.gallery||[]).filter(Boolean);
        if (arr.length){
          els.galleryStrip.innerHTML = arr.map((g,i)=>`<img data-idx="${i+1}" src="${g}" alt="${it.name} screenshot ${i+1}" loading="lazy" decoding="async" />`).join('');
          gallerySources = [it.image, ...arr];
          els.galleryStrip.querySelectorAll('img').forEach((imgEl, i) => {
            imgEl.addEventListener('click', ()=> openLightbox(i+1));
          });
          els.cover.addEventListener('click', ()=> openLightbox(0));
          if (els.imageMeta){
            els.imageMeta.innerHTML = `<span>${gallerySources.length} images</span><span>Click to enlarge</span>`;
          }
        } else {
          els.galleryStrip.style.display='none';
          if (els.imageMeta) els.imageMeta.style.display='none';
          gallerySources = [it.image];
          els.cover.addEventListener('click', ()=> openLightbox(0));
          if (els.imageMeta){
            els.imageMeta.innerHTML = `<span>1 image</span><span>Click to enlarge</span>`;
          }
        }
      }
      els.try1.href = it.url;
      els.try2.href = it.url;
      els.try1.textContent = tryLabelFor(it);
      els.try2.textContent = tryLabelFor(it);
  els.externalWrap.innerHTML = (it.external||[]).map(e => `<a class="btn ghost" href="${e.url}" target="_blank" rel="noopener">${e.label||'External'}</a>`).join('');
      els.tags.innerHTML = (it.tags||[]).map(t=>`<span class="tag small">#${t}</span>`).join('');
      // track clicks
      els.try1.addEventListener('click', ()=> addLocalClick(it.id));
      els.try2.addEventListener('click', ()=> addLocalClick(it.id));
      // Copy share link
      if (els.copyLink){
        els.copyLink.addEventListener('click', async ()=>{
          const url = `${location.origin}${location.pathname.replace(/[^/]*$/, '')}detail.html?id=${encodeURIComponent(it.id)}`;
          try{ await navigator.clipboard.writeText(url); }catch{}
          const o = document.createElement('div'); o.className='toast'; o.textContent='Link copied'; document.body.appendChild(o); o.classList.add('in'); setTimeout(()=>{o.classList.remove('in'); o.remove();}, 1200);
        });
      }
      // Simple stats (local clicks + seed)
      if (els.stats){
        let local = 0; try { local = JSON.parse(localStorage.getItem(storageKey(it.id))||'0'); } catch {}
        els.stats.textContent = `Total opens (local + seed): ${local + (Number(it.clicks||0))}`;
      }
      // reveal animations
      setTimeout(()=> document.querySelectorAll('.reveal').forEach(el => el.classList.add('in')), 60);
      // Related items (overlap >=2 tags or same type if insufficient)
      try {
        const baseTags = new Set(it.tags||[]);
        const scored = items.filter(o => o.id!==it.id).map(o => {
          const otags = new Set(o.tags||[]); let overlap = 0; baseTags.forEach(t=> { if (otags.has(t)) overlap++; });
          return { o, overlap };
        }).filter(r => r.overlap>0);
        scored.sort((a,b)=> b.overlap - a.overlap || new Date(b.o.createdAt||0) - new Date(a.o.createdAt||0));
        let picks = scored.filter(s=> s.overlap>=2).slice(0,4).map(s=>s.o);
        if (picks.length < 4){
          const fill = items.filter(o => o.id!==it.id && o.type===it.type && !picks.includes(o));
          for (const f of fill){ if (picks.length>=4) break; picks.push(f); }
        }
        if (picks.length){
          let host = document.getElementById('relatedWrap');
          if (!host){
            host = document.createElement('section'); host.id='relatedWrap'; host.className='related-wrap container';
            host.innerHTML = `<h3 style="margin:0 0 4px">Related</h3><div class="related-grid" id="relatedGrid"></div>`;
            const mainSec = document.querySelector('main .section.container');
            mainSec?.appendChild(host);
          }
          const grid = host.querySelector('#relatedGrid');
          grid.innerHTML = picks.map(p=> `<div class="mini-card"><h4>${p.name}</h4><p class="muted" style="margin:0;font-size:.7rem">${(p.highlight||'').slice(0,60)}</p><a href="detail.html?id=${encodeURIComponent(p.id)}" class="btn ghost small" style="padding:4px 8px;margin-top:auto">Open</a></div>`).join('');
        }
      } catch{}
  if (preview && authed){
        let banner = document.getElementById('previewBanner');
        if (!banner){ banner=document.createElement('div'); banner.id='previewBanner'; banner.className='preview-banner'; document.body.appendChild(banner); }
        banner.innerHTML = `<strong>Preview Mode:</strong> Showing draft. <button type="button" class="btn ghost small" id="exitPreviewBtn">Exit Preview</button>`;
        banner.querySelector('#exitPreviewBtn').addEventListener('click', ()=> { localStorage.removeItem('cortensor_preview_mode'); const p=new URLSearchParams(location.search); p.set('preview','0'); location.search=p.toString(); });
      }
      // Secret shortcut: Ctrl+Shift+E to edit this item in Admin
      document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'E' || e.key === 'e')) {
          e.preventDefault();
          location.href = `admin.html?id=${encodeURIComponent(it.id)}`;
        }
      });
    }catch(err){
      console.error(err);
      // Fallback to 404 page
      location.replace('404.html');
    }finally{
      setTimeout(()=> els.preloader?.classList.add('hidden'), 300);
    }
  }

  document.addEventListener('DOMContentLoaded', init);

  function openLightbox(idx){
    if (!gallerySources.length) return;
    galleryIndex = Math.max(0, Math.min(idx, gallerySources.length-1));
    els.lbImg.src = gallerySources[galleryIndex];
    els.lbCounter.textContent = `${galleryIndex+1} / ${gallerySources.length}`;
    els.lightbox.classList.add('show');
    els.lightbox.setAttribute('aria-hidden','false');
  resetZoom();
  preloadNeighbors();
  }
  function closeLightbox(){
    els.lightbox.classList.remove('show');
    els.lightbox.setAttribute('aria-hidden','true');
  }
  function nav(delta){
    if (!gallerySources.length) return;
    galleryIndex = (galleryIndex + delta + gallerySources.length) % gallerySources.length;
    els.lbImg.src = gallerySources[galleryIndex];
    els.lbCounter.textContent = `${galleryIndex+1} / ${gallerySources.length}`;
  resetZoom();
  preloadNeighbors();
  }
  els.lbPrev?.addEventListener('click', ()=> nav(-1));
  els.lbNext?.addEventListener('click', ()=> nav(1));
  els.lbClose?.addEventListener('click', closeLightbox);
  els.lightbox?.addEventListener('click', (e)=> { if (e.target.dataset.close!==undefined || e.target===els.lightbox) closeLightbox(); });
  document.addEventListener('keydown', (e)=> {
    if (!els.lightbox.classList.contains('show')) return;
    if (e.key==='Escape') closeLightbox();
    if (e.key==='ArrowRight') nav(1);
    if (e.key==='ArrowLeft') nav(-1);
  });

  // Zoom / pan logic
  els.lbImg.classList.add('zoomable');
  function resetZoom(){
    zoom.active=false; zoom.scale=1; zoom.x=0; zoom.y=0; applyZoom();
  }
  function applyZoom(){
    const rect = els.lbImg.getBoundingClientRect();
    // clamp when scaled
    if (zoom.scale>1){
      const maxX = (rect.width * (zoom.scale-1)) / 2 + 40;
      const maxY = (rect.height * (zoom.scale-1)) / 2 + 40;
      zoom.x = Math.max(-maxX, Math.min(maxX, zoom.x));
      zoom.y = Math.max(-maxY, Math.min(maxY, zoom.y));
    } else { zoom.x=0; zoom.y=0; }
    els.lbImg.style.transform = `translate(${zoom.x}px, ${zoom.y}px) scale(${zoom.scale})`;
  }
  function toggleZoom(ev){
    if (zoom.scale === 1){
      const rect = els.lbImg.getBoundingClientRect();
      const cx = (ev.clientX|| (ev.touches?.[0]?.clientX)|| (rect.left+rect.width/2)) - rect.left;
      const cy = (ev.clientY|| (ev.touches?.[0]?.clientY)|| (rect.top+rect.height/2)) - rect.top;
      zoom.scale = 2.2; zoom.active=true;
      zoom.x = -(cx - rect.width/2);
      zoom.y = -(cy - rect.height/2);
    } else { resetZoom(); }
    applyZoom();
  }
  els.lbImg.addEventListener('click', (e)=> {
    if (zoom.scale > 1) return; // single click to zoom in; second click resets
    toggleZoom(e);
  });
  els.lbImg.addEventListener('dblclick', (e)=> { toggleZoom(e); });
  let isPanning=false, panStart={x:0,y:0};
  els.lbImg.addEventListener('mousedown', (e)=>{ if (zoom.scale<=1) return; isPanning=true; panStart.x=e.clientX-zoom.x; panStart.y=e.clientY-zoom.y; });
  window.addEventListener('mousemove', (e)=>{ if(!isPanning) return; zoom.x = e.clientX - panStart.x; zoom.y = e.clientY - panStart.y; applyZoom(); });
  window.addEventListener('mouseup', ()=> { isPanning=false; });
  // Wheel zoom
  els.lbImg.addEventListener('wheel', (e)=>{
    if (!els.lightbox.classList.contains('show')) return;
    e.preventDefault();
    const delta = e.deltaY < 0 ? 0.2 : -0.2;
    const ns = Math.min(4, Math.max(1, zoom.scale + delta));
    if (ns === zoom.scale) return;
    // Zoom towards pointer
    const rect = els.lbImg.getBoundingClientRect();
    const px = e.clientX - rect.left; const py = e.clientY - rect.top;
    const ratio = ns / zoom.scale;
    zoom.x = (zoom.x - px) * ratio + px;
    zoom.y = (zoom.y - py) * ratio + py;
    zoom.scale = ns; zoom.active = zoom.scale>1; applyZoom();
  }, { passive:false });

  // Swipe navigation (touch)
  els.lbImg.addEventListener('touchstart', (e)=>{
    if (e.touches.length===1){ touchState.x = e.touches[0].clientX; touchState.y = e.touches[0].clientY; touchState.t=Date.now(); }
    if (e.touches.length===2){
      // pinch start
      pinch.startDist = dist(e.touches[0], e.touches[1]);
      pinch.startScale = zoom.scale; pinch.active=true;
    }
  }, {passive:true});
  els.lbImg.addEventListener('touchmove', (e)=>{
    if (pinch.active && e.touches.length===2){
      const d = dist(e.touches[0], e.touches[1]);
      const factor = d / (pinch.startDist||d);
      zoom.scale = Math.min(4, Math.max(1, pinch.startScale * factor));
      applyZoom();
      return;
    }
    if (zoom.scale>1 && e.touches.length===1){
      const dx = e.touches[0].clientX - touchState.x;
      const dy = e.touches[0].clientY - touchState.y;
      zoom.x += dx; zoom.y += dy; touchState.x = e.touches[0].clientX; touchState.y = e.touches[0].clientY; applyZoom();
    }
  }, {passive:true});
  els.lbImg.addEventListener('touchend', (e)=>{
    if (pinch.active && e.touches.length<2){ pinch.active=false; }
    if (zoom.scale>1) return; // when zoomed treat as pan only
    const dt = Date.now()-touchState.t;
    const dx = (e.changedTouches?.[0]?.clientX||0) - touchState.x;
    if (dt < 450 && Math.abs(dx) > 60){ nav(dx<0?1:-1); }
  });
  const pinch = { active:false, startDist:0, startScale:1 };
  function dist(a,b){ const dx=a.clientX-b.clientX, dy=a.clientY-b.clientY; return Math.hypot(dx,dy); }
  els.lbReset?.addEventListener('click', ()=> resetZoom());

  // Extended keyboard controls
  document.addEventListener('keydown', (e)=>{
    if (!els.lightbox.classList.contains('show')) return;
    if (e.key==='+'){ zoom.scale = Math.min(4, zoom.scale+0.2); applyZoom(); }
    if (e.key==='-'){ zoom.scale = Math.max(1, zoom.scale-0.2); applyZoom(); }
    if (e.key==='Home'){ nav(-(gallerySources.length)); }
    if (e.key==='End'){ nav(gallerySources.length); }
  });

  // Focus trap inside lightbox
  function trapFocus(){
    const focusables = els.lightbox.querySelectorAll('button, [tabindex]:not([tabindex="-1"])');
    const first = focusables[0]; const last = focusables[focusables.length-1];
    function cycle(e){
      if (e.key==='Tab'){
        if (e.shiftKey && document.activeElement===first){ e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement===last){ e.preventDefault(); first.focus(); }
      }
    }
    els.lightbox.addEventListener('keydown', cycle);
    setTimeout(()=> first?.focus(), 50);
  }
  // Show hint once per session
  if (!sessionStorage.getItem('lb_hint_shown')){
    setTimeout(()=> { els.lbHint?.classList.add('in'); setTimeout(()=> { els.lbHint?.classList.remove('in'); sessionStorage.setItem('lb_hint_shown','1'); }, 4000); }, 600);
  }
  // Preload all images after first open
  let preloadedAll = false;
  const origOpen = openLightbox;
  openLightbox = function(i){ origOpen(i); trapFocus(); if (!preloadedAll){
    preloadedAll = true; gallerySources.forEach(src => { const im = new Image(); im.src=src; }); }
  };

  function preloadNeighbors(){
    const next = gallerySources[(galleryIndex+1)%gallerySources.length];
    const prev = gallerySources[(galleryIndex-1+gallerySources.length)%gallerySources.length];
    [next, prev].forEach(src => { if (!src) return; const img = new Image(); img.src = src; });
  }
})();
