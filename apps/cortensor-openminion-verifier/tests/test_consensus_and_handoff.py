"""Real-runtime TDD tests for C2: dual-pass consensus, sessions/MemoryBundle, Handoff approval, telemetry, and CLI."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest
from openminion.modules.memory.portability import export_bundle, load_bundle

import tests.conftest as test_conftest
from cortensor_verifier.auditor import ConsensusAuditor
from cortensor_verifier.cli import main as cli_main
from cortensor_verifier.models import AuditRunBundle, ClaimDossier, ConsensusVerdict
from cortensor_verifier.tools import (
    assert_read_only_tools,
    load_claim_dossier,
    publish_consensus_verdict,
)
from tests.conftest import LoopbackLLMServer, json_step, text_step, tool_calls_step


_ACTION_SUMMARY_RE = re.compile(
    r"(?:^|\n)action_summary:\s*(.*?)(?=\n(?:closure_action_outputs|sub_intents|intent_outcomes|success_criteria):|\n\[|\Z)",
    re.DOTALL,
)


def _extract_closure_action_summary(request_body: dict[str, Any]) -> str:
    for msg in request_body.get("messages") or []:
        if not isinstance(msg, dict):
            continue
        content = str(msg.get("content") or "")
        match = _ACTION_SUMMARY_RE.search(content)
        if match:
            candidate = match.group(1).strip()
            if candidate:
                return candidate
    return "Action completed."


@pytest.fixture(autouse=True)
def _handle_closure_judgment_classifier(monkeypatch: pytest.MonkeyPatch) -> None:
    """Extend LoopbackLLMServer's internal classifier stub to also handle ClosureJudgment."""
    targets = []
    for mod_name in ("conftest", "tests.conftest"):
        mod = sys.modules.get(mod_name)
        if mod is not None and mod not in targets:
            targets.append(mod)
    if test_conftest not in targets:
        targets.append(test_conftest)
    original = targets[0]._maybe_internal_classifier_step

    def _wrapped(request_body: dict[str, Any]) -> dict[str, Any] | None:
        base = original(request_body)
        if base is not None:
            return base
        tool_choice = request_body.get("tool_choice")
        if not isinstance(tool_choice, dict):
            return None
        fn = tool_choice.get("function")
        if not isinstance(fn, dict) or fn.get("name") != "submit_output":
            return None
        tools = request_body.get("tools") or []
        schema_title = ""
        if tools and isinstance(tools[0], dict):
            schema_title = str(
                tools[0].get("function", {}).get("parameters", {}).get("title", "")
            )
        if schema_title == "ClosureJudgment":
            return {
                "type": "tool_calls",
                "calls": [
                    {
                        "id": "call_closure_1",
                        "name": "submit_output",
                        "arguments": {
                            "satisfied": True,
                            "reason": "Tool execution completed cleanly.",
                            "next_action": "close",
                            "final_answer": _extract_closure_action_summary(request_body),
                        },
                    }
                ],
            }
        return None

    for mod in targets:
        monkeypatch.setattr(mod, "_maybe_internal_classifier_step", _wrapped)


def _make_auditor(
    tmp_path: Path,
    server: LoopbackLLMServer,
    *,
    name: str = "auditor",
    **extra_kwargs: Any,
) -> ConsensusAuditor:
    root = tmp_path / name
    return ConsensusAuditor(
        preset="openai-compatible",
        base_url=server.base_url,
        model="stub-verifier-model",
        api_key_env="OPENAI_API_KEY",
        home_root=root / "home",
        data_root=root / "data",
        **extra_kwargs,
    )


def _btc_dossier() -> ClaimDossier:
    return load_claim_dossier("delphi-btc-etf-2024")


def _pass_payload(
    *,
    claim_id: str,
    pass_role: str,
    verdict: str,
    confidence: float,
    rationale: str,
    source_id: str = "sec-spot-btc-2024-01-10",
    title: str = "Statement on the Approval of Spot Bitcoin Exchange-Traded Products",
    url: str = "https://www.sec.gov/newsroom/speeches-statements/gensler-statement-spot-bitcoin-011023",
    quote: str = "Today, the Commission approved the listing and trading of a number of spot bitcoin exchange-traded product (ETP) shares on January 10, 2024.",
) -> dict[str, Any]:
    del claim_id
    return {
        "pass_role": pass_role,
        "verdict": verdict,
        "confidence": confidence,
        "rationale": rationale,
        "citations": [
            {
                "source_id": source_id,
                "title": title,
                "url": url,
                "excerpt": quote,
                "published_at": "2024-01-10",
            }
        ],
    }


def _enqueue_dual_pass_agreement(
    server: LoopbackLLMServer,
    *,
    claim_id: str = "delphi-btc-etf-2024",
    corr_conf: float = 0.92,
    skep_conf: float = 0.84,
) -> None:
    server.enqueue(
        tool_calls_step(
            {
                "id": "call_corr_1",
                "name": "search_public_evidence",
                "arguments": {"query": "SEC spot bitcoin ETP"},
            }
        )
    )
    server.enqueue(
        json_step(
            _pass_payload(
                claim_id=claim_id,
                pass_role="corroborator",
                verdict="SUPPORTED",
                confidence=corr_conf,
                rationale="Corroborator confirmed SEC release 34-99306 approval.",
            )
        )
    )
    server.enqueue(
        tool_calls_step(
            {
                "id": "call_skep_1",
                "name": "fetch_source_excerpt",
                "arguments": {"source_id": "sec-spot-btc-2024-01-10"},
            }
        )
    )
    server.enqueue(
        json_step(
            _pass_payload(
                claim_id=claim_id,
                pass_role="skeptic",
                verdict="SUPPORTED",
                confidence=skep_conf,
                rationale="Skeptic found no primary contradiction in SEC order.",
            )
        )
    )


def test_dual_pass_subagents_agreement_synthesizes_consensus(
    tmp_path: Path,
    loopback_server: LoopbackLLMServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "stub-key")
    dossier = _btc_dossier()
    _enqueue_dual_pass_agreement(loopback_server, corr_conf=0.92, skep_conf=0.84)

    with _make_auditor(tmp_path, loopback_server) as auditor:
        bundle = auditor.audit_claim(dossier, single_pass=False)

    assert isinstance(bundle, AuditRunBundle)
    assert isinstance(bundle.consensus, ConsensusVerdict)
    assert [p.pass_role for p in bundle.consensus.passes] == ["corroborator", "skeptic"]
    assert bundle.consensus.final_verdict == "SUPPORTED"
    assert bundle.consensus.requires_human_review is False
    assert bundle.consensus.agreement_score == pytest.approx(1.0 - abs(0.92 - 0.84) * 0.5)
    assert bundle.consensus.mean_confidence == pytest.approx(0.88)
    assert "search_public_evidence" in bundle.tool_calls
    assert "fetch_source_excerpt" in bundle.tool_calls

    system_prompts = [
        " ".join(
            str(m.get("content", ""))
            for m in req.body.get("messages", [])
            if m.get("role") == "system"
        ).lower()
        for req in loopback_server.requests
    ]
    assert any("corroborator" in text for text in system_prompts)
    assert any("skeptic" in text for text in system_prompts)


def test_dual_pass_conflict_flags_inconclusive_and_human_review(
    tmp_path: Path,
    loopback_server: LoopbackLLMServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "stub-key")
    dossier = _btc_dossier()

    loopback_server.enqueue(
        json_step(
            _pass_payload(
                claim_id=dossier.claim_id,
                pass_role="corroborator",
                verdict="SUPPORTED",
                confidence=0.90,
                rationale="Primary SEC filing supports Jan 10 approval.",
            )
        )
    )
    loopback_server.enqueue(
        json_step(
            _pass_payload(
                claim_id=dossier.claim_id,
                pass_role="skeptic",
                verdict="REFUTED",
                confidence=0.85,
                rationale="Counter-evidence indicates trading did not settle on that date.",
            )
        )
    )

    with _make_auditor(tmp_path, loopback_server) as auditor:
        bundle = auditor.audit_claim(dossier, single_pass=False)

    assert bundle.consensus.final_verdict == "INCONCLUSIVE"
    assert bundle.consensus.requires_human_review is True
    assert 0.0 <= bundle.consensus.agreement_score <= 0.30
    assert bundle.consensus.mean_confidence == pytest.approx(0.875)
    summary_lower = bundle.consensus.disagreement_summary.lower()
    assert "corroborator" in summary_lower and "supported" in summary_lower
    assert "skeptic" in summary_lower and "refuted" in summary_lower


def test_dual_pass_large_confidence_gap_triggers_human_review(
    tmp_path: Path,
    loopback_server: LoopbackLLMServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "stub-key")
    dossier = _btc_dossier()

    loopback_server.enqueue(
        json_step(
            _pass_payload(
                claim_id=dossier.claim_id,
                pass_role="corroborator",
                verdict="SUPPORTED",
                confidence=0.95,
                rationale="Strong primary match.",
            )
        )
    )
    loopback_server.enqueue(
        json_step(
            _pass_payload(
                claim_id=dossier.claim_id,
                pass_role="skeptic",
                verdict="SUPPORTED",
                confidence=0.40,
                rationale="Weak corroborating coverage outside main citation.",
            )
        )
    )

    with _make_auditor(tmp_path, loopback_server) as auditor:
        bundle = auditor.audit_claim(dossier, single_pass=False)

    assert bundle.consensus.final_verdict == "INCONCLUSIVE"
    assert bundle.consensus.requires_human_review is True
    assert bundle.consensus.agreement_score == pytest.approx(1.0 - (0.95 - 0.40) * 0.5)
    assert "gap" in bundle.consensus.disagreement_summary.lower()


def test_session_continuity_memory_bundle_portability_and_cross_session_isolation(
    tmp_path: Path,
    loopback_server: LoopbackLLMServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "stub-key")
    dossier_a1 = _btc_dossier()
    dossier_a2 = load_claim_dossier("delphi-eth-dencun-blobs")
    dossier_b = load_claim_dossier("delphi-falsified-quantum-rsa2048")
    exported_path = tmp_path / "sess_a_bundle.json"

    # Turn 1 in sess-A
    loopback_server.enqueue(
        json_step(
            _pass_payload(
                claim_id=dossier_a1.claim_id,
                pass_role="corroborator",
                verdict="SUPPORTED",
                confidence=0.91,
                rationale="SEC approval verified.",
                quote="UNIQUE_SESS_A_CITATION_TOKEN",
            )
        )
    )
    loopback_server.enqueue(
        json_step(
            _pass_payload(
                claim_id=dossier_a1.claim_id,
                pass_role="skeptic",
                verdict="SUPPORTED",
                confidence=0.87,
                rationale="No contradiction found.",
                quote="UNIQUE_SESS_A_CITATION_TOKEN",
            )
        )
    )

    with _make_auditor(tmp_path, loopback_server, name="auditor_one") as auditor1:
        b1 = auditor1.audit_claim(
            dossier_a1,
            single_pass=False,
            session_id="sess-A",
            memory_bundle_out=exported_path,
        )
        assert b1.session_id == "sess-A"
        bundle_a = auditor1.export_session_memory("sess-A")
        assert len(bundle_a.items) == 1
        assert "UNIQUE_SESS_A_CITATION_TOKEN" in json.dumps(bundle_a.items)
        assert exported_path.exists()
        reloaded = load_bundle(exported_path)
        assert len(reloaded.items) == 1

    # Port MemoryBundle into a brand-new ConsensusAuditor instance (separate runtime & state!)
    req_start = len(loopback_server.requests)
    loopback_server.enqueue(
        json_step(
            _pass_payload(
                claim_id=dossier_a2.claim_id,
                pass_role="corroborator",
                verdict="SUPPORTED",
                confidence=0.90,
                rationale="Dencun verified.",
                source_id="src-eth-dencun-eip4844",
                quote="Dencun mainnet blobs active.",
            )
        )
    )
    loopback_server.enqueue(
        json_step(
            _pass_payload(
                claim_id=dossier_a2.claim_id,
                pass_role="skeptic",
                verdict="SUPPORTED",
                confidence=0.86,
                rationale="Confirmed on beacon chain.",
                source_id="src-eth-dencun-eip4844",
                quote="Dencun mainnet blobs active.",
            )
        )
    )
    loopback_server.enqueue(
        json_step(
            _pass_payload(
                claim_id=dossier_b.claim_id,
                pass_role="corroborator",
                verdict="REFUTED",
                confidence=0.96,
                rationale="Falsified.",
                source_id="src-nist-pqc-faq",
                quote="No 4096-qubit break occurred.",
            )
        )
    )
    loopback_server.enqueue(
        json_step(
            _pass_payload(
                claim_id=dossier_b.claim_id,
                pass_role="skeptic",
                verdict="REFUTED",
                confidence=0.94,
                rationale="Confirmed falsified.",
                source_id="src-nist-pqc-faq",
                quote="No 4096-qubit break occurred.",
            )
        )
    )

    with _make_auditor(tmp_path, loopback_server, name="auditor_two") as auditor2:
        auditor2.import_session_memory("sess-A", exported_path)
        assert len(auditor2.export_session_memory("sess-B").items) == 0

        # Follow-up query in sess-A MUST retain sess-A prior citations
        b2 = auditor2.audit_claim(dossier_a2, single_pass=False, session_id="sess-A")
        assert b2.session_id == "sess-A"
        assert len(auditor2.export_session_memory("sess-A").items) == 2

        sess_a_reqs = loopback_server.requests[req_start : req_start + 4]
        sess_a_prompt_blob = " ".join(json.dumps(r.body.get("messages", [])) for r in sess_a_reqs)
        assert "UNIQUE_SESS_A_CITATION_TOKEN" in sess_a_prompt_blob
        assert dossier_a1.claim_id in sess_a_prompt_blob

        # Query in sess-B MUST see ZERO entries from sess-A
        req_b_start = len(loopback_server.requests)
        b_other = auditor2.audit_claim(dossier_b, single_pass=False, session_id="sess-B")
        assert b_other.session_id == "sess-B"
        sess_b_reqs = loopback_server.requests[req_b_start:]
        sess_b_prompt_blob = " ".join(json.dumps(r.body.get("messages", [])) for r in sess_b_reqs)
        assert "UNIQUE_SESS_A_CITATION_TOKEN" not in sess_b_prompt_blob
        assert dossier_a1.claim_id not in sess_b_prompt_blob
        sess_b_items = auditor2.export_session_memory("sess-B").items
        assert len(sess_b_items) == 1
        assert "UNIQUE_SESS_A_CITATION_TOKEN" not in json.dumps(sess_b_items)


def test_publication_tool_scope_and_handoff_deny_blocks_execution(
    tmp_path: Path,
    loopback_server: LoopbackLLMServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "stub-key")
    assert publish_consensus_verdict.tool_decl.min_scope == "WRITE_SAFE"
    assert publish_consensus_verdict.tool_decl.dangerous is True
    with pytest.raises(ValueError, match="READ_ONLY"):
        assert_read_only_tools([publish_consensus_verdict])

    dossier = _btc_dossier()
    pub_log = tmp_path / "published_deny.jsonl"
    _enqueue_dual_pass_agreement(loopback_server)
    loopback_server.enqueue(
        tool_calls_step(
            {
                "id": "call_handoff_deny",
                "name": "transfer_to_publisher",
                "arguments": {"message": "Publish verified verdict for delphi-btc-etf-2024"},
            }
        )
    )

    with _make_auditor(tmp_path, loopback_server) as auditor:
        bundle = auditor.audit_claim(
            dossier,
            single_pass=False,
            session_id="sess-deny",
            publish=True,
            approval_mode="deny",
            publication_log_path=pub_log,
        )

    assert bundle.publication is not None
    assert bundle.publication.published is False
    assert bundle.publication.publication_status == "denied"
    assert not pub_log.exists()
    assert any(
        "transfer_to_publisher"
        in [t.get("function", {}).get("name") for t in (r.body.get("tools") or [])]
        for r in loopback_server.requests
    )


def test_handoff_pause_and_thread_id_resume_allow_once_and_deny(
    tmp_path: Path,
    loopback_server: LoopbackLLMServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "stub-key")
    dossier = _btc_dossier()
    pub_log = tmp_path / "published_pause_resume.jsonl"

    # Step 1: pause before publication
    _enqueue_dual_pass_agreement(loopback_server)
    loopback_server.enqueue(
        tool_calls_step(
            {
                "id": "call_handoff_pause",
                "name": "transfer_to_publisher",
                "arguments": {"message": "Publish delphi-btc-etf-2024"},
            }
        )
    )

    with _make_auditor(tmp_path, loopback_server) as auditor:
        paused = auditor.audit_claim(
            dossier,
            single_pass=False,
            session_id="sess-pause",
            publish=True,
            approval_mode="pause",
            publication_log_path=pub_log,
        )
        assert paused.publication is not None
        assert paused.publication.published is False
        assert paused.publication.publication_status == "paused"
        assert paused.publication.thread_id
        assert not pub_log.exists()

        # Step 2: resume via paused thread_id + allow_once -> completes publication through Handoff
        loopback_server.enqueue(
            tool_calls_step(
                {
                    "id": "call_pub_resume",
                    "name": "publish_consensus_verdict",
                    "arguments": {
                        "claim_id": dossier.claim_id,
                        "final_verdict": "SUPPORTED",
                        "agreement_score": paused.consensus.agreement_score,
                        "mean_confidence": paused.consensus.mean_confidence,
                        "requires_human_review": False,
                        "session_id": "sess-pause",
                        "summary": "Resumed publication.",
                    },
                }
            )
        )
        loopback_server.enqueue(
            text_step(
                'Publisher recorded verdict.\n<finalization_status>{"status": "final_answer"}</finalization_status>'
            )
        )

        resumed = auditor.audit_claim(
            dossier,
            single_pass=False,
            session_id="sess-pause",
            thread_id=paused.publication.thread_id,
            publish=True,
            approval_mode="allow_once",
            publication_log_path=pub_log,
        )
        assert resumed.publication is not None
        assert resumed.publication.published is True
        assert resumed.publication.publication_status == "published"
        assert pub_log.exists()
        lines = pub_log.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["claim_id"] == dossier.claim_id

        # Step 3: replaying the same thread_id is denied and does NOT write again
        replay = auditor.audit_claim(
            dossier,
            single_pass=False,
            session_id="sess-pause",
            thread_id=paused.publication.thread_id,
            publish=True,
            approval_mode="allow_once",
            publication_log_path=pub_log,
        )
        assert replay.publication is not None
        assert replay.publication.published is False
        assert replay.publication.publication_status == "denied"
        assert len(pub_log.read_text(encoding="utf-8").strip().splitlines()) == 1

        # Step 4: pause -> resume with deny stays unpublished
        pub_log_2 = tmp_path / "published_pause_deny.jsonl"
        _enqueue_dual_pass_agreement(loopback_server)
        loopback_server.enqueue(
            tool_calls_step(
                {
                    "id": "call_handoff_pause_2",
                    "name": "transfer_to_publisher",
                    "arguments": {"message": "Publish delphi-btc-etf-2024"},
                }
            )
        )
        paused2 = auditor.audit_claim(
            dossier,
            single_pass=False,
            session_id="sess-pause-deny",
            publish=True,
            approval_mode="pause",
            publication_log_path=pub_log_2,
        )
        assert paused2.publication is not None and paused2.publication.thread_id
        denied2 = auditor.audit_claim(
            dossier,
            single_pass=False,
            session_id="sess-pause-deny",
            thread_id=paused2.publication.thread_id,
            publish=True,
            approval_mode="deny",
            publication_log_path=pub_log_2,
        )
        assert denied2.publication is not None
        assert denied2.publication.published is False
        assert denied2.publication.publication_status == "denied"
        assert not pub_log_2.exists()


def test_handoff_allow_once_single_use_and_replay_denial(
    tmp_path: Path,
    loopback_server: LoopbackLLMServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "stub-key")
    dossier = _btc_dossier()
    pub_log = tmp_path / "published_once.jsonl"
    callbacks: list[tuple[str, str]] = []

    def _cb(tool_name: str, args: dict[str, Any], approval_id: str) -> bool:
        del args
        callbacks.append((tool_name, approval_id))
        return True

    _enqueue_dual_pass_agreement(loopback_server)
    loopback_server.enqueue(
        tool_calls_step(
            {
                "id": "call_h_once",
                "name": "transfer_to_publisher",
                "arguments": {"message": "Publish delphi-btc-etf-2024"},
            }
        )
    )
    loopback_server.enqueue(
        tool_calls_step(
            {
                "id": "call_p_once",
                "name": "publish_consensus_verdict",
                "arguments": {
                    "claim_id": dossier.claim_id,
                    "final_verdict": "SUPPORTED",
                    "agreement_score": 0.96,
                    "mean_confidence": 0.88,
                    "requires_human_review": False,
                    "session_id": "sess-once",
                    "summary": "Once approval.",
                },
            }
        )
    )
    loopback_server.enqueue(
        text_step(
            'Published once.\n<finalization_status>{"status": "final_answer"}</finalization_status>'
        )
    )
    loopback_server.enqueue(
        text_step(
            'Coordinator finished publication.\n<finalization_status>{"status": "final_answer"}</finalization_status>'
        )
    )

    with _make_auditor(tmp_path, loopback_server) as auditor:
        first = auditor.audit_claim(
            dossier,
            single_pass=False,
            session_id="sess-once",
            publish=True,
            approval_mode="allow_once",
            approval_id="grant-once-001",
            approval_callback=_cb,
            publication_log_path=pub_log,
        )
        assert first.publication is not None
        assert first.publication.published is True
        assert first.publication.publication_status == "published"
        assert len(callbacks) == 1
        assert callbacks[0][0] == "transfer_to_publisher"
        assert len(pub_log.read_text(encoding="utf-8").strip().splitlines()) == 1

        # Replaying the same allow_once approval_id MUST be denied by policy
        _enqueue_dual_pass_agreement(loopback_server)
        replay = auditor.audit_claim(
            dossier,
            single_pass=False,
            session_id="sess-once",
            publish=True,
            approval_mode="allow_once",
            approval_id="grant-once-001",
            approval_callback=_cb,
            publication_log_path=pub_log,
        )
        assert replay.publication is not None
        assert replay.publication.published is False
        assert replay.publication.publication_status == "denied"
        assert "replay" in replay.publication.denial_reason.lower() or "used" in replay.publication.denial_reason.lower()
        assert len(pub_log.read_text(encoding="utf-8").strip().splitlines()) == 1


def test_real_turn_telemetry_and_stats_aggregation(
    tmp_path: Path,
    loopback_server: LoopbackLLMServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "stub-key")
    dossier = _btc_dossier()
    _enqueue_dual_pass_agreement(loopback_server)

    with _make_auditor(tmp_path, loopback_server) as auditor:
        bundle = auditor.audit_claim(dossier, single_pass=False, session_id="sess-telemetry")

    telemetry = bundle.metadata.get("telemetry")
    assert isinstance(telemetry, dict)
    assert telemetry["requests"] == len(loopback_server.requests)
    # Each subagent makes 4 LLM calls: tool_call(10/10), FreshnessContract(10/10), final json(12/15), ClosureJudgment(10/10) -> 42/45/87 per pass!
    assert telemetry["prompt_tokens"] == 84
    assert telemetry["completion_tokens"] == 90
    assert telemetry["total_tokens"] == 174
    assert telemetry["total_latency_ms"] >= 0
    assert set(telemetry["per_pass"].keys()) == {"corroborator", "skeptic"}
    assert telemetry["per_pass"]["corroborator"]["requests"] == 4
    assert telemetry["per_pass"]["skeptic"]["requests"] == 4
    assert len(telemetry["turn_telemetries"]) == 2


def test_cli_multi_pass_memory_bundle_and_pause_resume(
    tmp_path: Path,
    loopback_server: LoopbackLLMServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "stub-key")
    home_dir = tmp_path / "cli_home"
    data_dir = tmp_path / "cli_data"
    bundle_out = tmp_path / "cli_mem.json"
    pub_log = tmp_path / "cli_pub.jsonl"

    _enqueue_dual_pass_agreement(loopback_server)
    loopback_server.enqueue(
        tool_calls_step(
            {
                "id": "call_cli_h",
                "name": "transfer_to_publisher",
                "arguments": {"message": "Publish delphi-btc-etf-2024"},
            }
        )
    )

    rc_pause = cli_main(
        [
            "audit",
            "--claim-id",
            "delphi-btc-etf-2024",
            "--multi-pass",
            "--session-id",
            "cli-s1",
            "--publish",
            "--approval-mode",
            "pause",
            "--publication-log",
            str(pub_log),
            "--memory-bundle-out",
            str(bundle_out),
            "--base-url",
            loopback_server.base_url,
            "--model",
            "stub-cli-model",
            "--home-root",
            str(home_dir),
            "--data-root",
            str(data_dir),
        ]
    )
    assert rc_pause == 0
    paused_bundle = AuditRunBundle.model_validate_json(capsys.readouterr().out)
    assert [p.pass_role for p in paused_bundle.consensus.passes] == ["corroborator", "skeptic"]
    assert paused_bundle.publication is not None
    assert paused_bundle.publication.publication_status == "paused"
    paused_tid = paused_bundle.publication.thread_id
    assert paused_tid
    assert bundle_out.exists()
    assert len(load_bundle(bundle_out).items) == 1
    assert not pub_log.exists()

    # Resume same paused thread from CLI with --resume-thread-id and --approval-mode allow_once
    loopback_server.enqueue(
        tool_calls_step(
            {
                "id": "call_cli_pub",
                "name": "publish_consensus_verdict",
                "arguments": {
                    "claim_id": "delphi-btc-etf-2024",
                    "final_verdict": "SUPPORTED",
                    "agreement_score": paused_bundle.consensus.agreement_score,
                    "mean_confidence": paused_bundle.consensus.mean_confidence,
                    "requires_human_review": False,
                    "session_id": "cli-s1",
                    "summary": "CLI resumed publication.",
                },
            }
        )
    )
    loopback_server.enqueue(
        text_step(
            'CLI publisher done.\n<finalization_status>{"status": "final_answer"}</finalization_status>'
        )
    )

    rc_resume = cli_main(
        [
            "audit",
            "--claim-id",
            "delphi-btc-etf-2024",
            "--multi-pass",
            "--session-id",
            "cli-s1",
            "--publish",
            "--approval-mode",
            "allow_once",
            "--resume-thread-id",
            paused_tid,
            "--publication-log",
            str(pub_log),
            "--base-url",
            loopback_server.base_url,
            "--model",
            "stub-cli-model",
            "--home-root",
            str(home_dir),
            "--data-root",
            str(data_dir),
        ]
    )
    assert rc_resume == 0
    resumed_bundle = AuditRunBundle.model_validate_json(capsys.readouterr().out)
    assert resumed_bundle.publication is not None
    assert resumed_bundle.publication.published is True
    assert resumed_bundle.publication.publication_status == "published"
    assert len(pub_log.read_text(encoding="utf-8").strip().splitlines()) == 1


def test_thread_id_resume_fails_closed_when_mode_omitted_and_rejects_unknown_thread(
    tmp_path: Path,
    loopback_server: LoopbackLLMServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "stub-key")
    dossier = _btc_dossier()
    pub_log = tmp_path / "fail_closed_resume.jsonl"

    _enqueue_dual_pass_agreement(loopback_server)
    loopback_server.enqueue(
        tool_calls_step(
            {
                "id": "call_fc_pause",
                "name": "transfer_to_publisher",
                "arguments": {"message": "Publish delphi-btc-etf-2024"},
            }
        )
    )

    with _make_auditor(tmp_path, loopback_server) as auditor:
        paused = auditor.audit_claim(
            dossier,
            session_id="sess-fc",
            publish=True,
            approval_mode="pause",
            publication_log_path=pub_log,
        )
        assert paused.publication is not None and paused.publication.thread_id
        assert paused.publication.publication_status == "paused"

        # Passing approval_mode=None & no approval_callback MUST stay paused (fail-closed)
        still_paused = auditor.audit_claim(
            dossier,
            session_id="sess-fc",
            thread_id=paused.publication.thread_id,
            publish=True,
            approval_mode=None,
            publication_log_path=pub_log,
        )
        assert still_paused.publication is not None
        assert still_paused.publication.published is False
        assert still_paused.publication.publication_status == "paused"
        assert not pub_log.exists()

        # Unknown thread_id MUST raise ValueError instead of silently continuing
        with pytest.raises(ValueError, match="Unknown|thread_id"):
            auditor.audit_claim(
                dossier,
                session_id="sess-fc",
                thread_id="missing-thread-id-999",
                publish=True,
                approval_mode="allow_once",
                publication_log_path=pub_log,
            )

        # Passing explicit approval_callback with approval_mode=None resumes allow_once
        loopback_server.enqueue(
            tool_calls_step(
                {
                    "id": "call_fc_pub",
                    "name": "publish_consensus_verdict",
                    "arguments": {
                        "claim_id": dossier.claim_id,
                        "final_verdict": "SUPPORTED",
                        "agreement_score": paused.consensus.agreement_score,
                        "mean_confidence": paused.consensus.mean_confidence,
                        "requires_human_review": False,
                        "session_id": "sess-fc",
                        "summary": "Resumed via callback.",
                    },
                }
            )
        )
        loopback_server.enqueue(
            text_step('Done.\n<finalization_status>{"status": "final_answer"}</finalization_status>')
        )
        resumed = auditor.audit_claim(
            dossier,
            session_id="sess-fc",
            thread_id=paused.publication.thread_id,
            publish=True,
            approval_mode=None,
            approval_callback=lambda _t, _a, _id: True,
            publication_log_path=pub_log,
        )
        assert resumed.publication is not None
        assert resumed.publication.published is True
        assert len(pub_log.read_text(encoding="utf-8").strip().splitlines()) == 1


def test_cortensor_router_publisher_preserves_provider_and_avoids_double_nested_state_root(
    tmp_path: Path,
    loopback_server: LoopbackLLMServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORTENSOR_API_KEY", "cort-stub-key")
    monkeypatch.chdir(tmp_path)
    dossier = _btc_dossier()

    _enqueue_dual_pass_agreement(loopback_server)
    loopback_server.enqueue(
        tool_calls_step(
            {
                "id": "call_cort_h",
                "name": "transfer_to_publisher",
                "arguments": {"message": "Publish via cortensor-router"},
            }
        )
    )
    loopback_server.enqueue(
        tool_calls_step(
            {
                "id": "call_cort_p",
                "name": "publish_consensus_verdict",
                "arguments": {
                    "claim_id": dossier.claim_id,
                    "final_verdict": "SUPPORTED",
                    "agreement_score": 0.96,
                    "mean_confidence": 0.88,
                    "requires_human_review": False,
                    "session_id": "sess-cort-pub",
                    "summary": "Cortensor preset publish.",
                },
            }
        )
    )
    loopback_server.enqueue(
        text_step('Published.\n<finalization_status>{"status": "final_answer"}</finalization_status>')
    )
    loopback_server.enqueue(
        text_step('Coordinator done.\n<finalization_status>{"status": "final_answer"}</finalization_status>')
    )

    state_root = tmp_path / ".openminion-state"
    with ConsensusAuditor(
        preset="cortensor-router",
        base_url=loopback_server.base_url,
        model="stub-cortensor-model",
        api_key_env="CORTENSOR_API_KEY",
        home_root=tmp_path / "cort-home",
        data_root=state_root,
    ) as auditor:
        bundle = auditor.audit_claim(
            dossier,
            session_id="sess-cort-pub",
            publish=True,
            approval_mode="allow_once",
        )
        pub_rt = auditor._ensure_publisher_runtime()
        assert pub_rt.config.providers.cortensor.base_url.rstrip("/") == loopback_server.base_url.rstrip("/")
        mem = auditor.export_session_memory("sess-cort-pub")
        assert len(mem.metadata.get("pass_session_ids", [])) >= 2

    assert bundle.publication is not None
    assert bundle.publication.published is True
    expected_log = state_root / "published_verdicts.jsonl"
    nested_log = state_root / ".openminion-state" / "published_verdicts.jsonl"
    assert expected_log.exists()
    assert not nested_log.exists()


def test_session_memory_injects_prior_turn_snippets_and_import_clears_stale_pass_ids(
    tmp_path: Path,
    loopback_server: LoopbackLLMServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "stub-key")
    dossier_1 = _btc_dossier()
    dossier_2 = load_claim_dossier("delphi-eth-dencun-blobs")
    dossier_3 = load_claim_dossier("delphi-falsified-quantum-rsa2048")
    session_id = "sess-snippet-c5"

    # Turn 1: dual-pass audit with unique per-pass in-flight tokens
    loopback_server.enqueue(
        json_step(
            _pass_payload(
                claim_id=dossier_1.claim_id,
                pass_role="corroborator",
                verdict="SUPPORTED",
                confidence=0.93,
                rationale="TURN1_CORR_INFLIGHT_ALPHA SEC filing matched.",
                quote="TURN1_CITE_EXCERPT_MARKER",
            )
        )
    )
    loopback_server.enqueue(
        json_step(
            _pass_payload(
                claim_id=dossier_1.claim_id,
                pass_role="skeptic",
                verdict="SUPPORTED",
                confidence=0.89,
                rationale="TURN1_SKEP_INFLIGHT_BETA no counter-filing found.",
                quote="TURN1_CITE_EXCERPT_MARKER",
            )
        )
    )

    # Turn 2: dual-pass audit on the SAME session_id
    loopback_server.enqueue(
        json_step(
            _pass_payload(
                claim_id=dossier_2.claim_id,
                pass_role="corroborator",
                verdict="SUPPORTED",
                confidence=0.91,
                rationale="TURN2_CORR_INFLIGHT_GAMMA Dencun mainnet blobs confirmed.",
                source_id="src-eth-dencun-eip4844",
                quote="Dencun blobs active on mainnet.",
            )
        )
    )
    loopback_server.enqueue(
        json_step(
            _pass_payload(
                claim_id=dossier_2.claim_id,
                pass_role="skeptic",
                verdict="SUPPORTED",
                confidence=0.87,
                rationale="TURN2_SKEP_INFLIGHT_DELTA beacon chain verified.",
                source_id="src-eth-dencun-eip4844",
                quote="Dencun blobs active on mainnet.",
            )
        )
    )

    def _requests_for_role(reqs: list[Any], role: str) -> list[Any]:
        matched = []
        for req in reqs:
            sys_text = " ".join(
                str(m.get("content", ""))
                for m in req.body.get("messages", [])
                if m.get("role") == "system"
            ).lower()
            if f"'{role}'" in sys_text:
                matched.append(req)
        return matched

    with _make_auditor(tmp_path, loopback_server, name="auditor_c5") as auditor:
        b1 = auditor.audit_claim(dossier_1, single_pass=False, session_id=session_id)
        assert b1.consensus.final_verdict == "SUPPORTED"
        turn1_reqs = list(loopback_server.requests)
        t1_corr = _requests_for_role(turn1_reqs, "corroborator")
        t1_skep = _requests_for_role(turn1_reqs, "skeptic")
        assert t1_corr and t1_skep
        t1_skep_blob = " ".join(json.dumps(r.body.get("messages", [])) for r in t1_skep)
        t1_corr_blob = " ".join(json.dumps(r.body.get("messages", [])) for r in t1_corr)
        assert "TURN1_CORR_INFLIGHT_ALPHA" not in t1_skep_blob
        assert "TURN1_SKEP_INFLIGHT_BETA" not in t1_corr_blob

        turn2_start = len(loopback_server.requests)
        b2 = auditor.audit_claim(dossier_2, single_pass=False, session_id=session_id)
        assert b2.consensus.final_verdict == "SUPPORTED"
        turn2_reqs = loopback_server.requests[turn2_start:]
        t2_corr = _requests_for_role(turn2_reqs, "corroborator")
        t2_skep = _requests_for_role(turn2_reqs, "skeptic")
        assert t2_corr and t2_skep

        for role_reqs in (t2_corr, t2_skep):
            user_blob = " ".join(
                str(m.get("content", ""))
                for r in role_reqs
                for m in r.body.get("messages", [])
                if m.get("role") == "user"
            )
            # Turn 1 verdict summary from bundle.items
            assert dossier_1.claim_id in user_blob
            assert "TURN1_CITE_EXCERPT_MARKER" in user_blob
            # Concise prior recorded session_msgs snippet(s), not just message count
            assert "Prior openminion session messages recorded:" in user_blob
            assert "outbound:" in user_blob
            assert "TURN1_SKEP_INFLIGHT_BETA" in user_blob
            assert "TURN1_CORR_INFLIGHT_ALPHA" in user_blob

        # Within Turn 2, corroborator and skeptic remain blind to each other's in-flight output
        t2_skep_blob = " ".join(json.dumps(r.body.get("messages", [])) for r in t2_skep)
        t2_corr_blob = " ".join(json.dumps(r.body.get("messages", [])) for r in t2_corr)
        assert "TURN2_CORR_INFLIGHT_GAMMA" not in t2_skep_blob
        assert "TURN2_SKEP_INFLIGHT_DELTA" not in t2_corr_blob

        # (b) import_session_memory over an existing session_id that had pass_session_ids clears them to []
        pre_import = auditor.export_session_memory(session_id)
        assert len(pre_import.metadata.get("pass_session_ids", [])) >= 4

        incoming_bundle = export_bundle(
            [
                {
                    "id": f"{session_id}:imported:1",
                    "session_id": session_id,
                    "content": "Imported external verified record IMPORT_MARKER_ZETA.",
                }
            ],
            metadata={
                "session_id": session_id,
                "item_count": 1,
                "pass_session_ids": ["stale-imported-pass-id-999"],
            },
        )
        auditor.import_session_memory(session_id, incoming_bundle)

        post_import = auditor.export_session_memory(session_id)
        assert "pass_session_ids" in post_import.metadata
        assert post_import.metadata["pass_session_ids"] == []

    # Verify cleared pass_session_ids also persists across a fresh auditor runtime restart
    with _make_auditor(tmp_path, loopback_server, name="auditor_c5") as reloaded_auditor:
        reloaded_bundle = reloaded_auditor.export_session_memory(session_id)
        assert reloaded_bundle.metadata.get("pass_session_ids") == []

        # Next audit sees imported bundle item but NOT stale session_msgs from cleared pass_session_ids
        loopback_server.enqueue(
            json_step(
                _pass_payload(
                    claim_id=dossier_3.claim_id,
                    pass_role="corroborator",
                    verdict="REFUTED",
                    confidence=0.95,
                    rationale="Turn 3 corroborator refuted.",
                    source_id="src-nist-pqc-faq",
                    quote="No 4096-qubit break occurred.",
                )
            )
        )
        loopback_server.enqueue(
            json_step(
                _pass_payload(
                    claim_id=dossier_3.claim_id,
                    pass_role="skeptic",
                    verdict="REFUTED",
                    confidence=0.94,
                    rationale="Turn 3 skeptic confirmed.",
                    source_id="src-nist-pqc-faq",
                    quote="No 4096-qubit break occurred.",
                )
            )
        )
        turn3_start = len(loopback_server.requests)
        reloaded_auditor.audit_claim(dossier_3, single_pass=False, session_id=session_id)
        turn3_reqs = loopback_server.requests[turn3_start:]
        turn3_user_blob = " ".join(
            str(m.get("content", ""))
            for r in turn3_reqs
            for m in r.body.get("messages", [])
            if m.get("role") == "user"
        )
        assert "IMPORT_MARKER_ZETA" in turn3_user_blob
        assert "Prior openminion session messages recorded:" not in turn3_user_blob

