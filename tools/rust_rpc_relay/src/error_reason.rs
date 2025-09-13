use once_cell::sync::Lazy;
use parking_lot::RwLock;
use std::collections::HashMap;

#[derive(Copy, Clone, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum ErrorReason {
    None = 0,
    RpcError = 1,
    BadJson = 2,
    HttpError = 3,
    Timeout = 4,
}

impl ErrorReason {
    pub fn as_str(&self) -> &'static str {
        match self {
            ErrorReason::None => "-",
            ErrorReason::RpcError => "rpc_error",
            ErrorReason::BadJson => "bad_json",
            ErrorReason::HttpError => "http_error",
            ErrorReason::Timeout => "timeout",
        }
    }
}

static LAST_ERR: Lazy<RwLock<HashMap<String, ErrorReason>>> =
    Lazy::new(|| RwLock::new(HashMap::new()));

pub fn set_last_error(url: &str, reason: ErrorReason) {
    let mut map = LAST_ERR.write();
    if reason == ErrorReason::None {
        // Keep a "None" entry for visibility (“-” in UI) rather than removing.
        map.insert(url.to_string(), reason);
    } else {
        map.insert(url.to_string(), reason);
    }
}

pub fn get_last_error(url: &str) -> ErrorReason {
    let map = LAST_ERR.read();
    map.get(url).copied().unwrap_or(ErrorReason::None)
}
