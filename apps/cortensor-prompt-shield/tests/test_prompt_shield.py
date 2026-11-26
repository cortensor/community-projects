"""Automated pytest suite for Cortensor Prompt Shield & OpenMinion 0.1.24 SDK findings."""

from __future__ import annotations

import json
from pathlib import Path

import openminion
import pytest
from openminion import Agent
from openminion.base.config.base import ConfigError

from cortensor_prompt_shield.agent import build_runtime_config
from cortensor_prompt_shield.guard_proxy import compact_chat_payload
from cortensor_prompt_shield.scanner import audit_agents_config, scan_python_workspace


def test_ast_scanner_catches_all_misconfigurations() -> None:
    sample = Path(__file__).resolve().parent.parent / "examples" / "vulnerable_sample_agent.py"
    findings = scan_python_workspace(str(sample))
    rules = {f.rule_id for f in findings}
    assert "OM-SCOPE-001" in rules  # fetch_miner_metrics missing min_scope
    assert "OM-SCOPE-002" in rules  # sync_router_cache writes inside READ_ONLY
    assert "OM-DANGER-001" in rules  # restart_node_service mutates without dangerous=True
    assert "OM-DOC-001" in rules  # restart_node_service missing docstring


def test_config_auditor_flags_inline_secret_and_weak_policy(tmp_path: Path) -> None:
    bad_cfg = tmp_path / "agents.json"
    bad_cfg.write_text(
        json.dumps(
            {
                "action_policy": {"default_action": "allow"},
                "providers": {"openai": {"api_key": "sk-live-secret-should-not-be-here"}},
                "security": {"tool_policy": {"max_calls_per_run": 200}},
            }
        ),
        encoding="utf-8",
    )
    findings = audit_agents_config(str(bad_cfg))
    sections = {f.section for f in findings}
    assert "action_policy" in sections
    assert "providers.openai" in sections
    assert "security.tool_policy" in sections


def test_compact_guard_proxy_trims_openminion_prompt_bloat() -> None:
    bloated_system = "## Runtime Grounding\n" + ("boilerplate guidance line.\n" * 600) + "\nYou are Cortensor Prompt Shield, an authoritative OpenMinion security auditor."
    payload = {
        "model": "gemini-3.8-flash",
        "messages": [
            {"role": "system", "content": bloated_system},
            {"role": "user", "content": "Audit examples/vulnerable_sample_agent.py"},
        ],
        "tools": [
            {"type": "function", "function": {"name": "builtin_shell", "parameters": {}}},
            {"type": "function", "function": {"name": "scan_agent_tools", "parameters": {}}},
        ],
    }
    raw_len = len(json.dumps(payload).encode("utf-8"))
    compacted = compact_chat_payload(payload, max_prompt_bytes=6000)
    new_len = len(json.dumps(compacted).encode("utf-8"))
    assert raw_len > 15_000
    assert new_len < 3_000
    assert "Prompt Shield" in compacted["messages"][0]["content"]
    assert [t["function"]["name"] for t in compacted["tools"]] == ["scan_agent_tools"]


def test_finding_dir_openminion_hides_lazy_exports() -> None:
    """Reproduces Finding 5: dir(openminion) omits lazy-loaded public symbols like Agent and tool."""

    public_dir = set(dir(openminion))
    assert hasattr(openminion, "Agent")
    assert hasattr(openminion, "tool")
    # Confirm whether lazy exports are missing from dir() on 0.1.24
    assert "OPENMINION_VERSION" in public_dir


def test_finding_context_identity_budget_error_message(tmp_path: Path) -> None:
    """Reproduces Finding 3: integer context.identity_budget raises mislabeled ConfigError."""

    cfg_path = build_runtime_config(tmp_path, provider="echo", model="echo")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg["context"] = {"identity_budget": 100}
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    with pytest.raises(ConfigError) as exc_info:
        with Agent(config_path=str(cfg_path), agent_id="shield-auditor") as ag:
            ag.run("hi")
    assert "context.budget" in str(exc_info.value)


def test_finding_omitted_default_channel_fails_even_in_warn_mode(tmp_path: Path) -> None:
    """Reproduces Finding 2: omitting default_channel raises RuntimeError even with mode='warn'."""

    cfg_path = build_runtime_config(tmp_path, provider="echo", model="echo")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    del cfg["agents"]["shield-auditor"]["default_channel"]
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    with pytest.raises(RuntimeError, match="invalid_channel"):
        with Agent(config_path=str(cfg_path), agent_id="shield-auditor") as ag:
            ag.run("hi")
