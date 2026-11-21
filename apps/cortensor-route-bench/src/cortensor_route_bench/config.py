"""Configuration loading, provider catalog, secret redaction, and OpenMinion setup."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from .models import PreflightCheck, PreflightReport


@dataclass(frozen=True)
class ProviderProfile:
    """Normalized metadata for a supported OpenMinion provider preset."""

    provider_id: str
    label: str
    base_url: str
    credential_env: str | None
    default_model: str
    recommended_preset_model_bug: str | None
    supports_native_tool_calling: bool
    transport_kind: str
    notes: str


PROVIDER_PROFILES: dict[str, ProviderProfile] = {
    "gemini": ProviderProfile(
        provider_id="gemini",
        label="Google Gemini (OpenAI-compatible)",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        credential_env="GEMINI_API_KEY",
        default_model="gemini-3.5-flash-lite",
        recommended_preset_model_bug="gemini-3.6-flash (timed out at 15s on free-tier chat completions; light variants respond reliably)",
        supports_native_tool_calling=True,
        transport_kind="openai_compatible",
        notes="Free tier enforces ~20 requests/day per model ID; split probe and bench models to avoid daily cap exhaustion.",
    ),
    "cortensor-portal": ProviderProfile(
        provider_id="cortensor-portal",
        label="Cortensor Portal API Gateway",
        base_url="https://api.cortensor.app/v1",
        credential_env="CORTENSOR_API_KEY",
        default_model="oss-20b",
        recommended_preset_model_bug=None,
        supports_native_tool_calling=False,
        transport_kind="openai_compatible",
        notes="Hosted compatibility routes expose text-in/text-out only; multi-round @tool loops require prompt fallback.",
    ),
    "cortensor-router": ProviderProfile(
        provider_id="cortensor-router",
        label="Cortensor Direct Router",
        base_url="http://127.0.0.1:8080/api/v2/completions",
        credential_env="CORTENSOR_API_KEY",
        default_model="gpt-oss-20b",
        recommended_preset_model_bug=None,
        supports_native_tool_calling=False,
        transport_kind="cortensor_router",
        notes="Direct completion transport via Cortensor Router node REST API.",
    ),
    "openrouter": ProviderProfile(
        provider_id="openrouter",
        label="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        credential_env="OPENROUTER_API_KEY",
        default_model="openai/gpt-4.1-mini",
        recommended_preset_model_bug=None,
        supports_native_tool_calling=True,
        transport_kind="openai_compatible",
        notes="Supports broad model catalog via unified OpenAI-compatible API.",
    ),
    "groq": ProviderProfile(
        provider_id="groq",
        label="Groq",
        base_url="https://api.groq.com/openai/v1",
        credential_env="GROQ_API_KEY",
        default_model="llama-3.3-70b-versatile",
        recommended_preset_model_bug=None,
        supports_native_tool_calling=True,
        transport_kind="openai_compatible",
        notes="Low-latency OpenAI-compatible inference endpoint.",
    ),
    "ollama": ProviderProfile(
        provider_id="ollama",
        label="Ollama (Local)",
        base_url="http://127.0.0.1:11434",
        credential_env=None,
        default_model="llama3.1",
        recommended_preset_model_bug=None,
        supports_native_tool_calling=True,
        transport_kind="ollama_local",
        notes="Local inference with no external API key.",
    ),
}

_SECRET_PATTERNS = (
    re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]{8,}", re.IGNORECASE),
    re.compile(r"\b(AQ\.[A-Za-z0-9._\-]{10,})\b"),
    re.compile(r"\b(sk-[A-Za-z0-9._\-]{10,})\b"),
    re.compile(r"\b(AIza[A-Za-z0-9._\-]{10,})\b"),
)


def redact_secrets(text: str) -> str:
    """Mask bearer tokens and common API key prefixes before logging or saving artifacts."""
    cleaned = text
    for pattern in _SECRET_PATTERNS:
        cleaned = pattern.sub(lambda m: f"{m.group(1)[:6]}***REDACTED***", cleaned)
    return cleaned


def load_dotenv_file(env_path: Path | None = None) -> Path | None:
    """Load key=value pairs from a local .env file without overriding existing env vars."""
    candidate = env_path or Path.cwd() / ".env"
    if not candidate.is_file():
        return None
    for raw_line in candidate.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ and val:
            os.environ[key] = val
    return candidate


def resolve_provider_profile(provider_id: str | None = None) -> ProviderProfile:
    """Resolve provider metadata from explicit flag or ROUTE_BENCH_PROVIDER env."""
    chosen = (provider_id or os.environ.get("ROUTE_BENCH_PROVIDER") or "gemini").strip().lower()
    if chosen not in PROVIDER_PROFILES:
        valid = ", ".join(sorted(PROVIDER_PROFILES))
        raise ValueError(f"Unsupported provider {chosen!r}; choose from: {valid}")
    return PROVIDER_PROFILES[chosen]


def resolve_model(profile: ProviderProfile, model: str | None = None) -> str:
    """Pick explicit model, ROUTE_BENCH_MODEL env, or profile default."""
    chosen = (model or os.environ.get("ROUTE_BENCH_MODEL") or profile.default_model).strip()
    if not chosen:
        return profile.default_model
    return chosen


def is_credential_configured(profile: ProviderProfile) -> bool:
    """Return True if the provider needs no key or its credential env var is non-empty."""
    if profile.credential_env is None:
        return True
    return bool(os.environ.get(profile.credential_env, "").strip())


DEFAULT_DELEGATION_ALLOW_TOOLS: tuple[str, ...] = (
    "transfer_to_cortensor_specialist",
    "transfer_to_consensus_synthesizer",
)


def _configure_delegation_policy_rules(config_path: Path) -> None:
    """Register exact-tool `auto` policy rules for Handoff delegation tools so unattended runs skip UNKNOWN_REVERSIBILITY prompts."""
    if not config_path.is_file():
        return
    data = json.loads(config_path.read_text(encoding="utf-8") or "{}")
    if not isinstance(data, dict):
        return
    policy = data.setdefault("action_policy", {})
    if not isinstance(policy, dict):
        return
    policy.setdefault("mode", "auto")
    policy.setdefault("default_action", "require_confirm")
    policy.setdefault("allow_read_only_without_prompt", True)
    rules = list(policy.get("rules") or [])
    existing = {
        str(rule.get("match", {}).get("tool_name", "")).strip()
        for rule in rules
        if isinstance(rule, dict) and isinstance(rule.get("match"), dict)
    }
    changed = False
    for tool_name in DEFAULT_DELEGATION_ALLOW_TOOLS:
        if tool_name not in existing:
            rules.append(
                {
                    "match": {"tool_name": tool_name, "min_risk_class": ""},
                    "mode": "auto",
                }
            )
            changed = True
    if changed or "action_policy" not in data:
        policy["rules"] = rules
    gateway = data.setdefault("gateway", {})
    if isinstance(gateway, dict) and int(gateway.get("api_turn_timeout_seconds") or 0) < 180:
        gateway["api_turn_timeout_seconds"] = 180
        changed = True
    if changed or "action_policy" not in data:
        config_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )


def ensure_openminion_config(
    config_path: Path,
    profile: ProviderProfile,
    model: str,
) -> Path:
    """Generate or refresh an OpenMinion YAML config using the official CLI setup command."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "openminion",
        "--config",
        str(config_path),
        "setup",
        "--provider",
        profile.provider_id,
        "--model",
        model,
        "--no-chat",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(
            f"openminion setup failed (exit {proc.returncode}): "
            f"{redact_secrets((proc.stderr or proc.stdout).strip())}"
        )
    _configure_delegation_policy_rules(config_path)
    return config_path


def run_preflight(
    *,
    provider: str | None = None,
    model: str | None = None,
    config_path: Path | None = None,
) -> PreflightReport:
    """Run deterministic preflight checks for OpenMinion SDK version, credentials, and route posture."""
    import openminion
    from datetime import datetime, timezone

    profile = resolve_provider_profile(provider)
    selected_model = resolve_model(profile, model)
    cred_ok = is_credential_configured(profile)
    checks: list[PreflightCheck] = []

    checks.append(
        PreflightCheck(
            check_id="sdk.version",
            status="pass",
            summary=f"OpenMinion {openminion.__version__} imported successfully.",
            details={"openminion_version": openminion.__version__},
        )
    )
    checks.append(
        PreflightCheck(
            check_id="provider.credentials",
            status="pass" if cred_ok else "fail",
            summary=(
                f"Credential environment variable {profile.credential_env} is configured."
                if profile.credential_env and cred_ok
                else (
                    "No API key required for local provider."
                    if profile.credential_env is None
                    else f"Missing required credential env var: {profile.credential_env}"
                )
            ),
            details={"credential_env": profile.credential_env, "configured": cred_ok},
        )
    )
    checks.append(
        PreflightCheck(
            check_id="provider.tool_calling_posture",
            status="pass" if profile.supports_native_tool_calling else "warn",
            summary=(
                "Native OpenAI tool calling supported."
                if profile.supports_native_tool_calling
                else "Hosted Cortensor routes disable native tool_calling; use prompt fallback or single-turn Agent.run()."
            ),
            details={
                "supports_native_tool_calling": profile.supports_native_tool_calling,
                "transport_kind": profile.transport_kind,
            },
        )
    )
    if profile.recommended_preset_model_bug:
        checks.append(
            PreflightCheck(
                check_id="provider.preset_model_override",
                status="warn" if selected_model == "gemini-3.6-flash" else "pass",
                summary=(
                    f"Using live model {selected_model!r} instead of stale preset recommendation ({profile.recommended_preset_model_bug})."
                ),
                details={"selected_model": selected_model},
            )
        )

    if config_path is not None:
        checks.append(
            PreflightCheck(
                check_id="config.file_presence",
                status="pass" if config_path.is_file() else "warn",
                summary=f"OpenMinion config path: {config_path}",
                details={"exists": config_path.is_file()},
            )
        )

    overall = "blocked" if any(c.status == "fail" for c in checks) else (
        "degraded" if any(c.status == "warn" for c in checks) else "ready"
    )
    return PreflightReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        provider=profile.provider_id,
        model=selected_model,
        base_url=profile.base_url,
        supports_native_tool_calling=profile.supports_native_tool_calling,
        credential_configured=cred_ok,
        openminion_version=openminion.__version__,
        checks=checks,
        overall_status=overall,
    )
