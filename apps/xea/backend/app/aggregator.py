"""
Xea Governance Oracle - Aggregator

Aggregates miner responses into evidence bundles with PoI and PoUW metrics.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import numpy as np

from app.config import settings
from app.schemas import (
    EvidenceBundle,
    ClaimAggregation,
    MinerResponse,
    MinerScores,
)
from app.stats import (
    mean_pairwise_cosine_distance,
    bootstrap_ci,
    detect_mahalanobis_outliers,
    compute_mode_agreement,
)

logger = logging.getLogger(__name__)


def get_responses_dir() -> Path:
    """Get the responses data directory."""
    responses_dir = Path(settings.data_dir) / "responses"
    if not responses_dir.exists():
        responses_dir = Path(__file__).parent.parent.parent / "data" / "responses"
    responses_dir.mkdir(parents=True, exist_ok=True)
    return responses_dir


def get_evidence_dir() -> Path:
    """Get the evidence bundles data directory."""
    evidence_dir = Path(settings.data_dir) / "evidence"
    if not evidence_dir.exists():
        evidence_dir = Path(__file__).parent.parent.parent / "data" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    return evidence_dir


def get_jobs_dir() -> Path:
    """Get the jobs data directory."""
    jobs_dir = Path(settings.data_dir) / "jobs"
    if not jobs_dir.exists():
        jobs_dir = Path(__file__).parent.parent.parent / "data" / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    return jobs_dir


def load_job_data(job_id: str) -> Optional[Dict[str, Any]]:
    """Load job data from file."""
    jobs_dir = get_jobs_dir()
    file_path = jobs_dir / f"{job_id}.json"
    if not file_path.exists():
        return None
    with open(file_path, "r") as f:
        return json.load(f)


def load_raw_responses(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Load raw miner responses from persisted JSON.
    
    Args:
        job_id: The job identifier
        
    Returns:
        Dict with job_id and responses list, or None if not found
    """
    responses_dir = get_responses_dir()
    file_path = responses_dir / f"{job_id}.json"
    
    if not file_path.exists():
        logger.warning(f"Responses file not found: {file_path}")
        return None
    
    with open(file_path, "r") as f:
        return json.load(f)


def group_responses_by_claim(raw_data: Dict[str, Any]) -> Dict[str, List[Dict]]:
    """
    Group raw responses by claim_id.
    
    Args:
        raw_data: Raw responses data from file
        
    Returns:
        Dict mapping claim_id to list of miner responses
    """
    grouped = {}
    
    for entry in raw_data.get("responses", []):
        claim_id = entry.get("claim_id")
        response = entry.get("response", {})
        
        if claim_id not in grouped:
            grouped[claim_id] = []
        grouped[claim_id].append(response)
    
    return grouped


def aggregate_claim_responses(
    claim_id: str,
    responses: List[Dict],
    bootstrap_seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Aggregate miner responses for a single claim.
    
    Computes:
    - poi_agreement: Mode count of verdicts / total verdicts
    - embedding_dispersion: Mean pairwise cosine distance of embeddings
    - pouw_mean: Mean of composite PoUW scores
    - pouw_ci_95: Bootstrap 95% confidence interval for pouw_mean
    - outliers: Miner IDs flagged as outliers via Mahalanobis distance
    - final_recommendation: Based on thresholds
    
    Args:
        claim_id: The claim identifier
        responses: List of miner response dicts
        bootstrap_seed: Optional seed for reproducible bootstrap
        
    Returns:
        Dict with aggregated metrics
    """
    if not responses:
        return {
            "poi_agreement": 0.0,
            "mode_verdict": "unknown",
            "embedding_dispersion": 0.0,
            "pouw_mean": 0.0,
            "pouw_ci_95": [0.0, 0.0],
            "outliers": [],
            "final_recommendation": "disputed",
            "miner_responses": [],
        }
    
    # Extract verdicts
    verdicts = [r.get("verdict", "unknown") for r in responses]
    mode_verdict, poi_agreement = compute_mode_agreement(verdicts)
    
    # Extract embeddings for dispersion calculation
    embeddings = []
    for r in responses:
        emb = r.get("embedding")
        if emb and isinstance(emb, list) and len(emb) > 0:
            embeddings.append(emb)
    
    embedding_dispersion = mean_pairwise_cosine_distance(embeddings)
    
    # Extract PoUW scores
    pouw_scores = []
    score_vectors = []
    miner_ids = []
    
    for r in responses:
        scores = r.get("scores", {})
        composite = scores.get("composite", 0.0)
        pouw_scores.append(composite)
        miner_ids.append(r.get("miner_id", "unknown"))
        
        # Build score vector for Mahalanobis
        score_vector = [
            scores.get("accuracy", 0.0),
            scores.get("omission_risk", 0.0),
            scores.get("evidence_quality", 0.0),
            scores.get("governance_relevance", 0.0),
        ]
        score_vectors.append(score_vector)
    
    # Compute pouw_mean and CI
    pouw_mean = float(np.mean(pouw_scores)) if pouw_scores else 0.0
    pouw_ci_95 = bootstrap_ci(pouw_scores, n_iter=1000, alpha=0.05, seed=bootstrap_seed)
    
    # Detect outliers via Mahalanobis distance
    outlier_indices = []
    if len(score_vectors) >= 3:  # Need at least 3 samples for meaningful outlier detection
        score_matrix = np.array(score_vectors)
        outlier_indices = detect_mahalanobis_outliers(score_matrix, threshold=3.0)
    
    outlier_miner_ids = [miner_ids[i] for i in outlier_indices]
    
    # Determine final recommendation
    final_recommendation = determine_recommendation(poi_agreement, pouw_mean, mode_verdict)
    
    return {
        "poi_agreement": round(poi_agreement, 4),
        "mode_verdict": mode_verdict,
        "embedding_dispersion": round(embedding_dispersion, 4),
        "pouw_mean": round(pouw_mean, 4),
        "pouw_ci_95": list(pouw_ci_95),
        "outliers": outlier_miner_ids,
        "final_recommendation": final_recommendation,
        "miner_responses": responses,
    }


def determine_recommendation(
    poi_agreement: float,
    pouw_mean: float,
    mode_verdict: str,
) -> str:
    """
    Determine final recommendation based on thresholds.
    
    Decision logic:
    - If poi_agreement >= 0.8 AND pouw_mean >= 0.75 => "supported"
    - If poi_agreement < 0.5 OR pouw_mean < 0.5 => "disputed"
    - Else => "supported_with_caution"
    
    Additionally, if mode_verdict is "refuted", always return "disputed".
    
    Args:
        poi_agreement: Agreement ratio (0-1)
        pouw_mean: Mean PoUW score (0-1)
        mode_verdict: Most common verdict
        
    Returns:
        One of: "supported", "disputed", "supported_with_caution"
    """
    # If majority says refuted, claim is disputed
    if mode_verdict == "refuted":
        return "disputed"
    
    # High confidence support
    if poi_agreement >= 0.8 and pouw_mean >= 0.75:
        return "supported"
    
    # Low confidence or disagreement
    if poi_agreement < 0.5 or pouw_mean < 0.5:
        return "disputed"
    
    # Middle ground
    return "supported_with_caution"


def generate_critical_flags(
    claims_aggregated: List[Dict[str, Any]],
) -> List[str]:
    """
    Generate critical flags for the evidence bundle.
    
    Flags are generated for:
    - Claims with outliers
    - Claims marked as disputed
    - Claims with low poi_agreement
    - Evidence links from disputing miners
    
    Args:
        claims_aggregated: List of aggregated claim data
        
    Returns:
        List of critical flag strings
    """
    flags = []
    
    for claim in claims_aggregated:
        claim_id = claim.get("id", "unknown")
        recommendation = claim.get("final_recommendation", "")
        outliers = claim.get("outliers", [])
        poi = claim.get("poi_agreement", 0.0)
        
        # Flag disputes
        if recommendation == "disputed":
            flags.append(f"claim {claim_id}: marked as disputed")
        
        # Flag outliers
        for outlier in outliers:
            flags.append(f"claim {claim_id}: miner {outlier} flagged as outlier")
        
        # Flag low agreement
        if poi < 0.6 and poi > 0:
            flags.append(f"claim {claim_id}: low agreement ({poi:.0%})")
        
        # Check for refuting miners with evidence
        for resp in claim.get("miner_responses", []):
            if resp.get("verdict") == "refuted" and resp.get("evidence_links"):
                miner = resp.get("miner_id", "unknown")
                flags.append(f"claim {claim_id}: miner {miner} disputes with evidence")
    
    return flags


def aggregate_job(
    job_id: str,
    bootstrap_seed: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Aggregate all miner responses for a job into an evidence bundle.
    
    This function:
    1. Loads raw miner responses from /data/responses/{job_id}.json
    2. Groups responses by claim
    3. Computes per-claim metrics (PoI, PoUW, outliers)
    4. Aggregates into overall proposal-level metrics
    5. Generates critical flags
    6. Saves evidence bundle to /data/evidence/{job_id}.json
    
    Args:
        job_id: The job identifier
        bootstrap_seed: Optional seed for reproducible bootstrap CI
        
    Returns:
        Evidence bundle dict, or None if job not found
    """
    # Load raw responses
    raw_data = load_raw_responses(job_id)
    if not raw_data:
        logger.error(f"No responses found for job: {job_id}")
        return None
    
    # Load job data for proposal_hash
    job_data = load_job_data(job_id)
    proposal_hash = job_data.get("proposal_hash", "") if job_data else ""
    
    # Load versioning metadata from job
    proposal_id = job_data.get("proposal_id") if job_data else None
    version_number = job_data.get("version_number") if job_data else None
    claim_diff = job_data.get("claim_diff") if job_data else None
    revalidated_claim_ids = job_data.get("revalidated_claims", []) if job_data else []
    
    # Group by claim
    grouped = group_responses_by_claim(raw_data)
    
    if not grouped:
        logger.warning(f"No grouped responses for job: {job_id}")
        return None
    
    # Load original claims to get text
    from app.ingest import load_claims
    original_claims = {}
    if proposal_hash:
        claims_data = load_claims(proposal_hash)
        if claims_data and "claims" in claims_data:
            for c in claims_data["claims"]:
                original_claims[c["id"]] = c["text"]
    
    # Aggregate each claim
    claims_aggregated = []
    all_poi_agreements = []
    all_pouw_scores = []
    
    for claim_id in sorted(grouped.keys()):
        responses = grouped[claim_id]
        
        # Get claim text
        claim_text = original_claims.get(claim_id, "")
        
        aggregated = aggregate_claim_responses(claim_id, responses, bootstrap_seed)
        
        # Mark if this claim was revalidated (vs inherited)
        was_revalidated = claim_id in revalidated_claim_ids if revalidated_claim_ids else True
        
        claim_result = {
            "id": claim_id,
            "text": claim_text,
            "was_revalidated": was_revalidated,
            **aggregated,
        }
        
        claims_aggregated.append(claim_result)
        all_poi_agreements.append(aggregated["poi_agreement"])
        all_pouw_scores.extend([
            r.get("scores", {}).get("composite", 0.0)
            for r in responses
        ])
    
    # Compute overall metrics
    overall_poi = float(np.mean(all_poi_agreements)) if all_poi_agreements else 0.0
    overall_pouw = float(np.mean(all_pouw_scores)) if all_pouw_scores else 0.0
    overall_ci = bootstrap_ci(all_pouw_scores, n_iter=1000, alpha=0.05, seed=bootstrap_seed)
    
    # Generate critical flags
    critical_flags = generate_critical_flags(claims_aggregated)
    
    # Determine validation scope
    if claim_diff:
        validation_scope = "selective" if revalidated_claim_ids else "full"
    else:
        validation_scope = "full"
    
    # Build evidence bundle
    evidence_bundle = {
        "proposal_hash": proposal_hash,
        "job_id": job_id,
        
        # Versioning metadata (NEW)
        "proposal_id": proposal_id,
        "version_number": version_number,
        "claim_diff": claim_diff,
        "validation_scope": validation_scope,
        "revalidated_claims": revalidated_claim_ids,
        
        "claims": claims_aggregated,
        "overall_poi_agreement": round(overall_poi, 4),
        "overall_pouw_score": round(overall_pouw, 4),
        "overall_ci_95": list(overall_ci),
        "critical_flags": critical_flags,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        
        # Resilience metadata (defaults - can be overridden by workers)
        "redundancy_level": "full",
        "miners_requested": 5,
        "miners_responded": len(all_pouw_scores) if all_pouw_scores else 0,
        "missing_miners": [],
        "confidence_adjustment_factor": 1.0,
        
        # Verification metadata
        "replay_version": "1.0",
        "verification_instructions": {
            "algorithm": "SHA256",
            "components": ["claims_hash", "responses_hash", "aggregation_hash"],
            "cli_command": "python -m backend.cli verify <file.json>",
        },
        
        # Network metadata (for testnet visibility)
        "network_metadata": {
            "network_used": settings.cortensor_network,
            "fallback_attempted": False,
            "miner_quorum_target": settings.miner_quorum,
        },
    }
    
    # Compute and add computation hash
    from app.replay import compute_evidence_hash
    evidence_bundle["computation_hash"] = compute_evidence_hash(evidence_bundle)
    
    # Save to file
    save_evidence_bundle(job_id, evidence_bundle)
    
    logger.info(
        f"Aggregation complete for job {job_id}",
        extra={
            "claims_count": len(claims_aggregated),
            "overall_poi": overall_poi,
            "overall_pouw": overall_pouw,
            "flags_count": len(critical_flags),
            "computation_hash": evidence_bundle["computation_hash"],
        }
    )
    
    return evidence_bundle


def save_evidence_bundle(job_id: str, bundle: Dict[str, Any]):
    """Save evidence bundle to file."""
    evidence_dir = get_evidence_dir()
    file_path = evidence_dir / f"{job_id}.json"
    
    with open(file_path, "w") as f:
        json.dump(bundle, f, indent=2, default=str)
    
    logger.info(f"Evidence bundle saved: {file_path}")


def load_evidence_bundle(job_id: str) -> Optional[Dict[str, Any]]:
    """Load evidence bundle from file."""
    evidence_dir = get_evidence_dir()
    file_path = evidence_dir / f"{job_id}.json"
    
    if not file_path.exists():
        return None
    
    with open(file_path, "r") as f:
        return json.load(f)
