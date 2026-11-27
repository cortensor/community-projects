"""End-to-end OpenMinion 0.1.24 integration tests for NovaTriage Minion."""

import json
from pathlib import Path

from openminion import APIRuntime, Agent

from novatriage_minion.agent import run_novatriage_workflow
from novatriage_minion.local_model import (
    NovaTriageLocalModelServer,
    build_openminion_config_file,
)
from novatriage_minion.policy import NovaTriageApprovalGate
from novatriage_minion.tools import publish_emergency_freeze_notice


SAMPLES_DIR = Path(__file__).resolve().parents[1] / "samples"


def test_full_openminion_workflow_and_memory_recall(tmp_path: Path) -> None:
    # Run 1: VulnerableVault.sol -> CRITICAL BLOCK, writes report + MemoryBundle + Skill + Task
    summary1 = run_novatriage_workflow(
        workspace_dir=tmp_path,
        contract_path=SAMPLES_DIR / "VulnerableVault.sol",
        session_id="test-session-vault",
    )
    r1 = summary1.report
    assert r1.target_name == "VulnerableVault.sol"
    assert r1.overall_risk_score == 100
    assert r1.overall_risk_tier == "CRITICAL"
    assert r1.recommendation == "BLOCK"
    assert r1.solidity_audit.finding_count == 9
    assert r1.x402_probe is not None
    assert r1.x402_probe.challenge_status == 402
    assert r1.x402_probe.pay_to == "0x445F7447532d3e9300194E289C7C023A5f3CFc9E"
    assert len(r1.delegations) == 3
    assert summary1.stream_events_seen > 0
    assert "FLOATING_OR_LEGACY_PRAGMA@L2" in summary1.followup_reply
    assert summary1.skill_summary["skill_id"] == "novatriage_solidity_audit"
    assert "novatriage_solidity_audit" in summary1.skill_summary["matched_ids"]
    assert summary1.memory_summary["item_count"] == 1
    assert summary1.task_summary["visible_task_count"] >= 1
    assert summary1.diagnostics["tool_inventory_count"] >= 50
    assert summary1.diagnostics["session_db_exists"] is True
    assert summary1.written_report_path is not None
    assert Path(summary1.written_report_path).exists()
    assert [d["decision"] for d in summary1.approval_decisions] == [
        "approved",
        "approved",
        "approved",
    ]

    # Run 2: SafeTreasury.sol in same workspace recalls MemoryBundle and scores MINIMAL CLEAR
    summary2 = run_novatriage_workflow(
        workspace_dir=tmp_path,
        contract_path=SAMPLES_DIR / "SafeTreasury.sol",
        session_id="test-session-safe",
        schedule_watchlist=False,
    )
    assert summary2.report.overall_risk_score == 0
    assert summary2.report.overall_risk_tier == "MINIMAL"
    assert summary2.report.recommendation == "CLEAR"
    assert summary2.memory_summary["item_count"] == 2
    assert len(summary2.report.memory_hits) >= 1


def test_approval_gate_single_use_and_dangerous_denial(tmp_path: Path) -> None:
    gate = NovaTriageApprovalGate(allow_report_write=True, allow_dangerous_freeze=False)
    assert gate("write_triage_report", {}, "id-1") is True
    assert gate("write_triage_report", {}, "id-2") is False
    assert gate("publish_emergency_freeze_notice", {}, "id-3") is False
    assert gate("unknown_tool", {}, "id-4") is False
    assert [d.reason for d in gate.decisions] == [
        "single_use_write_report_approved",
        "single_use_write_already_consumed",
        "destructive_freeze_denied_by_default",
        "fail_closed_unknown_or_unapproved_tool",
    ]

    # Exercise dangerous=True denial inside live OpenMinion Agent.run()
    with NovaTriageLocalModelServer.start() as srv:
        cfg_path = build_openminion_config_file(
            tmp_path / "cfg.json",
            provider="local",
            local_base_url=srv.base_url,
        )
        rt = APIRuntime.from_config_path(
            str(cfg_path),
            home_root=str(tmp_path / "h"),
            data_root=str(tmp_path / "d"),
        )
        try:
            freeze_gate = NovaTriageApprovalGate(allow_dangerous_freeze=False)
            agent = Agent(
                runtime=rt,
                name="freeze_tester",
                tools=[publish_emergency_freeze_notice],
                instructions="Test dangerous tool gating.",
            )
            res = agent.run(
                "TEST_FREEZE_ESCALATION target_name=VulnerableVault.sol",
                approval_callback=freeze_gate,
            )
            assert "Confirmation denied" in res.text
            assert any(
                d.tool_name == "publish_emergency_freeze_notice" and d.decision == "denied"
                for d in freeze_gate.decisions
            )
        finally:
            rt.close()
