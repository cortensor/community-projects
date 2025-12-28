"""
Xea Governance Oracle - Database Models

SQLAlchemy models for persistence (if needed).
Currently using Redis for job state management.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class JobState(BaseModel):
    """In-memory/Redis job state model."""

    job_id: str
    proposal_hash: str
    status: str  # queued, running, completed, failed
    claims_total: int = 0
    claims_validated: int = 0
    miners_contacted: int = 0
    miners_responded: int = 0
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime
    error: Optional[str] = None


class ProposalCache(BaseModel):
    """Cached proposal data."""

    proposal_hash: str
    canonical_text: str
    claims: list[dict]
    created_at: datetime
    source_url: Optional[str] = None


class MinerResponseStore(BaseModel):
    """Stored miner response."""

    job_id: str
    miner_id: str
    claim_id: str
    verdict: str
    rationale: str
    evidence_links: list[str]
    scores: dict
    received_at: datetime
