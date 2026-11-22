"""Top-level vertical-slice orchestrator wiring EventBus and feature bricks."""

from __future__ import annotations

from pathlib import Path

from openminion import __version__ as OPENMINION_VERSION

from src.features.minion_runner import execute_triage_workflow
from src.features.report_exporter import export_diagnostic_artifacts
from src.features.runtime_diagnostics import (
    build_cortensor_posture_matrix,
    build_learned_findings,
    run_building_block_diagnostics,
)
from src.features.triage_tools import build_triage_toolset
from src.kernel.event_bus import DiagnosticReport, EventBus, TriageTarget, utc_now_iso


def run_minionbench_pipeline(
    *,
    workspace_root: Path,
    mode: str = "live",
    write_artifacts: bool = True,
) -> tuple[DiagnosticReport, dict[str, str]]:
    """Execute the full Minionbench Ops triage workflow, 6 SDK probes, and artifact export."""
    resolved_root = workspace_root.resolve()
    bus = EventBus()
    bus.publish("gate.check", source_brick="app", payload={"mode": mode})

    toolset = build_triage_toolset(
        workspace_root=resolved_root,
        runtime_staging_dir=resolved_root / ".openminion_runtime" / "staging",
        bus=bus,
    )
    live_receipt = execute_triage_workflow(
        workspace_root=resolved_root,
        tools=list(toolset.all_tools),
        bus=bus,
        mode=mode,
    )
    probes = run_building_block_diagnostics(
        workspace_root=resolved_root,
        bus=bus,
    )
    report = DiagnosticReport(
        generated_at_utc=utc_now_iso(),
        openminion_version=OPENMINION_VERSION,
        target=TriageTarget(
            workspace_root=".",
            project_slug="minionbench-ops",
            hackathon_id=2418,
            openminion_version=OPENMINION_VERSION,
        ),
        live_receipt=live_receipt,
        probes=probes,
        cortensor_posture=build_cortensor_posture_matrix(),
        learned_findings=build_learned_findings(),
    )
    report.verify_invariants()
    written = (
        export_diagnostic_artifacts(workspace_root=resolved_root, report=report)
        if write_artifacts
        else {}
    )
    return report, written
