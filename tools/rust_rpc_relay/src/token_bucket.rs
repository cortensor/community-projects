use std::time::Instant;

/// Simple token bucket (tokens per second) with fractional tokens.
#[derive(Debug)]
pub struct TokenBucket {
    capacity: f64,
    tokens: f64,
    refill_per_sec: f64,
    last: Instant,
}

impl TokenBucket {
    pub fn new(max_tps: u32) -> Self {
        let cap = if max_tps == 0 { f64::INFINITY } else { max_tps as f64 };
        let rps = if max_tps == 0 { f64::INFINITY } else { max_tps as f64 };
        Self { capacity: cap, tokens: cap, refill_per_sec: rps, last: Instant::now() }
    }

    fn refill(&mut self) {
        if self.capacity.is_infinite() { return; }
        let now = Instant::now();
        let dt = now.duration_since(self.last).as_secs_f64();
        if dt > 0.0 {
            self.tokens = (self.tokens + dt * self.refill_per_sec).min(self.capacity);
            self.last = now;
        }
    }

    /// Attempt to take tokens. Returns true if successful.
    pub fn try_take(&mut self, n: f64) -> bool {
        if self.capacity.is_infinite() { return true; }
        self.refill();
        if self.tokens >= n {
            self.tokens -= n;
            true
        } else {
            false
        }
    }
}
