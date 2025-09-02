use crate::config::Config;
use crate::state::{ProviderRegistry, ProviderState};
use reqwest::Client;
use serde_json::json;
use std::sync::Arc;
use tokio::sync::RwLock;
use tokio::time::{sleep, Duration};
use tracing::debug;

fn hex_to_u64(h: &str) -> Option<u64> {
    let s = h.trim_start_matches("0x");
    u64::from_str_radix(s, 16).ok()
}

pub async fn health_loop(cfg: Arc<RwLock<Config>>, registry: Arc<RwLock<ProviderRegistry>>, client: Client) {
    loop {
        let (interval_s, max_behind) = {
            let c = cfg.read().await;
            (
                c.health_monitor.monitor_interval_s,
                c.health_monitor.max_blocks_behind,
            )
        };

        let all = { registry.read().await.all() };
        if all.is_empty() {
            sleep(Duration::from_secs(interval_s.max(1))).await;
            continue;
        }

        // Probe all endpoints concurrently
        let mut handles = Vec::with_capacity(all.len());
        for p in all.iter() {
            let client = client.clone();
            let p = p.clone();
            handles.push(tokio::spawn(async move {
                let payload = json!({
                    "jsonrpc":"2.0",
                    "id":1,
                    "method":"eth_blockNumber",
                    "params":[]
                });
                let start = std::time::Instant::now();
                let res = client.post(&p.url).json(&payload).timeout(Duration::from_secs(3)).send().await;
                match res {
                    Ok(resp) => match resp.json::<serde_json::Value>().await {
                        Ok(v) => {
                            let latency_ms = start.elapsed().as_millis() as u64;
                            if let Some(hex) = v.get("result").and_then(|r| r.as_str()) {
                                if let Some(bn) = hex_to_u64(hex) {
                                    p.set_latest_block(bn);
                                    p.set_latency(latency_ms);
                                    p.mark_healthy(true);
                                    return Some((p, bn));
                                }
                            }
                            p.mark_healthy(false);
                            None
                        }
                        Err(_) => { p.mark_healthy(false); None }
                    },
                    Err(_) => { p.mark_healthy(false); None }
                }
            }));
        }

        let mut max_block = 0u64;
        let mut ok_states: Vec<(Arc<ProviderState>, u64)> = Vec::new();
        for h in handles {
            if let Ok(Some((p, bn))) = h.await {
                if bn > max_block { max_block = bn; }
                ok_states.push((p, bn));
            }
        }

        // Compute "behind" and mark over-threshold as unhealthy
        for (p, bn) in ok_states.into_iter() {
            let behind = max_block.saturating_sub(bn);
            p.set_behind(behind);
            if behind > max_behind {
                p.mark_healthy(false);
            }
        }

        debug!("health check done, max_block={}", max_block);
        sleep(Duration::from_secs(interval_s.max(1))).await;
    }
}
