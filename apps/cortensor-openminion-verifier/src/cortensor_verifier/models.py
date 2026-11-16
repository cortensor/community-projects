"""Pydantic v2 domain models for Claim Dossiers, Verifier Passes, Consensus, and Probes."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

VerdictLiteral = Literal["SUPPORTED", "REFUTED", "INCONCLUSIVE"]


class EvidenceCitation(BaseModel):
    """Single source citation supporting or refuting a claim."""

    source_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    url: str | None = None
    excerpt: str = Field(..., min_length=1)
    published_at: str | None = None


class ClaimDossier(BaseModel):
    """Structured package of claim text, market question, and resolution rules."""

    claim_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    claim: str = Field(..., min_length=1)
    market_question: str = Field(..., min_length=1)
    resolution_criteria: str = ""
    source_hints: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VerifierPassResult(BaseModel):
    """Structured output returned by a single openminion verifier pass."""

    verdict: VerdictLiteral
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str = Field(..., min_length=1)
    citations: list[EvidenceCitation] = Field(default_factory=list)
    pass_role: str = Field(default="primary", min_length=1)


class ConsensusVerdict(BaseModel):
    """Aggregated outcome synthesized across one or more verifier passes."""

    claim_id: str = Field(..., min_length=1)
    final_verdict: VerdictLiteral
    agreement_score: float = Field(..., ge=0.0, le=1.0)
    mean_confidence: float = Field(..., ge=0.0, le=1.0)
    disagreement_summary: str = ""
    passes: list[VerifierPassResult] = Field(default_factory=list)
    requires_human_review: bool = False


ApprovalModeLiteral = Literal["allow_once", "deny", "pause"]
PublicationStatusLiteral = Literal["not_requested", "published", "denied", "paused"]


class PublicationResult(BaseModel):
    """Outcome of approval-gated consensus publication via openminion Handoff."""

    requested: bool = False
    published: bool = False
    publication_status: PublicationStatusLiteral = "not_requested"
    claim_id: str = ""
    final_verdict: VerdictLiteral | None = None
    approval_mode: ApprovalModeLiteral | None = None
    thread_id: str | None = None
    approval_id: str | None = None
    confirmation_prompt: str = ""
    denial_reason: str = ""
    handoff_target: str = "publisher"
    log_path: str | None = None
    run_id: str | None = None


class PassTelemetry(BaseModel):
    """Measured request, token, and latency telemetry for a single agent pass."""

    pass_role: str = Field(..., min_length=1)
    requests: int = Field(default=0, ge=0)
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    latency_ms: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    tool_errors: int = Field(default=0, ge=0)


class TelemetrySummary(BaseModel):
    """Aggregated telemetry across coordinator, subagents, and publication runs."""

    requests: int = Field(default=0, ge=0)
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    total_latency_ms: int = Field(default=0, ge=0)
    per_pass: dict[str, PassTelemetry] = Field(default_factory=dict)
    turn_telemetries: list[dict[str, Any]] = Field(default_factory=list)


class AuditRunBundle(BaseModel):
    """Complete audit artifact emitted for CLI output, verification, and replay."""

    claim_id: str = Field(..., min_length=1)
    preset: str = Field(..., min_length=1)
    dossier: ClaimDossier
    consensus: ConsensusVerdict
    tool_calls: list[str] = Field(default_factory=list)
    run_id: str | None = None
    session_id: str | None = None
    publication: PublicationResult | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProbeCheckResult(BaseModel):
    """Outcome record for a building-block runtime probe."""

    probe_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    passed: bool
    detail: str = ""
    latency_ms: float | None = Field(default=None, ge=0.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
