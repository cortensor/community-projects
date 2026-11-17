"""Tests for read-only verifier tools and ConsensusAuditor.audit_claim(single_pass=True) seam."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from openminion.api import AgentOutputValidationError, ProviderError
from openminion.tools import tool

from cortensor_verifier.auditor import ConsensusAuditor
from cortensor_verifier.models import AuditRunBundle, VerifierPassResult
from cortensor_verifier.tools import (
    READ_ONLY_VERIFIER_TOOLS,
    fetch_source_excerpt,
    load_claim_dossier,
    load_delphi_market_fixture,
    search_public_evidence,
)
from tests.conftest import (
    LoopbackLLMServer,
    error_step,
    json_step,
    text_step,
    tool_calls_step,
)


def test_tools_declare_read_only_and_idempotent_metadata() -> None:
    expected_names = {
        "load_delphi_market_fixture",
        "search_public_evidence",
        "fetch_source_excerpt",
        "fetch_public_url_excerpt",
    }
    assert {fn.tool_decl.name for fn in READ_ONLY_VERIFIER_TOOLS} == expected_names
    for fn in READ_ONLY_VERIFIER_TOOLS:
        assert fn.tool_decl.min_scope == "READ_ONLY"
        assert fn.tool_decl.idempotent is True
        assert fn.tool_decl.dangerous is False

    dossier = load_claim_dossier("delphi-btc-etf-2024")
    assert dossier.claim_id == "delphi-btc-etf-2024"
    assert "SEC" in dossier.claim


def test_auditor_rejects_non_read_only_tools(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-token")

    @tool(min_scope="WRITE_SAFE", idempotent=False)
    def mutating_tool(path: str) -> str:
        return path

    with pytest.raises(ValueError, match="READ_ONLY"):
        ConsensusAuditor(
            preset="openai-compatible",
            base_url="http://127.0.0.1:9999/v1",
            home_root=tmp_path / "home",
            data_root=tmp_path / "state",
            tools=[load_delphi_market_fixture, mutating_tool],
        )


def test_audit_single_pass_roundtrips_read_only_tools_and_validates_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    loopback_server: LoopbackLLMServer,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-token")
    dossier = load_claim_dossier("delphi-btc-etf-2024")

    loopback_server.enqueue(
        tool_calls_step(
            {
                "id": "call_fixture",
                "name": "load_delphi_market_fixture",
                "arguments": {"claim_id": "delphi-btc-etf-2024"},
            },
            {
                "id": "call_search",
                "name": "search_public_evidence",
                "arguments": {"query": "SEC spot bitcoin approval January 10 2024", "limit": 3},
            },
        ),
        tool_calls_step(
            {
                "id": "call_excerpt",
                "name": "fetch_source_excerpt",
                "arguments": {"source_id": "sec-spot-btc-2024-01-10"},
            }
        ),
        json_step(
            {
                "verdict": "SUPPORTED",
                "confidence": 0.96,
                "rationale": "SEC statement and Release 34-99306 confirm spot Bitcoin ETP approval on 2024-01-10.",
                "citations": [
                    {
                        "source_id": "sec-spot-btc-2024-01-10",
                        "title": "Statement on the Approval of Spot Bitcoin Exchange-Traded Products",
                        "url": "https://www.sec.gov/newsroom/speeches-statements/gensler-statement-spot-bitcoin-011023",
                        "excerpt": "Today, the Commission approved the listing and trading of a number of spot bitcoin exchange-traded product (ETP) shares on January 10, 2024.",
                        "published_at": "2024-01-10",
                    }
                ],
                "pass_role": "primary",
            }
        ),
    )

    with ConsensusAuditor(
        preset="openai-compatible",
        base_url=loopback_server.base_url,
        home_root=tmp_path / "home",
        data_root=tmp_path / "state",
        provider_retry_max_attempts=1,
    ) as auditor:
        pass_result = auditor.audit_claim(dossier, single_pass=True).consensus.passes[0]

    assert isinstance(pass_result, VerifierPassResult)
    assert pass_result.verdict == "SUPPORTED"
    assert pass_result.confidence == pytest.approx(0.96)
    assert pass_result.pass_role == "primary"
    assert len(pass_result.citations) == 1
    assert pass_result.citations[0].source_id == "sec-spot-btc-2024-01-10"

    verifier_requests = [
        req
        for req in loopback_server.requests
        if req.body.get("tool_choice")
        != {"type": "function", "function": {"name": "submit_output"}}
    ]
    assert len(verifier_requests) == 3
    first_tools = {
        item["function"]["name"]
        for item in verifier_requests[0].body.get("tools", [])
        if isinstance(item, dict) and isinstance(item.get("function"), dict)
    }
    assert {
        "load_delphi_market_fixture",
        "search_public_evidence",
        "fetch_source_excerpt",
    }.issubset(first_tools)

    third_messages = verifier_requests[2].body.get("messages", [])
    tool_outputs = [
        str(msg.get("content", ""))
        for msg in third_messages
        if isinstance(msg, dict) and msg.get("role") == "tool"
    ]
    assert len(tool_outputs) >= 3
    joined = "\n".join(tool_outputs)
    assert "delphi-btc-etf-2024" in joined
    assert "sec-spot-btc-2024-01-10" in joined
    assert "spot bitcoin exchange-traded product" in joined


def test_audit_claim_returns_audit_run_bundle_with_tool_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    loopback_server: LoopbackLLMServer,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-token")
    dossier = load_claim_dossier("delphi-falsified-quantum-rsa2048")

    loopback_server.enqueue(
        tool_calls_step(
            {
                "id": "call_search_1",
                "name": "search_public_evidence",
                "arguments": {"query": "NIST RSA-2048 100-qubit", "limit": 2},
            }
        ),
        json_step(
            {
                "verdict": "REFUTED",
                "confidence": 0.94,
                "rationale": "NIST post-quantum announcement confirms no 100-qubit machine factored RSA-2048.",
                "citations": [
                    {
                        "source_id": "nist-fips-203-204-205-2024",
                        "title": "NIST Releases First 3 Finalized Post-Quantum Encryption Standards",
                        "excerpt": "no 100-qubit NISQ device has factored RSA-2048",
                    }
                ],
                "pass_role": "primary",
            }
        ),
    )

    with ConsensusAuditor(
        preset="openai-compatible",
        base_url=loopback_server.base_url,
        home_root=tmp_path / "home",
        data_root=tmp_path / "state",
        provider_retry_max_attempts=1,
    ) as auditor:
        bundle = auditor.audit_claim(dossier, single_pass=True)

    assert isinstance(bundle, AuditRunBundle)
    assert bundle.claim_id == dossier.claim_id
    assert bundle.consensus.final_verdict == "REFUTED"
    assert bundle.consensus.agreement_score == pytest.approx(1.0)
    assert "search_public_evidence" in bundle.tool_calls


def test_audit_single_pass_propagates_validation_error_on_malformed_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    loopback_server: LoopbackLLMServer,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-token")
    dossier = load_claim_dossier("delphi-eth-dencun-blobs")
    loopback_server.enqueue(text_step("NOT VALID JSON {{{"))

    with ConsensusAuditor(
        preset="openai-compatible",
        base_url=loopback_server.base_url,
        home_root=tmp_path / "home",
        data_root=tmp_path / "state",
        provider_retry_max_attempts=1,
    ) as auditor:
        with pytest.raises(AgentOutputValidationError):
            auditor.audit_claim(dossier, single_pass=True)


def test_audit_single_pass_propagates_provider_error_on_500_and_unreachable_port(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    loopback_server: LoopbackLLMServer,
    unused_loopback_url: str,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-token")
    dossier = load_claim_dossier("delphi-eth-dencun-blobs")

    loopback_server.enqueue(error_step(status=500, message="Simulated 500 error"))
    with ConsensusAuditor(
        preset="openai-compatible",
        base_url=loopback_server.base_url,
        home_root=tmp_path / "home-500",
        data_root=tmp_path / "state-500",
        provider_retry_max_attempts=1,
    ) as auditor_500:
        with pytest.raises(ProviderError):
            auditor_500.audit_claim(dossier, single_pass=True)

    with ConsensusAuditor(
        preset="openai-compatible",
        base_url=unused_loopback_url,
        home_root=tmp_path / "home-down",
        data_root=tmp_path / "state-down",
        provider_retry_max_attempts=1,
        timeout_seconds=5,
    ) as auditor_down:
        with pytest.raises(ProviderError):
            auditor_down.audit_claim(dossier, single_pass=True)
