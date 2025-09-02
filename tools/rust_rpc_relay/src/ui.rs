use crate::state::{AppState, ProviderState};
use crate::error_reason;
use std::{collections::HashMap, sync::Arc, time::{Duration, Instant}};
use tokio::time::sleep;

/// Run the live terminal dashboard.
/// - Default: ASCII status labels to avoid column drift.
/// - Set RLY_TUI_EMOJI=1 to use emoji status (may misalign on some terminals).
/// - Tick interval: RLY_TUI_INTERVAL_MS (default 2000 ms).
pub async fn run_terminal_dashboard(app: Arc<AppState>) {
    // Per-provider rolling counters to compute TPS/TPM
    let mut last_counts: HashMap<String, (u64, Instant)> = HashMap::new();
    let mut last_total_calls: (u64, Instant) = (0, Instant::now());

    let interval = std::env::var("RLY_TUI_INTERVAL_MS")
        .ok()
        .and_then(|s| s.parse::<u64>().ok())
        .unwrap_or(2000);

    let use_emoji = std::env::var("RLY_TUI_EMOJI").ok().map(|v| v == "1" || v.eq_ignore_ascii_case("true")).unwrap_or(false);

    loop {
        let start = Instant::now();

        // Snapshot providers
        let reg = app.registry.read().await;
        let providers: Vec<Arc<ProviderState>> =
            reg.primaries.iter().chain(reg.secondaries.iter()).cloned().collect();
        drop(reg);

        // Build rows
        let mut rows = Vec::new();
        let mut total_tps = 0.0f64;
        let mut total_tpm = 0.0f64;

        for p in providers.iter() {
            // TPS/TPM from call_count delta
            let now = Instant::now();
            let calls_now = p.call_count.load(std::sync::atomic::Ordering::Relaxed);
            let (tps, tpm) = match last_counts.get(&p.url) {
                Some((last, last_t)) => {
                    let dt = now.duration_since(*last_t).as_secs_f64().max(0.001);
                    let dc = calls_now.saturating_sub(*last) as f64;
                    (dc / dt, dc * (60.0 / dt))
                }
                None => (0.0, 0.0),
            };
            last_counts.insert(p.url.clone(), (calls_now, now));
            total_tps += tps;
            total_tpm += tpm;

            let status = if p.breaker.lock().is_banned() {
                if use_emoji { "⛔ BANNED".to_string() } else { "BANNED".to_string() }
            } else if p.is_healthy() {
                if use_emoji { "🟢 OK".to_string() } else { "OK".to_string() }
            } else {
                if use_emoji { "🔴 DOWN".to_string() } else { "DOWN".to_string() }
            };

            let url = truncate(&p.url, 45);
            let weight = p.get_weight();
            let block = p.get_latest_block();
            let behind = p.get_behind();
            let latency_ms = p.get_latency();
            let err = p.errors.load(std::sync::atomic::Ordering::Relaxed);
            let calls = calls_now;
            let last_err = error_reason::get_last_error(&p.url).as_str().to_string();

            rows.push(Row {
                url,
                status,
                weight,
                block,
                behind,
                latency_ms: latency_ms as f64,
                tps,
                tpm,
                err,
                last_err,
                calls,
            });
        }

        // Header line with totals + cache
        let total_calls = app.total_calls.load(std::sync::atomic::Ordering::Relaxed);
        let cache_hits = app.cache_hits.load(std::sync::atomic::Ordering::Relaxed);
        let hit_rate = if total_calls == 0 { 0.0 } else { (cache_hits as f64) * 100.0 / (total_calls as f64) };

        // Optional global TPS/TPM from total calls delta (incoming)
        let now = Instant::now();
        let (glob_tps, glob_tpm) = {
            let dt = now.duration_since(last_total_calls.1).as_secs_f64().max(0.001);
            let dc = total_calls.saturating_sub(last_total_calls.0) as f64;
            last_total_calls = (total_calls, now);
            (dc / dt, dc * (60.0 / dt))
        };

        print_frame(rows, total_calls, cache_hits, hit_rate, total_tps, total_tpm, glob_tps, glob_tpm);

        // Pace the loop
        let elapsed = start.elapsed();
        if elapsed < Duration::from_millis(interval) {
            sleep(Duration::from_millis(interval) - elapsed).await;
        }
    }
}

struct Row {
    url: String,
    status: String,
    weight: u32,
    block: u64,
    behind: u64,
    latency_ms: f64,
    tps: f64,
    tpm: f64,
    err: u64,
    last_err: String, // NEW
    calls: u64,
}

// --- formatting helpers ---

fn truncate(s: &str, width: usize) -> String {
    if s.chars().count() <= width { return s.to_string(); }
    let mut out = String::with_capacity(width);
    for (i, ch) in s.chars().enumerate() {
        if i + 1 >= width { break; }
        out.push(ch);
    }
    out.push('…');
    out
}

fn pad(s: &str, width: usize) -> String {
    let len = s.chars().count();
    if len >= width { s.to_string() } else { format!("{}{}", s, " ".repeat(width - len)) }
}

fn make_summary_line(total_width: usize, content: &str) -> String {
    let inner = total_width.saturating_sub(2);
    let clipped = {
        let mut out = String::new();
        for ch in content.chars() {
            if out.chars().count() >= inner { break; }
            out.push(ch);
        }
        out
    };
    format!("│{}│", pad(&clipped, inner))
}

fn print_frame(rows: Vec<Row>, total_calls: u64, cache_hits: u64, hit_rate: f64,
               total_tps: f64, total_tpm: f64, glob_tps: f64, glob_tpm: f64) {
    // Column widths
    let w_url   = 45usize;
    let w_stat  = 8usize;   // "OK/DOWN/." fits
    let w_wt    = 8usize;   // (weight)
    let w_block = 13usize;  // latest susize;   // behind
    let w_bhin  = 7usize;   // behind
    let w_lat   = 12usize;  // latency (ms)
    let w_tps   = 8usize;
    let w_tpm   = 8usize;
    let w_err   = 8usize;
    let w_lerr  = 12usize;  // NEW: last error reason (rpc_error/timeout/...)
    let w_calls = 12usize;

    let total_w =
        1 + w_url + 1 + w_stat + 1 + w_wt + 1 + w_block + 1 + w_bhin + 1 + w_lat + 1 + w_tps + 1 + w_tpm + 1 + w_err + 1 + w_lerr + 1 + w_calls + 1;

    // Summary header (exact widths, ASCII only to avoid drift)
    println!("╭{}╮", "─".repeat(total_w.saturating_sub(2)));
    let line1 = format!("  Total calls: {} | Cache hits: {} | Hit rate: {:.1}%",
                        total_calls, cache_hits, hit_rate);
    println!("{}", make_summary_line(total_w, &line1));
    let line2 = format!("  Ingress: {:.1} TPS | {:.0} TPM   Providers (sum): {:.1} TPS | {:.0} TPM",
                        glob_tps, glob_tpm, total_tps, total_tpm);
    println!("{}", make_summary_line(total_w, &line2));
    println!("╰{}╯", "─".repeat(total_w.saturating_sub(2)));

    // Table header
    println!(
        "┏{}┳{}┳{}┳{}┳{}┳{}┳{}┳{}┳{}┳{}┳{}┓",
        pad(" URL", w_url),
        pad(" Status", w_stat),
        pad(" Weight", w_wt),
        pad(" Block", w_block),
        pad(" >>>", w_bhin),
        pad(" Latency ms", w_lat),
        pad(" TPS", w_tps),
        pad(" TPM", w_tpm),
        pad(" Err", w_err),
        pad(" Last_err", w_lerr),
       pad(" Calls", w_calls),
   );

    println!(
       "┡{}┿{}┿{}┿{}┿{}┿{}┿{}┿{}┿{}┿{}┿{}┩",
        "━".repeat(w_url),
        "━".repeat(w_stat),
        "━".repeat(w_wt),
        "━".repeat(w_block),
        "━".repeat(w_bhin),
        "━".repeat(w_lat),
        "━".repeat(w_tps),
        "━".repeat(w_tpm),
        "━".repeat(w_err),
        "━".repeat(w_lerr),
        "━".repeat(w_calls),
    );

    for r in rows {
        let lat_display = if r.latency_ms > 1.0e9 { "∞".to_string() } else { format!("{:.1}", r.latency_ms) };
        let block_display = if r.block == 0 { "–".to_string() } else { format!("{}", r.block) };
        println!(
            "│{}│{}│{}│{}│{}│{}│{}│{}│{}│{}│{}│",
            pad(&r.url, w_url),
            pad(&r.status, w_stat),
            pad(&format!("{}", r.weight), w_wt),
            pad(&block_display, w_block),
            pad(&format!("{}", r.behind), w_bhin),
            pad(&lat_display, w_lat),
            pad(&format!("{:.1}", r.tps), w_tps),
            pad(&format!("{:.0}", r.tpm), w_tpm),
            pad(&format!("{}", r.err), w_err),
            pad(&r.last_err, w_lerr),
            pad(&format!("{}", r.calls), w_calls),
        );
    }

    println!("└{}┘", "─".repeat(total_w.saturating_sub(2)));
}
