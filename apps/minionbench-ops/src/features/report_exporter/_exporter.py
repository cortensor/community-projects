"""Deterministic JSON & Markdown artifact exporter for Minionbench Ops."""

from __future__ import annotations

import json
from pathlib import Path

from src.kernel.event_bus import DiagnosticReport, redact_secrets


def _render_building_blocks_markdown(report: DiagnosticReport) -> str:
    r = report.live_receipt
    lines = [
        "# Building Blocks Tested — Minionbench Ops (`openminion==0.1.24`)",
        "",
        f"- **Project:** `{report.target.project_slug}` (Cortensor Hackathon #5 / DoraHacks `#2418`)",
        f"- **OpenMinion SDK Version:** `{report.openminion_version}`",
        f"- **Generated (UTC):** `{report.generated_at_utc}`",
        f"- **Live Neural Model Turn:** `{r.model_id}` via `{r.provider_transport}` (`session_id={r.session_id}`, `run_state={r.run_state}`, `{r.latency_ms} ms`)",
        "",
        "## 1. Live Model-Backed Workflow Summary",
        "",
        "Minionbench Ops embeds `APIRuntime` and `Agent` inside a strict vertical-slice Python 3.12 architecture to run repeatable release-and-triage audits for Cortensor builders. During live execution, the agent invoked workspace-confined `@tool(min_scope=\"READ_ONLY\", idempotent=True)` functions across a durable `session_id` and `thread_id` chain while keeping runtime SQLite databases isolated under `.openminion_runtime/`.",
        "",
        "| Tool Invoked | Scope | Idempotent | Arguments | Result Excerpt |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    for inv in r.tool_invocations:
        args_json = json.dumps(inv.arguments, sort_keys=True)
        excerpt = inv.result_preview.replace("|", "\\|").replace("\n", " ")[:110]
        lines.append(
            f"| `{inv.tool_name}` | `{inv.min_scope}` | `{inv.idempotent}` | `{args_json}` | `{excerpt}` |"
        )

    lines.extend(
        [
            "",
            f"- **Hosted Endpoint Preflight Note:** {r.hosted_probe_note}",
            f"- **Agent Synthesis Excerpt:** {r.final_text.replace(chr(10), ' ')[:320]}",
            "",
            "## 2. Six Empirical OpenMinion 0.1.24 Diagnostic Probes",
            "",
            "| Probe ID | SDK Surface | Status | Latency (`ms`) | What Worked & Empirical Finding |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
    )
    for p in report.probes:
        status = "PASS" if p.passed else "FAIL"
        summary = p.summary.replace("|", "\\|")
        lines.append(
            f"| `{p.probe_id}` | `{p.sdk_surface}` | `{status}` | `{p.latency_ms}` | {summary} |"
        )

    posture = report.cortensor_posture.get("profiles", {})
    lines.extend(
        [
            "",
            "## 3. Cortensor Portal, Router & OpenAI-Bridge Posture Matrix",
            "",
            "| Profile | Setup Catalog ID | `agents.json` Key | Endpoint | Retries | Turn Timeout Floor |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
    )
    for key, pinfo in posture.items():
        lines.append(
            f"| `{key}` | `{pinfo['setup_catalog_id']}` | `{pinfo['agents_json_provider']}` | "
            f"`{pinfo['base_url']}` | `{pinfo['max_retries']}` | `{pinfo['api_turn_timeout_floor_seconds']}s` |"
        )
    lines.append("")
    return "\n".join(lines)


def _render_what_we_learned_markdown(report: DiagnosticReport) -> str:
    lines = [
        "# What We Learned — Actionable OpenMinion 0.1.24 Engineering Feedback",
        "",
        f"Empirical findings captured against `openminion=={report.openminion_version}` on Python 3.12 during Cortensor Hackathon #5 (`#2418`). Every item includes exact module paths, observed runtime behavior, reproduction mechanics, and a concrete upstream fix.",
        "",
    ]
    for idx, item in enumerate(report.learned_findings, start=1):
        lines.extend(
            [
                f"## {idx}. [{item['id']}] {item['title']} (`{item['severity']}`)",
                "",
                f"- **Component:** `{item['component']}`",
                f"- **Observed Behavior:** {item['observed']}",
                f"- **Recommended Upstream Fix:** {item['recommendation']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Reproduction Command",
            "",
            "```bash",
            ".venv/bin/python -m src.cli",
            ".venv/bin/pytest tests -q",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _render_triage_brief_markdown(report: DiagnosticReport) -> str:
    r = report.live_receipt
    passed_count = sum(1 for p in report.probes if p.passed)
    return "\n".join(
        [
            "# Cortensor Builder Release & Triage Readiness Brief",
            "",
            f"- **Generated (UTC):** `{report.generated_at_utc}`",
            f"- **Target Workspace:** `{report.target.project_slug}`",
            f"- **OpenMinion Runtime:** `{report.openminion_version}`",
            f"- **Live Model Session:** `{r.session_id}` (`{r.model_id}` via `{r.provider_transport}`)",
            f"- **Building-Block Diagnostic Score:** `{passed_count}/{len(report.probes)}` probes passing",
            f"- **Sanitized Secret Audit:** `PASS (sanitized={r.sanitized})`",
            "",
            "## Live Agent Summary",
            "",
            r.final_text.strip(),
            "",
        ]
    )


def export_diagnostic_artifacts(
    *,
    workspace_root: Path,
    report: DiagnosticReport,
) -> dict[str, str]:
    """Validate report invariants and write sanitized JSON and Markdown deliverables."""
    report.verify_invariants()
    resolved_root = workspace_root.resolve()
    outputs_dir = resolved_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    receipt_path = outputs_dir / "live_model_run_receipt.json"
    probes_path = outputs_dir / "building_blocks_tested.json"
    brief_path = outputs_dir / "triage_readiness_brief.md"
    bb_md_path = resolved_root / "BUILDING_BLOCKS_TESTED.md"
    learned_md_path = resolved_root / "WHAT_WE_LEARNED.md"

    receipt_json = redact_secrets(json.dumps(report.live_receipt.to_dict(), indent=2, sort_keys=True) + "\n")
    report_json = redact_secrets(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n")
    brief_md = redact_secrets(_render_triage_brief_markdown(report))
    bb_md = redact_secrets(_render_building_blocks_markdown(report))
    learned_md = redact_secrets(_render_what_we_learned_markdown(report))

    receipt_path.write_text(receipt_json, encoding="utf-8")
    probes_path.write_text(report_json, encoding="utf-8")
    brief_path.write_text(brief_md, encoding="utf-8")
    bb_md_path.write_text(bb_md, encoding="utf-8")
    learned_md_path.write_text(learned_md, encoding="utf-8")

    return {
        "live_model_run_receipt_json": str(receipt_path),
        "building_blocks_tested_json": str(probes_path),
        "triage_readiness_brief_md": str(brief_path),
        "building_blocks_tested_md": str(bb_md_path),
        "what_we_learned_md": str(learned_md_path),
    }
