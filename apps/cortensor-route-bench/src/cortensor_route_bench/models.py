"""Pydantic v2 data contracts for preflight checks, SDK probes, and consensus runs."""

from __future__ import annotations

import re
from typing import Literal, TypeVar

from pydantic import BaseModel, Field

M = TypeVar("M", bound=BaseModel)

_AGENT_PREFIX_RE = re.compile(r"^\s*([A-Za-z0-9_.\-]{1,48}):\s+")


def extract_json_object(raw_text: str) -> str:
    """Strip OpenMinion agent prefixes and markdown fences, returning the first JSON object."""
    text = raw_text.lstrip()
    prefix_match = _AGENT_PREFIX_RE.match(text)
    if prefix_match:
        remainder = text[prefix_match.end():].lstrip()
        if remainder.startswith("{") or remainder.startswith("```"):
            text = remainder

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text.strip())

    start = text.find("{")
    if start < 0:
        return text.strip()

    depth = 0
    in_string = False
    escaped = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
    return text[start:].strip()


def parse_structured_reply(raw_text: str, model_cls: type[M]) -> tuple[M, dict[str, bool]]:
    """Parse an OpenMinion agent reply into a Pydantic model and detect SDK envelope quirks."""
    stripped = raw_text.lstrip()
    prefix_match = _AGENT_PREFIX_RE.match(stripped)
    had_agent_prefix = bool(
        prefix_match
        and stripped[prefix_match.end():].lstrip().startswith(("{", "```"))
    )
    had_markdown_fence = "```" in stripped
    candidate = extract_json_object(raw_text)
    parsed = model_cls.model_validate_json(candidate)
    return parsed, {
        "had_agent_prefix": had_agent_prefix,
        "had_markdown_fence": had_markdown_fence,
    }


def detect_runtime_interception(raw_text: str) -> str | None:
    """Detect whether OpenMinion runtime safety/task-context guards intercepted a turn."""
    lowered = raw_text.lower()
    if "policy confirmation required" in lowered or "unknown_reversibility" in lowered:
        return "POLICY_CONFIRMATION_REQUIRED"
    if "could not safely update the task conditions" in lowered:
        return "INVALID_TASK_CONTEXT_UPDATE"
    if '"task_update"' in raw_text and '"expected_revision"' in raw_text:
        return "RAW_TASK_UPDATE_LEAK"
    return None


class PreflightCheck(BaseModel):
    """Single deterministic check on provider configuration or endpoint health."""

    check_id: str
    status: Literal["pass", "warn", "fail"]
    summary: str
    details: dict[str, object] = Field(default_factory=dict)


class PreflightReport(BaseModel):
    """Aggregated preflight inspection across local runtime and target provider."""

    generated_at_utc: str
    provider: str
    model: str
    base_url: str
    supports_native_tool_calling: bool
    credential_configured: bool
    openminion_version: str
    checks: list[PreflightCheck] = Field(default_factory=list)
    overall_status: Literal["ready", "degraded", "blocked"]


class BuildingBlockProbeResult(BaseModel):
    """Measured execution result for one OpenMinion 0.1 SDK building-block probe."""

    probe_id: str
    building_block: str
    status: Literal["pass", "workaround", "expected_error", "fail"]
    elapsed_ms: float
    attempts: int = 1
    run_id: str | None = None
    run_state: str | None = None
    session_id: str | None = None
    summary: str
    evidence: dict[str, object] = Field(default_factory=dict)


class ProbeMatrixReport(BaseModel):
    """Complete building-block probe matrix executed against a real model backend."""

    generated_at_utc: str
    provider: str
    model: str
    openminion_version: str
    total_probes: int
    passed_probes: int
    total_elapsed_ms: float
    probes: list[BuildingBlockProbeResult] = Field(default_factory=list)


class WorkerEvaluation(BaseModel):
    """Structured verdict emitted by an isolated OpenMinion worker subagent."""

    worker_role: str
    readiness: Literal["READY", "WARN", "BLOCKED"]
    confidence: float = Field(ge=0.0, le=1.0)
    key_findings: list[str] = Field(min_length=1)
    risks: list[str] = Field(default_factory=list)
    recommended_action: str


class ConsensusVerdict(BaseModel):
    """Coordinator synthesis comparing independent worker assessments."""

    task: str
    decision: Literal["READY", "WARN", "BLOCKED"]
    agreement_score: float = Field(ge=0.0, le=1.0)
    worker_summaries: list[str] = Field(min_length=1)
    discrepancies: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(min_length=1)
    final_summary: str


class RouteBenchSummary(BaseModel):
    """Top-level run bundle tying preflight, probe matrix, and consensus output together."""

    generated_at_utc: str
    provider: str
    model: str
    openminion_version: str
    preflight: PreflightReport
    probe_matrix: ProbeMatrixReport | None = None
    consensus_verdict: ConsensusVerdict | None = None
    telemetry: dict[str, object] = Field(default_factory=dict)
