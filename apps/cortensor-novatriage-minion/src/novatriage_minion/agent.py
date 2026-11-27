"""OpenMinion Agent, bounded subagent, and Handoff orchestration for NovaTriage Minion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from openminion import APIRuntime, Agent, AgentRunResult, Handoff, subagent

from .local_model import NovaTriageLocalModelServer, build_openminion_config_file
from .models import NovaTriageReport, ReconBundleResult, SolidityAuditResult, SubagentDelegationSummary
from .policy import NovaTriageApprovalGate
from .runtime_services import (
    collect_runtime_diagnostics,
    persist_triage_memory_bundle,
    schedule_watchlist_task,
    setup_novatriage_skill,
)
from .tools import (
    analyze_solidity_contract,
    fetch_token_onchain_preflight,
    probe_x402_endpoint,
    publish_emergency_freeze_notice,
    recall_triage_memory,
    write_triage_report,
)


@dataclass
class NovaTriageRunSummary:
    """Complete end-to-end result across all OpenMinion 0.1 building blocks."""

    report: NovaTriageReport
    session_id: str
    thread_id: str | None
    run_id: str | None
    run_state: str | None
    stream_events_seen: int
    followup_reply: str
    subagent_checks: list[dict[str, Any]]
    skill_summary: dict[str, Any]
    memory_summary: dict[str, Any]
    task_summary: dict[str, Any]
    diagnostics: dict[str, Any]
    approval_decisions: list[dict[str, Any]]
    written_report_path: str | None = None


def run_novatriage_workflow(
    *,
    workspace_dir: Path,
    contract_path: Path,
    token_address: str = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    chain_id: str = "base",
    x402_base_url: str = "",
    provider: str = "local",
    model: str = "",
    allow_report_write: bool = True,
    schedule_watchlist: bool = True,
    run_followup: bool = True,
    run_bounded_subagent_check: bool = True,
    session_id: str | None = None,
) -> NovaTriageRunSummary:
    """Execute the full NovaTriage Minion workflow on OpenMinion 0.1."""
    workspace_dir.mkdir(parents=True, exist_ok=True)
    home_root = workspace_dir / ".openminion" / "home"
    data_root = workspace_dir / ".openminion" / "data"
    config_path = workspace_dir / ".openminion" / "config.json"
    memory_bundle_path = workspace_dir / "artifacts" / "novatriage_memory_bundle.json"
    report_output_path = workspace_dir / "artifacts" / f"{contract_path.stem}_triage_report.json"

    skill_path = Path(__file__).resolve().parents[2] / "skills" / "novatriage-solidity-audit.md"
    if not skill_path.exists():
        skill_path = workspace_dir / "skills" / "novatriage-solidity-audit.md"

    local_server: NovaTriageLocalModelServer | None = None
    if provider == "local":
        local_server = NovaTriageLocalModelServer.start()

    try:
        build_openminion_config_file(
            config_path,
            provider=provider,
            model=model,
            local_base_url=local_server.base_url if local_server else "",
        )
        runtime = APIRuntime.from_config_path(
            str(config_path),
            home_root=str(home_root),
            data_root=str(data_root),
        )
        # Separate runtimes for Handoff peers avoid OpenMinion 0.1.24's cross-thread
        # shared-runtime ToolRegistry deadlock inside Handoff tool execution.
        sol_runtime = APIRuntime.from_config_path(
            str(config_path),
            home_root=str(workspace_dir / ".openminion" / "peer-sol" / "home"),
            data_root=str(workspace_dir / ".openminion" / "peer-sol" / "data"),
        )
        recon_runtime = APIRuntime.from_config_path(
            str(config_path),
            home_root=str(workspace_dir / ".openminion" / "peer-recon" / "home"),
            data_root=str(workspace_dir / ".openminion" / "peer-recon" / "data"),
        )
        try:
            active_session_id = session_id or f"novatriage-{uuid4().hex[:8]}"
            gate = NovaTriageApprovalGate(
                allow_report_write=allow_report_write,
                allow_dangerous_freeze=False,
            )

            # 1. Modular Skill ingestion, verification, matching & snippet rendering
            skill_summary: dict[str, Any] = {}
            if skill_path.exists():
                skill_summary = setup_novatriage_skill(
                    skill_markdown_path=skill_path,
                    home_root=home_root,
                    known_tools=[
                        "analyze_solidity_contract",
                        "fetch_token_onchain_preflight",
                        "probe_x402_endpoint",
                        "recall_triage_memory",
                        "write_triage_report",
                    ],
                )

            # 2a. Bounded subagent() verification on parent runtime (exercises SubagentRunContext)
            subagent_checks: list[dict[str, Any]] = []
            if run_bounded_subagent_check:
                coordinator_seed = Agent(
                    runtime=runtime,
                    name="novatriage_coordinator",
                    instructions="Parent coordinator for bounded subagent execution.",
                )
                bounded_auditor = subagent(
                    coordinator_seed,
                    name="bounded_solidity_subagent",
                    instructions="Run deterministic Solidity static analysis and return JSON findings.",
                    tools=[analyze_solidity_contract],
                    timeout_seconds=45,
                )
                sub_res = bounded_auditor.run(
                    f"Audit contract_path={contract_path} target_name={contract_path.name}"
                )
                ctx = bounded_auditor.subagent_context
                subagent_checks.append(
                    {
                        "context_id": ctx.context_id if ctx else "",
                        "child_agent_id": ctx.child_agent_id if ctx else "bounded_solidity_subagent",
                        "tool_allowlist": list(ctx.tool_allowlist) if ctx else [],
                        "parent_transcript_inherited": ctx.parent_transcript_inherited if ctx else False,
                        "run_state": sub_res.run_state,
                    }
                )

            # 2b. Peer Agents wired via Handoff for nested coordinator.run_stream() execution
            solidity_peer = Agent[str, SolidityAuditResult](
                runtime=sol_runtime,
                name="solidity_auditor_minion",
                instructions="Run deterministic Solidity static analysis and return SolidityAuditResult JSON.",
                tools=[analyze_solidity_contract],
                output_type=SolidityAuditResult,
            )
            recon_peer = Agent[str, ReconBundleResult](
                runtime=recon_runtime,
                name="recon_minion",
                instructions="Run live public token preflight and HTTP 402 x402 challenge probes.",
                tools=[fetch_token_onchain_preflight, probe_x402_endpoint],
                output_type=ReconBundleResult,
            )

            coordinator = Agent[str, NovaTriageReport](
                runtime=runtime,
                name="novatriage_coordinator",
                instructions=(
                    "You are NovaTriageCoordinator. Recall prior memory if present, delegate Solidity "
                    "scanning to solidity_auditor_minion, delegate live preflight + x402 checks to "
                    "recon_minion, optionally persist the report, and return a NovaTriageReport JSON."
                ),
                tools=[
                    recall_triage_memory,
                    write_triage_report,
                    publish_emergency_freeze_notice,
                ],
                handoffs=[
                    Handoff(
                        target=solidity_peer,
                        name="transfer_to_solidity_auditor_minion",
                        description="Delegate read-only Solidity static analysis to SolidityAuditorMinion.",
                    ),
                    Handoff(
                        target=recon_peer,
                        name="transfer_to_recon_minion",
                        description="Delegate live DexScreener/GoPlus & x402 probing to ReconMinion.",
                    ),
                ],
                output_type=NovaTriageReport,
                session_id=active_session_id,
            )

            stream_events: list[object] = []
            prompt = (
                f"Triage target_name={contract_path.name} "
                f"contract_path={contract_path} "
                f"token_address={token_address} "
                f"chain_id={chain_id} "
            )
            if x402_base_url:
                prompt += f"x402_base_url={x402_base_url} "
            if memory_bundle_path.exists():
                prompt += f"memory_bundle={memory_bundle_path} "
            if allow_report_write:
                prompt += f"output_path={report_output_path} "

            result: AgentRunResult[NovaTriageReport] = coordinator.run_stream(
                prompt,
                session_id=active_session_id,
                on_delta=stream_events.append,
                approval_callback=gate,
            )

            # Attach bounded subagent summary to report delegations if not already listed
            if subagent_checks and not any(
                d.agent_name == "bounded_solidity_subagent" for d in result.output.delegations
            ):
                result.output.delegations.append(
                    SubagentDelegationSummary(
                        agent_name="bounded_solidity_subagent",
                        role="Bounded openminion.subagent (SubagentRunContext)",
                        tool_allowlist=subagent_checks[0]["tool_allowlist"],
                        run_state=str(subagent_checks[0]["run_state"] or "completed"),
                        summary=f"context_id={subagent_checks[0]['context_id']}",
                    )
                )

            # 3. Persist verdict into portable OpenMinion MemoryBundle
            memory_summary = persist_triage_memory_bundle(
                report=result.output,
                bundle_path=memory_bundle_path,
            )

            # 4. Multi-turn session follow-up reusing session_id + thread_id in SQLite
            followup_reply = ""
            if run_followup:
                followup_agent = Agent(
                    runtime=runtime,
                    name="novatriage_coordinator",
                    instructions="Answer concise follow-up questions grounded in the prior triage session.",
                    session_id=active_session_id,
                )
                followup_res = followup_agent.run(
                    f"FOLLOWUP: Summarize the verdict and top risk findings for {contract_path.name}.",
                    session_id=active_session_id,
                    thread_id=result.thread_id,
                )
                followup_reply = followup_res.text

            # 5. Task scheduling & inspection via OpenMinion task surface
            task_summary: dict[str, Any] = {}
            if schedule_watchlist:
                task_summary = schedule_watchlist_task(
                    runtime,
                    target_label=contract_path.stem,
                    token_address=token_address,
                    session_id=active_session_id,
                )

            # 6. Runtime posture, self-model, capability & tool inventory diagnostics
            diagnostics = collect_runtime_diagnostics(runtime)

            return NovaTriageRunSummary(
                report=result.output,
                session_id=result.session_id or active_session_id,
                thread_id=result.thread_id,
                run_id=result.run_id,
                run_state=result.run_state,
                stream_events_seen=len(stream_events),
                followup_reply=followup_reply,
                subagent_checks=subagent_checks,
                skill_summary=skill_summary,
                memory_summary=memory_summary,
                task_summary=task_summary,
                diagnostics=diagnostics,
                approval_decisions=[d.model_dump(mode="json") for d in gate.decisions],
                written_report_path=str(report_output_path) if report_output_path.exists() else None,
            )
        finally:
            recon_runtime.close()
            sol_runtime.close()
            runtime.close()
    finally:
        if local_server is not None:
            local_server.close()
