"""
History service for managing validation history in the database.
"""

import json
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from .database import ValidationHistory, get_db, SessionLocal


def save_history(
    job_id: str,
    proposal_hash: str,
    proposal_id: Optional[str] = None,
    version_number: int = 1,
    proposal_title: Optional[str] = None,
    claims_count: int = 0,
    status: str = "pending",
    overall_verdict: Optional[str] = None,
    confidence_score: Optional[float] = None,
    ipfs_cid: Optional[str] = None,
    network_used: Optional[str] = None,
    evidence_json: Optional[dict] = None,
) -> ValidationHistory:
    """Save a new history entry or update existing one."""
    db = SessionLocal()
    try:
        # Check if exists
        existing = db.query(ValidationHistory).filter(
            ValidationHistory.job_id == job_id
        ).first()
        
        if existing:
            # Update existing
            existing.status = status
            existing.overall_verdict = overall_verdict
            existing.confidence_score = confidence_score
            existing.ipfs_cid = ipfs_cid
            existing.network_used = network_used
            if proposal_id:
                existing.proposal_id = proposal_id
            if version_number:
                existing.version_number = version_number
            if evidence_json:
                existing.evidence_json = json.dumps(evidence_json)
            if status == "completed":
                existing.completed_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # Create new
            history = ValidationHistory(
                job_id=job_id,
                proposal_id=proposal_id,
                version_number=version_number,
                proposal_hash=proposal_hash,
                proposal_title=proposal_title,
                claims_count=claims_count,
                status=status,
                overall_verdict=overall_verdict,
                confidence_score=confidence_score,
                ipfs_cid=ipfs_cid,
                network_used=network_used,
                evidence_json=json.dumps(evidence_json) if evidence_json else None,
            )
            db.add(history)
            db.commit()
            db.refresh(history)
            return history
    finally:
        db.close()


def get_history(limit: int = 50, offset: int = 0) -> List[dict]:
    """Get validation history list."""
    db = SessionLocal()
    try:
        items = (
            db.query(ValidationHistory)
            .order_by(ValidationHistory.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [
            {
                "job_id": item.job_id,
                "proposal_id": item.proposal_id,
                "version_number": item.version_number,
                "proposal_hash": item.proposal_hash,
                "proposal_title": item.proposal_title,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "completed_at": item.completed_at.isoformat() if item.completed_at else None,
                "status": item.status,
                "claims_count": item.claims_count,
                "overall_verdict": item.overall_verdict,
                "confidence_score": item.confidence_score,
                "ipfs_cid": item.ipfs_cid,
                "network_used": item.network_used,
            }
            for item in items
        ]
    finally:
        db.close()


def get_history_by_job_id(job_id: str) -> Optional[dict]:
    """Get a specific history entry by job_id."""
    db = SessionLocal()
    try:
        item = db.query(ValidationHistory).filter(
            ValidationHistory.job_id == job_id
        ).first()
        
        if not item:
            return None
            
        return {
            "job_id": item.job_id,
            "proposal_id": item.proposal_id,
            "version_number": item.version_number,
            "proposal_hash": item.proposal_hash,
            "proposal_title": item.proposal_title,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "completed_at": item.completed_at.isoformat() if item.completed_at else None,
            "status": item.status,
            "claims_count": item.claims_count,
            "overall_verdict": item.overall_verdict,
            "confidence_score": item.confidence_score,
            "ipfs_cid": item.ipfs_cid,
            "network_used": item.network_used,
            "evidence_json": json.loads(item.evidence_json) if item.evidence_json else None,
        }
    finally:
        db.close()


def get_recent_history(limit: int = 3) -> List[dict]:
    """Get the most recent history items for display on home page."""
    return get_history(limit=limit)
