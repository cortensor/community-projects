"""Typed Pydantic v2 contracts for release gate audits and OpenMinion probes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["critical", "high", "medium", "low"]
GateDecision = Literal["READY", "CHANGES_REQUIRED", "BLOCKED"]


class AuditFinding(BaseModel):
    """Single actionable finding discovered in a repository scan."""

    check_id: str
    category: Literal["security", "docs", "cortensor", "packaging"]
    severity: Severity
    path: str
    message: str
    remediation: str


class SecurityAuditReport(BaseModel):
    """Output contract for the READ_ONLY security auditor subagent."""

    passed: bool
    files_scanned: int
    findings: list[AuditFinding] = Field(default_factory=list)
    summary: str


class DocsAuditReport(BaseModel):
    """Output contract for the READ_ONLY documentation and manifest auditor subagent."""

    passed: bool
    present_files: list[str] = Field(default_factory=list)
    missing_files: list[str] = Field(default_factory=list)
    findings: list[AuditFinding] = Field(default_factory=list)
    summary: str


class CortensorWiringReport(BaseModel):
    """Static check of OpenMinion SDK pinning, Cortensor endpoints, and test presence."""

    uses_openminion: bool
    openminion_pin: str | None = None
    cortensor_endpoints_detected: list[str] = Field(default_factory=list)
    has_tests: bool = False
    findings: list[AuditFinding] = Field(default_factory=list)


class TriageAction(BaseModel):
    """Single prioritized remediation step produced by the triage handoff agent."""

    priority: int = Field(ge=1)
    check_id: str
    owner_area: str
    action: str


class TriagePlan(BaseModel):
    """Ordered remediation plan produced via Handoff when a repo fails the gate."""

    decision: GateDecision
    actions: list[TriageAction] = Field(default_factory=list)
    summary: str


class ReleaseGateVerdict(BaseModel):
    """Top-level coordinator decision combining security, docs, wiring, and memory diff."""

    target_path: str
    decision: GateDecision
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    resolved_since_last_run: list[str] = Field(default_factory=list)
    persistent_from_last_run: list[str] = Field(default_factory=list)
    triage_plan: TriagePlan | None = None
    report_written: bool = False
    report_path: str | None = None
    summary: str


class ProbeCheckResult(BaseModel):
    """Measured outcome of exercising one OpenMinion 0.1 building block."""

    block_name: str
    passed: bool
    duration_ms: float
    details: dict[str, str] = Field(default_factory=dict)
    error: str | None = None


class ProbeMatrixReport(BaseModel):
    """Aggregated telemetry from running all OpenMinion building-block probes."""

    openminion_version: str
    provider_mode: str
    checks: list[ProbeCheckResult] = Field(default_factory=list)
    all_passed: bool
