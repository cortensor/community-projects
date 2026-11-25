"""Pydantic v2 contracts and deterministic anti-hallucination validators for router audits."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

SLAGrade = Literal["HEALTHY", "DEGRADED", "CRITICAL_DRIFT"]
RecommendedAction = Literal["NONE", "MONITOR", "QUARANTINE"]
SeverityLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class VerdictMismatchError(ValueError):
    """Raised when an LLM-authored audit report contradicts deterministic probe evidence."""


class ProbeRoundSample(BaseModel):
    """Single redundant inference round executed against a Cortensor Router endpoint."""

    model_config = ConfigDict(extra="forbid")

    round_index: int = Field(ge=1)
    status_code: int = Field(ge=0)
    latency_ms: float = Field(ge=0.0)
    ok: bool
    response_text: str = ""
    error: str | None = None


class PoIDriftAnalysis(BaseModel):
    """Proof-of-Inference (PoI) cross-round consensus consistency metrics."""

    model_config = ConfigDict(extra="forbid")

    rounds_requested: int = Field(ge=1)
    rounds_succeeded: int = Field(ge=0)
    exact_match_ratio: float = Field(ge=0.0, le=1.0)
    mean_jaccard_agreement: float = Field(ge=0.0, le=1.0)
    poi_agreement_score: float = Field(ge=0.0, le=1.0)
    unique_responses: int = Field(ge=0)
    drift_detected: bool


class ProbeResult(BaseModel):
    """Structured output returned by the `probe_cortensor_router` tool."""

    model_config = ConfigDict(extra="forbid")

    endpoint_url: str
    prompt: str
    session_id: int = Field(ge=0)
    rounds: int = Field(ge=1)
    success_rate: float = Field(ge=0.0, le=1.0)
    p50_latency_ms: float = Field(ge=0.0)
    p95_latency_ms: float = Field(ge=0.0)
    mean_latency_ms: float = Field(ge=0.0)
    poi_analysis: PoIDriftAnalysis
    samples: list[ProbeRoundSample] = Field(default_factory=list)


class SLAPolicyEvaluation(BaseModel):
    """Deterministic Cortensor SLA policy grading returned by `evaluate_sla_policy`."""

    model_config = ConfigDict(extra="forbid")

    endpoint_url: str
    grade: SLAGrade
    recommended_action: RecommendedAction
    violations: list[str] = Field(default_factory=list)
    thresholds: dict[str, float] = Field(default_factory=dict)
    measured: dict[str, float] = Field(default_factory=dict)


class QuarantineAction(BaseModel):
    """Signed quarantine directive written by `apply_router_quarantine`."""

    model_config = ConfigDict(extra="forbid")

    endpoint_url: str
    reason: str
    severity: SeverityLevel
    quarantine_file: str
    applied: bool
    signature_sha256: str
    timestamp_utc: str


class RouterAuditReport(BaseModel):
    """Final structured audit report produced by the Cortensor Router Doctor agent.

    Includes an internal self-consistency validator preventing contradictory verdicts
    (e.g. certifying HEALTHY while violations exist or while quarantine was applied).
    """

    model_config = ConfigDict(extra="forbid")

    endpoint_url: str
    verdict: SLAGrade
    summary: str = Field(min_length=1)
    recommended_action: RecommendedAction
    measured_p95_ms: float = Field(ge=0.0)
    measured_poi_agreement: float = Field(ge=0.0, le=1.0)
    measured_success_rate: float = Field(ge=0.0, le=1.0)
    quarantine_applied: bool = False
    quarantine_file: str | None = None
    violations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _enforce_internal_consistency(self) -> "RouterAuditReport":
        if self.verdict == "HEALTHY":
            if self.violations:
                raise ValueError(
                    "Cannot certify verdict='HEALTHY' when SLA violations are present: "
                    f"{self.violations}"
                )
            if self.recommended_action == "QUARANTINE":
                raise ValueError(
                    "Cannot certify verdict='HEALTHY' with recommended_action='QUARANTINE'"
                )
            if self.quarantine_applied:
                raise ValueError(
                    "Cannot certify verdict='HEALTHY' when quarantine_applied=True"
                )
        if self.verdict == "CRITICAL_DRIFT" and self.recommended_action == "NONE":
            raise ValueError(
                "verdict='CRITICAL_DRIFT' cannot have recommended_action='NONE'"
            )
        if self.quarantine_applied and not (self.quarantine_file or "").strip():
            raise ValueError(
                "quarantine_file must be provided when quarantine_applied=True"
            )
        return self


def verify_report_against_evidence(
    report: RouterAuditReport,
    evaluation: SLAPolicyEvaluation,
    *,
    quarantine: QuarantineAction | None = None,
    metric_tolerance: float = 1e-2,
) -> RouterAuditReport:
    """Deterministically cross-check an LLM report against measured tool evidence.

    Prevents hallucinated certification of drifting or degraded Cortensor routers.
    """
    mismatches: list[str] = []

    if report.verdict != evaluation.grade:
        mismatches.append(
            f"verdict mismatch: report={report.verdict!r} vs measured={evaluation.grade!r}"
        )

    if evaluation.grade in {"DEGRADED", "CRITICAL_DRIFT"} and report.verdict == "HEALTHY":
        mismatches.append(
            "hallucinated HEALTHY certification for a drifting or degraded router"
        )

    measured_p95 = float(evaluation.measured.get("p95_latency_ms", 0.0))
    measured_poi = float(evaluation.measured.get("poi_agreement_score", 0.0))
    measured_sr = float(evaluation.measured.get("success_rate", 0.0))

    if abs(report.measured_p95_ms - measured_p95) > max(metric_tolerance, 2.0):
        mismatches.append(
            f"p95_latency_ms mismatch: report={report.measured_p95_ms:.2f} "
            f"vs measured={measured_p95:.2f}"
        )
    if abs(report.measured_poi_agreement - measured_poi) > max(metric_tolerance, 0.02):
        mismatches.append(
            f"poi_agreement mismatch: report={report.measured_poi_agreement:.4f} "
            f"vs measured={measured_poi:.4f}"
        )
    if abs(report.measured_success_rate - measured_sr) > max(metric_tolerance, 0.02):
        mismatches.append(
            f"success_rate mismatch: report={report.measured_success_rate:.4f} "
            f"vs measured={measured_sr:.4f}"
        )

    if quarantine is not None and report.quarantine_applied != quarantine.applied:
        mismatches.append(
            f"quarantine_applied mismatch: report={report.quarantine_applied} "
            f"vs tool={quarantine.applied}"
        )
    if quarantine is None and report.quarantine_applied:
        mismatches.append(
            "report claims quarantine_applied=True but no quarantine tool execution succeeded"
        )

    if mismatches:
        raise VerdictMismatchError(
            "Audit report failed deterministic evidence cross-check: "
            + "; ".join(mismatches)
        )
    return report
