"""OpenMinion 0.1 multi-agent release gate workflow and SDK probe runner."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from openminion import Agent, APIRuntime, Handoff, subagent
from openminion import __version__ as OPENMINION_VERSION

from cortensor_release_gate.loopback_server import running_loopback_server
from cortensor_release_gate.memory_store import (
    diff_findings,
    load_prior_check_ids,
    record_audit_memory,
)
from cortensor_release_gate.models import (
    AuditFinding,
    CortensorWiringReport,
    DocsAuditReport,
    GateDecision,
    ProbeCheckResult,
    ProbeMatrixReport,
    ReleaseGateVerdict,
    SecurityAuditReport,
    TriageAction,
    TriagePlan,
)
from cortensor_release_gate.runtime import RuntimeSettings, create_isolated_runtime
from cortensor_release_gate.scanners import (
    scan_cortensor_wiring,
    scan_repository_docs,
    scan_repository_security,
)
from cortensor_release_gate.tools import (
    scan_cortensor_wiring_tool,
    scan_docs_tool,
    scan_security_tool,
    write_release_gate_report,
)

ApprovalHandler = Callable[[str, dict[str, Any], str], bool]


def _default_approval_callback(tool_name: str, args: dict[str, Any], approval_id: str) -> bool:
    del tool_name, args, approval_id
    return False


def _render_markdown_report(
    *,
    target_path: Path,
    decision: GateDecision,
    security: SecurityAuditReport,
    docs: DocsAuditReport,
    wiring: CortensorWiringReport,
    resolved: list[str],
    persistent: list[str],
    triage_plan: TriagePlan | None,
) -> str:
    lines = [
        "# Cortensor Release Gate Report",
        "",
        f"- Target: `{target_path}`",
        f"- Decision: **{decision}**",
        f"- OpenMinion SDK: `{OPENMINION_VERSION}`",
        "",
        "## Security Scan",
        f"- Status: {'PASS' if security.passed else 'FAIL'} ({security.summary})",
        "",
        "## Documentation & Manifests",
        f"- Status: {'PASS' if docs.passed else 'FAIL'} ({docs.summary})",
        f"- Present: {', '.join(docs.present_files) or 'none'}",
        f"- Missing: {', '.join(docs.missing_files) or 'none'}",
        "",
        "## Cortensor & OpenMinion Wiring",
        f"- Imports openminion: `{wiring.uses_openminion}`",
        f"- Dependency pin: `{wiring.openminion_pin or 'unpinned'}`",
        f"- Tests present: `{wiring.has_tests}`",
        f"- Endpoints: {', '.join(wiring.cortensor_endpoints_detected) or 'none'}",
        "",
        "## Memory Diff Across Runs",
        f"- Resolved since last run: {', '.join(resolved) or 'none'}",
        f"- Persistent from last run: {', '.join(persistent) or 'none'}",
    ]
    all_findings = [*security.findings, *docs.findings, *wiring.findings]
    if all_findings:
        lines.extend(["", "## Findings", ""])
        for item in all_findings:
            lines.append(
                f"- `[{item.severity.upper()}]` **{item.check_id}** (`{item.path}`): "
                f"{item.message} Remediation: {item.remediation}"
            )
    if triage_plan is not None and triage_plan.actions:
        lines.extend(["", "## Triage Plan", ""])
        for act in triage_plan.actions:
            lines.append(
                f"{act.priority}. `{act.check_id}` ({act.owner_area}): {act.action}"
            )
    return "\n".join(lines) + "\n"


def _compute_decision(findings: list[AuditFinding]) -> tuple[GateDecision, list[str], list[str]]:
    blockers = [
        f"{f.check_id}: {f.message}"
        for f in findings
        if f.severity in {"critical", "high"}
    ]
    warnings = [
        f"{f.check_id}: {f.message}"
        for f in findings
        if f.severity in {"medium", "low"}
    ]
    if blockers:
        return "BLOCKED", blockers, warnings
    if warnings:
        return "CHANGES_REQUIRED", blockers, warnings
    return "READY", blockers, warnings


def _build_triage_actions(findings: list[AuditFinding]) -> list[TriageAction]:
    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    ordered = sorted(findings, key=lambda item: severity_rank[item.severity])
    return [
        TriageAction(
            priority=idx + 1,
            check_id=item.check_id,
            owner_area=item.category,
            action=item.remediation,
        )
        for idx, item in enumerate(ordered)
    ]


def _run_with_runtime(
    runtime: APIRuntime,
    *,
    target_dir: Path,
    output_dir: Path,
    memory_path: Path,
    write_report: bool,
    approval_callback: ApprovalHandler | None,
) -> ReleaseGateVerdict:
    resolved_target = target_dir.resolve()
    resolved_output = output_dir.resolve()

    coordinator: Agent[str, ReleaseGateVerdict] = Agent(
        name="release_gate_coordinator",
        runtime=runtime,
        instructions=(
            "Coordinate release readiness checks using scoped subagents, handoffs, "
            "and approval-gated artifact export."
        ),
        tools=[scan_cortensor_wiring_tool, write_release_gate_report],
        output_type=ReleaseGateVerdict,
    )

    sec_agent = subagent(
        coordinator,
        name="security_auditor",
        instructions="Run scan_security_tool on the target directory and return SecurityAuditReport JSON.",
        tools=[scan_security_tool],
        output_type=SecurityAuditReport,
    )
    docs_agent = subagent(
        coordinator,
        name="docs_auditor",
        instructions="Run scan_docs_tool on the target directory and return DocsAuditReport JSON.",
        tools=[scan_docs_tool],
        output_type=DocsAuditReport,
    )
    wiring_agent = subagent(
        coordinator,
        name="wiring_auditor",
        instructions="Run scan_cortensor_wiring_tool on the target directory and return CortensorWiringReport JSON.",
        tools=[scan_cortensor_wiring_tool],
        output_type=CortensorWiringReport,
    )

    sec_result = sec_agent.run(f"SECURITY_AUDIT TARGET_DIR={resolved_target}")
    docs_result = docs_agent.run(f"DOCS_AUDIT TARGET_DIR={resolved_target}")
    wiring_result = wiring_agent.run(f"WIRING_AUDIT TARGET_DIR={resolved_target}")

    # Reconcile with deterministic scanners so remote LLM paraphrasing never drops a finding.
    det_sec = scan_repository_security(resolved_target)
    det_docs = scan_repository_docs(resolved_target)
    det_wiring = scan_cortensor_wiring(resolved_target)

    sec_report = (
        sec_result.output
        if len(sec_result.output.findings) >= len(det_sec.findings)
        and sec_result.output.files_scanned > 0
        else det_sec
    )
    docs_report = (
        docs_result.output
        if len(docs_result.output.findings) >= len(det_docs.findings)
        and docs_result.output.present_files
        else det_docs
    )
    wiring_report = (
        wiring_result.output
        if wiring_result.output.uses_openminion == det_wiring.uses_openminion
        and len(wiring_result.output.findings) >= len(det_wiring.findings)
        else det_wiring
    )

    all_findings = [
        *sec_report.findings,
        *docs_report.findings,
        *wiring_report.findings,
    ]
    decision, blockers, warnings = _compute_decision(all_findings)

    prior_ids = load_prior_check_ids(memory_path)
    current_blocker_ids = [
        f.check_id for f in all_findings if f.severity in {"critical", "high"}
    ]
    warning_ids = [
        f.check_id for f in all_findings if f.severity in {"medium", "low"}
    ]
    resolved_ids, persistent_ids = diff_findings(prior_ids, current_blocker_ids)

    triage_plan: TriagePlan | None = None
    if all_findings:
        triage_agent: Agent[str, TriagePlan] = Agent(
            name="triage_planner",
            runtime=runtime,
            instructions="Produce a concise TriagePlan JSON for failed release checks.",
            output_type=TriagePlan,
        )
        triage_coordinator: Agent[str, TriagePlan] = Agent(
            name="triage_router",
            runtime=runtime,
            instructions="Delegate remediation planning to triage_planner.",
            handoffs=[Handoff(target=triage_agent, name="transfer_to_triage_planner")],
            output_type=TriagePlan,
        )
        triage_res = triage_coordinator.run(
            f"TRIAGE_PLAN TARGET_DIR={resolved_target} DECISION={decision}",
            approval_callback=lambda tool_name, _args, _aid: (
                tool_name == "transfer_to_triage_planner"
            ),
        )
        triage_plan = triage_res.output
        if not triage_plan.actions or len(triage_plan.actions) < len(all_findings):
            triage_plan = TriagePlan(
                decision=decision,
                actions=_build_triage_actions(all_findings),
                summary=triage_plan.summary,
            )

    markdown = _render_markdown_report(
        target_path=resolved_target,
        decision=decision,
        security=sec_report,
        docs=docs_report,
        wiring=wiring_report,
        resolved=resolved_ids,
        persistent=persistent_ids,
        triage_plan=triage_plan,
    )

    report_written = False
    report_path: str | None = None
    effective_approval = approval_callback or _default_approval_callback
    if write_report:
        export_agent: Agent[str, ReleaseGateVerdict] = Agent(
            name="report_exporter",
            runtime=runtime,
            instructions="Write the release gate report when approved by the caller.",
            tools=[write_release_gate_report],
            forced_tools=["write_release_gate_report"],
            output_type=ReleaseGateVerdict,
        )
        try:
            export_res = export_agent.run(
                (
                    f"RELEASE_GATE_SYNTHESIS TARGET_DIR={resolved_target} "
                    f"OUTPUT_DIR={resolved_output} HAS_BLOCKERS={1 if blockers else 0} "
                    "WRITE_REPORT=1"
                ),
                approval_callback=effective_approval,
            )
            if export_res.output.report_written:
                # Overwrite with the deterministic full markdown & verdict payload so
                # live LLM paraphrasing never drops verified findings.
                verdict_payload = ReleaseGateVerdict(
                    target_path=str(resolved_target),
                    decision=decision,
                    blockers=blockers,
                    warnings=warnings,
                    resolved_since_last_run=resolved_ids,
                    persistent_from_last_run=persistent_ids,
                    triage_plan=triage_plan,
                    report_written=True,
                    report_path=str((resolved_output / "RELEASE_GATE_REPORT.md").resolve()),
                    summary=(
                        f"Decision {decision}: {len(blockers)} blocker(s), "
                        f"{len(warnings)} warning(s)."
                    ),
                )
                write_res = write_release_gate_report(
                    output_dir=str(resolved_output),
                    markdown_report=markdown,
                    summary_json=verdict_payload.model_dump_json(indent=2),
                )
                report_written = bool(write_res.get("written"))
                report_path = str(write_res.get("markdown_path"))
        except Exception as exc:  # noqa: BLE001
            # OpenMinion aborts or raises when approval_callback returns False.
            warnings.append(f"REPORT-EXPORT-DECLINED: {exc}")

    record_audit_memory(
        memory_path,
        target_path=str(resolved_target),
        decision=decision,
        blocker_ids=current_blocker_ids,
        warning_ids=warning_ids,
    )

    return ReleaseGateVerdict(
        target_path=str(resolved_target),
        decision=decision,
        blockers=blockers,
        warnings=warnings,
        resolved_since_last_run=resolved_ids,
        persistent_from_last_run=persistent_ids,
        triage_plan=triage_plan,
        report_written=report_written,
        report_path=report_path,
        summary=(
            f"Decision {decision}: {len(blockers)} blocker(s), {len(warnings)} warning(s). "
            f"Security scanned {sec_report.files_scanned} file(s)."
        ),
    )


def run_release_gate(
    *,
    target_dir: Path,
    output_dir: Path | None = None,
    state_root: Path | None = None,
    memory_path: Path | None = None,
    settings: RuntimeSettings | None = None,
    demo_local: bool = False,
    write_report: bool = False,
    approval_callback: ApprovalHandler | None = None,
) -> ReleaseGateVerdict:
    """Execute the full OpenMinion release gate workflow against target_dir."""
    resolved_target = target_dir.resolve()
    resolved_output = (output_dir or resolved_target).resolve()
    resolved_state = (state_root or (resolved_output / ".openminion" / "gate_state")).resolve()
    resolved_memory = (memory_path or (resolved_output / "audit_memory.json")).resolve()

    if demo_local:
        with running_loopback_server() as server:
            loopback_settings = RuntimeSettings(
                provider="cortensor",
                model="gpt-oss-20b",
                base_url=server.base_url,
                api_key="demo-local-key",
                api_mode="openai_chat",
            )
            runtime = create_isolated_runtime(loopback_settings, state_root=resolved_state)
            try:
                return _run_with_runtime(
                    runtime,
                    target_dir=resolved_target,
                    output_dir=resolved_output,
                    memory_path=resolved_memory,
                    write_report=write_report,
                    approval_callback=approval_callback,
                )
            finally:
                runtime.close()

    if settings is None:
        raise ValueError("settings must be provided when demo_local is False")
    runtime = create_isolated_runtime(settings, state_root=resolved_state)
    try:
        return _run_with_runtime(
            runtime,
            target_dir=resolved_target,
            output_dir=resolved_output,
            memory_path=resolved_memory,
            write_report=write_report,
            approval_callback=approval_callback,
        )
    finally:
        runtime.close()


def _timed_probe(name: str, fn: Callable[[], dict[str, str]]) -> ProbeCheckResult:
    started = time.perf_counter()
    try:
        details = fn()
        return ProbeCheckResult(
            block_name=name,
            passed=True,
            duration_ms=round((time.perf_counter() - started) * 1000.0, 2),
            details=details,
        )
    except Exception as exc:  # noqa: BLE001
        return ProbeCheckResult(
            block_name=name,
            passed=False,
            duration_ms=round((time.perf_counter() - started) * 1000.0, 2),
            error=str(exc),
        )


def run_building_block_probes(
    *,
    target_dir: Path,
    state_root: Path,
) -> ProbeMatrixReport:
    """Exercise core OpenMinion 0.1.23 building blocks and collect measured telemetry."""
    resolved_target = target_dir.resolve()
    checks: list[ProbeCheckResult] = []

    with running_loopback_server() as server:
        settings = RuntimeSettings(
            provider="cortensor",
            model="gpt-oss-20b",
            base_url=server.base_url,
            api_key="probe-local-key",
            api_mode="openai_chat",
        )
        runtime = create_isolated_runtime(settings, state_root=state_root / "runtime_probe")
        try:
            checks.append(
                _timed_probe(
                    "runtime_diagnostics",
                    lambda: {
                        "tools_count": str(len(runtime.tool_inventory_report())),
                        "posture_keys": str(len(runtime.runtime_posture())),
                        "self_model_keys": str(len(runtime.runtime_self_model())),
                    },
                )
            )

            coordinator: Agent[str, SecurityAuditReport] = Agent(
                name="probe_coordinator",
                runtime=runtime,
                tools=[scan_security_tool, write_release_gate_report],
                output_type=SecurityAuditReport,
            )

            def _probe_tool_and_typed_output() -> dict[str, str]:
                res = coordinator.run(f"SECURITY_AUDIT TARGET_DIR={resolved_target}")
                return {
                    "run_id": str(res.run_id or ""),
                    "run_state": str(res.run_state or ""),
                    "files_scanned": str(res.output.files_scanned),
                }

            checks.append(_timed_probe("agent_tool_and_output_type", _probe_tool_and_typed_output))

            def _probe_subagent() -> dict[str, str]:
                child = subagent(
                    coordinator,
                    name="probe_docs_child",
                    tools=[scan_docs_tool],
                    output_type=DocsAuditReport,
                )
                res = child.run(f"DOCS_AUDIT TARGET_DIR={resolved_target}")
                return {
                    "subagent_session_id": str(res.session_id or ""),
                    "present_files": str(len(res.output.present_files)),
                }

            checks.append(_timed_probe("subagent_isolation", _probe_subagent))

            def _probe_handoff() -> dict[str, str]:
                target: Agent[str, TriagePlan] = Agent(
                    name="probe_triage_target",
                    runtime=runtime,
                    output_type=TriagePlan,
                )
                router: Agent[str, TriagePlan] = Agent(
                    name="probe_triage_router",
                    runtime=runtime,
                    handoffs=[Handoff(target=target, name="transfer_to_triage_planner")],
                    output_type=TriagePlan,
                )
                res = router.run(
                    f"TRIAGE_PLAN TARGET_DIR={resolved_target}",
                    approval_callback=lambda tool_name, _args, _aid: (
                        tool_name == "transfer_to_triage_planner"
                    ),
                )
                return {
                    "decision": res.output.decision,
                    "actions_count": str(len(res.output.actions)),
                }

            checks.append(_timed_probe("handoff_delegation", _probe_handoff))

            def _probe_approval_gate() -> dict[str, str]:
                seen_approvals: list[str] = []
                export_dir = state_root / "probe_export"
                exporter: Agent[str, ReleaseGateVerdict] = Agent(
                    name="probe_exporter",
                    runtime=runtime,
                    tools=[write_release_gate_report],
                    forced_tools=["write_release_gate_report"],
                    output_type=ReleaseGateVerdict,
                )

                def _approve(tool_name: str, args: dict[str, Any], approval_id: str) -> bool:
                    del args
                    seen_approvals.append(f"{tool_name}:{approval_id}")
                    return True

                res = exporter.run(
                    (
                        f"RELEASE_GATE_SYNTHESIS TARGET_DIR={resolved_target} "
                        f"OUTPUT_DIR={export_dir} HAS_BLOCKERS=0 WRITE_REPORT=1"
                    ),
                    approval_callback=_approve,
                )
                return {
                    "approvals_triggered": str(len(seen_approvals)),
                    "report_written": str(res.output.report_written),
                }

            checks.append(_timed_probe("approval_callback_gate", _probe_approval_gate))

            def _probe_memory_bundle() -> dict[str, str]:
                bundle_file = state_root / "probe_memory.json"
                record_audit_memory(
                    bundle_file,
                    target_path=str(resolved_target),
                    decision="READY",
                    blocker_ids=[],
                    warning_ids=[],
                )
                loaded = load_prior_check_ids(bundle_file)
                return {
                    "bundle_exists": str(bundle_file.is_file()),
                    "loaded_blockers": str(len(loaded)),
                }

            checks.append(_timed_probe("memory_bundle_portability", _probe_memory_bundle))

            def _probe_cortensor_completion_mode() -> dict[str, str]:
                comp_settings = RuntimeSettings(
                    provider="cortensor",
                    model="gpt-oss-20b",
                    base_url=server.completion_url,
                    api_key="probe-local-key",
                    api_mode="cortensor_completion",
                    session_id=7,
                )
                comp_runtime = create_isolated_runtime(
                    comp_settings, state_root=state_root / "cortensor_completion_probe"
                )
                try:
                    comp_agent: Agent[str, str] = Agent(
                        name="probe_completion", runtime=comp_runtime
                    )
                    res = comp_agent.run("Ping completion mode")
                    raw_json = res.text[res.text.find("{") :]
                    parsed = json.loads(raw_json)
                    return {
                        "mode": str(parsed.get("mode")),
                        "ok": str(parsed.get("ok")),
                    }
                finally:
                    comp_runtime.close()

            checks.append(_timed_probe("cortensor_completion_mode", _probe_cortensor_completion_mode))

            def _probe_subagent_memory_guard() -> dict[str, str]:
                try:
                    subagent(
                        coordinator,
                        name="probe_guarded_child",
                        memory_posture="read_only_bounded",
                    )
                except ValueError as exc:
                    return {
                        "guard_raised": "True",
                        "message": str(exc),
                    }
                raise RuntimeError("Expected ValueError for read_only_bounded subagent posture")

            checks.append(_timed_probe("subagent_memory_guard", _probe_subagent_memory_guard))

            def _probe_forced_tools_and_capabilities() -> dict[str, str]:
                forced_agent: Agent[str, DocsAuditReport] = Agent(
                    name="probe_forced_docs",
                    runtime=runtime,
                    tools=[scan_docs_tool],
                    forced_tools=["scan_docs_tool"],
                    output_type=DocsAuditReport,
                )
                res = forced_agent.run(f"DOCS_AUDIT TARGET_DIR={resolved_target}")
                cap_report = runtime.capability_report()
                custom_schema = runtime.tool_schema_report(tool_name="scan_docs_tool")
                return {
                    "present_files": str(len(res.output.present_files)),
                    "capability_keys": str(len(cap_report)),
                    "custom_tool_schema_found": str(custom_schema is not None),
                }

            checks.append(
                _timed_probe(
                    "forced_tools_and_capabilities",
                    _probe_forced_tools_and_capabilities,
                )
            )

            def _probe_session_continuity() -> dict[str, str]:
                sess_agent: Agent[str, SecurityAuditReport] = Agent(
                    name="probe_session_agent",
                    runtime=runtime,
                    tools=[scan_security_tool],
                    output_type=SecurityAuditReport,
                )
                first = sess_agent.run(
                    f"SECURITY_AUDIT TARGET_DIR={resolved_target}",
                    session_id="probe-continuity-1",
                )
                second = sess_agent.run(
                    f"SECURITY_AUDIT TARGET_DIR={resolved_target}",
                    session_id="probe-continuity-1",
                )
                return {
                    "session_id": str(second.session_id or ""),
                    "turns_matched": str(first.session_id == second.session_id),
                    "second_files_scanned": str(second.output.files_scanned),
                }

            checks.append(_timed_probe("session_continuity_turns", _probe_session_continuity))
        finally:
            runtime.close()

    return ProbeMatrixReport(
        openminion_version=OPENMINION_VERSION,
        provider_mode="cortensor-loopback",
        checks=checks,
        all_passed=all(c.passed for c in checks),
    )
