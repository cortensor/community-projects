mod config;
mod state;
mod token_bucket;
mod circuit_breaker;
mod health;
mod relay;
mod ui;
// NEW: declare the error_reason module so others can use crate::error_reason
mod error_reason;

use axum::{routing::get, Router};
use config::Config;
use notify::{Event, EventKind, RecommendedWatcher, RecursiveMode, Watcher};
use reqwest::Client;
use std::{env, net::SocketAddr, path::PathBuf, sync::Arc};
use tokio::net::TcpListener;
use tracing::{error, info};
use anyhow::Result;

use state::{AppState, reconcile_registry};
use relay::{HttpState, RelayCtx};
use health::health_loop;
use ui::run_terminal_dashboard;

static DEFAULT_CONFIG_PATH: &str = "config.yaml";

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(std::env::var("RUST_LOG").unwrap_or_else(|_| "info".to_string()))
        .with_target(true)
        .compact()
        .init();

    // Load config
    let cfg_path = env::var("RLY_CONFIG_PATH").unwrap_or_else(|_| DEFAULT_CONFIG_PATH.to_string());
    let cfg_path = PathBuf::from(cfg_path);
    let cfg = Config::load_from_path(&cfg_path)?;
    info!("loaded config for network {}", cfg.network);

    // State
    let app_state = Arc::new(AppState::new(cfg));
    let client = Client::builder()
        .pool_max_idle_per_host(32)
        .tcp_keepalive(Some(std::time::Duration::from_secs(30)))
        .build()?;

    let relay_ctx = RelayCtx::new(client.clone());
    let http_state = HttpState { app: app_state.clone(), relay: relay_ctx };

    // Health monitor
    {
        let cfg_arc = app_state.cfg.clone();
        let reg_arc = app_state.registry.clone();
        let client = client.clone();
        tokio::spawn(async move {
            health_loop(cfg_arc, reg_arc, client).await;
        });
    }

    // Config watcher
    {
        let app_state = app_state.clone();
        let cfg_path = cfg_path.clone();
        tokio::spawn(async move {
            if let Err(e) = watch_config_and_apply(cfg_path, app_state).await {
                error!("config watcher error: {:?}", e);
            }
        });
    }

    // Terminal dashboard (enabled by default; set RLY_TUI=0 to disable)
    let enable_tui = env::var("RLY_TUI").ok().map(|v| v != "0").unwrap_or(true);
    if enable_tui {
        let app = app_state.clone();
        tokio::spawn(async move { run_terminal_dashboard(app).await; });
    }

    // HTTP server
    let (addr, router) = {
        let cfg = app_state.cfg.read().await;
        let addr: SocketAddr = format!("{}:{}", cfg.server.bind_addr, cfg.server.port).parse()?;
        let router = Router::new()
            .route("/", get(relay::health).post(relay::relay))
            .route("/status", get(relay::status))
            .with_state(http_state);
        (addr, router)
    };

    info!("listening on http://{}", addr);
    let listener = TcpListener::bind(addr).await?;
    axum::serve(listener, router).await?;
    Ok(())
}

async fn watch_config_and_apply(cfg_path: PathBuf, app: Arc<AppState>) -> Result<()> {
    use tokio::sync::mpsc;
    let (tx, mut rx) = mpsc::channel::<()>(8);

    let mut watcher: RecommendedWatcher = Watcher::new(
        move |res: Result<Event, notify::Error>| {
            if let Ok(ev) = res {
                match ev.kind {
                    EventKind::Modify(_) | EventKind::Create(_) | EventKind::Remove(_) => {
                        let _ = tx.try_send(());
                    }
                    _ => {}
                }
            }
        },
        notify::Config::default(),
    )?;

    let watch_dir = cfg_path.parent().unwrap_or_else(|| std::path::Path::new("."));
    watcher.watch(watch_dir, RecursiveMode::NonRecursive)?;

    loop {
        rx.recv().await;
        match Config::load_from_path(&cfg_path) {
            Ok(new_cfg) => {
                // swap config
                {
                    let mut cfg_guard = app.cfg.write().await;
                    *cfg_guard = new_cfg.clone();
                }
                // update breaker cfg
                {
                    let mut bcfg = app.breaker_cfg.write().await;
                    bcfg.ban_error_threshold = new_cfg.relay.ban_error_threshold;
                    bcfg.ban_seconds = new_cfg.relay.ban_seconds;
                }
                // reconcile providers
                {
                    let mut reg = app.registry.write().await;
                    reconcile_registry(&mut reg, &new_cfg.rpc_endpoints);
                }
                info!("applied new config (hot reload)");
            }
            Err(e) => {
                error!("failed to reload config: {:?}", e);
            }
        }
    }
}
