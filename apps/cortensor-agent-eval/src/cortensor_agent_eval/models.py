"""Typed Pydantic v2 schemas for Cortensor Agent Eval."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ProbeResult(BaseModel):
    """Connectivity and protocol probe for an inference endpoint."""

    endpoint: str
    adapter: str
    reachable: bool
    status_code: int | None = None
    latency_ms: float = 0.0
    detail: str = ""


class EvalCaseSpec(BaseModel):
    """Single deterministic evaluation case loaded from a suite manifest."""

    case_id: str
    category: Literal[
        "tool_calling",
        "structured_output",
        "policy_gate",
        "delegated_subagent",
        "session_continuity",
    ]
    prompt: str
    expected_status: str = "PASS"
    max_latency_ms: float = 5000.0


class EvalCaseResult(BaseModel):
    """Execution result for one OpenMinion benchmark case."""

    case_id: str
    category: str
    passed: bool
    run_state: str
    latency_ms: float
    llm_calls: int = 0
    tool_calls_observed: int = 0
    detail: str = ""
    session_id: str | None = None


class ApprovalDecisionRecord(BaseModel):
    """Audit record captured by the fail-closed approval callback."""

    tool_name: str
    approval_id: str
    decision: Literal["approved", "denied"]
    reason: str
    args_keys: list[str] = Field(default_factory=list)


class EvalSuiteSummary(BaseModel):
    """Deterministic scorecard computed from executed benchmark cases."""

    suite_name: str
    provider: str
    model: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    avg_latency_ms: float
    approvals_logged: int
    session_persisted: bool
    posture_keys: list[str] = Field(default_factory=list)
    capability_keys: list[str] = Field(default_factory=list)
    self_model_health: str = ""
    tool_inventory_count: int = 0
    stream_events_observed: int = 0
    memory_bundle_items: int


class EvalReport(BaseModel):
    """Structured final verdict returned by the Judge Agent."""

    verdict: Literal["READY", "DEGRADED", "FAILED"]
    score: int = Field(ge=0, le=100)
    summary: str
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
