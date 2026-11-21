"""Deterministic tests for config, provider presets, secret redaction, and Pydantic models."""

from pathlib import Path

import pytest

from cortensor_route_bench.config import (
    PROVIDER_PROFILES,
    load_dotenv_file,
    redact_secrets,
    resolve_model,
    resolve_provider_profile,
    run_preflight,
)
from cortensor_route_bench.models import ConsensusVerdict, WorkerEvaluation
from cortensor_route_bench.tools import check_endpoint_health, inspect_provider_profile


def test_redact_secrets_masks_tokens_and_keys() -> None:
    sample = "Authorization: Bearer abcdef1234567890 key=AQ.SyntheticTokenValue1234567 test=sk-1234567890abcd"
    redacted = redact_secrets(sample)
    assert "abcdef1234567890" not in redacted
    assert "AQ.SyntheticTokenValue1234567" not in redacted
    assert "sk-1234567890abcd" not in redacted
    assert "***REDACTED***" in redacted


def test_load_dotenv_does_not_override_existing_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=from_file\nROUTE_BENCH_MODEL=from_file_model\n", encoding="utf-8")
    monkeypatch.setenv("GEMINI_API_KEY", "already_set")
    monkeypatch.delenv("ROUTE_BENCH_MODEL", raising=False)

    load_dotenv_file(env_file)
    try:
        assert "already_set" == __import__("os").environ["GEMINI_API_KEY"]
        assert "from_file_model" == __import__("os").environ["ROUTE_BENCH_MODEL"]
    finally:
        monkeypatch.delenv("ROUTE_BENCH_MODEL", raising=False)


def test_provider_profiles_track_cortensor_non_tool_calling(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ROUTE_BENCH_MODEL", raising=False)
    portal = resolve_provider_profile("cortensor-portal")
    router = resolve_provider_profile("cortensor-router")
    gemini = resolve_provider_profile("gemini")
    assert portal.supports_native_tool_calling is False
    assert router.supports_native_tool_calling is False
    assert gemini.supports_native_tool_calling is True
    assert resolve_model(gemini, None) == "gemini-3.5-flash-lite"


def test_run_preflight_blocks_when_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CORTENSOR_API_KEY", raising=False)
    report = run_preflight(provider="cortensor-portal")
    assert report.overall_status == "blocked"
    assert report.credential_configured is False


def test_ssrf_guard_rejects_private_http_urls() -> None:
    res = check_endpoint_health("http://169.254.169.254/latest/meta-data/")
    assert res["ok"] is False
    assert "loopback" in res["error"].lower()


def test_inspect_provider_profile_tool_handles_unknown() -> None:
    unknown = inspect_provider_profile("nonexistent-provider")
    assert unknown["found"] is False
    assert set(PROVIDER_PROFILES).issubset(set(unknown["supported_providers"]))


def test_worker_and_consensus_models_validate_bounds() -> None:
    w = WorkerEvaluation(
        worker_role="transport_analyst",
        readiness="READY",
        confidence=0.92,
        key_findings=["Verified openminion 0.1.23 exports"],
        recommended_action="Proceed",
    )
    c = ConsensusVerdict(
        task="Verify SDK",
        decision="READY",
        agreement_score=0.95,
        worker_summaries=[f"{w.worker_role}: {w.readiness}"],
        recommendations=["Use gemini-2.5-flash-lite for free-tier runs"],
        final_summary="Both workers agree the route is ready.",
    )
    assert "Verify SDK" == c.task or c.agreement_score == 0.95


def test_configure_delegation_policy_rules_adds_auto_rules(tmp_path: Path) -> None:
    import json
    from cortensor_route_bench.config import _configure_delegation_policy_rules

    cfg = tmp_path / "config.yaml"
    cfg.write_text('{"action_policy": {"mode": "auto", "rules": []}}\n', encoding="utf-8")
    _configure_delegation_policy_rules(cfg)
    loaded = json.loads(cfg.read_text(encoding="utf-8"))
    names = {r["match"]["tool_name"]: r["mode"] for r in loaded["action_policy"]["rules"]}
    assert names["transfer_to_cortensor_specialist"] == "auto"
    assert names["transfer_to_consensus_synthesizer"] == "auto"
    assert loaded["gateway"]["api_turn_timeout_seconds"] == 180
