use crate::circuit_breaker::{BreakerConfig, CircuitBreaker};
use crate::config::{Config, Endpoint, RpcEndpoints};
use crate::token_bucket::TokenBucket;
use std::sync::{
    atomic::{AtomicBool, AtomicU32, AtomicU64, Ordering},
    Arc,
};
use tokio::sync::RwLock;

#[derive(Debug)]
pub struct ProviderState {
    pub url: String,
    pub weight: AtomicU32,
    pub max_tps: AtomicU32, // 0 => unlimited
    pub healthy: AtomicBool,
    pub latest_block: AtomicU64,
    pub behind: AtomicU64,
    pub latency_ms: AtomicU64,
    pub errors: AtomicU64,
    pub call_count: AtomicU64, // attempts
    pub bucket: parking_lot::Mutex<TokenBucket>,
    pub breaker: parking_lot::Mutex<CircuitBreaker>,
}

impl ProviderState {
    pub fn from_endpoint(ep: &Endpoint) -> Arc<Self> {
        let mtps = ep.max_tps.unwrap_or(0);
        Arc::new(Self {
            url: ep.url.clone(),
            weight: AtomicU32::new(ep.weight.max(1)),
            max_tps: AtomicU32::new(mtps),
            healthy: AtomicBool::new(true),
            latest_block: AtomicU64::new(0),
            behind: AtomicU64::new(0),
            latency_ms: AtomicU64::new(u64::MAX),
            errors: AtomicU64::new(0),
            call_count: AtomicU64::new(0),
            bucket: parking_lot::Mutex::new(TokenBucket::new(mtps)),
            breaker: parking_lot::Mutex::new(CircuitBreaker::default()),
        })
    }

    pub fn is_healthy(&self) -> bool {
        self.healthy.load(Ordering::Relaxed)
    }

    pub fn mark_healthy(&self, ok: bool) {
        self.healthy.store(ok, Ordering::Relaxed);
    }

    pub fn breaker_is_banned(&self) -> bool { self.breaker.lock().is_banned() }
    pub fn breaker_success(&self) { self.breaker.lock().on_success(); }
    pub fn breaker_failure(&self, cfg: &BreakerConfig) { self.breaker.lock().on_failure(cfg); }

    pub fn try_consume_token(&self) -> bool { self.bucket.lock().try_take(1.0) }

    pub fn set_latency(&self, ms: u64) { self.latency_ms.store(ms, Ordering::Relaxed) }
    pub fn get_latency(&self) -> u64 { self.latency_ms.load(Ordering::Relaxed) }

    pub fn set_latest_block(&self, b: u64) { self.latest_block.store(b, Ordering::Relaxed) }
    pub fn get_latest_block(&self) -> u64 { self.latest_block.load(Ordering::Relaxed) }

    pub fn set_behind(&self, d: u64) { self.behind.store(d, Ordering::Relaxed) }
    pub fn get_behind(&self) -> u64 { self.behind.load(Ordering::Relaxed) }

    pub fn get_weight(&self) -> u32 { self.weight.load(Ordering::Relaxed).max(1) }
}

#[derive(Default)]
pub struct ProviderRegistry {
    pub primaries: Vec<Arc<ProviderState>>,
    pub secondaries: Vec<Arc<ProviderState>>,
}

impl ProviderRegistry {
    pub fn all(&self) -> Vec<Arc<ProviderState>> {
        let mut v = Vec::with_capacity(self.primaries.len() + self.secondaries.len());
        v.extend(self.primaries.iter().cloned());
        v.extend(self.secondaries.iter().cloned());
        v
    }
}

pub struct AppState {
    pub cfg: Arc<RwLock<Config>>,
    pub registry: Arc<RwLock<ProviderRegistry>>,
    pub breaker_cfg: Arc<RwLock<BreakerConfig>>,
    pub rr_main: AtomicU64,

    // Global counters for the live dashboard
    pub total_calls: AtomicU64,   // incoming POST /
    pub cache_hits: AtomicU64,    // cache served
}

impl AppState {
    pub fn new(cfg: Config) -> Self {
        let breaker_cfg = BreakerConfig {
            ban_error_threshold: cfg.relay.ban_error_threshold,
            ban_seconds: cfg.relay.ban_seconds,
        };
        let registry = build_registry(&cfg.rpc_endpoints);
        Self {
            cfg: Arc::new(RwLock::new(cfg)),
            registry: Arc::new(RwLock::new(registry)),
            breaker_cfg: Arc::new(RwLock::new(breaker_cfg)),
            rr_main: AtomicU64::new(0),
            total_calls: AtomicU64::new(0),
            cache_hits: AtomicU64::new(0),
        }
    }
}

pub fn build_registry(eps: &RpcEndpoints) -> ProviderRegistry {
    ProviderRegistry {
        primaries: eps.primary.iter().map(ProviderState::from_endpoint).collect(),
        secondaries: eps.secondary.iter().map(ProviderState::from_endpoint).collect(),
    }
}

/// Reconcile existing registry with a new config
pub fn reconcile_registry(reg: &mut ProviderRegistry, new_eps: &RpcEndpoints) {
    use std::collections::HashMap;
    let mut existing: HashMap<String, Arc<ProviderState>> =
        reg.all().into_iter().map(|p| (p.url.clone(), p)).collect();

    let mut new_prim = Vec::new();
    for ep in &new_eps.primary {
        if let Some(p) = existing.remove(&ep.url) {
            p.weight.store(ep.weight.max(1), Ordering::Relaxed);
            let new_mtps = ep.max_tps.unwrap_or(0);
            let old_mtps = p.max_tps.load(Ordering::Relaxed);
            if new_mtps != old_mtps {
                p.max_tps.store(new_mtps, Ordering::Relaxed);
                *p.bucket.lock() = TokenBucket::new(new_mtps);
            }
            new_prim.push(p);
        } else {
            new_prim.push(ProviderState::from_endpoint(ep));
        }
    }

    let mut new_sec = Vec::new();
    for ep in &new_eps.secondary {
        if let Some(p) = existing.remove(&ep.url) {
            p.weight.store(ep.weight.max(1), Ordering::Relaxed);
            let new_mtps = ep.max_tps.unwrap_or(0);
            let old_mtps = p.max_tps.load(Ordering::Relaxed);
            if new_mtps != old_mtps {
                p.max_tps.store(new_mtps, Ordering::Relaxed);
                *p.bucket.lock() = TokenBucket::new(new_mtps);
            }
            new_sec.push(p);
        } else {
            new_sec.push(ProviderState::from_endpoint(ep));
        }
    }

    reg.primaries = new_prim;
    reg.secondaries = new_sec;
}
