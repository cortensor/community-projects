"""Pydantic data contracts for ReleaseGuard Minion."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ReleaseCheck(BaseModel):
    """Single audited release-readiness dimension."""

    category: str = Field(description="Check category: manifest, ci_tests, or secrets.")
    passed: bool = Field(description="Whether this check passed release standards.")
    evidence: str = Field(description="Concise factual evidence observed from tools.")


class ReleaseAuditReport(BaseModel):
    """Structured release-readiness report returned by the OpenMinion Agent.

    Note: deliberately uses ``verdict`` and ``rationale`` rather than
    ``status`` + ``summary`` to avoid a bug in OpenMinion 0.1.24 where
    ``_looks_like_unexecutable_tool_payload_text`` misclassifies JSON
    containing both ``status`` and ``summary`` as raw tool markup.
    """

    repo_name: str = Field(description="Repository directory or slug audited.")
    verdict: Literal["ready", "needs_work", "blocked"] = Field(
        description="Overall release readiness verdict."
    )
    score: int = Field(ge=0, le=100, description="Readiness score from 0 to 100.")
    rationale: str = Field(description="One-paragraph justification of the verdict.")
    checks: list[ReleaseCheck] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class ApprovalDecisionRecord(BaseModel):
    """Auditable record of one OpenMinion policy confirmation callback."""

    tool_name: str
    approval_id: str
    allowed: bool
    reason: str
    args_keys: list[str] = Field(default_factory=list)


class AuditRunEnvelope(BaseModel):
    """Full inspectable envelope combining structured output and runtime metadata."""

    report: ReleaseAuditReport
    session_id: str | None = None
    run_id: str | None = None
    run_state: str | None = None
    thread_id: str | None = None
    approvals: list[ApprovalDecisionRecord] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)
    memory_bundle_path: str | None = None
    brief_path: str | None = None
