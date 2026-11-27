"""Pydantic data contracts for NovaTriage Minion."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


Severity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
RiskTier = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "MINIMAL"]


class SolidityFinding(BaseModel):
    """Single deterministic static finding in a Solidity contract."""

    rule_id: str
    severity: Severity
    title: str
    line: int
    snippet: str
    remediation: str


class SolidityAuditResult(BaseModel):
    """Deterministic static analysis summary for a Solidity contract."""

    contract_label: str
    lines_scanned: int
    risk_score: int = Field(ge=0, le=100)
    risk_tier: RiskTier
    finding_count: int = Field(ge=0)
    findings: list[SolidityFinding] = Field(default_factory=list)


class TokenPreflightResult(BaseModel):
    """Live public DexScreener + GoPlus token risk preflight summary."""

    token_address: str
    chain_id: str
    dexscreener_ok: bool
    goplus_ok: bool
    pair_count: int = 0
    top_dex: str = ""
    symbol: str = ""
    liquidity_usd: float | None = None
    volume_24h_usd: float | None = None
    price_usd: str = ""
    is_honeypot: str = "unknown"
    buy_tax: str = "unknown"
    sell_tax: str = "unknown"
    is_mintable: str = "unknown"
    can_take_back_ownership: str = "unknown"
    errors: list[str] = Field(default_factory=list)


class X402ProbeResult(BaseModel):
    """Live HTTP 402 & .well-known/x402.json verification without fake payments."""

    base_url: str
    discovery_status: int | None = None
    x402_version: int | None = None
    service_name: str = ""
    pay_to: str = ""
    network: str = ""
    facilitator: str = ""
    resource_paths: list[str] = Field(default_factory=list)
    challenge_endpoint: str = ""
    challenge_status: int | None = None
    challenge_amount_atomic: str = ""
    challenge_asset: str = ""
    challenge_scheme: str = ""
    challenge_error: str = ""


class ReconBundleResult(BaseModel):
    """Typed output returned by ReconMinion over Handoff."""

    token_preflight: TokenPreflightResult | None = None
    x402_probe: X402ProbeResult | None = None


class SubagentDelegationSummary(BaseModel):
    """Audit trail of bounded OpenMinion subagent / handoff delegation."""

    agent_name: str
    role: str
    tool_allowlist: list[str] = Field(default_factory=list)
    run_state: str = ""
    summary: str = ""


class ApprovalDecisionRecord(BaseModel):
    """Recorded policy confirmation decision from NovaTriageApprovalGate."""

    approval_id: str
    tool_name: str
    decision: Literal["approved", "denied"]
    reason: str


class NovaTriageReport(BaseModel):
    """Structured final triage report produced by NovaTriageCoordinator."""

    target_name: str
    overall_risk_score: int = Field(ge=0, le=100)
    overall_risk_tier: RiskTier
    recommendation: Literal["BLOCK", "MANUAL_REVIEW", "PROCEED_WITH_CAUTION", "CLEAR"]
    solidity_audit: SolidityAuditResult
    token_preflight: TokenPreflightResult | None = None
    x402_probe: X402ProbeResult | None = None
    delegations: list[SubagentDelegationSummary] = Field(default_factory=list)
    memory_hits: list[str] = Field(default_factory=list)
    executive_summary: str
