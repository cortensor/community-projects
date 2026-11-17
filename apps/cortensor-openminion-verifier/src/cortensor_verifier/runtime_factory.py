"""Isolated OpenMinion configuration and APIRuntime factory with zero-secret persistence."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from openminion.api import APIRuntime
from openminion.base.config import OpenMinionConfig
from openminion.base.constants import (
    BASE_DEFAULT_CONFIG_DIRNAME,
    BASE_DEFAULT_CONFIG_FILENAME,
)
from openminion.modules.llm.setup_catalog import get_setup_preset

PROVIDER_PRESETS: tuple[str, ...] = (
    "openai-compatible",
    "cortensor-portal",
    "cortensor-router",
)


@dataclass(frozen=True)
class _PresetSpec:
    preset_id: str
    catalog_id: str
    base_url_env: str
    default_timeout_seconds: int
    provider_identity: dict[str, str]


_PRESET_TABLE: dict[str, _PresetSpec] = {
    "openai-compatible": _PresetSpec(
        preset_id="openai-compatible",
        catalog_id="openai",
        base_url_env="OPENAI_BASE_URL",
        default_timeout_seconds=60,
        provider_identity={},
    ),
    "cortensor-portal": _PresetSpec(
        preset_id="cortensor-portal",
        catalog_id="cortensor-portal",
        base_url_env="CORTENSOR_PORTAL_URL",
        default_timeout_seconds=480,
        provider_identity={
            "transport_adapter": "openai_chat",
            "wire_protocol_family": "openai_chat_completions",
            "service_vendor": "cortensor",
            "model_family": "oss",
        },
    ),
    "cortensor-router": _PresetSpec(
        preset_id="cortensor-router",
        catalog_id="cortensor-router",
        base_url_env="CORTENSOR_ROUTER_URL",
        default_timeout_seconds=120,
        provider_identity={},
    ),
}


def resolve_isolated_paths(
    *,
    home_root: str | Path | None = None,
    data_root: str | Path | None = None,
    config_path: str | Path | None = None,
) -> tuple[Path, Path, Path]:
    """Resolve repo-isolated home, state data root, and agents.json config paths."""
    resolved_home = Path(home_root or os.environ.get("OPENMINION_HOME") or Path.cwd()).resolve()
    resolved_data = Path(
        data_root or os.environ.get("OPENMINION_DATA_ROOT") or (resolved_home / ".openminion-state")
    ).resolve()
    resolved_config = Path(
        config_path or (resolved_home / BASE_DEFAULT_CONFIG_DIRNAME / BASE_DEFAULT_CONFIG_FILENAME)
    ).resolve()
    return resolved_home, resolved_data, resolved_config


def _resolve_preset_spec(preset: str) -> _PresetSpec:
    spec = _PRESET_TABLE.get(preset)
    if spec is None:
        supported = ", ".join(PROVIDER_PRESETS)
        raise ValueError(f"Unknown preset {preset!r}; expected one of: {supported}")
    return spec


def _scrub_persisted_secrets(payload: dict[str, Any]) -> dict[str, Any]:
    """Guarantee persisted agents.json holds zero plaintext API keys or secret env maps."""
    providers = payload.get("providers")
    if isinstance(providers, dict):
        for section in providers.values():
            if isinstance(section, dict) and "api_key" in section:
                section["api_key"] = ""
    runtime = payload.get("runtime")
    if isinstance(runtime, dict):
        runtime["env"] = {}
    return payload


def build_isolated_config(
    *,
    preset: str = "openai-compatible",
    base_url: str | None = None,
    model: str | None = None,
    api_key_env: str | None = None,
    agent_id: str = "verifier",
    home_root: str | Path | None = None,
    data_root: str | Path | None = None,
    config_path: str | Path | None = None,
    tool_call_strategy: Literal["native", "hybrid"] = "native",
    timeout_seconds: int | None = None,
    provider_retry_max_attempts: int = 2,
    agent_loop_max_steps: int = 16,
    http_connection_reuse_enabled: bool = False,
    cortensor_api_mode: str = "auto",
    cortensor_session_id: int = 1,
    persist: bool = True,
) -> OpenMinionConfig:
    """Build (and optionally persist without secrets) an OpenMinionConfig for a preset."""
    spec = _resolve_preset_spec(preset)
    catalog_preset = get_setup_preset(spec.catalog_id)

    _, resolved_data, resolved_config = resolve_isolated_paths(
        home_root=home_root,
        data_root=data_root,
        config_path=config_path,
    )

    resolved_base_url = (
        base_url
        or os.environ.get(spec.base_url_env)
        or catalog_preset.default_base_url
    )
    resolved_model = model or catalog_preset.recommended_models[0]
    resolved_api_key_env = api_key_env or catalog_preset.credential_env
    resolved_timeout = (
        timeout_seconds
        if timeout_seconds is not None
        else (catalog_preset.timeout_seconds or spec.default_timeout_seconds)
    )

    openai_catalog = get_setup_preset("openai")
    cortensor_catalog = get_setup_preset("cortensor-router")

    openai_cfg: dict[str, Any] = {
        "model": resolved_model if catalog_preset.runtime_adapter == "openai" else openai_catalog.recommended_models[0],
        "api_key": "",
        "api_key_env": resolved_api_key_env if catalog_preset.runtime_adapter == "openai" else openai_catalog.credential_env,
        "base_url": resolved_base_url if catalog_preset.runtime_adapter == "openai" else openai_catalog.default_base_url,
        "provider_identity": dict(spec.provider_identity) if catalog_preset.runtime_adapter == "openai" else {},
        "timeout_seconds": resolved_timeout if catalog_preset.runtime_adapter == "openai" else 60,
        "http_connection_reuse_enabled": http_connection_reuse_enabled,
        "temperature": 0.0,
        "tool_call_strategy": tool_call_strategy,
    }

    cortensor_cfg: dict[str, Any] = {
        "model": resolved_model if catalog_preset.runtime_adapter == "cortensor" else cortensor_catalog.recommended_models[0],
        "base_url": resolved_base_url if catalog_preset.runtime_adapter == "cortensor" else cortensor_catalog.default_base_url,
        "api_key": "",
        "api_key_env": resolved_api_key_env if catalog_preset.runtime_adapter == "cortensor" else cortensor_catalog.credential_env,
        "timeout_seconds": resolved_timeout if catalog_preset.runtime_adapter == "cortensor" else 120,
        "http_connection_reuse_enabled": http_connection_reuse_enabled,
        "temperature": 0.0,
        "tool_call_strategy": tool_call_strategy,
        "api_mode": cortensor_api_mode,
        "session_id": cortensor_session_id,
    }

    active_provider = catalog_preset.runtime_adapter
    payload: dict[str, Any] = {
        "default_agent": agent_id,
        "enabled_channels": ["console"],
        "agents": {
            agent_id: {
                "name": agent_id,
                "role": "Cortensor Consensus Verifier: evidence-backed claim and market resolution auditor",
                "default_channel": "console",
                "provider": active_provider,
                "provider_policy": {
                    "enabled": [active_provider],
                    "default_provider": active_provider,
                    "provider_order": [active_provider],
                },
            }
        },
        "providers": {
            "openai": openai_cfg,
            "cortensor": cortensor_cfg,
        },
        "storage": {
            "path": "state/openminion.db",
            "backend": "sqlite",
        },
        "action_policy": {
            "mode": "auto",
            "default_action": "require_confirm",
            "allow_read_only_without_prompt": True,
        },
        "runtime": {
            "memory_enabled": False,
            "telemetry_enabled": False,
            "provider_retry_max_attempts": provider_retry_max_attempts,
            "agent_loop_max_steps": agent_loop_max_steps,
            "env": {},
        },
    }

    config = OpenMinionConfig.from_dict(payload)
    if persist:
        resolved_data.mkdir(parents=True, exist_ok=True)
        resolved_config.parent.mkdir(parents=True, exist_ok=True)
        serialized = _scrub_persisted_secrets(config.to_dict(persistence=True))
        resolved_config.write_text(
            json.dumps(serialized, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return config


def create_isolated_runtime(
    *,
    preset: str = "openai-compatible",
    base_url: str | None = None,
    model: str | None = None,
    api_key_env: str | None = None,
    agent_id: str = "verifier",
    home_root: str | Path | None = None,
    data_root: str | Path | None = None,
    config_path: str | Path | None = None,
    tool_call_strategy: Literal["native", "hybrid"] = "native",
    timeout_seconds: int | None = None,
    provider_retry_max_attempts: int = 2,
    agent_loop_max_steps: int = 16,
    http_connection_reuse_enabled: bool = False,
    cortensor_api_mode: str = "auto",
    cortensor_session_id: int = 1,
    logging_mode: str = "silent",
) -> APIRuntime:
    """Persist a secret-free isolated config and boot a real openminion APIRuntime."""
    resolved_home, resolved_data, resolved_config = resolve_isolated_paths(
        home_root=home_root,
        data_root=data_root,
        config_path=config_path,
    )
    build_isolated_config(
        preset=preset,
        base_url=base_url,
        model=model,
        api_key_env=api_key_env,
        agent_id=agent_id,
        home_root=resolved_home,
        data_root=resolved_data,
        config_path=resolved_config,
        tool_call_strategy=tool_call_strategy,
        timeout_seconds=timeout_seconds,
        provider_retry_max_attempts=provider_retry_max_attempts,
        agent_loop_max_steps=agent_loop_max_steps,
        http_connection_reuse_enabled=http_connection_reuse_enabled,
        cortensor_api_mode=cortensor_api_mode,
        cortensor_session_id=cortensor_session_id,
        persist=True,
    )
    return APIRuntime.from_config_path(
        str(resolved_config),
        home_root=resolved_home,
        data_root=resolved_data,
        logging_mode=logging_mode,
    )
