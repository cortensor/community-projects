"""Typer CLI for Cortensor Router Doctor (demo-sim, audit, verify-sdk-bugs)."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import tempfile
import threading
import time
from typing import Any, Literal, Optional

for _noisy in ("openminion", "alembic", "httpx", "httpcore", "sophiagraph"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import typer

from cortensor_router_doctor.agent import (
    ProviderPreset,
    build_audit_agent,
    build_forensics_handoff,
    create_isolated_runtime,
    run_audit,
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
    RouterAuditReport,
    SLAPolicyEvaluation,
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

app = typer.Typer(
    name="cortensor-router-doctor",
    help=(
        "Cortensor Router & Node SLA Diagnostic, Proof-of-Inference (PoI) Consensus Drift "
        "Auditor, and Approval-Gated Incident Remediation Agent powered by OpenMinion 0.1.24."
    ),
    no_args_is_help=True,
)
console = Console()


def _render_report_table(title: str, report: RouterAuditReport) -> None:
    table = Table(title=title, show_lines=True)
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")
    table.add_row("Endpoint", report.endpoint_url)
    verdict_style = {
        "HEALTHY": "bold green",
        "DEGRADED": "bold yellow",
        "CRITICAL_DRIFT": "bold red",
    }[report.verdict]
    table.add_row("Verdict", f"[{verdict_style}]{report.verdict}[/{verdict_style}]")
    table.add_row("Recommended Action", report.recommended_action)
    table.add_row("p95 Latency (ms)", f"{report.measured_p95_ms:.2f}")
    table.add_row("PoI Agreement", f"{report.measured_poi_agreement:.4f}")
    table.add_row("HTTP Success Rate", f"{report.measured_success_rate:.4f}")
    table.add_row("Quarantine Applied", str(report.quarantine_applied))
    table.add_row("Quarantine File", str(report.quarantine_file or "None"))
    table.add_row("Violations", ", ".join(report.violations) if report.violations else "None")
    table.add_row("Summary", report.summary)
    console.print(table)


@app.command("demo-sim")
def demo_sim(
    provider: ProviderPreset = typer.Option(
        "ollama",
        "--provider",
        help="OpenMinion LLM provider preset: ollama, cortensor-portal, or cortensor-router.",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help="Model name override (default: qwen2.5:1.5b for Ollama, gpt-oss-20b for Cortensor).",
    ),
    base_url: Optional[str] = typer.Option(
        None,
        "--base-url",
        help="Optional provider base URL override.",
    ),
    api_key: str = typer.Option(
        "",
        "--api-key",
        envvar="CORTENSOR_API_KEY",
        help="Optional API key (reads CORTENSOR_API_KEY env var by default).",
    ),
    rounds: int = typer.Option(
        3,
        "--rounds",
        min=2,
        max=10,
        help="Number of redundant PoI inference rounds per node.",
    ),
    timeout: float = typer.Option(
        180.0,
        "--timeout",
        help="Per-turn timeout in seconds.",
    ),
    output_dir: Path = typer.Option(
        Path("outputs"),
        "--output-dir",
        help="Directory where quarantine directives, MemoryBundleSnapshot, and receipt are saved.",
    ),
) -> None:
    """Spin up local healthy & poi_drift Cortensor Router simulators and run full OpenMinion agent demos."""
    out_dir = output_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = out_dir / "live_run_receipt.json"
    bundle_path = out_dir / "router_doctor_memory_bundle.tar.gz"
    quarantine_denied_file = out_dir / "quarantine_denied.json"
    quarantine_approved_file = out_dir / "quarantine_approved.json"

    console.print(
        Panel.fit(
            f"[bold cyan]Cortensor Router Doctor — Live OpenMinion 0.1.24 Simulator Demo[/bold cyan]\n"
            f"Provider: [bold]{provider}[/bold] | Model: [bold]{model or 'preset default'}[/bold] | "
            f"Rounds: [bold]{rounds}[/bold]",
            border_style="cyan",
        )
    )

    with (
        SimulatedCortensorRouter(
            RouterNodeProfile(profile="healthy", node_id="cortensor-sim-healthy-01", base_latency_ms=18.0)
        ) as healthy_sim,
        SimulatedCortensorRouter(
            RouterNodeProfile(profile="poi_drift", node_id="cortensor-sim-drift-02", base_latency_ms=25.0)
        ) as drift_sim,
        tempfile.TemporaryDirectory(prefix="router-doctor-demo-") as tmp_str,
    ):
        tmp_root = Path(tmp_str)
        runtime_a = create_isolated_runtime(
            tmp_root / "runtime_primary",
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=api_key,
            chat_turn_timeout_seconds=timeout,
        )
        runtime_b = create_isolated_runtime(
            tmp_root / "runtime_replica",
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=api_key,
            chat_turn_timeout_seconds=timeout,
        )

        receipt: dict[str, Any] = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "provider": provider,
            "model": model,
            "simulators": {
                "healthy": healthy_sim.completions_url,
                "poi_drift": drift_sim.completions_url,
            },
            "scenarios": {},
        }

        def _print_delta(event: object) -> None:
            phase = getattr(event, "phase", None) or getattr(event, "kind", None)
            msg = getattr(event, "message", None) or getattr(event, "tool_name", None)
            if phase or msg:
                console.print(f"  [dim]delta[/dim] phase={phase} detail={msg}")

        try:
            # Scenario 1: Healthy router audit (no quarantine triggered)
            console.rule("[bold green]Scenario 1: Healthy Cortensor Router Audit[/bold green]")
            res_healthy = run_audit(
                runtime_a,
                endpoint_url=healthy_sim.completions_url,
                quarantine_file=out_dir / "quarantine_healthy_unused.json",
                rounds=rounds,
                timeout_seconds=timeout,
                on_delta=_print_delta,
                approval_callback=lambda tool_name, args, aid: False,
            )
            _render_report_table("Scenario 1 — Healthy Node", res_healthy.report)
            rec_id_1 = record_audit_incident(
                runtime_a,
                report=res_healthy.report,
                incident_key="sim:healthy-01",
            )
            receipt["scenarios"]["healthy"] = {
                "report": res_healthy.report.model_dump(mode="json"),
                "approval_events": res_healthy.approval_events,
                "tool_trace": res_healthy.tool_trace,
                "reconciled_from_tool_ledger": res_healthy.reconciled_from_tool_ledger,
                "delta_count": len(res_healthy.deltas),
                "memory_record_id": rec_id_1,
            }

            # Scenario 2: PoI Drift router with approval DENIED
            console.rule("[bold yellow]Scenario 2: PoI Drift Audit (Approval DENIED)[/bold yellow]")
            res_drift_denied = run_audit(
                runtime_a,
                endpoint_url=drift_sim.completions_url,
                quarantine_file=quarantine_denied_file,
                rounds=rounds,
                timeout_seconds=timeout,
                on_delta=_print_delta,
                approval_callback=lambda tool_name, args, aid: False,
            )
            _render_report_table("Scenario 2 — PoI Drift (Denied)", res_drift_denied.report)
            receipt["scenarios"]["poi_drift_denied"] = {
                "report": res_drift_denied.report.model_dump(mode="json"),
                "approval_events": res_drift_denied.approval_events,
                "tool_trace": res_drift_denied.tool_trace,
                "reconciled_from_tool_ledger": res_drift_denied.reconciled_from_tool_ledger,
                "quarantine_file_exists": quarantine_denied_file.exists(),
                "delta_count": len(res_drift_denied.deltas),
            }

            # Scenario 3: PoI Drift router with approval ALLOWED
            console.rule("[bold red]Scenario 3: PoI Drift Audit (Approval ALLOWED)[/bold red]")
            res_drift_allowed = run_audit(
                runtime_a,
                endpoint_url=drift_sim.completions_url,
                quarantine_file=quarantine_approved_file,
                rounds=rounds,
                timeout_seconds=timeout,
                on_delta=_print_delta,
                approval_callback=lambda tool_name, args, aid: True,
            )
            _render_report_table("Scenario 3 — PoI Drift (Approved)", res_drift_allowed.report)
            rec_id_3 = record_audit_incident(
                runtime_a,
                report=res_drift_allowed.report,
                incident_key="sim:drift-02",
            )
            receipt["scenarios"]["poi_drift_approved"] = {
                "report": res_drift_allowed.report.model_dump(mode="json"),
                "approval_events": res_drift_allowed.approval_events,
                "tool_trace": res_drift_allowed.tool_trace,
                "reconciled_from_tool_ledger": res_drift_allowed.reconciled_from_tool_ledger,
                "quarantine_file_exists": quarantine_approved_file.exists(),
                "memory_record_id": rec_id_3,
                "delta_count": len(res_drift_allowed.deltas),
            }

            # Scenario 4: Durable MemoryBundleSnapshot export & atomic cross-session import
            console.rule("[bold magenta]Scenario 4: Durable MemoryBundleSnapshot Export/Import[/bold magenta]")
            snapshot, written_bundle = export_audit_bundle(runtime_a, bundle_path)
            import_res = import_audit_bundle_atomic(runtime_b, written_bundle)
            replicated_records = list_audit_incidents(runtime_b, scope=DEFAULT_AUDIT_SCOPE)
            receipt["memory_portability"] = {
                "bundle_path": str(written_bundle),
                "exported_records": len(snapshot.records),
                "import_applied": import_res.applied,
                "imported_records": import_res.imported_records,
                "replicated_count": len(replicated_records),
            }
            console.print(
                f"Exported [bold]{len(snapshot.records)}[/bold] records to {written_bundle} "
                f"and atomically imported [bold]{import_res.imported_records}[/bold] into replica runtime."
            )

            receipt_path.write_text(
                json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            console.print(f"\n[bold green]Saved live run receipt:[/bold green] {receipt_path}")
        finally:
            runtime_a.close()
            runtime_b.close()


@app.command("audit")
def audit_endpoint(
    endpoint: str = typer.Option(
        ...,
        "--endpoint",
        help="Target Cortensor Router (/api/v2/completions) or Portal (/v1/chat/completions) URL.",
    ),
    provider: ProviderPreset = typer.Option(
        "ollama",
        "--provider",
        help="OpenMinion LLM provider preset: ollama, cortensor-portal, or cortensor-router.",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help="LLM model name override.",
    ),
    base_url: Optional[str] = typer.Option(
        None,
        "--base-url",
        help="Optional provider base URL override.",
    ),
    api_key: str = typer.Option(
        "",
        "--api-key",
        envvar="CORTENSOR_API_KEY",
        help="Optional API key (defaults to CORTENSOR_API_KEY).",
    ),
    rounds: int = typer.Option(3, "--rounds", min=1, max=20),
    session_id: int = typer.Option(1, "--session-id"),
    max_p95_ms: float = typer.Option(500.0, "--max-p95-ms"),
    min_poi_agreement: float = typer.Option(0.85, "--min-poi-agreement"),
    min_success_rate: float = typer.Option(0.95, "--min-success-rate"),
    quarantine_file: Path = typer.Option(
        Path("outputs/quarantine_directive.json"),
        "--quarantine-file",
    ),
    approve_quarantine: bool = typer.Option(
        False,
        "--approve-quarantine/--deny-quarantine",
        help="Whether to approve `apply_router_quarantine` if the agent requests it.",
    ),
    timeout: float = typer.Option(180.0, "--timeout"),
    output_receipt: Optional[Path] = typer.Option(
        None,
        "--output-receipt",
        help="Optional path to save the audit JSON receipt.",
    ),
) -> None:
    """Audit any live Cortensor Router or Portal endpoint using the OpenMinion agent."""
    with tempfile.TemporaryDirectory(prefix="router-doctor-audit-") as tmp_str:
        runtime = create_isolated_runtime(
            Path(tmp_str),
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=api_key,
            session_id=session_id,
            chat_turn_timeout_seconds=timeout,
        )
        try:
            result = run_audit(
                runtime,
                endpoint_url=endpoint,
                quarantine_file=quarantine_file,
                rounds=rounds,
                session_id=session_id,
                max_p95_ms=max_p95_ms,
                min_poi_agreement=min_poi_agreement,
                min_success_rate=min_success_rate,
                timeout_seconds=timeout,
                approval_callback=lambda _tool, _args, _aid: approve_quarantine,
            )
            record_id = record_audit_incident(runtime, report=result.report)
            _render_report_table("Cortensor Router Audit Result", result.report)
            console.print(f"[dim]Persisted durable memory record: {record_id}[/dim]")
            if output_receipt is not None:
                out = output_receipt.expanduser().resolve()
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(
                    json.dumps(
                        {
                            "report": result.report.model_dump(mode="json"),
                            "approval_events": result.approval_events,
                            "memory_record_id": record_id,
                        },
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                console.print(f"[green]Saved receipt:[/green] {out}")
        finally:
            runtime.close()


@app.command("verify-sdk-bugs")
def verify_sdk_bugs() -> None:
    """Run deterministic offline self-checks reproducing verified OpenMinion 0.1.24 SDK bugs."""
    from unittest.mock import patch

    from openminion import Agent, Handoff
    from openminion.base.config.providers import OllamaProviderConfig
    from openminion.modules.llm.errors import LLMCtlError
    from openminion.modules.llm.providers.ollama.adapter import OllamaProvider
    from openminion.modules.llm.schemas import LLMRequest, Message, ToolSpec
    from openminion.modules.memory.models import MemoryNamespace
    from openminion.modules.memory.portability.models import (
        MemoryBundleExportOptions,
        MemoryBundleImportOptions,
    )
    from openminion.modules.runtime.contracts import TurnResponse
    from openminion.services.runtime.turn_handle import TurnHandle

    findings: list[tuple[str, str, str, str]] = []

    # Finding 1: Ollama default tool_call_strategy="fallback" drops tool calls + missing f-string
    ollama_cfg_default = OllamaProviderConfig().tool_call_strategy
    provider = OllamaProvider()
    req = LLMRequest(
        messages=[Message(role="user", content="probe")],
        tools=[ToolSpec(name="probe_cortensor_router", description="probe", input_schema={"type": "object"})],
    )
    captured: dict[str, Any] = {}

    def _fake_post(**kwargs: Any) -> dict[str, Any]:
        captured["payload"] = kwargs["payload"]
        return {
            "model": "qwen2.5:3b",
            "message": {
                "role": "assistant",
                "content": '{"tool": "probe_cortensor_router", "arguments": {}}',
            },
            "done_reason": "stop",
        }

    with patch("openminion.modules.llm.providers.ollama.adapter._http_json_post", side_effect=_fake_post):
        resp = provider.complete(req, config={"model": "qwen2.5:3b"})
    missing_fstring = False
    with patch(
        "openminion.modules.llm.providers.ollama.adapter._http_json_post",
        return_value={"model": "qwen2.5:3b", "message": {"role": "assistant", "content": ""}},
    ):
        try:
            provider.complete(LLMRequest(messages=[Message(role="user", content="hi")]), config={"model": "qwen2.5:3b"})
        except LLMCtlError as exc:
            missing_fstring = "{model}" in exc.message
    provider.close()
    bug1_repro = (
        ollama_cfg_default == "fallback"
        and "tools" not in captured.get("payload", {})
        and len(resp.tool_calls) == 0
        and missing_fstring
    )
    findings.append(
        (
            "BUG-1",
            "REPRODUCED" if bug1_repro else "FIXED",
            "ollama/adapter.py:244,323,333",
            "Default fallback strategy omits tools & drops fallback calls; literal {model} in error",
        )
    )

    # Finding 2: TurnHandle.stream(timeout_s=...) hangs past timeout
    handle = TurnHandle(trace_id="selfcheck-timeout", on_cancel=lambda _: True)
    finished = threading.Event()

    def _wait_stream() -> None:
        try:
            next(handle.stream(timeout_s=0.05))
        except StopIteration:
            pass
        finally:
            finished.set()

    t = threading.Thread(target=_wait_stream, daemon=True)
    t.start()
    time.sleep(0.18)
    hung = not finished.is_set()
    handle._set_result(TurnResponse(final_text="done"))  # noqa: SLF001
    t.join(timeout=1.0)
    findings.append(
        (
            "BUG-2",
            "REPRODUCED" if hung else "FIXED",
            "services/runtime/turn_handle.py:258",
            "Condition.wait(timeout=timeout_s) return value ignored; stream() loops forever",
        )
    )

    # Finding 3 & 4: MemoryMerger non-atomic conflict_mode='error' & ignored namespace_allowlist
    with tempfile.TemporaryDirectory(prefix="sdk-verify-") as tmp_str:
        tmp = Path(tmp_str)
        rt_src = create_isolated_runtime(tmp / "src", provider="echo")
        rt_dst = create_isolated_runtime(tmp / "dst", provider="echo")
        try:
            svc_src = rt_src.runtime_memory_assembly.service
            svc_dst = rt_dst.runtime_memory_assembly.service
            id_a = svc_src.write_record(
                scope="agent:router-doctor",
                record_type="fact",
                title="Record A",
                content={"note": "new"},
            )
            id_b = svc_src.write_record(
                scope="agent:router-doctor",
                record_type="fact",
                title="Record B",
                content={"note": "v1"},
            )
            snap = svc_src.export_bundle_snapshot(
                MemoryBundleExportOptions(scopes=["agent:router-doctor"], types=["fact"])
            )
            # Pre-seed conflicting Record B in destination
            from dataclasses import replace

            rec_b = next(r for r in snap.records if r.id == id_b)
            svc_dst._store.put(replace(rec_b, content={"note": "conflicting_v2"}))  # noqa: SLF001
            raw_res = svc_dst.import_bundle_snapshot(
                snap,
                MemoryBundleImportOptions(trust_mode="direct", conflict_mode="error", id_mode="preserve"),
            )
            non_atomic = (not raw_res.applied) and (svc_dst._store.get(id_a) is not None)  # noqa: SLF001
            findings.append(
                (
                    "BUG-3",
                    "REPRODUCED" if non_atomic else "FIXED",
                    "modules/memory/portability/merger.py:377-417",
                    "conflict_mode='error' returns applied=False yet persists earlier records",
                )
            )

            # Finding 4: ignored namespace_allowlist
            svc_src.write_record(
                scope="agent:untrusted",
                record_type="fact",
                title="Untrusted",
                content={"note": "disallowed"},
            )
            snap_untrusted = svc_src.export_bundle_snapshot(
                MemoryBundleExportOptions(scopes=["agent:untrusted"], types=["fact"])
            )
            ns_res = svc_dst.import_bundle_snapshot(
                snap_untrusted,
                MemoryBundleImportOptions(
                    trust_mode="direct",
                    conflict_mode="skip",
                    namespace_allowlist=[MemoryNamespace(agent_id="router-doctor")],
                ),
            )
            ignored_allowlist = ns_res.applied and ns_res.imported_records == 1
            findings.append(
                (
                    "BUG-4",
                    "REPRODUCED" if ignored_allowlist else "FIXED",
                    "modules/memory/portability/merger.py:73-125",
                    "MemoryMerger silently ignores options.namespace_allowlist",
                )
            )
        finally:
            rt_src.close()
            rt_dst.close()

    # Finding 5: Handoff.resolved_description() IndexError on whitespace instructions
    whitespace_crash = False
    try:
        Handoff(target=Agent(name="blank", instructions="   \n  ")).resolved_description()
    except IndexError:
        whitespace_crash = True
    findings.append(
        (
            "BUG-5",
            "REPRODUCED" if whitespace_crash else "FIXED",
            "api/handoff.py:158",
            "str(instr).strip().splitlines()[0] raises IndexError on whitespace-only instructions",
        )
    )

    table = Table(title="OpenMinion 0.1.24 SDK Verification Matrix", show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold yellow", no_wrap=True)
    table.add_column("Location", style="magenta")
    table.add_column("Observed Behavior", style="white")
    for fid, status, loc, desc in findings:
        table.add_row(fid, status, loc, desc)
    console.print(table)


if __name__ == "__main__":
    app()
