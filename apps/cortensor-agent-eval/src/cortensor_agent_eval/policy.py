"""Fail-closed single-use approval gate and runtime isolation helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openminion.services.bootstrap.provider_setup import (
    ProviderSetupMissingCredential,
    ProviderSetupRequest,
    atomic_save_setup_config,
    build_provider_setup,
)

from cortensor_agent_eval.models import ApprovalDecisionRecord

DEFAULT_MODELS: dict[str, str] = {
    "openrouter": "openai/gpt-4.1-mini",
    "cortensor-portal": "oss-20b",
    "cortensor-router": "gpt-oss-20b",
    "groq": "llama-3.3-70b-versatile",
    "openai": "gpt-4.1-mini",
    "ollama": "llama3.1",
}

DEFAULT_BASE_URLS: dict[str, str] = {
    "openrouter": "https://openrouter.ai/api/v1",
    "cortensor-portal": "https://api.cortensor.app/v1",
    "cortensor-router": "http://127.0.0.1:8080/api/v2/completions",
    "groq": "https://api.groq.com/openai/v1",
    "openai": "https://api.openai.com/v1",
    "ollama": "http://127.0.0.1:11434",
}


@dataclass
class FailClosedApprovalGate:
    """Single-use policy gate that permits only explicit safe report writes."""

    allowed_write_tools: frozenset[str] = frozenset({"write_eval_artifact"})
    allow_single_write: bool = True
    _write_consumed: bool = False
    records: list[ApprovalDecisionRecord] = field(default_factory=list)

    def __call__(
        self, tool_name: str, args: dict[str, Any], approval_id: str
    ) -> bool:
        keys = sorted(str(k) for k in (args or {}).keys())
        if tool_name in self.allowed_write_tools:
            if not self.allow_single_write:
                self.records.append(
                    ApprovalDecisionRecord(
                        tool_name=tool_name,
                        approval_id=approval_id,
                        decision="denied",
                        reason="write_disabled_by_policy",
                        args_keys=keys,
                    )
                )
                return False
            raw_filename = str((args or {}).get("filename", "") or "").strip()
            if (
                not raw_filename
                or raw_filename in {".", ".."}
                or any(sep in raw_filename for sep in ("/", "\\", ":", "\x00"))
            ):
                self.records.append(
                    ApprovalDecisionRecord(
                        tool_name=tool_name,
                        approval_id=approval_id,
                        decision="denied",
                        reason="invalid_or_traversal_artifact_filename",
                        args_keys=keys,
                    )
                )
                return False
            if self._write_consumed:
                self.records.append(
                    ApprovalDecisionRecord(
                        tool_name=tool_name,
                        approval_id=approval_id,
                        decision="denied",
                        reason="single_use_write_already_consumed",
                        args_keys=keys,
                    )
                )
                return False
            self._write_consumed = True
            self.records.append(
                ApprovalDecisionRecord(
                    tool_name=tool_name,
                    approval_id=approval_id,
                    decision="approved",
                    reason="single_use_artifact_write_approved",
                    args_keys=keys,
                )
            )
            return True

        self.records.append(
            ApprovalDecisionRecord(
                tool_name=tool_name,
                approval_id=approval_id,
                decision="denied",
                reason="fail_closed_unlisted_tool",
                args_keys=keys,
            )
        )
        return False


def build_isolated_config(
    *,
    work_dir: Path,
    provider: str,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> Path:
    """Create an isolated agents.json using OpenMinion ProviderSetupRequest."""
    work_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = work_dir / "agents.json"
    resolved_model = (model or "").strip() or DEFAULT_MODELS.get(provider, "gpt-4.1-mini")
    env = dict(os.environ)
    if api_key:
        env["OPENAI_API_KEY"] = api_key
        env["OPENROUTER_API_KEY"] = api_key
        env["CORTENSOR_API_KEY"] = api_key
        env["GROQ_API_KEY"] = api_key

    request = ProviderSetupRequest(
        preset_id=provider,
        agent_id="evaluator",
        model=resolved_model,
        base_url=(base_url or "").strip(),
        stored_api_key=api_key or "",
        allow_local_api_key=bool(api_key),
        config_path=str(cfg_path),
        home_root=work_dir,
        data_root=work_dir,
        env=env,
    )
    setup_result = build_provider_setup(request)
    atomic_save_setup_config(setup_result.config, cfg_path)
    if api_key:
        import json

        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        adapter = setup_result.preview.runtime_adapter
        if adapter in raw.get("providers", {}):
            raw["providers"][adapter]["api_key"] = api_key
        evaluator_conns = (
            raw.get("agents", {}).get("evaluator", {}).get("model_connections", {})
        )
        for conn in evaluator_conns.values():
            overrides = conn.setdefault("provider_config_overrides", {})
            overrides["api_key"] = api_key
            if base_url:
                overrides["base_url"] = base_url.strip()
        tmp_cfg = cfg_path.with_suffix(".json.tmp")
        tmp_cfg.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        os.replace(tmp_cfg, cfg_path)
    return cfg_path
