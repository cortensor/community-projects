"""Typer CLI for cortensor-release-gate."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from cortensor_release_gate.agent_workflow import (
    run_building_block_probes,
    run_release_gate,
)
from cortensor_release_gate.memory_store import load_prior_check_ids
from cortensor_release_gate.runtime import ProviderKind, resolve_live_settings

app = typer.Typer(
    name="cortensor-release-gate",
    help="OpenMinion 0.1 release and submission QA gate agent for Cortensor projects.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def audit(
    target: Annotated[
        Path,
        typer.Argument(help="Path to the repository or app directory to audit."),
    ] = Path("."),
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "--output-dir",
            help="Directory for RELEASE_GATE_REPORT.md and release-gate-summary.json.",
        ),
    ] = None,
    demo_local: Annotated[
        bool,
        typer.Option(
            "--demo-local",
            help="Run against the built-in local OpenAI/Cortensor loopback server.",
        ),
    ] = False,
    provider: Annotated[
        str | None,
        typer.Option(
            "--provider",
            help="Provider name when not using --demo-local ('cortensor' or 'openai').",
        ),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option("--model", help="Override model name."),
    ] = None,
    base_url: Annotated[
        str | None,
        typer.Option("--base-url", help="Override provider base URL."),
    ] = None,
    write_report: Annotated[
        bool,
        typer.Option(
            "--write-report",
            help="Write RELEASE_GATE_REPORT.md and release-gate-summary.json.",
        ),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Auto-approve the gated write_release_gate_report tool call.",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit the ReleaseGateVerdict as JSON."),
    ] = False,
) -> None:
    """Audit a Cortensor repository and optionally export an approval-gated report."""
    resolved_provider: ProviderKind | None = None
    if provider is not None:
        if provider not in {"cortensor", "openai"}:
            raise typer.BadParameter("provider must be 'cortensor' or 'openai'")
        resolved_provider = provider  # type: ignore[assignment]

    settings = (
        None
        if demo_local
        else resolve_live_settings(
            provider=resolved_provider,
            model=model,
            base_url=base_url,
        )
    )

    def _cli_approval(tool_name: str, args: dict[str, object], approval_id: str) -> bool:
        if yes:
            return True
        if not write_report:
            return False
        prompt = f"Approve {tool_name} ({approval_id}) writing to {args.get('output_dir')}?"
        return typer.confirm(prompt, default=False)

    verdict = run_release_gate(
        target_dir=target,
        output_dir=output_dir,
        settings=settings,
        demo_local=demo_local,
        write_report=write_report,
        approval_callback=_cli_approval,
    )

    if json_output:
        console.print_json(verdict.model_dump_json())
        raise typer.Exit(code=0 if verdict.decision != "BLOCKED" else 1)

    table = Table(title=f"Release Gate Verdict: {verdict.decision}")
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Target", verdict.target_path)
    table.add_row("Decision", verdict.decision)
    table.add_row("Blockers", str(len(verdict.blockers)))
    table.add_row("Warnings", str(len(verdict.warnings)))
    table.add_row("Resolved Since Last Run", ", ".join(verdict.resolved_since_last_run) or "none")
    table.add_row("Report Written", str(verdict.report_written))
    if verdict.report_path:
        table.add_row("Report Path", verdict.report_path)
    console.print(table)
    console.print(verdict.summary)
    raise typer.Exit(code=0 if verdict.decision != "BLOCKED" else 1)


@app.command()
def probe(
    target: Annotated[
        Path,
        typer.Argument(help="Repository path used during probe execution."),
    ] = Path("."),
    state_root: Annotated[
        Path,
        typer.Option(
            "--state-root",
            help="Isolated directory for probe runtime databases and artifacts.",
        ),
    ] = Path(".openminion/probe_state"),
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit ProbeMatrixReport as JSON."),
    ] = False,
) -> None:
    """Exercise OpenMinion 0.1.23 building blocks and print measured probe telemetry."""
    report = run_building_block_probes(target_dir=target, state_root=state_root.resolve())
    if json_output:
        console.print_json(report.model_dump_json())
        raise typer.Exit(code=0 if report.all_passed else 1)

    table = Table(title=f"OpenMinion {report.openminion_version} Building-Block Probes")
    table.add_column("Building Block", style="bold")
    table.add_column("Status")
    table.add_column("Duration (ms)", justify="right")
    table.add_column("Measured Details")
    for check in report.checks:
        status = "PASS" if check.passed else "FAIL"
        detail = (
            ", ".join(f"{k}={v}" for k, v in check.details.items())
            if check.passed
            else (check.error or "unknown error")
        )
        table.add_row(check.block_name, status, f"{check.duration_ms:.2f}", detail)
    console.print(table)
    raise typer.Exit(code=0 if report.all_passed else 1)


@app.command()
def memory(
    bundle_path: Annotated[
        Path,
        typer.Argument(help="Path to the portable OpenMinion MemoryBundle JSON file."),
    ] = Path("audit_memory.json"),
) -> None:
    """Inspect blocker IDs recorded in the latest MemoryBundle snapshot."""
    blockers = load_prior_check_ids(bundle_path.resolve())
    if not blockers:
        console.print(f"No prior blocker IDs recorded in {bundle_path}.")
        return
    console.print(f"Latest recorded blockers ({len(blockers)}): {', '.join(blockers)}")


if __name__ == "__main__":
    app()
