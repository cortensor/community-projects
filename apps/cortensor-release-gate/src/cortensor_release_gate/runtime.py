"""Isolated OpenMinion APIRuntime configuration and lifecycle helpers."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from openminion import APIRuntime

ProviderKind = Literal["cortensor", "openai"]


@dataclass(frozen=True)
class RuntimeSettings:
    """Resolved provider and workspace settings for APIRuntime."""

    provider: ProviderKind
    model: str
    base_url: str
    api_key: str
    api_mode: str = "openai_chat"
    session_id: int = 1


def _load_dotenv_if_present(dotenv_path: Path | None = None) -> None:
    candidate = dotenv_path or (Path.cwd() / ".env")
    if not candidate.is_file():
        return
    for raw_line in candidate.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        clean_key = key.strip()
        if clean_key and clean_key not in os.environ:
            os.environ[clean_key] = value.strip().strip('"').strip("'")


def resolve_live_settings(
    *,
    provider: ProviderKind | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> RuntimeSettings:
    """Resolve Cortensor Portal/Router or OpenAI-compatible credentials from env."""
    _load_dotenv_if_present()
    chosen: ProviderKind = provider or (
        "cortensor" if os.getenv("CORTENSOR_API_KEY") else "openai"
    )
    if chosen == "cortensor":
        api_key = os.getenv("CORTENSOR_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "CORTENSOR_API_KEY is not set. Pass --demo-local for offline loopback "
                "execution or export CORTENSOR_API_KEY."
            )
        return RuntimeSettings(
            provider="cortensor",
            model=model or os.getenv("CORTENSOR_MODEL") or "gpt-oss-20b",
            base_url=base_url
            or os.getenv("CORTENSOR_API_URL")
            or "https://api.cortensor.app/v1",
            api_key=api_key,
            api_mode=os.getenv("CORTENSOR_API_MODE") or "openai_chat",
            session_id=int(os.getenv("CORTENSOR_SESSION_ID") or "1"),
        )

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY is not set. Pass --demo-local for offline loopback "
            "execution or export OPENAI_API_KEY."
        )
    return RuntimeSettings(
        provider="openai",
        model=model or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini",
        base_url=base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1",
        api_key=api_key,
    )


def build_config_payload(settings: RuntimeSettings, workspace_dir: Path) -> dict[str, Any]:
    """Build an explicit OpenMinion 0.1.23 configuration payload."""
    # Keep state isolated under workspace_dir/.openminion so runs never mutate ~/.openminion.
    db_path = (workspace_dir / "openminion.db").as_posix()
    providers: dict[str, Any] = {}
    if settings.provider == "cortensor":
        providers["cortensor"] = {
            "model": settings.model,
            "base_url": settings.base_url,
            "api_key": settings.api_key,
            "api_mode": settings.api_mode,
            "session_id": settings.session_id,
            "tool_call_strategy": "hybrid",
            "timeout_seconds": 180,
            "result_wait_attempts": 1,
            "result_wait_interval_seconds": 0.0,
        }
    else:
        providers["openai"] = {
            "model": settings.model,
            "base_url": settings.base_url,
            "api_key": settings.api_key,
            "tool_call_strategy": "hybrid",
            "timeout_seconds": 180,
        }

    return {
        "default_agent": "release_gate",
        "storage": {"backend": "sqlite", "path": db_path},
        "action_policy": {
            "mode": "auto",
            "default_action": "require_confirm",
            "allow_read_only_without_prompt": True,
        },
        "providers": providers,
        "agents": {
            "release_gate": {
                "name": "release_gate",
                "role": "Release readiness gatekeeper",
                # Agent._build_payload() omits channel; set default_channel so GatewaySecurity accepts local turns.
                "default_channel": "console",
                "provider": settings.provider,
                "system_prompt": (
                    "You are a precise release readiness auditor for Cortensor projects. "
                    "Return JSON only when asked for structured outputs."
                ),
            }
        },
    }


def create_isolated_runtime(
    settings: RuntimeSettings,
    *,
    state_root: Path,
) -> APIRuntime:
    """Write an isolated agents.json and construct an OpenMinion APIRuntime."""
    state_root.mkdir(parents=True, exist_ok=True)
    home_root = state_root / "home"
    data_root = state_root / "data"
    home_root.mkdir(parents=True, exist_ok=True)
    data_root.mkdir(parents=True, exist_ok=True)
    config_path = state_root / "agents.json"
    config_path.write_text(
        json.dumps(build_config_payload(settings, data_root), indent=2),
        encoding="utf-8",
    )
    runtime: APIRuntime = APIRuntime.from_config_path(
        str(config_path),
        home_root=home_root,
        data_root=data_root,
    )
    return runtime
