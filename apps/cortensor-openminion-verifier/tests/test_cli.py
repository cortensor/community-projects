"""Tests for cortensor_verifier.cli.main() seam with real openminion runtime."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cortensor_verifier.cli import main
from cortensor_verifier.models import AuditRunBundle
from tests.conftest import LoopbackLLMServer, error_step, json_step, text_step, tool_calls_step


def test_cli_audit_by_claim_id_emits_audit_bundle_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    loopback_server: LoopbackLLMServer,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "cli-test-openai-token")
    loopback_server.enqueue(
        tool_calls_step(
            {
                "id": "call_cli_1",
                "name": "fetch_source_excerpt",
                "arguments": {"source_id": "sec-spot-btc-2024-01-10"},
            }
        ),
        json_step(
            {
                "verdict": "SUPPORTED",
                "confidence": 0.91,
                "rationale": "CLI loopback audit confirmed SEC approval order.",
                "citations": [
                    {
                        "source_id": "sec-spot-btc-2024-01-10",
                        "title": "Statement on the Approval of Spot Bitcoin Exchange-Traded Products",
                        "excerpt": "approved the listing and trading of a number of spot bitcoin exchange-traded product (ETP) shares on January 10, 2024.",
                    }
                ],
                "pass_role": "primary",
            }
        ),
    )

    home_root = tmp_path / "cli-home"
    data_root = tmp_path / "cli-state"
    out_file = tmp_path / "bundle.json"
    exit_code = main(
        [
            "audit",
            "--claim-id",
            "delphi-btc-etf-2024",
            "--preset",
            "openai-compatible",
            "--base-url",
            loopback_server.base_url,
            "--home-root",
            str(home_root),
            "--data-root",
            str(data_root),
            "--single-pass",
            "--output",
            str(out_file),
        ]
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    bundle = AuditRunBundle.model_validate_json(captured.out)
    assert bundle.claim_id == "delphi-btc-etf-2024"
    assert bundle.preset == "openai-compatible"
    assert bundle.consensus.final_verdict == "SUPPORTED"
    assert out_file.exists()
    assert json.loads(out_file.read_text(encoding="utf-8"))["claim_id"] == "delphi-btc-etf-2024"

    agents_json = (home_root / ".openminion" / "agents.json").read_text(encoding="utf-8")
    assert "cli-test-openai-token" not in agents_json


def test_cli_audit_by_dossier_file_with_cortensor_portal_preset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    loopback_server: LoopbackLLMServer,
) -> None:
    monkeypatch.setenv("CORTENSOR_API_KEY", "cli-test-cortensor-token")
    dossier_path = tmp_path / "custom_dossier.json"
    dossier_path.write_text(
        json.dumps(
            {
                "claim_id": "custom-001",
                "title": "Custom Test Claim",
                "claim": "Loopback test claim is verifiable.",
                "market_question": "Is the loopback test claim verified?",
                "resolution_criteria": "Verify from stub evidence.",
            }
        ),
        encoding="utf-8",
    )

    loopback_server.enqueue(
        json_step(
            {
                "verdict": "INCONCLUSIVE",
                "confidence": 0.45,
                "rationale": "Insufficient independent sources.",
                "citations": [],
                "pass_role": "primary",
            }
        )
    )

    exit_code = main(
        [
            "audit",
            "--dossier",
            str(dossier_path),
            "--preset",
            "cortensor-portal",
            "--base-url",
            loopback_server.base_url,
            "--single-pass",
            "--home-root",
            str(tmp_path / "home"),
            "--data-root",
            str(tmp_path / "state"),
        ]
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    bundle = AuditRunBundle.model_validate_json(captured.out)
    assert bundle.claim_id == "custom-001"
    assert bundle.preset == "cortensor-portal"
    assert bundle.consensus.final_verdict == "INCONCLUSIVE"
    assert bundle.consensus.requires_human_review is True


def test_cli_audit_returns_nonzero_on_provider_and_validation_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    loopback_server: LoopbackLLMServer,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "cli-test-openai-token")
    loopback_server.enqueue(text_step("not json"))
    rc_validation = main(
        [
            "audit",
            "--claim-id",
            "delphi-eth-dencun-blobs",
            "--base-url",
            loopback_server.base_url,
            "--single-pass",
            "--home-root",
            str(tmp_path / "h1"),
            "--data-root",
            str(tmp_path / "s1"),
            "--max-retries",
            "1",
        ]
    )
    assert rc_validation != 0
    err1 = capsys.readouterr().err
    assert "validation" in err1.lower() or "VerifierPassResult" in err1

    loopback_server.enqueue(error_step(status=500, message="Router crashed"))
    rc_provider = main(
        [
            "audit",
            "--claim-id",
            "delphi-eth-dencun-blobs",
            "--base-url",
            loopback_server.base_url,
            "--single-pass",
            "--home-root",
            str(tmp_path / "h2"),
            "--data-root",
            str(tmp_path / "s2"),
            "--max-retries",
            "1",
        ]
    )
    assert rc_provider != 0
    err2 = capsys.readouterr().err
    assert "provider" in err2.lower() or "error" in err2.lower()


def test_cli_audit_defaults_to_dual_pass_without_single_pass_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    loopback_server: LoopbackLLMServer,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "cli-test-openai-token")
    citation = {
        "source_id": "sec-spot-btc-2024-01-10",
        "title": "Statement on the Approval of Spot Bitcoin Exchange-Traded Products",
        "excerpt": "approved the listing and trading of spot bitcoin ETP shares.",
    }
    loopback_server.enqueue(
        json_step(
            {
                "verdict": "SUPPORTED",
                "confidence": 0.93,
                "rationale": "Corroborator pass verified order.",
                "citations": [citation],
                "pass_role": "corroborator",
            }
        ),
        json_step(
            {
                "verdict": "SUPPORTED",
                "confidence": 0.89,
                "rationale": "Skeptic pass found no contradicting filing.",
                "citations": [citation],
                "pass_role": "skeptic",
            }
        ),
    )

    rc = main(
        [
            "audit",
            "--claim-id",
            "delphi-btc-etf-2024",
            "--preset",
            "openai-compatible",
            "--base-url",
            loopback_server.base_url,
            "--home-root",
            str(tmp_path / "dual-home"),
            "--data-root",
            str(tmp_path / "dual-state"),
        ]
    )
    assert rc == 0
    bundle = AuditRunBundle.model_validate_json(capsys.readouterr().out)
    assert len(bundle.consensus.passes) == 2
    assert [p.pass_role for p in bundle.consensus.passes] == ["corroborator", "skeptic"]
    assert bundle.consensus.final_verdict == "SUPPORTED"
