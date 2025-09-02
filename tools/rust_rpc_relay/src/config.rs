use serde::{Deserialize, Serialize};
use std::{collections::HashMap, env, fs, path::PathBuf};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Config {
    pub network: String,
    pub server: ServerConfig,
    pub relay: RelayConfig,
    #[serde(default)]
    pub health_monitor: HealthMonitorConfig,
    #[serde(default)]
    pub cache_ttl: HashMap<String, u64>, // per-method TTL in milliseconds
    pub rpc_endpoints: RpcEndpoints,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ServerConfig {
    pub bind_addr: String, // e.g., "0.0.0.0"
    pub port: u16,         // e.g., 5588
    #[serde(default = "default_request_timeout_ms")]
    pub request_timeout_ms: u64,
}
fn default_request_timeout_ms() -> u64 { 30_000 }

#[derive(Clone, Debug, Serialize, Deserialize, Default)]
pub struct HealthMonitorConfig {
    #[serde(default = "default_max_blocks_behind")]
    pub max_blocks_behind: u64,
    #[serde(default = "default_monitor_interval_s")]
    pub monitor_interval_s: u64,
}
fn default_max_blocks_behind() -> u64 { 6 }
fn default_monitor_interval_s() -> u64 { 5 }

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct RelayConfig {
    #[serde(default)]
    pub latency_threshold_ms: Option<u64>,
    #[serde(default = "default_max_provider_tries")]
    pub max_provider_tries: u32,
    #[serde(default = "default_upstream_timeout_ms")]
    pub upstream_timeout_ms: u64,
    #[serde(default = "default_broadcast_methods")]
    pub broadcast_methods: Vec<String>,
    #[serde(default = "default_broadcast_redundancy")]
    pub broadcast_redundancy: usize,
    #[serde(default = "default_ban_error_threshold")]
    pub ban_error_threshold: u32,
    #[serde(default = "default_ban_seconds")]
    pub ban_seconds: u64,
}
fn default_max_provider_tries() -> u32 { 3 }
fn default_upstream_timeout_ms() -> u64 { 30_000 }
fn default_broadcast_methods() -> Vec<String> { vec!["eth_sendRawTransaction".to_string()] }
fn default_broadcast_redundancy() -> usize { 2 }
fn default_ban_error_threshold() -> u32 { 3 }
fn default_ban_seconds() -> u64 { 30 }

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct RpcEndpoints {
    #[serde(default)]
    pub primary: Vec<Endpoint>,
    #[serde(default)]
    pub secondary: Vec<Endpoint>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Endpoint {
    pub url: String,
    #[serde(default)]
    pub max_tps: Option<u32>, // None or 0 => unlimited
    #[serde(default = "default_weight")]
    pub weight: u32,
}
fn default_weight() -> u32 { 1 }

impl Config {
    pub fn load_from_path(path: &PathBuf) -> anyhow::Result<Self> {
        let content = fs::read_to_string(path)?;
        let mut cfg: Self = serde_yaml::from_str(&content)?;
        apply_env_overrides(&mut cfg);
        Ok(cfg)
    }
}

pub fn apply_env_overrides(cfg: &mut Config) {
    if let Ok(net) = env::var("RLY_NETWORK") { cfg.network = net; }
    if let Ok(addr) = env::var("RLY_HTTP_ADDR") { cfg.server.bind_addr = addr; }
    if let Ok(port) = env::var("RLY_HTTP_PORT") {
        if let Ok(p) = port.parse::<u16>() { cfg.server.port = p; }
    }
    if let Ok(n) = env::var("RLY_BROADCAST_REDUNDANCY") {
        if let Ok(nu) = n.parse::<usize>() { cfg.relay.broadcast_redundancy = nu.max(1); }
    }
    if let Ok(ms) = env::var("RLY_LATENCY_THRESHOLD_MS") {
        cfg.relay.latency_threshold_ms = ms.parse::<u64>().ok();
    }
    if let Ok(tries) = env::var("RLY_MAX_PROVIDER_TRIES") {
        if let Ok(t) = tries.parse::<u32>() { cfg.relay.max_provider_tries = t.max(1); }
    }
    if let Ok(ms) = env::var("RLY_UPSTREAM_TIMEOUT_MS") {
        if let Ok(v) = ms.parse::<u64>() { cfg.relay.upstream_timeout_ms = v.max(1000); }
    }
    if let Ok(sec) = env::var("RLY_BAN_SECONDS") {
        if let Ok(v) = sec.parse::<u64>() { cfg.relay.ban_seconds = v; }
    }
}
