"""OpenMinion 0.1 Python SDK runtime orchestration for Cortensor Release Guardian."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from openminion import APIRuntime, Agent, AgentOutputValidationError, ProviderError

from release_guardian.schemas import ReleaseVerdict
from release_guardian.tools import (
    ALL_TOOLS,
    check_openminion_config,
    run_syntax_audit,
    scan_repo_structure,
    scan_secret_leaks,
)

SYSTEM_INSTRUCTIONS = """You are Cortensor Release Guardian, a strict release-readiness engineer.
You audit Python/OpenMinion repositories before public release or Hackathon PR submission.
Always inspect the deterministic tool evidence carefully, highlight any real blockers (missing docs,
syntax errors, leaked secrets, or unsafe OpenMinion configs), and produce a concise, actionable verdict."""


def collect_deterministic_evidence(repo_path: str, config_path: str | None = None) -> dict[str, Any]:
    """Run all read-only audit tools directly to guarantee reproducible baseline evidence."""
    evidence: dict[str, Any] = {
        "repo_structure": json.loads(scan_repo_structure(repo_path)),
        "secret_leaks": json.loads(scan_secret_leaks(repo_path)),
        "syntax_audit": json.loads(run_syntax_audit(repo_path)),
    }
    if config_path:
        evidence["openminion_config"] = json.loads(check_openminion_config(config_path))
    return evidence


def run_release_audit(
    repo_path: str,
    config_path: str,
    agent_id: str | None = None,
    session_id: str = "release-guardian-session",
    stream: bool = False,
    structured: bool = False,
    use_tools: bool = True,
    on_event: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Execute a full release audit using OpenMinion APIRuntime and Agent."""
    repo_abs = str(Path(repo_path).resolve())
    cfg_abs = str(Path(config_path).resolve())
    baseline = collect_deterministic_evidence(repo_abs, cfg_abs)

    prompt = (
        f"Audit repository '{repo_abs}' (OpenMinion config: '{cfg_abs}') for release readiness.\n"
        f"Deterministic tool findings:\n{json.dumps(baseline, indent=2)}\n\n"
        "Give a clear GO / CONDITIONAL_GO / NO_GO decision, readiness score (0-100), "
        "any blockers, and 2-3 concrete recommendations for Cortensor builders."
    )

    runtime = APIRuntime.from_config_path(cfg_abs)
    try:
        agent_kwargs: dict[str, Any] = {
            "runtime": runtime,
            "agent_id": agent_id,
            "instructions": SYSTEM_INSTRUCTIONS,
            "session_id": session_id,
        }
        if use_tools:
            agent_kwargs["tools"] = ALL_TOOLS
            agent_kwargs["forced_tools"] = ["scan_repo_structure"]
        if structured:
            agent_kwargs["output_type"] = ReleaseVerdict

        with Agent(**agent_kwargs) as agent:
            if stream and not structured:
                result = agent.run_stream(prompt, on_delta=on_event or (lambda _e: None))
            else:
                result = agent.run(prompt)

        payload: dict[str, Any] = {
            "session_id": result.session_id,
            "repo_path": repo_abs,
            "config_path": cfg_abs,
            "baseline_evidence": baseline,
            "text": result.text,
            "structured_verdict": None,
        }
        if structured and getattr(result, "output", None) is not None:
            payload["structured_verdict"] = result.output.model_dump()
        return payload
    except AgentOutputValidationError as exc:
        return {
            "session_id": session_id,
            "repo_path": repo_abs,
            "config_path": cfg_abs,
            "baseline_evidence": baseline,
            "text": exc.raw_text,
            "structured_verdict": None,
            "validation_warning": f"Model output did not match ReleaseVerdict JSON schema: {exc}",
        }
    except ProviderError as exc:
        raise RuntimeError(f"OpenMinion provider error ({exc.code}): {exc.message}") from exc
    finally:
        runtime.close()


def run_followup(
    question: str,
    config_path: str,
    session_id: str = "release-guardian-session",
    agent_id: str | None = None,
) -> dict[str, Any]:
    """Continue an existing OpenMinion session to verify session continuity."""
    cfg_abs = str(Path(config_path).resolve())
    runtime = APIRuntime.from_config_path(cfg_abs)
    try:
        with Agent(
            runtime=runtime,
            agent_id=agent_id,
            instructions=SYSTEM_INSTRUCTIONS,
            session_id=session_id,
        ) as agent:
            result = agent.run(question)
        return {
            "session_id": result.session_id,
            "text": result.text,
        }
    finally:
        runtime.close()
