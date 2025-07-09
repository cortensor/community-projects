# File: error_scan.py
"""
error_scan.py

Provides functions to scan in-memory log feeds for various error conditions:
- saw_traceback: detects Python traceback patterns in logs
- saw_ping_fail: detects repeated "Pinging network..." failures
- saw_node_pool_stale: detects stale node pool conditions in logs
"""

TRACEBACK_PATTERN = "Traceback (most recent call last):"
PING_FAIL_PATTERN = "Pinging network..."


def saw_traceback(lines: list[str]) -> bool:
    """
    Returns True if any line contains a Python traceback indicator.
    """
    return any(TRACEBACK_PATTERN in ln for ln in lines)


def saw_ping_fail(lines: list[str], threshold: int = 2, window: int = 52) -> bool:
    """
    Returns True if the ping failure pattern appears at least `threshold` times
    in the last `window` lines of logs.
    """
    recent = lines[-window:]
    count = sum(1 for ln in recent if ln.strip().startswith(PING_FAIL_PATTERN))
    return count >= threshold


def saw_node_pool_stale(lines: list[str]) -> bool:
    """
    Returns True if either the ephemeral or reserved node pool is stale.
    Detects lines like:
      "* Node Pool Ephemeral Node Stale:  True"
      "* Node Pool Reserved Node Stale:  True"
    """
    for ln in lines:
        if 'Node Pool Ephemeral Node Stale:' in ln or 'Node Pool Reserved Node Stale:' in ln:
            # Split on colon and check the boolean value
            parts = ln.split(':', 1)
            if len(parts) == 2 and parts[1].strip().lower().startswith('true'):
                return True
    return False