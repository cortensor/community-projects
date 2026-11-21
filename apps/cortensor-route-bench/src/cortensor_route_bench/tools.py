"""Read-only diagnostic tools decorated with @openminion.tool."""

from __future__ import annotations

from contextlib import contextmanager
import ipaddress
import os
import threading
from typing import Any, Iterator
from urllib.parse import urlparse

import httpx
import openminion
from openminion import tool

from .config import PROVIDER_PROFILES, is_credential_configured, redact_secrets
from .models import ConsensusVerdict, WorkerEvaluation

_CAPTURE_LOCK = threading.Lock()
_ACTIVE_CONTRACT_CAPTURES: list[tuple[str, dict[str, Any]]] | None = None


@contextmanager
def capture_validated_contracts() -> Iterator[list[tuple[str, dict[str, Any]]]]:
    """Collect valid Pydantic payloads submitted to `evaluate_json_contract` across executor threads."""
    global _ACTIVE_CONTRACT_CAPTURES
    buf: list[tuple[str, dict[str, Any]]] = []
    with _CAPTURE_LOCK:
        previous = _ACTIVE_CONTRACT_CAPTURES
        _ACTIVE_CONTRACT_CAPTURES = buf
    try:
        yield buf
    finally:
        with _CAPTURE_LOCK:
            _ACTIVE_CONTRACT_CAPTURES = previous


def _is_safe_probe_url(url: str) -> tuple[bool, str]:
    """Allow only HTTPS or local loopback URLs to prevent SSRF onto private LANs."""
    parsed = urlparse(url.strip())
    if parsed.scheme == "https" and parsed.netloc:
        return True, ""
    if parsed.scheme == "http" and parsed.hostname:
        host = parsed.hostname.lower()
        if host == "localhost":
            return True, ""
        try:
            addr = ipaddress.ip_address(host)
            if addr.is_loopback:
                return True, ""
        except ValueError:
            pass
    return False, "Only HTTPS or loopback HTTP URLs are permitted for health probes."


@tool(
    min_scope="READ_ONLY",
    idempotent=True,
    description="Inspect a configured OpenMinion/Cortensor provider profile, tool-calling compatibility, and credential status.",
)
def inspect_provider_profile(provider_id: str) -> dict[str, Any]:
    """Return non-secret metadata for a supported provider preset."""
    key = provider_id.strip().lower()
    profile = PROVIDER_PROFILES.get(key)
    if profile is None:
        return {
            "found": False,
            "provider_id": key,
            "supported_providers": sorted(PROVIDER_PROFILES),
        }
    return {
        "found": True,
        "provider_id": profile.provider_id,
        "label": profile.label,
        "base_url": profile.base_url,
        "default_model": profile.default_model,
        "supports_native_tool_calling": profile.supports_native_tool_calling,
        "transport_kind": profile.transport_kind,
        "credential_env": profile.credential_env,
        "credential_configured": is_credential_configured(profile),
        "notes": profile.notes,
    }


@tool(
    min_scope="READ_ONLY",
    idempotent=True,
    description="Check HTTP reachability of an HTTPS or localhost Cortensor/LLM endpoint without transmitting secrets.",
)
def check_endpoint_health(url: str) -> dict[str, Any]:
    """Run a bounded unauthenticated GET check on a safe endpoint URL."""
    ok, reason = _is_safe_probe_url(url)
    if not ok:
        return {"ok": False, "url": url, "error": reason}
    try:
        resp = httpx.get(url.strip(), timeout=6.0, follow_redirects=False)
        return {
            "ok": resp.status_code < 500,
            "url": url.strip(),
            "status_code": resp.status_code,
            "content_type": resp.headers.get("content-type", ""),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "url": url.strip(),
            "error": redact_secrets(f"{type(exc).__name__}: {exc}"),
        }


@tool(
    min_scope="READ_ONLY",
    idempotent=True,
    description="Return local OpenMinion SDK version, exported public symbols, and redacted environment key posture.",
)
def inspect_openminion_runtime_snapshot() -> dict[str, Any]:
    """Return runtime metadata for auditing OpenMinion readiness."""
    env_flags = {
        env_name: bool(os.environ.get(env_name, "").strip())
        for env_name in (
            "GEMINI_API_KEY",
            "CORTENSOR_API_KEY",
            "OPENROUTER_API_KEY",
            "GROQ_API_KEY",
        )
    }
    return {
        "openminion_version": openminion.__version__,
        "python_exports": [
            name
            for name in (
                "Agent",
                "APIRuntime",
                "AgentOutputValidationError",
                "AgentRunResult",
                "Handoff",
                "MemoryBundle",
                "OpenMinionConfig",
                "ProviderError",
                "TurnTimeoutError",
                "subagent",
                "tool",
            )
            if hasattr(openminion, name)
        ],
        "configured_credentials": env_flags,
    }


@tool(
    min_scope="READ_ONLY",
    idempotent=True,
    description="Validate a JSON string against WorkerEvaluation or ConsensusVerdict Pydantic contract.",
)
def evaluate_json_contract(raw_text: str, schema_name: str = "WorkerEvaluation") -> dict[str, Any]:
    """Validate candidate JSON payload against the requested benchmark schema."""
    schemas = {
        "WorkerEvaluation": WorkerEvaluation,
        "ConsensusVerdict": ConsensusVerdict,
    }
    model_cls = schemas.get(schema_name)
    if model_cls is None:
        return {"valid": False, "error": f"Unknown schema {schema_name!r}"}
    try:
        parsed = model_cls.model_validate_json(raw_text)
        dumped = parsed.model_dump(mode="json")
        with _CAPTURE_LOCK:
            if _ACTIVE_CONTRACT_CAPTURES is not None:
                _ACTIVE_CONTRACT_CAPTURES.append((schema_name, dumped))
        return {"valid": True, "schema": schema_name, "parsed": dumped}
    except Exception as exc:  # noqa: BLE001
        return {"valid": False, "schema": schema_name, "error": str(exc)}


ALL_DIAGNOSTIC_TOOLS = [
    inspect_provider_profile,
    check_endpoint_health,
    inspect_openminion_runtime_snapshot,
    evaluate_json_contract,
]
