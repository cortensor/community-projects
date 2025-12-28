"""
Xea Governance Oracle - Pydantic Schemas

Request/Response schemas for API endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Literal, Dict, List, Any
from pydantic import BaseModel, Field


# ============================================================================
# Versioning & Diff Schemas
# ============================================================================

class ClaimStatus(str, Enum):
    """Status of a claim when comparing versions."""
    UNCHANGED = "unchanged"
    MODIFIED = "modified"
    NEW = "new"
    REMOVED = "removed"


class ClaimDiffItem(BaseModel):
    """Details about a modified or compared claim."""
    
    claim_id: str = Field(..., description="Claim identifier")
    status: ClaimStatus = Field(..., description="Change status")
    similarity_score: Optional[float] = Field(None, ge=0, le=1, description="Semantic similarity to previous version")
    prev_claim_text: Optional[str] = Field(None, description="Text from previous version")
    curr_claim_text: Optional[str] = Field(None, description="Text in current version")
    numeric_delta: Optional[Dict[str, float]] = Field(None, description="Changes in numeric values")


class ClaimDiff(BaseModel):
    """Complete diff between two versions of claims."""
    
    unchanged: List[str] = Field(default_factory=list, description="IDs of unchanged claims")
    modified: List[ClaimDiffItem] = Field(default_factory=list, description="Modified claim details")
    new: List[str] = Field(default_factory=list, description="IDs of newly added claims")
    removed: List[str] = Field(default_factory=list, description="IDs of removed claims")
    
    @property
    def has_changes(self) -> bool:
        """Returns True if there are any changes."""
        return bool(self.modified or self.new or self.removed)


class ProposalVersion(BaseModel):
    """A single version of a proposal."""
    
    proposal_id: str = Field(..., description="Stable proposal identifier")
    version_number: int = Field(..., ge=1, description="Version number (v1, v2, ...)")
    proposal_hash: str = Field(..., description="SHA-256 hash of this version")
    previous_hash: Optional[str] = Field(None, description="Hash of previous version")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    claim_ids: List[str] = Field(default_factory=list, description="Claim IDs in this version")


class ProposalHistory(BaseModel):
    """Complete version history for a proposal."""
    
    proposal_id: str
    versions: List[ProposalVersion] = Field(default_factory=list)
    latest_version: int = Field(0, description="Latest version number")


# ============================================================================
# View Role & Intelligence Mode Schemas
# ============================================================================

class ViewRole(str, Enum):
    """Role for evidence view transformation."""
    VOTER = "voter"
    DELEGATE = "delegate"
    AUDITOR = "auditor"


class VoterView(BaseModel):
    """Simplified view for voters - quick governance decision."""
    
    proposal_hash: str
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    recommendation: Literal["Approve", "Caution", "Reject"]
    key_flags: List[str] = Field(default_factory=list, max_length=2)
    rubric_id: Optional[str] = None
    rubric_version: Optional[int] = None


class DelegateClaimView(BaseModel):
    """Claim-level view for delegates."""
    
    id: str
    text: str
    verdict: str
    recommendation: str
    poi_agreement: float
    pouw_mean: float
    pouw_ci_95: List[float]
    has_disagreement: bool


class DelegateView(BaseModel):
    """Detailed view for delegates - informed voting."""
    
    proposal_hash: str
    claims: List[DelegateClaimView]
    overall_poi_agreement: float
    overall_pouw_score: float
    overall_ci_95: List[float]
    flags: List[str] = Field(default_factory=list)
    rubric_id: Optional[str] = None
    rubric_version: Optional[int] = None


# ============================================================================
# DAO & Rubric Schemas
# ============================================================================

class RubricWeights(BaseModel):
    """PoUW scoring weights for a rubric."""
    
    accuracy: float = Field(0.4, ge=0, le=1)
    omission_risk: float = Field(0.3, ge=0, le=1)
    evidence_quality: float = Field(0.2, ge=0, le=1)
    governance_relevance: float = Field(0.1, ge=0, le=1)
    
    def model_post_init(self, __context):
        total = self.accuracy + self.omission_risk + self.evidence_quality + self.governance_relevance
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Rubric weights must sum to 1.0, got {total}")


class ProposalTypePreset(BaseModel):
    """Preset weights for specific proposal types."""
    
    proposal_type: Literal["treasury", "protocol_upgrade", "grants", "general"]
    weights: RubricWeights
    thresholds: Dict[str, float] = Field(default_factory=dict)


class Rubric(BaseModel):
    """DAO-specific PoUW rubric definition."""
    
    rubric_id: str
    version: int = Field(1, ge=1)
    dao_id: str
    name: str
    description: Optional[str] = None
    weights: RubricWeights
    presets: List[ProposalTypePreset] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_immutable: bool = Field(False, description="True once used in evidence - cannot be modified")


class DAO(BaseModel):
    """DAO registration."""
    
    dao_id: str
    name: str
    description: Optional[str] = None
    default_rubric_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DAORegisterRequest(BaseModel):
    """Request to register a DAO."""
    
    dao_id: str = Field(..., description="Unique DAO identifier")
    name: str
    description: Optional[str] = None
    default_rubric_id: Optional[str] = None


class RubricCreateRequest(BaseModel):
    """Request to create a rubric."""
    
    dao_id: str
    name: str
    description: Optional[str] = None
    weights: RubricWeights
    presets: List[ProposalTypePreset] = Field(default_factory=list)


# ============================================================================
# Claim Schemas
# ============================================================================

class ClaimCanonical(BaseModel):
    """Canonical extracted values from a claim."""
    
    numbers: List[float] = Field(default_factory=list, description="Normalized numeric values (e.g., 10% -> 0.10)")
    addresses: List[str] = Field(default_factory=list, description="Normalized ETH addresses (lowercased)")
    urls: List[str] = Field(default_factory=list, description="Normalized URLs")


class Claim(BaseModel):
    """Atomic claim extracted from a proposal."""

    id: str = Field(..., description="Claim identifier (c1, c2, ...)")
    text: str = Field(..., description="The verbatim claim text extracted from the proposal")
    paragraph_index: int = Field(..., ge=0, description="Zero-indexed paragraph number")
    char_range: List[int] = Field(..., description="Character start and end positions [start, end]")
    type: Literal["factual", "normative", "numeric"] = Field(..., description="Claim type classification")
    canonical: ClaimCanonical = Field(default_factory=ClaimCanonical, description="Canonicalized values")


# ============================================================================
# Ingest Schemas
# ============================================================================

class IngestRequest(BaseModel):
    """Request to ingest a proposal."""

    url: Optional[str] = Field(None, description="URL of the proposal to ingest")
    text: Optional[str] = Field(None, description="Raw text of the proposal")
    previous_proposal_id: Optional[str] = Field(None, description="ID of previous proposal version for diff tracking")

    def model_post_init(self, __context):
        if not self.url and not self.text:
            raise ValueError("Either 'url' or 'text' must be provided")


class IngestResponse(BaseModel):
    """Response from proposal ingestion."""

    # Versioning fields
    proposal_id: str = Field(..., description="Stable proposal identifier")
    version_number: int = Field(1, ge=1, description="Version number of this proposal")
    proposal_hash: str = Field(..., description="SHA-256 hash of canonical text with URI")
    previous_hash: Optional[str] = Field(None, description="Hash of previous version if this is an update")
    
    # Content
    canonical_text: str = Field(..., description="Canonicalized proposal text")
    claims: List[Claim] = Field(..., description="Extracted atomic claims")
    
    # Diff (only present when previous_proposal_id was provided)
    claim_diff: Optional[ClaimDiff] = Field(None, description="Changes from previous version")


# ============================================================================
# Miner Schemas
# ============================================================================

class MinerScores(BaseModel):
    """PoUW scoring breakdown for a miner response."""

    accuracy: float = Field(..., ge=0, le=1)
    omission_risk: float = Field(..., ge=0, le=1)
    evidence_quality: float = Field(..., ge=0, le=1)
    governance_relevance: float = Field(..., ge=0, le=1)
    composite: float = Field(..., ge=0, le=1)


class MinerResponse(BaseModel):
    """Response from a single miner for a claim."""

    miner_id: str
    claim_id: str
    verdict: Literal["verified", "refuted", "unverifiable", "partial"]
    rationale: str
    evidence_links: List[str] = Field(default_factory=list)
    embedding: Optional[List[float]] = None
    scores: MinerScores
    
    # Audit: Raw response from Cortensor Testnet
    cortensor_raw: Optional[Dict[str, Any]] = Field(None, description="Raw unaltered response from Cortensor Router")


# ============================================================================
# Validate Schemas
# ============================================================================

class ValidateRequest(BaseModel):
    """Request to start validation job."""

    proposal_hash: str = Field(..., description="Hash of proposal to validate")


class ValidateResponse(BaseModel):
    """Response from validation job creation."""

    job_id: str
    proposal_hash: str
    status: Literal["queued", "running", "completed", "failed"]
    created_at: datetime
    estimated_completion: Optional[datetime] = None


# ============================================================================
# Status Schemas
# ============================================================================

class JobProgress(BaseModel):
    """Progress information for a validation job."""

    claims_total: int
    claims_validated: int
    miners_contacted: int
    miners_responded: int


class StatusResponse(BaseModel):
    """Response for job status query."""

    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    progress: JobProgress
    partial_results: List[MinerResponse] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    ready_for_aggregation: bool = False
    # Stage tracking (NEW)
    current_stage: Optional[str] = None
    retries_attempted: Optional[int] = 0
    last_heartbeat: Optional[str] = None
    quorum_target: Optional[int] = 3


# ============================================================================
# Aggregate Schemas
# ============================================================================

class AggregateRequest(BaseModel):
    """Request to aggregate validation results."""

    job_id: str = Field(..., description="Job ID to aggregate")
    publish: bool = Field(False, description="Whether to publish to IPFS")


class ClaimAggregation(BaseModel):
    """Aggregated results for a single claim."""
    
    id: str
    text: str = ""
    poi_agreement: float = Field(..., ge=0, le=1)
    mode_verdict: str
    embedding_dispersion: float = Field(..., ge=0)
    pouw_mean: float = Field(..., ge=0, le=1)
    pouw_ci_95: List[float] = Field(..., min_length=2, max_length=2)
    outliers: List[str] = Field(default_factory=list)
    final_recommendation: Literal["supported", "disputed", "supported_with_caution"]
    miner_responses: List[Dict[str, Any]] = Field(default_factory=list)


class AggregateResponse(BaseModel):
    """Response from aggregation."""
    
    job_id: str
    evidence_bundle: Dict[str, Any]
    ipfs_cid: Optional[str] = None


# ============================================================================
# Evidence Bundle Schema (matches exact spec)
# ============================================================================

class EvidenceBundle(BaseModel):
    """
    Complete evidence bundle with aggregated results.
    
    Schema:
    {
      "proposal_hash": "<sha256>",
      "job_id": "<job_id>",
      "claims": [...aggregated claim data...],
      "overall_poi_agreement": <float>,
      "overall_pouw_score": <float>,
      "overall_ci_95": [low, high],
      "critical_flags": [...],
      "timestamp": "ISO8601"
    }
    """
    
    proposal_hash: str
    job_id: str
    claims: List[ClaimAggregation]
    overall_poi_agreement: float = Field(..., ge=0, le=1)
    overall_pouw_score: float = Field(..., ge=0, le=1)
    overall_ci_95: List[float] = Field(..., min_length=2, max_length=2)
    critical_flags: List[str] = Field(default_factory=list)
    timestamp: str
    
    # Versioning & Selective Revalidation
    proposal_id: Optional[str] = Field(None, description="Stable proposal identifier")
    version_number: Optional[int] = Field(None, description="Version number this evidence is for")
    validation_scope: Literal["full", "partial"] = Field("full", description="Whether all claims were revalidated")
    revalidated_claims: List[str] = Field(default_factory=list, description="IDs of claims that were revalidated in this job")
    inherited_claims: List[str] = Field(default_factory=list, description="IDs of claims with inherited results from previous version")
    previous_job_id: Optional[str] = Field(None, description="Job ID from which results were inherited")
    
    # Resilience Metadata (Retry/Fallback)
    redundancy_level: Literal["full", "reduced", "minimal"] = Field("full", description="Miner redundancy achieved")
    miners_requested: int = Field(5, description="Number of miners requested")
    miners_responded: int = Field(5, description="Number of miners that responded")
    missing_miners: List[str] = Field(default_factory=list, description="IDs of miners that failed/timed out")
    confidence_adjustment_factor: float = Field(1.0, ge=0, le=1, description="Confidence adjustment based on redundancy")
    
    # Verification & Replay
    computation_hash: Optional[str] = Field(None, description="Deterministic hash of all evidence components")
    replay_version: str = Field("1.0", description="Replay algorithm version for compatibility")
    verification_instructions: Dict[str, Any] = Field(
        default_factory=lambda: {
            "algorithm": "SHA256",
            "components": ["claims_hash", "responses_hash", "aggregation_hash"],
            "cli_command": "python -m backend.cli verify <file.json>",
        },
        description="Instructions for independent verification"
    )


# ============================================================================
# Attest Schemas
# ============================================================================

class AttestRequest(BaseModel):
    """Request to create attestation."""

    job_id: str = Field(..., description="Job ID to attest")
    publish: bool = Field(False, description="Whether to publish to IPFS")


class AttestResponse(BaseModel):
    """Response from attestation creation."""

    job_id: str
    proposal_hash: str
    ipfs_cid: Optional[str] = None
    signature: str
    signer: str
    message_hash: str
    verification_instructions: Dict[str, str]


# ============================================================================
# Claims Edit Schemas
# ============================================================================

class ClaimsEditRequest(BaseModel):
    """Request to update claims for a proposal."""
    
    claims: List[Claim] = Field(..., description="Updated claims list")


# ============================================================================
# WebSocket Message Schemas
# ============================================================================

class WSMinerResponseMessage(BaseModel):
    """WebSocket message for miner response."""
    
    type: Literal["miner_response"] = "miner_response"
    job_id: str
    claim_id: str
    miner_response: Dict[str, Any]


class WSAggregateMessage(BaseModel):
    """WebSocket message for aggregation complete."""
    
    type: Literal["aggregate"] = "aggregate"
    job_id: str
    evidence_bundle: Dict[str, Any]


class WSStatusMessage(BaseModel):
    """WebSocket message for job status update."""
    
    type: Literal["status"] = "status"
    job_id: str
    status: str
    progress: Dict[str, int]
