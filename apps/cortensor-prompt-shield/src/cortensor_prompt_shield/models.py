"""Typed Pydantic v2 models for Cortensor Prompt Shield."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ToolSurfaceFinding(BaseModel):
    file_path: str
    function_name: str
    line_number: int
    severity: Literal["HIGH", "MEDIUM", "LOW", "INFO"]
    rule_id: str
    detail: str
    recommendation: str


class ConfigPolicyFinding(BaseModel):
    section: str
    severity: Literal["HIGH", "MEDIUM", "LOW", "INFO"]
    detail: str
    recommendation: str


class AttackProbeResult(BaseModel):
    vector_id: str
    category: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    prompt_summary: str
    blocked: bool
    canary_leaked: bool
    approval_intercepted: bool
    response_excerpt: str


class SessionIsolationResult(BaseModel):
    shared_session_recalled: bool
    isolated_session_leaked: bool
    shared_session_id: str
    isolated_session_id: str
    shared_excerpt: str
    isolated_excerpt: str


class SecurityAuditReport(BaseModel):
    """Structured Pydantic output produced by the OpenMinion Lead Auditor Agent."""

    overall_grade: Literal["A", "B", "C", "D", "F"] = Field(
        description="Overall security grade from A (hardened) to F (critical bypass)."
    )
    risk_score_0_100: int = Field(
        ge=0,
        le=100,
        description="Aggregate risk score where 0 is safest and 100 is highest risk.",
    )
    executive_summary: str = Field(
        description="Concise 2-3 sentence summary of agent security posture."
    )
    top_findings: list[str] = Field(
        description="Top 3-5 prioritized security or policy findings."
    )
    openminion_patches: list[str] = Field(
        description="Concrete @tool decorator or agents.json hardening recommendations."
    )
    cortensor_readiness_verdict: Literal["READY", "NEEDS_HARDENING", "BLOCK_DEPLOY"] = Field(
        description="Deployment recommendation for Cortensor Portal/Router production workflows."
    )


class FullAuditBundle(BaseModel):
    schema_version: str = "1.0.0"
    openminion_version: str
    provider: str
    model: str
    target_path: str
    timestamp_utc: str
    stream_events_observed: int
    static_tool_findings: list[ToolSurfaceFinding]
    config_policy_findings: list[ConfigPolicyFinding]
    live_attack_probes: list[AttackProbeResult]
    session_isolation: SessionIsolationResult
    write_gate_denied_verified: bool
    write_gate_approved_verified: bool
    proxy_requests: int = 0
    proxy_raw_bytes: int = 0
    proxy_compacted_bytes: int = 0
    structured_report: SecurityAuditReport
    report_sha256: str = ""
