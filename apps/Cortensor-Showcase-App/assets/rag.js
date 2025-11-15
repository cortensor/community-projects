// Lightweight client-side retriever that loads the prebuilt index from /database
// and returns top-k chunks with simple BM25 scoring.

(async function(){
  const RAG = {};
  const basePath = (window.RAG_BASE || '').replace(/\/?$/, '') || '';
  async function loadJSON(p){
    const res = await fetch(p, { cache: 'no-store' });
    if(!res.ok) throw new Error('Load failed: '+p);
    return res.json();
  }
  RAG.load = async function(prefix='/database'){
    const pref = prefix.replace(/\/?$/, '');
    const [meta, texts, idx] = await Promise.all([
      loadJSON(`${pref}/docs_meta.json`),
      loadJSON(`${pref}/docs_text.json`),
      loadJSON(`${pref}/index.json`)
    ]);
    RAG.meta = meta; RAG.texts = texts; RAG.index = idx;
    return true;
  }
  function tokenize(s){ return (s||'').toLowerCase().split(/[^a-z0-9_]+/).filter(Boolean); }
  RAG.search = function(query, k=5){
    if(!RAG.index) return [];
    const { idf, postings, docLens, avgDocLen } = RAG.index;
    const toks = tokenize(query);
    const scores = new Map();
    const seen = new Set();
    const k1=1.6, b=0.75;
    for(const t of toks){
      const plist = postings[t]; if(!plist) continue;
      const idf_t = idf[t] ?? 0;
      for(const [docId, tf] of plist){
        const len = docLens[docId] || 1;
        const denom = tf + k1 * (1 - b + b * (len/avgDocLen));
        const s = idf_t * ((tf * (k1 + 1)) / denom);
        const prev = scores.get(docId) || 0;
        scores.set(docId, prev + s);
        if(scores.size > 5000) break;
      }
    }
    const ranked = [...scores.entries()].sort((a,b)=>b[1]-a[1]).slice(0,k).map(([id,score])=>({id,score,meta:RAG.meta[id],text:RAG.texts[id]}));
    return ranked;
  }
  window.CortensorRAG = RAG;
})();
