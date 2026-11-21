"""Provider presets + environment fixes.

Three presets, same application code (mirrors the reference pattern of
switching provider without touching the agent):

- openai-compatible (default): Pollinations free text endpoint, no key.
  model "openai" is the alias the endpoint actually serves as gpt-oss-20b.
- cortensor-portal: Cortensor Portal hosted inference (access TBD with
  the organisers; honoured here as a preset only, never required).
- cortensor-router: Cortensor Router endpoint (same status as portal).

No API key is ever written to disk by this package. Keys come from the
environment only, at call time.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def fix_proxy_env() -> None:
    """Bare/bracketed IPv6 entries in NO_PROXY break httpx parsing
    (``InvalidURL: Invalid port: ':1]'``). Narrow it to loopback hosts."""
    os.environ["NO_PROXY"] = "localhost,127.0.0.1"
    os.environ["no_proxy"] = "localhost,127.0.0.1"


@dataclass
class ProviderSettings:
    preset: str
    base_url: str
    model: str
    api_key: str = ""


PRESETS: dict[str, dict[str, str]] = {
    "openai-compatible": {
        "base_url": "https://text.pollinations.ai/openai/v1",
        "model": "openai",
    },
    "cortensor-portal": {
        "base_url": os.environ.get(
            "CORTENSOR_PORTAL_BASE_URL", "https://portal.cortensor.network/v1"),
        "model": os.environ.get("CORTENSOR_PORTAL_MODEL", "openai"),
    },
    "cortensor-router": {
        "base_url": os.environ.get(
            "CORTENSOR_ROUTER_BASE_URL", "https://router.cortensor.network/v1"),
        "model": os.environ.get("CORTENSOR_ROUTER_MODEL", "openai"),
    },
}


def resolve_provider(preset: str, api_key: str | None = None) -> ProviderSettings:
    if preset not in PRESETS:
        raise ValueError(f"unknown preset {preset!r}; choose from {sorted(PRESETS)}")
    cfg = PRESETS[preset]
    key = api_key if api_key is not None else os.environ.get("HACKATHON_WATCH_API_KEY", "")
    if preset == "openai-compatible" and not key:
        # Pollinations does not validate the key; this is a placeholder
        # string, not a real credential.
        key = "pollinations-no-key-needed"
    return ProviderSettings(preset=preset, base_url=cfg["base_url"],
                            model=cfg["model"], api_key=key)
