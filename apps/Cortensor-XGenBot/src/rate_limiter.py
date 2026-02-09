"""
Rate limiter for XGenBot.
Prevents abuse by limiting requests per user per time window.
"""
import os
import time
import logging
from typing import Dict, Tuple
from functools import wraps

logger = logging.getLogger(__name__)

# Load rate limit settings from environment (with defaults)
def _get_int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        return default

DEFAULT_REQUESTS_PER_MINUTE = _get_int_env('RATE_LIMIT_PER_MINUTE', 10)
DEFAULT_REQUESTS_PER_HOUR = _get_int_env('RATE_LIMIT_PER_HOUR', 60)
DEFAULT_GENERATION_COOLDOWN = _get_int_env('GENERATION_COOLDOWN', 5)


class RateLimiter:
    """
    Token bucket rate limiter with per-user tracking.
    """
    
    def __init__(
        self,
        requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE,
        requests_per_hour: int = DEFAULT_REQUESTS_PER_HOUR,
        generation_cooldown: int = DEFAULT_GENERATION_COOLDOWN
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.generation_cooldown = generation_cooldown
        
        # Track requests: {user_id: [(timestamp, action), ...]}
        self._requests: Dict[str, list] = {}
        # Track last generation time: {user_id: timestamp}
        self._last_generation: Dict[str, float] = {}
        # Cleanup old entries periodically
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes
    
    def _cleanup_old_entries(self):
        """Remove entries older than 1 hour"""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        self._last_cleanup = now
        cutoff = now - 3600  # 1 hour
        
        for uid in list(self._requests.keys()):
            self._requests[uid] = [
                (ts, action) for ts, action in self._requests[uid]
                if ts > cutoff
            ]
            if not self._requests[uid]:
                del self._requests[uid]
    
    def _get_request_counts(self, user_id: str) -> Tuple[int, int]:
        """Get request counts for last minute and last hour"""
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600
        
        requests = self._requests.get(user_id, [])
        minute_count = sum(1 for ts, _ in requests if ts > minute_ago)
        hour_count = sum(1 for ts, _ in requests if ts > hour_ago)
        
        return minute_count, hour_count
    
    def check_rate_limit(self, user_id: str, action: str = "request") -> Tuple[bool, str]:
        """
        Check if user is within rate limits.
        
        Returns:
            Tuple of (is_allowed, error_message)
        """
        self._cleanup_old_entries()
        
        minute_count, hour_count = self._get_request_counts(user_id)
        
        if minute_count >= self.requests_per_minute:
            wait_time = 60 - (time.time() - min(
                ts for ts, _ in self._requests.get(user_id, [(time.time(), "")])
                if ts > time.time() - 60
            ))
            return False, f"Rate limit exceeded. Please wait {int(wait_time)}s before trying again."
        
        if hour_count >= self.requests_per_hour:
            return False, "Hourly rate limit exceeded. Please try again later."
        
        return True, ""
    
    def check_generation_cooldown(self, user_id: str) -> Tuple[bool, str]:
        """
        Check if user can generate (cooldown between generations).
        
        Returns:
            Tuple of (is_allowed, error_message)
        """
        now = time.time()
        last_gen = self._last_generation.get(user_id, 0)
        
        if now - last_gen < self.generation_cooldown:
            wait_time = self.generation_cooldown - (now - last_gen)
            return False, f"Please wait {int(wait_time)}s before generating again."
        
        return True, ""
    
    def record_request(self, user_id: str, action: str = "request"):
        """Record a request from user"""
        now = time.time()
        if user_id not in self._requests:
            self._requests[user_id] = []
        self._requests[user_id].append((now, action))
    
    def record_generation(self, user_id: str):
        """Record a generation action from user"""
        self._last_generation[user_id] = time.time()
        self.record_request(user_id, "generation")
    
    def get_user_stats(self, user_id: str) -> Dict:
        """Get rate limit stats for a user"""
        minute_count, hour_count = self._get_request_counts(user_id)
        last_gen = self._last_generation.get(user_id, 0)
        cooldown_remaining = max(0, self.generation_cooldown - (time.time() - last_gen))
        
        return {
            "requests_last_minute": minute_count,
            "requests_last_hour": hour_count,
            "minute_limit": self.requests_per_minute,
            "hour_limit": self.requests_per_hour,
            "generation_cooldown_remaining": int(cooldown_remaining),
        }


# Global rate limiter instance
_rate_limiter: RateLimiter = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def rate_limit_check(user_id: str, is_generation: bool = False) -> Tuple[bool, str]:
    """
    Convenience function to check rate limits.
    
    Args:
        user_id: The user ID to check
        is_generation: If True, also check generation cooldown
    
    Returns:
        Tuple of (is_allowed, error_message)
    """
    limiter = get_rate_limiter()
    
    # Check general rate limit
    allowed, msg = limiter.check_rate_limit(user_id)
    if not allowed:
        return allowed, msg
    
    # Check generation cooldown if applicable
    if is_generation:
        allowed, msg = limiter.check_generation_cooldown(user_id)
        if not allowed:
            return allowed, msg
    
    return True, ""


def record_user_action(user_id: str, is_generation: bool = False):
    """Record a user action for rate limiting"""
    limiter = get_rate_limiter()
    if is_generation:
        limiter.record_generation(user_id)
    else:
        limiter.record_request(user_id)
