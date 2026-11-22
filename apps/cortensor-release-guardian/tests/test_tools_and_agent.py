"""Automated unit and OpenMinion runtime tests for Cortensor Release Guardian."""

from __future__ import annotations

import json
from pathlib import Path

from release_guardian.agent import collect_deterministic_evidence, run_followup, run_release_audit
from release_guardian.tools import (
    check_openminion_config,
    run_syntax_audit,
    scan_repo_structure,
    scan_secret_leaks,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_scan_repo_structure_passes_on_self() -> None:
    data = json.loads(scan_repo_structure(str(REPO_ROOT)))
    assert data["ok"] is True
    assert data["checks"]["has_readme"] is True
    assert data["checks"]["has_license"] is True
    assert data["checks"]["has_tests_dir"] is True
    assert data["checks"]["has_building_blocks_doc"] is True
    assert data["checks"]["has_what_we_learned_doc"] is True
    assert data["missing"] == []


def test_scan_secret_leaks_clean_on_self() -> None:
    data = json.loads(scan_secret_leaks(str(REPO_ROOT)))
    assert data["ok"] is True
    assert data["clean"] is True
    assert data["finding_count"] == 0


def test_scan_secret_leaks_catches_hardcoded_key_and_env(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("SECRET=12345\n", encoding="utf-8")
    fake_key = "sk-" + "1234567890" + "abcdefghijklmnop"
    (tmp_path / "leaky.py").write_text(f'API = "{fake_key}"\n', encoding="utf-8")
    data = json.loads(scan_secret_leaks(str(tmp_path)))
    assert data["ok"] is True
    assert data["clean"] is False
    kinds = {f["kind"] for f in data["findings"]}
    assert "Committed .env file" in kinds
    assert "OpenAI/Stripe-like secret key" in kinds


def test_run_syntax_audit_detects_broken_python(tmp_path: Path) -> None:
    (tmp_path / "broken.py").write_text("def bad(:\n    pass\n", encoding="utf-8")
    data = json.loads(run_syntax_audit(str(tmp_path)))
    assert data["ok"] is True
    assert data["syntax_clean"] is False
    assert data["errors"][0]["file"] == "broken.py"


def test_check_openminion_config_flags_unsafe_settings(tmp_path: Path) -> None:
    bad_cfg = tmp_path / "agents.bad.json"
    bad_cfg.write_text(
        json.dumps(
            {
                "default_agent": "missing-agent",
                "action_policy": {"mode": "bypass"},
                "agents": {
                    "dev": {
                        "provider": "openai",
                        "api_key": "sk-" + "literal-secret-value-not-env",
                        "permission_mode": "bypass",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    data = json.loads(check_openminion_config(str(bad_cfg)))
    assert data["ok"] is True
    assert data["safe"] is False
    assert len(data["warnings"]) >= 3


def test_openminion_echo_runtime_audit_and_session(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENMINION_HOME", str(tmp_path))
    monkeypatch.setenv("OPENMINION_DATA_ROOT", str(tmp_path / ".openminion"))
    echo_cfg = REPO_ROOT / "configs" / "agents.echo.json"

    report = run_release_audit(
        repo_path=str(REPO_ROOT),
        config_path=str(echo_cfg),
        session_id="pytest-guardian-session",
        use_tools=True,
    )
    assert report["session_id"] == "pytest-guardian-session"
    assert report["baseline_evidence"]["secret_leaks"]["clean"] is True
    assert report["baseline_evidence"]["syntax_audit"]["syntax_clean"] is True
    assert isinstance(report["text"], str) and len(report["text"]) > 0

    follow = run_followup(
        question="Summarize the top release risk.",
        config_path=str(echo_cfg),
        session_id="pytest-guardian-session",
    )
    assert follow["session_id"] == "pytest-guardian-session"
    assert isinstance(follow["text"], str) and len(follow["text"]) > 0


def test_collect_deterministic_evidence() -> None:
    ev = collect_deterministic_evidence(str(REPO_ROOT), str(REPO_ROOT / "configs" / "agents.ollama.json"))
    assert ev["openminion_config"]["safe"] is True
    assert ev["syntax_audit"]["syntax_clean"] is True
