"""Comprehensive offline test suite for cortensor-router-doctor."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import httpx
import pytest
from openminion.modules.memory.models import MemoryNamespace
from openminion.modules.memory.portability.models import (
    MemoryBundleImportOptions,
)

from cortensor_router_doctor.agent import (
    build_audit_agent,
    build_forensics_handoff,
    build_isolated_config,
    create_isolated_runtime,
    run_audit_via_submit_turn,
)
from cortensor_router_doctor.memory_ops import (
    DEFAULT_AUDIT_SCOPE,
    export_audit_bundle,
    import_audit_bundle_atomic,
    list_audit_incidents,
    record_audit_incident,
)
from cortensor_router_doctor.models import (
    ProbeResult,
    QuarantineAction,
    RouterAuditReport,
    SLAPolicyEvaluation,
    VerdictMismatchError,
    verify_report_against_evidence,
)
from cortensor_router_doctor.router_sim import (
    RouterNodeProfile,
    SimulatedCortensorRouter,
)
from cortensor_router_doctor.tools import (
    apply_router_quarantine,
    evaluate_sla_policy,
    probe_cortensor_router,
)


class TestRouterSimulatorAndTools:
    def test_healthy_router_probe_and_policy(self) -> None:
        with SimulatedCortensorRouter(
            RouterNodeProfile(profile="healthy", node_id="sim-healthy", base_latency_ms=5.0)
        ) as router:
            health = httpx.get(router.health_url, timeout=3.0).json()
            assert health["status"] == "ok"
            assert health["profile"] == "healthy"

            probe_json = probe_cortensor_router(
                endpoint_url=router.completions_url,
                prompt="Check Cortensor epoch 4092 quorum",
                rounds=3,
                session_id=7,
                timeout_seconds=5.0,
            )
            probe = ProbeResult.model_validate_json(probe_json)
            assert probe.rounds == 3
            assert probe.success_rate == 1.0
            assert probe.poi_analysis.exact_match_ratio == 1.0
            assert probe.poi_analysis.poi_agreement_score == 1.0
            assert probe.poi_analysis.drift_detected is False
            assert router.request_count == 3

            eval_json = evaluate_sla_policy(probe_json, max_p95_ms=500.0, min_poi_agreement=0.85)
            evaluation = SLAPolicyEvaluation.model_validate_json(eval_json)
            assert evaluation.grade == "HEALTHY"
            assert evaluation.recommended_action == "NONE"
            assert evaluation.violations == []

    def test_poi_drift_router_triggers_critical_drift(self) -> None:
        with SimulatedCortensorRouter(
            RouterNodeProfile(profile="poi_drift", node_id="sim-drift", base_latency_ms=5.0)
        ) as router:
            probe_json = probe_cortensor_router(
                endpoint_url=router.completions_url,
                prompt="Verify validator state root",
                rounds=3,
                session_id=1,
            )
            probe = ProbeResult.model_validate_json(probe_json)
            assert probe.success_rate == 1.0
            assert probe.poi_analysis.unique_responses == 3
            assert probe.poi_analysis.exact_match_ratio == 0.0
            assert probe.poi_analysis.poi_agreement_score < 0.85
            assert probe.poi_analysis.drift_detected is True

            eval_json = evaluate_sla_policy(probe_json)
            evaluation = SLAPolicyEvaluation.model_validate_json(eval_json)
            assert evaluation.grade == "CRITICAL_DRIFT"
            assert evaluation.recommended_action == "QUARANTINE"
            assert any("poi_agreement_below_threshold" in v for v in evaluation.violations)

    def test_sla_degraded_router_triggers_degraded_grade(self) -> None:
        with SimulatedCortensorRouter(
            RouterNodeProfile(
                profile="sla_degraded",
                node_id="sim-slow",
                base_latency_ms=25.0,
                fail_every_n=2,
            )
        ) as router:
            probe_json = probe_cortensor_router(
                endpoint_url=router.completions_url,
                prompt="Ping slow router",
                rounds=4,
            )
            probe = ProbeResult.model_validate_json(probe_json)
            assert probe.success_rate == 0.5
            assert any(s.status_code == 503 for s in probe.samples)

            eval_json = evaluate_sla_policy(
                probe_json,
                max_p95_ms=10.0,
                min_poi_agreement=0.85,
                min_success_rate=0.95,
            )
            evaluation = SLAPolicyEvaluation.model_validate_json(eval_json)
            assert evaluation.grade == "DEGRADED"
            assert evaluation.recommended_action == "QUARANTINE"
            assert any("success_rate_below_threshold" in v for v in evaluation.violations)
            assert any("p95_latency_above_threshold" in v for v in evaluation.violations)

    def test_chat_completions_openai_compatible_probe(self) -> None:
        with SimulatedCortensorRouter(
            RouterNodeProfile(profile="healthy", base_latency_ms=2.0)
        ) as router:
            probe_json = probe_cortensor_router(
                endpoint_url=router.chat_completions_url,
                prompt="OpenAI compat health check",
                rounds=2,
            )
            probe = ProbeResult.model_validate_json(probe_json)
            assert probe.success_rate == 1.0
            assert probe.poi_analysis.poi_agreement_score == 1.0

    def test_apply_router_quarantine_writes_signed_directive_and_has_risk_metadata(
        self, tmp_path: Path
    ) -> None:
        assert probe_cortensor_router.tool_decl.min_scope == "READ_ONLY"
        assert probe_cortensor_router.tool_decl.idempotent is True
        assert evaluate_sla_policy.tool_decl.min_scope == "READ_ONLY"
        assert evaluate_sla_policy.tool_decl.idempotent is True
        assert apply_router_quarantine.tool_decl.min_scope == "WRITE_SAFE"
        assert apply_router_quarantine.tool_decl.dangerous is True
        assert apply_router_quarantine.tool_decl.idempotent is False

        q_file = tmp_path / "directives" / "node_quarantine.json"
        action_json = apply_router_quarantine(
            endpoint_url="http://127.0.0.1:8080/api/v2/completions",
            reason="PoI agreement dropped to 0.21 across 3 redundant rounds",
            severity="CRITICAL",
            quarantine_file=str(q_file),
        )
        action = QuarantineAction.model_validate_json(action_json)
        assert action.applied is True
        assert action.severity == "CRITICAL"
        assert len(action.signature_sha256) == 64
        assert q_file.exists()

        on_disk = json.loads(q_file.read_text(encoding="utf-8"))
        assert on_disk["status"] == "QUARANTINED"
        assert on_disk["signature_sha256"] == action.signature_sha256


class TestAntiHallucinationGuards:
    def test_report_rejects_self_contradictory_healthy_verdict(self) -> None:
        with pytest.raises(ValueError, match="Cannot certify verdict='HEALTHY'"):
            RouterAuditReport(
                endpoint_url="http://127.0.0.1:8080/api/v2/completions",
                verdict="HEALTHY",
                summary="Claimed healthy despite violations",
                recommended_action="NONE",
                measured_p95_ms=25.0,
                measured_poi_agreement=0.40,
                measured_success_rate=1.0,
                quarantine_applied=False,
                violations=["poi_agreement_below_threshold: 0.4000 < 0.8500"],
            )

    def test_verify_report_blocks_hallucinated_healthy_on_drift_evidence(self) -> None:
        evaluation = SLAPolicyEvaluation(
            endpoint_url="http://127.0.0.1:8080/api/v2/completions",
            grade="CRITICAL_DRIFT",
            recommended_action="QUARANTINE",
            violations=["poi_agreement_below_threshold: 0.2500 < 0.8500"],
            thresholds={"max_p95_ms": 500.0, "min_poi_agreement": 0.85, "min_success_rate": 0.95},
            measured={"p95_latency_ms": 30.0, "poi_agreement_score": 0.25, "success_rate": 1.0},
        )
        hallucinated = RouterAuditReport(
            endpoint_url="http://127.0.0.1:8080/api/v2/completions",
            verdict="HEALTHY",
            summary="Everything looks fine!",
            recommended_action="NONE",
            measured_p95_ms=30.0,
            measured_poi_agreement=1.0,
            measured_success_rate=1.0,
            quarantine_applied=False,
            violations=[],
        )
        with pytest.raises(VerdictMismatchError, match="verdict mismatch"):
            verify_report_against_evidence(hallucinated, evaluation)

    def test_verify_report_accepts_truthful_drift_report(self) -> None:
        evaluation = SLAPolicyEvaluation(
            endpoint_url="http://127.0.0.1:8080/api/v2/completions",
            grade="CRITICAL_DRIFT",
            recommended_action="QUARANTINE",
            violations=["poi_agreement_below_threshold: 0.2500 < 0.8500"],
            thresholds={"max_p95_ms": 500.0, "min_poi_agreement": 0.85, "min_success_rate": 0.95},
            measured={"p95_latency_ms": 30.0, "poi_agreement_score": 0.25, "success_rate": 1.0},
        )
        quarantine = QuarantineAction(
            endpoint_url="http://127.0.0.1:8080/api/v2/completions",
            reason="PoI consensus drift",
            severity="CRITICAL",
            quarantine_file="/tmp/q.json",
            applied=True,
            signature_sha256="a" * 64,
            timestamp_utc="2026-11-25T10:00:00+00:00",
        )
        truthful = RouterAuditReport(
            endpoint_url="http://127.0.0.1:8080/api/v2/completions",
            verdict="CRITICAL_DRIFT",
            summary="Severe PoI drift detected; node quarantined.",
            recommended_action="QUARANTINE",
            measured_p95_ms=30.0,
            measured_poi_agreement=0.25,
            measured_success_rate=1.0,
            quarantine_applied=True,
            quarantine_file="/tmp/q.json",
            violations=["poi_agreement_below_threshold: 0.2500 < 0.8500"],
        )
        verified = verify_report_against_evidence(truthful, evaluation, quarantine=quarantine)
        assert verified.verdict == "CRITICAL_DRIFT"


class TestDurableMemoryAndAtomicBundleGuard:
    def test_durable_memory_export_and_atomic_import_across_runtimes(self, tmp_path: Path) -> None:
        rt_a = create_isolated_runtime(tmp_path / "rt_a", provider="echo")
        rt_b = create_isolated_runtime(tmp_path / "rt_b", provider="echo")
        try:
            report = RouterAuditReport(
                endpoint_url="http://127.0.0.1:8080/api/v2/completions",
                verdict="CRITICAL_DRIFT",
                summary="Divergent miner outputs across 3 PoI rounds.",
                recommended_action="QUARANTINE",
                measured_p95_ms=31.5,
                measured_poi_agreement=0.22,
                measured_success_rate=1.0,
                quarantine_applied=True,
                quarantine_file="/tmp/q.json",
                violations=["poi_agreement_below_threshold: 0.2200 < 0.8500"],
            )
            record_id = record_audit_incident(rt_a, report=report, incident_key="router:8080")
            assert record_id

            stored_a = list_audit_incidents(rt_a, scope=DEFAULT_AUDIT_SCOPE)
            assert len(stored_a) == 1

            bundle_file = tmp_path / "audit_bundle.tar.gz"
            snapshot, written = export_audit_bundle(rt_a, bundle_file)
            assert written.exists()
            assert len(snapshot.records) == 1

            import_res = import_audit_bundle_atomic(
                rt_b,
                written,
                options=MemoryBundleImportOptions(
                    trust_mode="direct",
                    conflict_mode="error",
                    id_mode="preserve",
                    namespace_allowlist=[MemoryNamespace(agent_id="router-doctor")],
                ),
            )
            assert import_res.applied is True
            assert import_res.imported_records == 1

            stored_b = list_audit_incidents(rt_b, scope=DEFAULT_AUDIT_SCOPE)
            assert len(stored_b) == 1
            assert stored_b[0].id == record_id
        finally:
            rt_a.close()
            rt_b.close()

    def test_atomic_wrapper_blocks_partial_write_on_conflict_error(self, tmp_path: Path) -> None:
        rt_src = create_isolated_runtime(tmp_path / "src", provider="echo")
        rt_dst = create_isolated_runtime(tmp_path / "dst", provider="echo")
        try:
            svc_src = rt_src.runtime_memory_assembly.service
            svc_dst = rt_dst.runtime_memory_assembly.service

            rec1_id = svc_src.write_record(
                scope=DEFAULT_AUDIT_SCOPE,
                record_type="fact",
                title="Incident 1",
                content={"endpoint": "node-1", "verdict": "HEALTHY"},
            )
            rec2_id = svc_src.write_record(
                scope=DEFAULT_AUDIT_SCOPE,
                record_type="fact",
                title="Incident 2",
                content={"endpoint": "node-2", "verdict": "CRITICAL_DRIFT"},
            )
            snapshot, bundle_path = export_audit_bundle(rt_src, tmp_path / "conflict.tar.gz")

            # Seed conflicting record 2 in destination before importing
            rec2 = next(r for r in snapshot.records if r.id == rec2_id)
            svc_dst._store.put(replace(rec2, content={"endpoint": "node-2", "verdict": "HEALTHY"}))  # noqa: SLF001

            result = import_audit_bundle_atomic(
                rt_dst,
                bundle_path,
                options=MemoryBundleImportOptions(
                    trust_mode="direct",
                    conflict_mode="error",
                    id_mode="preserve",
                ),
            )
            assert result.applied is False
            assert result.imported_records == 0
            assert len(result.conflicts) == 1
            assert result.conflicts[0]["reason"] == "exact_id_conflict"
            # Crucially: record 1 was NOT partially written!
            assert svc_dst._store.get(rec1_id) is None  # noqa: SLF001
        finally:
            rt_src.close()
            rt_dst.close()

    def test_atomic_wrapper_enforces_namespace_allowlist(self, tmp_path: Path) -> None:
        rt_src = create_isolated_runtime(tmp_path / "src_ns", provider="echo")
        rt_dst = create_isolated_runtime(tmp_path / "dst_ns", provider="echo")
        try:
            svc_src = rt_src.runtime_memory_assembly.service
            svc_dst = rt_dst.runtime_memory_assembly.service
            foreign_id = svc_src.write_record(
                scope="agent:rogue-agent",
                record_type="fact",
                title="Foreign fact",
                content={"note": "should be rejected"},
            )
            _, bundle_path = export_audit_bundle(
                rt_src, tmp_path / "foreign.tar.gz", scopes=["agent:rogue-agent"]
            )
            result = import_audit_bundle_atomic(
                rt_dst,
                bundle_path,
                options=MemoryBundleImportOptions(
                    trust_mode="direct",
                    conflict_mode="skip",
                    namespace_allowlist=[MemoryNamespace(agent_id="router-doctor")],
                ),
            )
            assert result.applied is False
            assert result.imported_records == 0
            assert result.conflicts[0]["reason"] == "namespace_not_allowed"
            assert svc_dst._store.get(foreign_id) is None  # noqa: SLF001
        finally:
            rt_src.close()
            rt_dst.close()


class TestRuntimeAgentHandoffAndSubmitTurn:
    def test_provider_configs_encode_verified_workarounds(self, tmp_path: Path) -> None:
        cfg_ollama = build_isolated_config(tmp_path / "o", provider="ollama", model="qwen2.5:3b")
        assert cfg_ollama.agents["router-doctor"].default_channel == "console"
        assert cfg_ollama.enabled_plugins == []
        assert cfg_ollama.runtime.reactions_enabled is False
        assert cfg_ollama.runtime.telemetry_enabled is False
        assert cfg_ollama.providers.ollama.tool_call_strategy == "native"

        cfg_portal = build_isolated_config(tmp_path / "p", provider="cortensor-portal")
        assert cfg_portal.agents["router-doctor"].provider == "openai"
        assert cfg_portal.runtime.chat_turn_timeout_seconds == 480.0

        cfg_router = build_isolated_config(tmp_path / "r", provider="cortensor-router", session_id=42)
        assert cfg_router.agents["router-doctor"].provider == "cortensor"
        assert cfg_router.providers.cortensor.session_id == 42

    def test_agent_allowlisting_and_forensics_handoff_construction(self, tmp_path: Path) -> None:
        rt = create_isolated_runtime(tmp_path / "rt_agent", provider="echo")
        try:
            agent = build_audit_agent(rt)
            assert agent.tools == [
                "probe_cortensor_router",
                "evaluate_sla_policy",
                "apply_router_quarantine",
            ]
            assert "RouterAuditReport" in (agent.instructions or "")

            payload = agent._build_payload("test message")  # noqa: SLF001
            assert payload["allowed_tools"] == [
                "probe_cortensor_router",
                "evaluate_sla_policy",
                "apply_router_quarantine",
            ]
            assert payload["deliver"] is False

            child, handoff = build_forensics_handoff(agent, timeout_seconds=45)
            assert child.subagent_context is not None
            assert child.subagent_context.parent_agent_id == "router-doctor"
            assert child.subagent_context.child_agent_id == "poi-forensics"
            assert child.subagent_context.timeout_seconds == 45
            # Crucially: child holds tool NAME strings (0 family builders) to avoid Bug #7 collision!
            assert child.tools == ["probe_cortensor_router", "evaluate_sla_policy"]
            assert child._tool_family_builders == []  # noqa: SLF001
            assert handoff.resolved_name() == "transfer_to_poi_forensics"
            assert "PoI" in handoff.resolved_description() or "Proof-of-Inference" in handoff.resolved_description()
        finally:
            rt.close()

    def test_submit_turn_end_to_end_with_echo_runtime(self, tmp_path: Path) -> None:
        rt = create_isolated_runtime(tmp_path / "rt_submit", provider="echo")
        try:
            res = run_audit_via_submit_turn(
                rt,
                message="ping cortensor router doctor",
                allowed_tools=[],
                timeout_seconds=15.0,
            )
            assert res.trace_id
            assert res.response.errors == []
            assert "ping cortensor router doctor" in res.response.final_text
        finally:
            rt.close()
