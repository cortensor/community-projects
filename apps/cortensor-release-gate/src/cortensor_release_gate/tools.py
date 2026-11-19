"""OpenMinion @tool definitions for repository scanning and gated report export."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

from openminion import tool
from pydantic import Field

from cortensor_release_gate.scanners import (
    scan_cortensor_wiring,
    scan_repository_docs,
    scan_repository_security,
)


def _resolve_target_dir(target_dir: str) -> Path:
    path = Path(target_dir).expanduser().resolve()
    if not path.is_dir():
        raise ValueError(f"Target directory does not exist: {path}")
    return path


@tool(
    name="scan_security_tool",
    description="Scan a repository directory for leaked keys, private keys, or committed .env files.",
    min_scope="READ_ONLY",
    idempotent=True,
    tags=("audit", "security"),
)
def scan_security_tool(
    target_dir: Annotated[str, Field(description="Absolute or relative path to repository root.")],
) -> dict[str, Any]:
    """Run read-only security scan and return serialized SecurityAuditReport."""
    report = scan_repository_security(_resolve_target_dir(target_dir))
    return report.model_dump(mode="json")


@tool(
    name="scan_docs_tool",
    description="Verify required Cortensor community-projects files (PROJECTS.yml, README, STATUS, RELEASE, LICENSE).",
    min_scope="READ_ONLY",
    idempotent=True,
    tags=("audit", "docs"),
)
def scan_docs_tool(
    target_dir: Annotated[str, Field(description="Absolute or relative path to repository root.")],
) -> dict[str, Any]:
    """Run read-only docs and manifest audit and return serialized DocsAuditReport."""
    report = scan_repository_docs(_resolve_target_dir(target_dir))
    return report.model_dump(mode="json")


@tool(
    name="scan_cortensor_wiring_tool",
    description="Check openminion dependency pin, imports, Cortensor endpoints, and tests directory.",
    min_scope="READ_ONLY",
    idempotent=True,
    tags=("audit", "cortensor"),
)
def scan_cortensor_wiring_tool(
    target_dir: Annotated[str, Field(description="Absolute or relative path to repository root.")],
) -> dict[str, Any]:
    """Run read-only wiring check and return serialized CortensorWiringReport."""
    report = scan_cortensor_wiring(_resolve_target_dir(target_dir))
    return report.model_dump(mode="json")


@tool(
    name="write_release_gate_report",
    description="Write RELEASE_GATE_REPORT.md and release-gate-summary.json to the output directory.",
    min_scope="WRITE_SAFE",
    dangerous=True,
    tags=("audit", "export"),
)
def write_release_gate_report(
    output_dir: Annotated[str, Field(description="Directory where report artifacts are written.")],
    markdown_report: Annotated[str, Field(description="Markdown contents for RELEASE_GATE_REPORT.md.")],
    summary_json: Annotated[str, Field(description="JSON string for release-gate-summary.json.")],
) -> dict[str, Any]:
    """Persist release gate markdown and JSON outputs after policy/human approval."""
    out_path = Path(output_dir).expanduser().resolve()
    out_path.mkdir(parents=True, exist_ok=True)
    # Validate JSON before writing so partial or corrupt artifacts are never persisted.
    parsed_summary = json.loads(summary_json)
    md_file = out_path / "RELEASE_GATE_REPORT.md"
    json_file = out_path / "release-gate-summary.json"
    md_file.write_text(markdown_report, encoding="utf-8")
    json_file.write_text(
        json.dumps(parsed_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "written": True,
        "markdown_path": str(md_file),
        "json_path": str(json_file),
    }
