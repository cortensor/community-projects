"""Typed Pydantic schemas for structured OpenMinion release-readiness verdicts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReleaseVerdict(BaseModel):
    """Structured go/no-go verdict returned by the Release Guardian agent."""

    decision: Literal["GO", "CONDITIONAL_GO", "NO_GO"] = Field(
        description="Final release decision based on repository structure, secret scan, syntax, and OpenMinion config."
    )
    readiness_score: int = Field(
        ge=0,
        le=100,
        description="Overall release readiness score from 0 to 100.",
    )
    summary: str = Field(
        description="Concise 1-2 sentence executive summary of the audit."
    )
    blockers: list[str] = Field(
        default_factory=list,
        description="Critical issues that must be fixed before releasing or opening a public PR.",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Actionable improvements to strengthen reproducibility and builder UX.",
    )
