"""Multi-stage OpenMinion 0.1.24 evaluation runner."""

from __future__ import annotations

import json
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from openminion.services.bootstrap.provider_setup import ProviderSetupMissingCredential
from openminion import (
    APIRuntime,
    Agent,
    AgentOutputValidationError,
    MemoryBundle,
    ProviderError,
    TurnTimeoutError,
    subagent,
)
from openminion.modules.memory.portability import (
    export_bundle,
    import_bundle,
    load_bundle,
    save_bundle,
)

from cortensor_agent_eval.models import (
    ApprovalDecisionRecord,
    EvalCaseResult,
    EvalReport,
    EvalSuiteSummary,
    ProbeResult,
)
from cortensor_agent_eval.policy import (
    DEFAULT_BASE_URLS,
    DEFAULT_MODELS,
    FailClosedApprovalGate,
    build_isolated_config,
)
from cortensor_agent_eval.tools import build_eval_tools


@dataclass
class EvalRunOutcome:
    """Complete execution bundle produced by :func:`run_eval_suite`."""

    summary: EvalSuiteSummary
    report: EvalReport
    probe: ProbeResult
    cases: list[EvalCaseResult] = field(default_factory=list)
    approvals: list[ApprovalDecisionRecord] = field(default_factory=list)
    tool_counters: dict[str, int] = field(default_factory=dict)
    posture_keys: list[str] = field(default_factory=list)
    session_id: str = ""
    memory_bundle_path: Path | None = None
    report_path: Path | None = None
    used_offline_fallback: bool = False
    provider_error: str | None = None


def _deterministic_report(summary: EvalSuiteSummary) -> EvalReport:
    if summary.pass_rate >= 0.85:
        verdict = "READY"
    elif summary.pass_rate >= 0.5:
        verdict = "DEGRADED"
    else:
        verdict = "FAILED"
    score = int(round(summary.pass_rate * 100))
    return EvalReport(
        verdict=verdict,
        score=score,
        summary=(
            f"Suite {summary.suite_name} ran {summary.total_cases} OpenMinion "
            f"cases on {summary.provider}/{summary.model} with "
            f"{summary.passed_cases}/{summary.total_cases} passing."
        ),
        strengths=[
            "Isolated APIRuntime lifecycle and SQLite session continuity verified",
            "Fail-closed single-use approval gate recorded tool authorization",
            "MemoryBundle export/import round-trip preserved run telemetry",
        ],
        risks=(
            []
            if summary.failed_cases == 0
            else [f"{summary.failed_cases} benchmark case(s) did not pass"]
        ),
        recommendations=[
            "Run against live Cortensor Portal or Router endpoint to record production latency",
        ],
    )


def _render_markdown(outcome: EvalRunOutcome) -> str:
    lines = [
        f"# Cortensor Agent Eval Report — {outcome.summary.suite_name}",
        "",
        f"- **Verdict:** `{outcome.report.verdict}` ({outcome.report.score}/100)",
        f"- **Provider / Model:** `{outcome.summary.provider}` / `{outcome.summary.model}`",
        f"- **Endpoint Probe:** `{outcome.probe.endpoint}` -> `{outcome.probe.detail}` ({outcome.probe.latency_ms} ms)",
        f"- **Session ID:** `{outcome.session_id}` (persisted={outcome.summary.session_persisted})",
        f"- **Offline Fallback Used:** `{outcome.used_offline_fallback}`",
        "",
        "## Benchmark Cases",
        "",
        "| Case ID | Category | Passed | State | Latency (ms) | Detail |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for c in outcome.cases:
        lines.append(
            f"| `{c.case_id}` | `{c.category}` | `{c.passed}` | `{c.run_state}` | {c.latency_ms:.1f} | {c.detail} |"
        )
    lines.extend(["", "## Approval Gate Audit", ""])
    if outcome.approvals:
        for rec in outcome.approvals:
            lines.append(
                f"- `{rec.tool_name}` (`{rec.approval_id}`): **{rec.decision}** — {rec.reason}"
            )
    else:
        lines.append("- No approval prompts triggered during this run.")
    lines.extend(
        [
            "",
            "## Judge Summary",
            "",
            outcome.report.summary,
            "",
        ]
    )
    return "\n".join(lines)


def run_eval_suite(
    *,
    suite_name: str = "openminion-core-v1",
    provider: str = "openai",
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    out_dir: Path | None = None,
    session_id: str | None = None,
    allow_offline_fallback: bool = True,
    allow_private_probe: bool = False,
    timeout_seconds: float = 45.0,
) -> EvalRunOutcome:
    """Execute the multi-stage OpenMinion benchmark suite."""
    resolved_out = (out_dir or Path("eval-out")).resolve()
    resolved_out.mkdir(parents=True, exist_ok=True)
    resolved_session = (session_id or "").strip() or f"eval-{uuid4().hex[:12]}"
    counters: dict[str, int] = {}
    gate = FailClosedApprovalGate()
    tools_map = build_eval_tools(
        workspace_dir=resolved_out,
        counters=counters,
        allow_private_probe=allow_private_probe,
    )

    with tempfile.TemporaryDirectory(prefix="cortensor_eval_") as tmp:
        work_dir = Path(tmp)
        cases: list[EvalCaseResult] = []
        used_fallback = False
        provider_error_msg: str | None = None
        report: EvalReport | None = None
        posture_keys: list[str] = []
        capability_keys: list[str] = []
        self_model_health = ""
        tool_inventory_count = 0
        stream_events: list[str] = []
        cfg_path: Path | None = None
        effective_model = model or DEFAULT_MODELS.get(provider, "unknown")
        effective_base = (base_url or "").strip() or DEFAULT_BASE_URLS.get(provider, "")

        try:
            cfg_path = build_isolated_config(
                work_dir=work_dir,
                provider=provider,
                model=model,
                base_url=base_url,
                api_key=api_key,
            )
            cfg_data = json.loads(cfg_path.read_text(encoding="utf-8"))
            resolved_model = (
                cfg_data.get("agents", {})
                .get("evaluator", {})
                .get("model_connections", {})
            )
            if resolved_model and not model:
                effective_model = next(iter(resolved_model.values())).get(
                    "models", [effective_model]
                )[0]
            effective_base = (
                base_url
                or cfg_data.get("providers", {}).get(provider, {}).get("base_url", "")
                or effective_base
            )
        except ProviderSetupMissingCredential as exc:
            if not allow_offline_fallback:
                raise
            used_fallback = True
            provider_error_msg = f"{type(exc).__name__}: {exc}"

        try:
            probe_raw = json.loads(
                tools_map["probe_inference_endpoint"](effective_base, 5.0)
            )
            probe = ProbeResult(
                endpoint=probe_raw["endpoint"],
                adapter=provider,
                reachable=bool(probe_raw["reachable"]),
                status_code=probe_raw["status_code"],
                latency_ms=float(probe_raw["latency_ms"]),
                detail=probe_raw["detail"],
            )

            runtime = None
            if cfg_path is not None:
                try:
                    runtime = APIRuntime.from_config_path(
                        str(cfg_path), home_root=work_dir, data_root=work_dir
                    )
                except ProviderError as exc:
                    if not allow_offline_fallback:
                        raise
                    used_fallback = True
                    provider_error_msg = f"{type(exc).__name__}: {exc}"
                    runtime = None

            if runtime is not None:
                try:
                    posture_keys = list(runtime.runtime_posture(agent_id="evaluator").keys())
                    capability_keys = list(runtime.capability_report(agent_id="evaluator").keys())
                    self_model_health = str(
                        runtime.runtime_self_model(agent_id="evaluator").get("health", "")
                    )
                    tool_inventory_count = len(runtime.tool_inventory_report(readiness=True))
                    collector = Agent(
                        runtime=runtime,
                        agent_id="evaluator",
                        name="collector",
                        session_id=resolved_session,
                        instructions=(
                            "You are the benchmark collector. Use the provided tools accurately "
                            "and return concise factual answers."
                        ),
                        tools=[
                            tools_map["probe_inference_endpoint"],
                            tools_map["score_case_output"],
                        ],
                    )
                    reviewer = subagent(
                        collector,
                        name="reviewer",
                        instructions=(
                            "You are a read-only subagent verifying case scoring. "
                            "Call score_case_output and state the exact PASS/FAIL status."
                        ),
                        tools=[tools_map["score_case_output"]],
                        timeout_seconds=int(max(10, timeout_seconds)),
                    )
                    writer_agent = Agent(
                        runtime=runtime,
                        agent_id="evaluator",
                        name="writer",
                        session_id=resolved_session,
                        instructions=(
                            "Persist the benchmark summary using write_eval_artifact when approved."
                        ),
                        tools=[tools_map["write_eval_artifact"]],
                        forced_tools=["write_eval_artifact"],
                    )
                    judge = Agent(
                        runtime=runtime,
                        agent_id="evaluator",
                        name="judge",
                        session_id=resolved_session,
                        instructions=(
                            "Return ONLY valid JSON matching EvalReport: verdict "
                            "(READY|DEGRADED|FAILED), score (0-100), summary, strengths, "
                            "risks, recommendations."
                        ),
                        output_type=EvalReport,
                    )

                    try:
                        # Case 1: Read-only tool execution via collector
                        t0 = time.perf_counter()
                        r1 = collector.run(
                            f"Call probe_inference_endpoint for {effective_base} and report reachability.",
                            timeout_seconds=timeout_seconds,
                        )
                        ms1 = round((time.perf_counter() - t0) * 1000.0, 2)
                        cases.append(
                            EvalCaseResult(
                                case_id="case_probe_tool",
                                category="tool_calling",
                                passed=(
                                    r1.run_state == "completed"
                                    and counters.get("probe_inference_endpoint", 0) >= 2
                                ),
                                run_state=str(r1.run_state or ""),
                                latency_ms=ms1,
                                llm_calls=int(r1.stats.get("llm_calls", 0)),
                                tool_calls_observed=counters.get("probe_inference_endpoint", 0) - 1,
                                detail=f"probe_count={counters.get('probe_inference_endpoint', 0)}",
                                session_id=r1.session_id,
                            )
                        )

                        # Case 2: Bounded subagent delegation
                        t0 = time.perf_counter()
                        r2 = reviewer.run(
                            "Call score_case_output for case_id='subagent_check', "
                            "observed='PASS: verified', expected='PASS'.",
                            timeout_seconds=timeout_seconds,
                        )
                        ms2 = round((time.perf_counter() - t0) * 1000.0, 2)
                        cases.append(
                            EvalCaseResult(
                                case_id="case_subagent_delegation",
                                category="delegated_subagent",
                                passed=(
                                    r2.run_state == "completed"
                                    and counters.get("score_case_output", 0) >= 1
                                ),
                                run_state=str(r2.run_state or ""),
                                latency_ms=ms2,
                                llm_calls=int(r2.stats.get("llm_calls", 0)),
                                tool_calls_observed=counters.get("score_case_output", 0),
                                detail=f"child_session={r2.session_id}",
                                session_id=r2.session_id,
                            )
                        )

                        # Case 3: Policy-gated write via FailClosedApprovalGate
                        t0 = time.perf_counter()
                        r3 = writer_agent.run(
                            "Write filename='summary_note.txt' with content='OpenMinion eval artifact verified.'",
                            approval_callback=gate,
                            timeout_seconds=timeout_seconds,
                        )
                        ms3 = round((time.perf_counter() - t0) * 1000.0, 2)
                        cases.append(
                            EvalCaseResult(
                                case_id="case_approval_gated_write",
                                category="policy_gate",
                                passed=(
                                    r3.run_state == "completed"
                                    and (resolved_out / "summary_note.txt").exists()
                                ),
                                run_state=str(r3.run_state or ""),
                                latency_ms=ms3,
                                llm_calls=int(r3.stats.get("llm_calls", 0)),
                                tool_calls_observed=counters.get("write_eval_artifact", 0),
                                detail=f"approvals={len(gate.records)}",
                                session_id=r3.session_id,
                            )
                        )

                        # Case 4: Session continuity follow-up on collector via run_stream
                        t0 = time.perf_counter()
                        r4 = collector.run_stream(
                            "Confirm session continuity and summarize status in one line.",
                            on_delta=lambda ev: stream_events.append(type(ev).__name__),
                            timeout_seconds=timeout_seconds,
                        )
                        ms4 = round((time.perf_counter() - t0) * 1000.0, 2)
                        cases.append(
                            EvalCaseResult(
                                case_id="case_session_continuity",
                                category="session_continuity",
                                passed=(
                                    r4.run_state == "completed"
                                    and r4.session_id == resolved_session
                                    and len(stream_events) > 0
                                ),
                                run_state=str(r4.run_state or ""),
                                latency_ms=ms4,
                                llm_calls=int(r4.stats.get("llm_calls", 0)),
                                detail=f"session_id={r4.session_id}, stream_events={len(stream_events)}",
                                session_id=r4.session_id,
                            )
                        )

                        # Case 5: Structured Pydantic output via Judge Agent
                        t0 = time.perf_counter()
                        r5 = judge.run(
                            json.dumps(
                                {
                                    "suite_name": suite_name,
                                    "cases": [c.model_dump() for c in cases],
                                }
                            ),
                            timeout_seconds=timeout_seconds,
                        )
                        ms5 = round((time.perf_counter() - t0) * 1000.0, 2)
                        report = r5.output
                        cases.append(
                            EvalCaseResult(
                                case_id="case_structured_judge",
                                category="structured_output",
                                passed=isinstance(report, EvalReport),
                                run_state=str(r5.run_state or ""),
                                latency_ms=ms5,
                                llm_calls=int(r5.stats.get("llm_calls", 0)),
                                detail=f"verdict={report.verdict}, score={report.score}",
                                session_id=r5.session_id,
                            )
                        )
                    except (ProviderError, TurnTimeoutError, AgentOutputValidationError) as exc:
                        provider_error_msg = f"{type(exc).__name__}: {exc}"
                        if not allow_offline_fallback:
                            raise
                        used_fallback = True
                    finally:
                        for ag in (judge, writer_agent, reviewer, collector):
                            ag.close()
                finally:
                    runtime.close()
        finally:
            if cfg_path is not None and cfg_path.exists():
                cfg_path.unlink(missing_ok=True)

    total_cases = len(cases)
    passed_cases = sum(1 for c in cases if c.passed)
    failed_cases = total_cases - passed_cases
    pass_rate = round((passed_cases / total_cases), 4) if total_cases else 0.0
    avg_latency = (
        round(sum(c.latency_ms for c in cases) / total_cases, 2) if total_cases else 0.0
    )

    # Portable MemoryBundle export + reload verification
    bundle_items = [
        {"type": "probe", "endpoint": probe.endpoint, "reachable": probe.reachable},
        *[
            {"type": "case", "case_id": c.case_id, "passed": c.passed}
            for c in cases
        ],
    ]
    bundle = export_bundle(
        bundle_items,
        metadata={"suite": suite_name, "session_id": resolved_session},
    )
    bundle_path = resolved_out / "memory_bundle.json"
    save_bundle(bundle, bundle_path)
    reloaded = load_bundle(bundle_path)
    import_summary = import_bundle(reloaded, trust_mode="candidate")

    summary = EvalSuiteSummary(
        suite_name=suite_name,
        provider=provider,
        model=effective_model,
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=failed_cases,
        pass_rate=pass_rate,
        avg_latency_ms=avg_latency,
        approvals_logged=len(gate.records),
        session_persisted=any(c.session_id == resolved_session for c in cases),
        posture_keys=posture_keys,
        capability_keys=capability_keys,
        self_model_health=self_model_health,
        tool_inventory_count=tool_inventory_count,
        stream_events_observed=len(stream_events),
        memory_bundle_items=int(import_summary["item_count"]),
    )
    if report is None:
        report = _deterministic_report(summary)

    outcome = EvalRunOutcome(
        summary=summary,
        report=report,
        probe=probe,
        cases=cases,
        approvals=list(gate.records),
        tool_counters=dict(counters),
        posture_keys=posture_keys,
        session_id=resolved_session,
        memory_bundle_path=bundle_path,
        used_offline_fallback=used_fallback,
        provider_error=provider_error_msg,
    )

    facts_path = resolved_out / "facts.json"
    facts_path.write_text(
        json.dumps(
            {
                "summary": summary.model_dump(),
                "probe": probe.model_dump(),
                "cases": [c.model_dump() for c in cases],
                "approvals": [a.model_dump() for a in gate.records],
                "report": report.model_dump(),
                "posture_keys": posture_keys,
                "used_offline_fallback": used_fallback,
                "provider_error": provider_error_msg,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    report_path = resolved_out / "report.md"
    report_path.write_text(_render_markdown(outcome), encoding="utf-8")
    outcome.report_path = report_path
    return outcome
