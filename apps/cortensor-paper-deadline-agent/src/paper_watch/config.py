"""Provider presets + the two environment quirks found by running.

Presets (switching needs no application-code change):
- ``openai-compatible`` (default): Pollinations free endpoint, no key.
  Model ``openai`` (the endpoint's free default, gpt-oss-20b class).
- ``cortensor-portal``: Cortensor Portal base URL from
  ``CORTENSOR_PORTAL_BASE_URL`` (+ ``CORTENSOR_PORTAL_API_KEY`` if set).
  Not blocking: if the URL is unset the preset reports itself unavailable
  and the caller falls back to the free default.
- ``cortensor-router``: same shape via ``CORTENSOR_ROUTER_BASE_URL``.

Two findings baked in here (see docs/WHAT_WE_LEARNED.md):
1. ``no_proxy`` sanitising: this sandbox's ``no_proxy`` contains bracketed
   IPv6 entries (``[::1]``, ``[fd8b:...]``). OpenMinion's HTTP client is
   ``httpx.Client(trust_env=True)``; httpx chokes on those entries with
   ``InvalidURL: Invalid port: ':1]'`` before any request is sent. We strip
   bracketed entries from ``no_proxy``/``NO_PROXY`` in-process before
   building any runtime. Direct egress does not exist here, so the proxy
   itself must stay.
2. Pollinations free tier allows ~1 reply per 45 s per IP (HTTP 402
   otherwise). ``min_interval_seconds`` paces model calls: every agent run
   waits until at least that long has passed since the previous model call
   in this process. The SDK retries internally at ~300 ms, which cannot
   beat a 45 s window, so pacing must happen *before* the call.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

__all__ = [
    "PRESETS",
    "ProviderSettings",
    "resolve_preset",
    "sanitize_no_proxy",
    "pace_model_call",
    "POLLINATIONS_BASE_URL",
    "POLLINATIONS_MODEL",
]

PRESETS = ("openai-compatible", "cortensor-portal", "cortensor-router")

POLLINATIONS_BASE_URL = "https://text.pollinations.ai/openai/v1"
POLLINATIONS_MODEL = "openai"
POLLINATIONS_API_KEY = "pollinations-no-key-needed"

# Pollinations free tier: 1 reply / 45 s per IP. Keep a margin.
FREE_TIER_MIN_INTERVAL_SECONDS = 50.0

_last_call_at: float = 0.0


@dataclass(frozen=True)
class ProviderSettings:
    preset: str
    base_url: str
    model: str
    api_key: str
    api_key_env: str
    timeout_seconds: int = 240
    available: bool = True
    unavailable_reason: str = ""


def sanitize_no_proxy() -> dict[str, str]:
    """Drop bracketed IPv6 entries from no_proxy; return what changed."""
    changed: dict[str, str] = {}
    for key in ("no_proxy", "NO_PROXY"):
        raw = os.environ.get(key, "")
        if not raw:
            continue
        kept = [p for p in raw.split(",") if not p.strip().startswith("[")]
        cleaned = ",".join(kept)
        if cleaned != raw:
            os.environ[key] = cleaned
            changed[key] = cleaned
    return changed


def pace_model_call(min_interval: float = FREE_TIER_MIN_INTERVAL_SECONDS) -> float:
    """Sleep until ``min_interval`` passed since the last model call.

    Returns seconds waited (0 if no wait was needed). Only applies to the
    free Pollinations preset; keyed presets set their own interval.
    """
    global _last_call_at
    now = time.monotonic()
    wait = min_interval - (now - _last_call_at)
    if wait > 0:
        time.sleep(wait)
    _last_call_at = time.monotonic()
    return max(0.0, wait)


def resolve_preset(preset: str | None = None) -> ProviderSettings:
    """Resolve a preset name (or env override) to concrete settings."""
    name = (preset or os.environ.get("PAPER_WATCH_PRESET") or "openai-compatible").strip()
    if name == "openai-compatible":
        return ProviderSettings(
            preset=name,
            base_url=os.environ.get("OPENAI_BASE_URL") or POLLINATIONS_BASE_URL,
            model=os.environ.get("OPENAI_MODEL") or POLLINATIONS_MODEL,
            api_key=os.environ.get("OPENAI_API_KEY") or POLLINATIONS_API_KEY,
            api_key_env="OPENAI_API_KEY",
            timeout_seconds=int(os.environ.get("PAPER_WATCH_TIMEOUT", "240")),
        )
    if name in ("cortensor-portal", "cortensor-router"):
        env_base = "CORTENSOR_PORTAL_BASE_URL" if name == "cortensor-portal" else "CORTENSOR_ROUTER_BASE_URL"
        env_key = "CORTENSOR_PORTAL_API_KEY" if name == "cortensor-portal" else "CORTENSOR_ROUTER_API_KEY"
        base_url = os.environ.get(env_base) or ""
        if not base_url:
            return ProviderSettings(
                preset=name, base_url="", model="", api_key="", api_key_env=env_key,
                available=False,
                unavailable_reason=(
                    f"{env_base} is not set (Portal access is still pending "
                    "official coordination); falling back to openai-compatible."
                ),
            )
        return ProviderSettings(
            preset=name,
            base_url=base_url,
            model=os.environ.get("CORTENSOR_MODEL") or "gpt-oss-20b",
            api_key=os.environ.get(env_key) or "",
            api_key_env=env_key,
            timeout_seconds=420,
        )
    raise ValueError(f"unknown preset {name!r}; expected one of {PRESETS}")
