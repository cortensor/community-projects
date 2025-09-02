use crate::state::{AppState, ProviderRegistry, ProviderState};
use axum::{extract::State, http::StatusCode, Json};
use futures::stream::{FuturesUnordered, StreamExt};
use reqwest::Client;
use serde_json::{json, Value};
use std::{
    collections::HashMap,
    sync::Arc,
    time::{Duration, Instant},
};
use tokio::sync::RwLock;

// NEW: last-error classification
use crate::error_reason::{self, ErrorReason};

// ----------------------
// TTL Cache (simple, per-entry)
// ----------------------
#[derive(Clone, Default)]
pub struct TtlCache {
    inner: Arc<RwLock<HashMap<(String, String), (Instant, Value)>>>,
}

impl TtlCache {
    pub fn new() -> Self {
        Self { inner: Arc::new(RwLock::new(HashMap::new())) }
    }

    pub async fn get(&self, key: &(String, String)) -> Option<Value> {
        let mut guard = self.inner.write().await; // write to allow cleanup
        if let Some((exp, v)) = guard.get(key) {
            if *exp > Instant::now() {
                return Some(v.clone());
            } else {
                guard.remove(key);
            }
        }
        None
    }

    pub async fn insert_with_ttl(&self, key: (String, String), val: Value, ttl: Duration) {
        let exp = Instant::now() + ttl;
        self.inner.write().await.insert(key, (exp, val));
    }
}

// ----------------------
#[derive(Clone)]
pub struct RelayCtx {
    pub client: Client,
    pub cache: TtlCache,
}

impl RelayCtx {
    pub fn new(client: Client) -> Self {
        Self { client, cache: TtlCache::new() }
    }
}

#[derive(Clone)]
pub struct HttpState {
    pub app: Arc<AppState>,
    pub relay: RelayCtx,
}

// ----------------------
// Handlers
// ----------------------
pub async fn health() -> (StatusCode, Json<Value>) {
    (StatusCode::OK, Json(json!({"status":"ok"})))
}

pub async fn status(State(state): State<HttpState>) -> (StatusCode, Json<Value>) {
    let reg = state.app.registry.read().await;
    let mut list = Vec::new();
    for p in reg.primaries.iter().chain(reg.secondaries.iter()) {
        let obj = json!({
            "url": p.url,
            "healthy": p.is_healthy(),
            "latest_block": p.get_latest_block(),
            "behind": p.get_behind(),
            "latency_ms": p.get_latency(),
            "call_count": p.call_count.load(std::sync::atomic::Ordering::Relaxed),
            "errors": p.errors.load(std::sync::atomic::Ordering::Relaxed),
            "banned_until": p.breaker.lock().banned_until(),
            // NEW: persistently show the last error reason (not cleared on success)
            "last_error": error_reason::get_last_error(&p.url).as_str(),
        });
        list.push(obj);
    }
    (StatusCode::OK, Json(json!({ "rpcs": list })))
}

pub async fn relay(State(state): State<HttpState>, Json(body): Json<Value>) -> (StatusCode, Json<Value>) {
    // increment incoming call counter
    state.app.total_calls.fetch_add(1, std::sync::atomic::Ordering::Relaxed);

    let cfg_arc = state.app.cfg.clone();
    let reg_arc = state.app.registry.clone();

    let method = body.get("method").and_then(|m| m.as_str()).unwrap_or_default().to_string();
    let id_value = body.get("id").cloned().unwrap_or(Value::Number(0u64.into()));
    let mut params_value = body.get("params").cloned().unwrap_or(Value::Null);

    // Normalize "eth_getTransactionCount" -> pending
    if method == "eth_getTransactionCount" {
        if let Value::Array(ref mut arr) = params_value {
            if !arr.is_empty() {
                arr.truncate(2);
                if arr.len() == 1 { arr.push(Value::String("pending".into())); }
                else { arr[1] = Value::String("pending".into()); }
            }
        }
    }

    // TTL cache lookup
    let ttl_ms = {
        let cfg = cfg_arc.read().await;
        cfg.cache_ttl.get(&method).cloned().unwrap_or(0)
    };
    if ttl_ms > 0 {
        let key = (method.clone(), params_value.clone().to_string());
        if let Some(mut cached) = state.relay.cache.get(&key).await {
            // count cache hit
            state.app.cache_hits.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
            if let Some(obj) = cached.as_object_mut() {
                obj.insert("id".to_string(), id_value.clone());
            }
            return (StatusCode::OK, Json(cached));
        }
    }

    // Choose candidates
    let (cands, _lt, broadcast_methods, redundancy, tries, upstream_timeout_ms, breaker_cfg) = {
        let cfg = cfg_arc.read().await;
        let reg = reg_arc.read().await;

        let lt = cfg.relay.latency_threshold_ms;
        let methods = cfg.relay.broadcast_methods.clone();
        let redundancy = cfg.relay.broadcast_redundancy.max(1);
        let tries = cfg.relay.max_provider_tries.max(1);
        let upstream_ms = cfg.relay.upstream_timeout_ms.max(1000);
        let breaker_cfg = crate::circuit_breaker::BreakerConfig {
            ban_error_threshold: cfg.relay.ban_error_threshold,
            ban_seconds: cfg.relay.ban_seconds,
        };

        let healthy = healthy_candidates(&reg);
        let under = filter_latency(healthy, lt);
        (under, lt, methods, redundancy, tries, upstream_ms, breaker_cfg)
    };

    if cands.is_empty() {
        let resp = json!({"jsonrpc":"2.0","id": id_value,"error":{"code":-32000,"message":"No healthy RPCs available"}});
        return (StatusCode::INTERNAL_SERVER_ERROR, Json(resp));
    }

    let upstream_timeout = Duration::from_millis(upstream_timeout_ms);

    // Prepare payload and cache key
    let id_for_resp = id_value.clone();
    let payload = json!({
        "jsonrpc":"2.0",
        "id": id_value,
        "method": method,
        "params": params_value.clone()
    });
    let cache_key_opt = if ttl_ms > 0 {
        Some((payload.get("method").unwrap().as_str().unwrap_or_default().to_string(),
              payload.get("params").cloned().unwrap_or(Value::Null).to_string()))
    } else { None };

    // Broadcast path
    if broadcast_methods.iter().any(|m| m == payload.get("method").and_then(|x| x.as_str()).unwrap_or("")) {
        let uniq_sorted = unique_by_low_latency(cands);

        let mut chosen = Vec::new();
        for p in uniq_sorted {
            if chosen.len() >= redundancy { break; }
            if p.try_consume_token() { chosen.push(p); }
        }
        if chosen.is_empty() {
            let resp = json!({"jsonrpc":"2.0","id": id_for_resp,"error":{"code":-32005,"message":"Rate limited; try later"}});
            return (StatusCode::TOO_MANY_REQUESTS, Json(resp));
        }

        let client = state.relay.client.clone();
        let payload_arc = Arc::new(payload);
        let futs: FuturesUnordered<_> = chosen.into_iter().map(|p| {
            let client = client.clone();
            let url = p.url.clone();
            let payload = payload_arc.clone();
            // count attempt for this provider
            p.call_count.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
            async move {
                let res = tokio::time::timeout(upstream_timeout, client.post(url).json(&*payload).send()).await;
                (p, res)
            }
        }).collect();

        tokio::pin!(futs);
        let mut first_err: Option<String> = None;

        while let Some((prov, res)) = futs.next().await {
            match res {
                Ok(Ok(resp)) => match resp.json::<Value>().await {
                    Ok(v) => {
                        if v.get("error").is_none() {
                            // NOTE: do NOT clear last error on success; keep it sticky
                            prov.breaker_success();
                            if let Some(ref key) = cache_key_opt {
                                state.relay.cache.insert_with_ttl(key.clone(), v.clone(), Duration::from_millis(ttl_ms)).await;
                            }
                            return (StatusCode::OK, Json(v));
                        } else {
                            first_err.get_or_insert(format!("{}", v.get("error").unwrap_or(&Value::String("error".into()))));
                            prov.errors.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                            prov.breaker_failure(&breaker_cfg);
                            error_reason::set_last_error(&prov.url, ErrorReason::RpcError);
                        }
                    }
                    Err(e) => {
                        first_err.get_or_insert(format!("bad json: {}", e));
                        prov.errors.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        prov.breaker_failure(&breaker_cfg);
                        error_reason::set_last_error(&prov.url, ErrorReason::BadJson);
                    }
                },
                Ok(Err(_e)) => {
                    first_err.get_or_insert("upstream error".to_string());
                    prov.errors.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    prov.breaker_failure(&breaker_cfg);
                    error_reason::set_last_error(&prov.url, ErrorReason::HttpError);
                }
                Err(_) => {
                    first_err.get_or_insert("upstream timeout".to_string());
                    prov.errors.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    prov.breaker_failure(&breaker_cfg);
                    error_reason::set_last_error(&prov.url, ErrorReason::Timeout);
                }
            }
        }

        let resp = json!({"jsonrpc":"2.0","id": id_for_resp,"error":{"code":-32603,"message": format!("All broadcast attempts failed: {}", first_err.unwrap_or_else(|| "unknown".into()))}});
        return (StatusCode::BAD_GATEWAY, Json(resp));
    }

    // Non-broadcast path with failover
    let mut attempt = 0usize;
    let mut last_err = String::new();
    let mut rr_idx = state.app.rr_main.fetch_add(1, std::sync::atomic::Ordering::Relaxed) as usize;

    while attempt < tries as usize {
        let mut candidates = cands.clone();

        if !candidates.is_empty() {
            rr_idx %= candidates.len();
            candidates.rotate_left(rr_idx);
        }

        let prov = candidates.into_iter().find(|p| p.try_consume_token());
        let Some(prov) = prov else {
            let resp = json!({"jsonrpc":"2.0","id": id_for_resp,"error":{"code":-32005,"message":"Rate limited; try later"}});
            return (StatusCode::TOO_MANY_REQUESTS, Json(resp));
        };

        // count attempt for this provider
        prov.call_count.fetch_add(1, std::sync::atomic::Ordering::Relaxed);

        let url = prov.url.clone();
        let client = state.relay.client.clone();

        let res = tokio::time::timeout(upstream_timeout, client.post(url).json(&payload).send()).await;
        match res {
            Ok(Ok(resp)) => match resp.json::<Value>().await {
                Ok(v) => {
                    if v.get("error").is_none() {
                        // NOTE: sticky last error — do not clear on success
                        prov.breaker_success();
                        if let Some(ref key) = cache_key_opt {
                            state.relay.cache.insert_with_ttl(key.clone(), v.clone(), Duration::from_millis(ttl_ms)).await;
                        }
                        return (StatusCode::OK, Json(v));
                    } else {
                        last_err = format!("{}", v.get("error").unwrap_or(&Value::String("error".into())));
                        prov.errors.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        prov.breaker_failure(&breaker_cfg);
                        error_reason::set_last_error(&prov.url, ErrorReason::RpcError);
                    }
                }
                Err(e) => {
                    last_err = format!("bad json: {}", e);
                    prov.errors.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    prov.breaker_failure(&breaker_cfg);
                    error_reason::set_last_error(&prov.url, ErrorReason::BadJson);
                }
            },
            Ok(Err(_e)) => {
                last_err = "upstream error".to_string();
                prov.errors.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                prov.breaker_failure(&breaker_cfg);
                error_reason::set_last_error(&prov.url, ErrorReason::HttpError);
            }
            Err(_) => {
                last_err = "upstream timeout".to_string();
                prov.errors.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                prov.breaker_failure(&breaker_cfg);
                error_reason::set_last_error(&prov.url, ErrorReason::Timeout);
            }
        }

        attempt += 1;
        rr_idx = rr_idx.wrapping_add(1);
    }

    let resp = json!({"jsonrpc":"2.0","id": id_for_resp,"error":{"code":-32603,"message": format!("Upstream provider error after failover: {}", last_err)}});
    (StatusCode::BAD_GATEWAY, Json(resp))
}

// -------- helpers --------

fn healthy_candidates(reg: &ProviderRegistry) -> Vec<Arc<ProviderState>> {
    let now_healthy = |p: &Arc<ProviderState>| p.is_healthy() && !p.breaker_is_banned();

    let prim: Vec<_> = reg.primaries.iter().cloned().filter(now_healthy).collect();
    if !prim.is_empty() { return apply_weights(prim); }

    let sec: Vec<_> = reg.secondaries.iter().cloned().filter(now_healthy).collect();
    apply_weights(sec)
}

fn apply_weights(list: Vec<Arc<ProviderState>>) -> Vec<Arc<ProviderState>> {
    let mut out = Vec::new();
    for p in list {
        let w = p.get_weight();
        for _ in 0..w { out.push(p.clone()); }
    }
    out
}

fn filter_latency(list: Vec<Arc<ProviderState>>, threshold_ms: Option<u64>) -> Vec<Arc<ProviderState>> {
    if let Some(th) = threshold_ms {
        let under: Vec<_> = list.iter().cloned().filter(|p| p.get_latency() < th).collect();
        if !under.is_empty() { return under; }
        if let Some(min) = list.iter().map(|p| p.get_latency()).min() {
            return list.into_iter().filter(|p| p.get_latency() == min).collect();
        }
    }
    list
}

fn unique_by_low_latency(mut list: Vec<Arc<ProviderState>>) -> Vec<Arc<ProviderState>> {
    use std::collections::HashSet;
    list.sort_by_key(|p| p.get_latency());
    let mut seen = HashSet::new();
    let mut out = Vec::new();
    for p in list {
        if seen.insert(p.url.clone()) { out.push(p); }
    }
    out
}
