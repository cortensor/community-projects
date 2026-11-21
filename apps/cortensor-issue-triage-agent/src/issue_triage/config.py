"""Provider presets and environment handling.

Three presets, one code path (all OpenAI-compatible chat completions):

- ``openai-compatible`` (default): Pollinations free endpoint, no key.
- ``cortensor-portal``: Cortensor Portal, needs official access coordination.
- ``cortensor-router``: Cortensor Router, needs official access coordination.

Portal/router are presets only: they are never required for the default
flow and never block it. No credential is ever written to disk by this
package; tokens come from the environment only.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://text.pollinations.ai/openai/v1"
DEFAULT_MODEL = "openai"
# Pollinations does not check the key; the placeholder is not a real secret.
PLACEHOLDER_API_KEY = "pollinations-no-key-needed"

PRESETS = ("openai-compatible", "cortensor-portal", "cortensor-router")


@dataclass(frozen=True)
class ProviderSettings:
    preset: str
    base_url: str
    model: str
    api_key: str


def fix_proxy_env() -> None:
    """Sandbox workaround (SPIKE.md §3): the sandbox's ``NO_PROXY`` holds
    bare and bracketed IPv6 literals (``::1``, ``[::1]``,
    ``fd8b:4f84:7d32:99::1``, ``[fd8b:4f84:7d32:99::1]``). httpx parses
    those entries as ``host:port`` and raises
    ``InvalidURL: Invalid port: ...`` before any request is made. Keep
    only plain hostnames / IPv4 entries (optionally with a port); drop
    everything with ``::`` or brackets. The egress proxy still handles
    the dropped hosts, so nothing is lost for our public-API calls."""
    safe_entry = re.compile(r"^[A-Za-z0-9._-]+(:\d+)?$")
    for var in ("NO_PROXY", "no_proxy"):
        value = os.environ.get(var, "")
        if not value:
            continue
        kept = [p.strip() for p in value.split(",") if safe_entry.match(p.strip())]
        os.environ[var] = ",".join(kept) if kept else "localhost,127.0.0.1"


def load_dotenv(path: str | None = None) -> None:
    """Best-effort ``.env`` loader (no dependency). Never overwrites real env."""
    from pathlib import Path

    candidate = Path(path) if path else Path.cwd() / ".env"
    if not candidate.is_file():
        return
    for line in candidate.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


def resolve_provider(preset: str | None = None) -> ProviderSettings:
    """Resolve a provider preset from env. Raises ValueError for presets
    that need access that is not configured (portal/router)."""
    preset = (preset or os.environ.get("ISSUE_TRIAGE_PRESET") or "openai-compatible").strip()
    if preset not in PRESETS:
        raise ValueError(f"unknown preset {preset!r}; expected one of {PRESETS}")

    if preset == "openai-compatible":
        return ProviderSettings(
            preset=preset,
            base_url=os.environ.get("OPENAI_BASE_URL") or DEFAULT_BASE_URL,
            model=os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL,
            api_key=os.environ.get("OPENAI_API_KEY") or PLACEHOLDER_API_KEY,
        )
    if preset == "cortensor-portal":
        base_url = os.environ.get("CORTENSOR_PORTAL_BASE_URL") or ""
        if not base_url:
            raise ValueError(
                "cortensor-portal preset needs CORTENSOR_PORTAL_BASE_URL; "
                "Portal access is pending official coordination, so the "
                "default openai-compatible (Pollinations, free) preset is used instead."
            )
        return ProviderSettings(
            preset=preset,
            base_url=base_url,
            model=os.environ.get("CORTENSOR_MODEL") or "oss-20b",
            api_key=os.environ.get("CORTENSOR_PORTAL_API_KEY") or "",
        )
    # cortensor-router
    base_url = os.environ.get("CORTENSOR_ROUTER_BASE_URL") or ""
    if not base_url:
        raise ValueError(
            "cortensor-router preset needs CORTENSOR_ROUTER_BASE_URL; "
            "Router access is pending official coordination, so the "
            "default openai-compatible (Pollinations, free) preset is used instead."
        )
    return ProviderSettings(
        preset=preset,
        base_url=base_url,
        model=os.environ.get("CORTENSOR_MODEL") or "oss-20b",
        api_key=os.environ.get("CORTENSOR_ROUTER_API_KEY") or "",
    )


def min_interval_seconds() -> float:
    try:
        return max(0.0, float(os.environ.get("ISSUE_TRIAGE_MIN_INTERVAL_SEC", "45")))
    except ValueError:
        return 45.0


def reasoning_effort_default() -> str | None:
    value = os.environ.get("ISSUE_TRIAGE_REASONING_EFFORT", "low").strip()
    return value or None


def github_token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or None
