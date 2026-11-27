"""Model-backed run of the Sentinel agent through the OpenMinion SDK.

The model decides which tools to call and in what order. The verdict is read
from the tool results (the AST audit and the sandboxed test), not from the
model's prose, so a model that misreads a result cannot certify bad code.
"""

from __future__ import annotations

import ast
import json
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openminion import Agent

from cortensor_validator import openminion_agent as om


AGENT_ID = "sentinel"

INSTRUCTIONS = (
    "You verify code submitted by Cortensor subnet miners. For each task: "
    "1) call audit_code_safety on the code; "
    "2) only if the audit says valid, call execute_test_case with the given input and expected output; "
    "3) call create_attestation_receipt with the task id and passed=true only if both the audit "
    "and the test passed, otherwise passed=false; "
    "4) reply with one sentence: the verdict and the reason."
)

# Provider presets. Both use OpenMinion's OpenAI-compatible adapter.
PRESETS: dict[str, dict[str, Any]] = {
    # Any OpenAI-compatible server: Ollama, Lemonade, vLLM, llama.cpp server.
    "local": {
        "base_url": "http://localhost:11434/v1",
        "model": "",
        "api_key_env": "SENTINEL_API_KEY",
        "timeout_seconds": 240,
    },
    # Cortensor Portal, using the SDK's own "cortensor-portal" preset values.
    "portal": {
        "base_url": "https://api.cortensor.app/v1",
        "model": "oss-20b",
        "api_key_env": "CORTENSOR_API_KEY",
        "timeout_seconds": 600,
    },
}


@dataclass
class LiveResult:
    task_id: str
    passed: bool
    reason: str
    model_text: str
    tool_calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)
    llm_calls_by_purpose: dict[str, int] = field(default_factory=dict)


def write_agent_config(preset: str, runtime_dir: Path) -> Path:
    """Write an OpenMinion agents.json for the chosen preset and return its path.

    SENTINEL_BASE_URL and SENTINEL_MODEL override the preset values.
    """
    if preset not in PRESETS:
        raise ValueError(f"unknown provider preset {preset!r}; choose from {sorted(PRESETS)}")
    cfg = dict(PRESETS[preset])
    cfg["base_url"] = os.getenv("SENTINEL_BASE_URL", cfg["base_url"])
    cfg["model"] = os.getenv("SENTINEL_MODEL", cfg["model"])
    if not cfg["model"]:
        raise ValueError(
            "set SENTINEL_MODEL to a model your server serves, e.g. SENTINEL_MODEL=llama3.1"
        )
    if preset == "local" and not os.getenv(cfg["api_key_env"]):
        # Local servers ignore the key, but the OpenAI adapter requires one.
        cfg["api_key"] = "local"
    agent_cfg: dict[str, Any] = {"provider": "openai", "default_channel": "console"}
    config: dict[str, Any] = {
        "default_agent": AGENT_ID,
        "providers": {"openai": cfg},
        # Without default_channel the SDK sends an empty channel and the inbound
        # authenticity check denies the turn (see docs/cortensor_openminion_feedback_report.md).
        "agents": {AGENT_ID: agent_cfg},
    }
    if preset == "portal":
        # Decentralized Cortensor Portal routers take ~20 to 90 s per completion.
        # Disabling OpenMinion's pre-turn reflection and memory extraction keeps
        # end-to-end verification turns inside the 900 s ceiling while leaving
        # agent thinking/act profile at defaults so entry task updates work reliably.
        config["runtime"] = {
            "memory_enabled": False,
            "brain_turn_timeout_seconds": 900,
            "chat_turn_timeout_seconds": 900,
        }
        config["brain"] = {
            "auto_fact_extraction": {"enabled": False},
            "reflection": {
                "enabled": False,
                "auto_save_lessons": False,
                "stage_policy_candidates": False,
                "governance_progress_checkpoints_enabled": False,
                "governance_step_risk_gate_enabled": False,
                "reserved_llm_calls": 0,
            },
            "adaptive_budget": {"idle_timeout_s": 900},
        }
    runtime_dir.mkdir(parents=True, exist_ok=True)
    path = runtime_dir / "agents.json"
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return path


def _same_code(a: str, b: str) -> bool:
    """True when two sources are the same program, ignoring formatting and comments.

    Models often reflow code they pass to a tool (add a blank line, drop the
    trailing newline). Comparing ASTs ignores that but still catches a real edit
    such as a removed import. Unparseable code falls back to exact text.
    """
    try:
        return ast.dump(ast.parse(a)) == ast.dump(ast.parse(b))
    except SyntaxError:
        return a.strip() == b.strip()


def _verdict_from_tools(calls: list[tuple[str, dict[str, Any]]], submitted_code: str) -> tuple[bool, str]:
    """Derive the verdict from tool results on the submitted code only.

    The model picks tool arguments. A model that rewrites the code (for example
    drops a forbidden import) and then audits and tests the rewrite must not
    certify the original, so calls on any other code are disqualifying.
    """
    code_calls = [(n, r) for n, r in calls if n in ("audit_code_safety", "execute_test_case")]
    for name, r in code_calls:
        if not _same_code(r.get("_code", ""), submitted_code):
            return False, f"model called {name} on code other than the submission"
    audits = [r for n, r in code_calls if n == "audit_code_safety"]
    tests = [r for n, r in code_calls if n == "execute_test_case"]
    if not audits:
        return False, "model never called audit_code_safety"
    blocked = [r for r in audits if not r.get("valid")]
    if blocked:
        return False, "audit blocked: " + "; ".join(blocked[0].get("violations", []))
    if not tests:
        return False, "model never called execute_test_case"
    failed = [r for r in tests if not r.get("passed")]
    if failed:
        t = failed[0]
        detail = t.get("error") or f"got {t.get('actual_output')}, expected {t.get('expected_output')}"
        return False, f"test failed: {detail}"
    return True, f"test passed (output {tests[-1].get('actual_output')})"


def run_live_task(
    config_path: Path,
    task_id: str,
    code: str,
    test_input: int,
    expected_output: int,
    timeout_seconds: float = 400.0,
    force_audit: bool = True,
) -> LiveResult:
    """Run one verification task through a real model and return the result.

    With force_audit, the SDK's forced_tools makes the audit the first call on
    every run; the model still decides whether to execute and what to attest.
    """
    om.TOOL_LOG.clear()
    prompt = (
        f"Task id: {task_id}\n"
        f"Test: solution({test_input}) must return {expected_output}.\n"
        f"Code:\n```python\n{code}```"
    )
    with Agent(
        config_path=str(config_path),
        agent_id=AGENT_ID,
        instructions=INSTRUCTIONS,
        tools=[om.audit_code_safety, om.execute_test_case, om.create_attestation_receipt],
        forced_tools=["audit_code_safety"] if force_audit else [],
        session_id=f"sentinel-{task_id}-{uuid.uuid4().hex[:8]}",
    ) as agent:
        result = agent.run(prompt, timeout_seconds=timeout_seconds)

    calls = list(om.TOOL_LOG)
    passed, reason = _verdict_from_tools(calls, code)
    meta = result.metadata or {}
    try:
        by_purpose = {
            k: v for k, v in json.loads(meta.get("llm_call_counts_by_purpose", "{}")).items() if v
        }
    except (TypeError, ValueError):
        by_purpose = {}
    return LiveResult(
        task_id=task_id,
        passed=passed,
        reason=reason,
        model_text=result.text,
        tool_calls=calls,
        stats=dict(result.stats or {}),
        llm_calls_by_purpose=by_purpose,
    )
