"""Tests for Pydantic domain models and isolated openminion runtime presets."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from openminion.api import APIRuntime, Agent
from pydantic import ValidationError

from cortensor_verifier.models import (
    AuditRunBundle,
    ClaimDossier,
    ConsensusVerdict,
    EvidenceCitation,
    ProbeCheckResult,
    VerifierPassResult,
)
from cortensor_verifier.runtime_factory import (
    PROVIDER_PRESETS,
    build_isolated_config,
    create_isolated_runtime,
)
from tests.conftest import LoopbackLLMServer, json_step


def test_models_validate_domain_contracts() -> None:
    citation = EvidenceCitation(
        source_id="src-1",
        title="Official Release Notes",
        url="https://example.org/release",
        excerpt="Mainnet v1.2 shipped on 2026-10-01.",
    )
    dossier = ClaimDossier(
        claim_id="claim-001",
        title="Mainnet launch date",
        claim="Protocol v1.2 launched on October 1, 2026.",
        market_question="Did Protocol v1.2 launch on or before Oct 1, 2026?",
        resolution_criteria="Requires official release tag dated <= 2026-10-01 UTC.",
        tags=["release", "milestone"],
        metadata={"market_slug": "protocol-v1-2"},
    )
    pass_result = VerifierPassResult(
        verdict="SUPPORTED",
        confidence=0.92,
        rationale="Official release notes confirm launch date.",
        citations=[citation],
        pass_role="primary",
    )
    consensus = ConsensusVerdict(
        claim_id=dossier.claim_id,
        final_verdict="SUPPORTED",
        agreement_score=1.0,
        mean_confidence=0.92,
        disagreement_summary="Single pass verified.",
        passes=[pass_result],
        requires_human_review=False,
    )
    bundle = AuditRunBundle(
        claim_id=dossier.claim_id,
        preset="openai-compatible",
        dossier=dossier,
        consensus=consensus,
        tool_calls=["load_delphi_market_fixture"],
        run_id="run-1",
        session_id="sess-1",
    )
    probe = ProbeCheckResult(
        probe_id="probe-1",
        name="structured-output",
        passed=True,
        detail="Validated JSON schema",
        latency_ms=12.4,
    )

    assert bundle.consensus.final_verdict == "SUPPORTED"
    assert probe.passed is True

    with pytest.raises(ValidationError):
        VerifierPassResult(
            verdict="MAYBE",  # type: ignore[arg-type]
            confidence=0.5,
            rationale="Invalid verdict",
        )

    with pytest.raises(ValidationError):
        VerifierPassResult(
            verdict="SUPPORTED",
            confidence=1.5,
            rationale="Confidence out of bounds",
        )


@pytest.mark.parametrize("preset", PROVIDER_PRESETS)
def test_build_isolated_config_persists_zero_plaintext_secrets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    preset: str,
) -> None:
    secret_openai = "sk-test-secret-openai-value-999"
    secret_cortensor = "cs-test-secret-cortensor-value-999"
    monkeypatch.setenv("OPENAI_API_KEY", secret_openai)
    monkeypatch.setenv("CORTENSOR_API_KEY", secret_cortensor)

    home_root = tmp_path / "isolated-home"
    data_root = tmp_path / "isolated-state"
    config_path = home_root / ".openminion" / "agents.json"

    cfg = build_isolated_config(
        preset=preset,
        base_url="http://127.0.0.1:9999/v1" if preset != "cortensor-router" else "http://127.0.0.1:9999/api/v2/completions",
        config_path=config_path,
        data_root=data_root,
    )

    assert config_path.exists()
    raw_text = config_path.read_text(encoding="utf-8")
    assert secret_openai not in raw_text
    assert secret_cortensor not in raw_text

    persisted = json.loads(raw_text)
    assert persisted["providers"]["openai"]["api_key"] == ""
    assert persisted["providers"]["cortensor"]["api_key"] == ""
    assert persisted["runtime"]["env"] == {}
    expected_openai_env = "CORTENSOR_API_KEY" if preset == "cortensor-portal" else "OPENAI_API_KEY"
    assert persisted["providers"]["openai"]["api_key_env"] == expected_openai_env
    assert persisted["providers"]["cortensor"]["api_key_env"] == "CORTENSOR_API_KEY"

    storage_path = Path(cfg.storage.path)
    assert storage_path.is_relative_to(data_root) or not storage_path.is_absolute()


def test_unknown_preset_raises_value_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown preset"):
        build_isolated_config(
            preset="nonexistent-preset",
            config_path=tmp_path / "agents.json",
            data_root=tmp_path / "state",
        )


@pytest.mark.parametrize(
    ("preset", "expected_path", "env_var", "expected_token"),
    [
        ("openai-compatible", "/v1/chat/completions", "OPENAI_API_KEY", "test-openai-token"),
        ("cortensor-portal", "/v1/chat/completions", "CORTENSOR_API_KEY", "test-portal-token"),
        ("cortensor-router", "/api/v2/completions", "CORTENSOR_API_KEY", "test-router-token"),
    ],
)
def test_create_isolated_runtime_drives_real_agent_across_presets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    loopback_server: LoopbackLLMServer,
    preset: str,
    expected_path: str,
    env_var: str,
    expected_token: str,
) -> None:
    monkeypatch.setenv(env_var, expected_token)
    base_url = (
        loopback_server.router_url if preset == "cortensor-router" else loopback_server.base_url
    )
    loopback_server.enqueue(
        json_step(
            {
                "verdict": "SUPPORTED",
                "confidence": 0.88,
                "rationale": f"Verified cleanly under preset {preset}.",
                "citations": [
                    {
                        "source_id": "src-loopback",
                        "title": "Loopback Source",
                        "excerpt": "Confirmed evidence.",
                    }
                ],
                "pass_role": "primary",
            }
        )
    )

    home_root = tmp_path / "home"
    data_root = tmp_path / "state"
    runtime = create_isolated_runtime(
        preset=preset,
        base_url=base_url,
        home_root=home_root,
        data_root=data_root,
        provider_retry_max_attempts=1,
    )
    try:
        assert isinstance(runtime, APIRuntime)
        config_text = (home_root / ".openminion" / "agents.json").read_text(encoding="utf-8")
        assert expected_token not in config_text

        agent = Agent(
            runtime=runtime,
            agent_id="verifier",
            instructions="Return JSON matching VerifierPassResult.",
            output_type=VerifierPassResult,
        )
        result = agent.run("Verify the sample claim and output JSON.")
        assert isinstance(result.output, VerifierPassResult)
        assert result.output.verdict == "SUPPORTED"
        assert result.output.confidence == pytest.approx(0.88)
        assert loopback_server.requests
        assert loopback_server.requests[0].path == expected_path
    finally:
        runtime.close()
