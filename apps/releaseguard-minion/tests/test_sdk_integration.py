"""End-to-end integration tests exercising real OpenMinion 0.1.24 SDK primitives."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from openminion import APIRuntime
from openminion.modules.memory.portability import load_bundle

from release_guard_minion import ReleaseAuditReport, ReleaseGuardMinion
from conftest import (
    LocalOpenAIServer,
    make_text_reply,
    make_tool_call_reply,
    write_openminion_config,
)


def _audit_router(repo_path: Path, brief_path: Path | None) -> Any:
    """Deterministic OpenAI-compatible router that drives ReleaseGuard's tool loop."""

    called = {"manifest": False, "ci": False, "secrets": False, "brief": False}

    def route(body: dict[str, Any], _idx: int) -> dict[str, Any]:
        tools = [
            t["function"]["name"]
            for t in body.get("tools", [])
            if isinstance(t, dict) and "function" in t
        ]
        if tools == ["submit_output"]:
            return make_text_reply("{}")
        if "inspect_repo_manifest" in tools and not called["manifest"]:
            called["manifest"] = True
            return make_tool_call_reply(
                "c_manifest", "inspect_repo_manifest", {"repo_path": str(repo_path)}
            )
        if "inspect_ci_and_tests" in tools and not called["ci"]:
            called["ci"] = True
            return make_tool_call_reply(
                "c_ci", "inspect_ci_and_tests", {"repo_path": str(repo_path)}
            )
        if "scan_secret_hygiene" in tools and not called["secrets"]:
            called["secrets"] = True
            return make_tool_call_reply(
                "c_secrets", "scan_secret_hygiene", {"repo_path": str(repo_path)}
            )
        if brief_path is not None and "write_release_brief" in tools and not called["brief"]:
            called["brief"] = True
            return make_tool_call_reply(
                "c_brief",
                "write_release_brief",
                {
                    "output_path": str(brief_path),
                    "brief_markdown": f"# Release Brief for {repo_path.name}\n\nVerdict: READY\n",
                },
            )
        report = ReleaseAuditReport(
            repo_name=repo_path.name,
            verdict="ready",
            score=96,
            rationale="README, LICENSE, CI workflow, tests, and secret hygiene all passed.",
            checks=[
                {"category": "manifest", "passed": True, "evidence": "README, LICENSE, CHANGELOG, SECURITY present."},
                {"category": "ci_tests", "passed": True, "evidence": "ci.yml and 1 test file present."},
                {"category": "secrets", "passed": True, "evidence": "No secrets or .env files found."},
            ],
            blockers=[],
            recommendations=["Tag v0.1.0 after maintainer review."],
        )
        return make_text_reply(report.model_dump_json())

    return route


def test_full_release_audit_with_policy_gate_memory_and_diagnostics(
    sample_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise READ_ONLY auto-run, WRITE_SAFE approval callback, MemoryBundle, and diagnostics."""

    om_root = tmp_path / "om_home"
    monkeypatch.setenv("OPENMINION_HOME", str(om_root))
    monkeypatch.setenv("OPENMINION_DATA_ROOT", str(om_root / ".openminion"))

    brief_path = tmp_path / "artifacts" / "RELEASE_BRIEF.md"
    bundle_path = tmp_path / "artifacts" / "memory_bundle.json"

    with LocalOpenAIServer(_audit_router(sample_repo, brief_path)) as srv:
        cfg_path = write_openminion_config(om_root, openai_base_url=srv.base_url)
        with ReleaseGuardMinion(config_path=str(cfg_path), agent_id="auditor") as guard:
            diag = guard.diagnostics_snapshot()
            assert diag["tool_count"] > 0
            assert "runtime_posture" in diag
            assert "capability_report" in diag
            assert "runtime_self_model" in diag

            envelope = guard.audit_repository(
                sample_repo,
                output_brief_path=brief_path,
                memory_bundle_path=bundle_path,
                allow_write_brief=True,
                allow_release_tag=False,
            )

    # Structured output validated via Pydantic
    assert envelope.report.verdict == "ready"
    assert envelope.report.score == 96
    assert envelope.report.repo_name == "demo-protocol"

    # Durable session & telemetry populated
    assert envelope.session_id == "release-guard-demo-protocol"
    assert envelope.run_id is not None
    assert envelope.stats.get("tool_calls", 0) >= 4
    assert envelope.stats.get("tool_errors", 0) == 0

    # READ_ONLY tools ran without prompting; ONLY write_release_brief hit approval_callback
    assert len(envelope.approvals) == 1
    assert envelope.approvals[0].tool_name == "write_release_brief"
    assert envelope.approvals[0].allowed is True

    # Both brief and portable MemoryBundle written to disk
    assert brief_path.is_file()
    assert "Verdict: READY" in brief_path.read_text(encoding="utf-8")
    loaded = load_bundle(bundle_path)
    assert len(loaded.items) == 1
    assert loaded.items[0]["verdict"] == "ready"


def test_security_subagent_and_submitted_stream(
    leaky_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise bounded subagent delegation and APIRuntime.submit_turn() streaming."""

    om_root = tmp_path / "om_home_stream"
    monkeypatch.setenv("OPENMINION_HOME", str(om_root))
    monkeypatch.setenv("OPENMINION_DATA_ROOT", str(om_root / ".openminion"))

    called = {"scan": False}

    def route(body: dict[str, Any], _idx: int) -> dict[str, Any]:
        tools = [
            t["function"]["name"]
            for t in body.get("tools", [])
            if isinstance(t, dict) and "function" in t
        ]
        if tools == ["submit_output"]:
            return make_text_reply("{}")
        if "scan_secret_hygiene" in tools and not called["scan"]:
            called["scan"] = True
            return make_tool_call_reply(
                "c_scan", "scan_secret_hygiene", {"repo_path": str(leaky_repo)}
            )
        return make_text_reply("Blocked: exposed .env and EVM private key detected in config.py.")

    with LocalOpenAIServer(route) as srv:
        cfg_path = write_openminion_config(om_root, openai_base_url=srv.base_url)
        with ReleaseGuardMinion(config_path=str(cfg_path), agent_id="auditor") as guard:
            summary = guard.run_security_subagent(leaky_repo)
            assert "private key" in summary.lower()
            assert called["scan"] is True

            # Exercise APIRuntime.submit_turn() typed streaming chunks
            handle = guard.runtime.submit_turn(
                payload={
                    "message": "Confirm audit session status.",
                    "agent_id": "auditor",
                    "session_id": "release-guard-stream-check",
                    "deliver": False,
                }
            )
            chunks = list(handle.stream())
            resp = handle.result(timeout_s=30.0)
            assert len(chunks) >= 1
            assert "private key" in resp.final_text.lower()
