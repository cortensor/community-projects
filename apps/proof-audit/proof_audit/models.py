"""Pydantic v2 data models for ProofAudit Minion."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CheckFinding(BaseModel):
    """Single deterministic or judged check finding."""

    check_id: str = Field(..., description="Unique identifier for the check.")
    category: str = Field(..., description="Check category such as manifest, sdk, endpoint, or smoke.")
    status: Literal["PASS", "WARN", "FAIL"] = Field(..., description="Check status.")
    evidence: str = Field(..., description="Concrete observed evidence from the repository or probe.")
    fix: str = Field(default="", description="Actionable remediation step if status is WARN or FAIL.")


class ProofAuditReport(BaseModel):
    """Structured final readiness report for an OpenMinion / Cortensor hackathon repo."""

    repo_name: str = Field(..., description="Target repository directory name.")
    verdict: Literal["READY", "WARNINGS", "BLOCKED"] = Field(
        ...,
        description="Overall submission readiness verdict.",
    )
    score: int = Field(..., ge=0, le=100, description="Readiness score from 0 to 100.")
    building_blocks_detected: list[str] = Field(
        default_factory=list,
        description="OpenMinion SDK building blocks detected via AST scan.",
    )
    findings: list[CheckFinding] = Field(
        default_factory=list,
        description="List of individual check findings.",
    )
    remediation_steps: list[str] = Field(
        default_factory=list,
        description="Prioritized remediation steps for any WARN/FAIL findings.",
    )
    summary: str = Field(..., description="Concise executive summary of repository readiness.")
