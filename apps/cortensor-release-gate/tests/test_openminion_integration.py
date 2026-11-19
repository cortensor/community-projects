"""End-to-end integration tests exercising real OpenMinion 0.1.23 primitives."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from cortensor_release_gate.agent_workflow import (
    run_building_block_probes,
    run_release_gate,
)
from cortensor_release_gate.cli import app


def _seed_compliant_repo(root: Path) -> None:
    (root / "PROJECTS.yml").write_text(
        "- name: sample-app\n  category: apps\n  owner: '@alice'\n  status: active\n  version: v0.1.0\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        "# Sample App\nBuilt with OpenMinion 0.1 SDK.\n",
        encoding="utf-8",
    )
    (root / "STATUS.md").write_text("# Status\nActive.\n", encoding="utf-8")
    (root / "RELEASE.md").write_text("# Release\n## v0.1.0\n", encoding="utf-8")
    (root / "LICENSE").write_text("MIT License\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\ndependencies = ["openminion==0.1.23"]\n',
        encoding="utf-8",
    )
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "BUILDING_BLOCKS_TESTED.md").write_text("# Tested\n", encoding="utf-8")
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "app.py").write_text(
        'import openminion\nENDPOINT = "https://api.cortensor.app/v1"\n',
        encoding="utf-8",
    )
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "tests" / "test_app.py").write_text("def test_ok(): assert True\n", encoding="utf-8")


def test_release_gate_full_workflow_and_approval_gating(tmp_path: Path) -> None:
    repo = tmp_path / "sample_repo"
    repo.mkdir()
    _seed_compliant_repo(repo)
    # Introduce one blocker on run 1 (.env file) to trigger triage handoff and memory history.
    dotenv = repo / ".env"
    dotenv.write_text("TOKEN=placeholder\n", encoding="utf-8")

    out_dir = tmp_path / "artifacts"
    state_dir = tmp_path / "state"
    memory_file = tmp_path / "memory.json"

    # Run 1: decline approval -> report must NOT be written.
    declined_verdict = run_release_gate(
        target_dir=repo,
        output_dir=out_dir,
        state_root=state_dir,
        memory_path=memory_file,
        demo_local=True,
        write_report=True,
        approval_callback=lambda _t, _a, _id: False,
    )
    assert declined_verdict.decision == "BLOCKED"
    assert declined_verdict.triage_plan is not None
    assert len(declined_verdict.triage_plan.actions) >= 1
    assert declined_verdict.report_written is False
    assert not (out_dir / "RELEASE_GATE_REPORT.md").exists()

    # Remove blocker and run again with approval=True -> resolved_since_last_run tracks fix.
    dotenv.unlink()
    approved_verdict = run_release_gate(
        target_dir=repo,
        output_dir=out_dir,
        state_root=state_dir,
        memory_path=memory_file,
        demo_local=True,
        write_report=True,
        approval_callback=lambda _t, _a, _id: True,
    )
    assert approved_verdict.decision == "READY"
    assert approved_verdict.resolved_since_last_run == ["SEC-DOTENV-FILE"]
    assert approved_verdict.report_written is True
    assert (out_dir / "RELEASE_GATE_REPORT.md").is_file()
    summary_data = json.loads((out_dir / "release-gate-summary.json").read_text(encoding="utf-8"))
    assert summary_data["decision"] == "READY"


def test_building_block_probes_all_pass(tmp_path: Path) -> None:
    repo = tmp_path / "probe_repo"
    repo.mkdir()
    _seed_compliant_repo(repo)

    report = run_building_block_probes(
        target_dir=repo,
        state_root=tmp_path / "probe_state",
    )
    assert report.all_passed is True
    assert len(report.checks) == 10
    assert {c.block_name for c in report.checks} == {
        "runtime_diagnostics",
        "agent_tool_and_output_type",
        "subagent_isolation",
        "handoff_delegation",
        "approval_callback_gate",
        "memory_bundle_portability",
        "cortensor_completion_mode",
        "subagent_memory_guard",
        "forced_tools_and_capabilities",
        "session_continuity_turns",
    }


def test_cli_probe_and_audit_smoke(tmp_path: Path) -> None:
    repo = tmp_path / "cli_repo"
    repo.mkdir()
    _seed_compliant_repo(repo)
    out_dir = tmp_path / "cli_out"

    runner = CliRunner()
    probe_res = runner.invoke(
        app,
        ["probe", str(repo), "--state-root", str(tmp_path / "cli_probe_state"), "--json"],
    )
    assert probe_res.exit_code == 0, probe_res.output
    probe_payload = json.loads(probe_res.output)
    assert probe_payload["all_passed"] is True

    audit_res = runner.invoke(
        app,
        [
            "audit",
            str(repo),
            "--output-dir",
            str(out_dir),
            "--demo-local",
            "--write-report",
            "--yes",
            "--json",
        ],
    )
    assert audit_res.exit_code == 0, audit_res.output
    audit_payload = json.loads(audit_res.output)
    assert audit_payload["decision"] == "READY"
    assert audit_payload["report_written"] is True
