use std::time::{SystemTime, UNIX_EPOCH};

pub struct BreakerConfig {
    pub ban_error_threshold: u32,
    pub ban_seconds: u64,
}

#[derive(Debug)]
pub struct CircuitBreaker {
    fail_streak: u32,
    banned_until_epoch: u64, // seconds since epoch
}

impl Default for CircuitBreaker {
    fn default() -> Self {
        Self { fail_streak: 0, banned_until_epoch: 0 }
    }
}

impl CircuitBreaker {
    pub fn is_banned(&self) -> bool {
        let now = now_epoch();
        now < self.banned_until_epoch
    }

    pub fn on_success(&mut self) { self.fail_streak = 0; }

    pub fn on_failure(&mut self, cfg: &BreakerConfig) {
        self.fail_streak = self.fail_streak.saturating_add(1);
        if self.fail_streak >= cfg.ban_error_threshold {
            self.banned_until_epoch = now_epoch().saturating_add(cfg.ban_seconds);
            self.fail_streak = 0;
        }
    }

    pub fn banned_until(&self) -> u64 { self.banned_until_epoch }
}

fn now_epoch() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_secs()
}
