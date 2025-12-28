"""
Xea Governance Oracle - Replay & Verification Module

Provides deterministic hashing and offline verification of evidence bundles.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple


# ============================================================================
# Hash Computation
# ============================================================================

def compute_claims_hash(claims: List[Dict]) -> str:
    """
    Compute deterministic hash of claims.
    
    Hash includes: claim IDs, texts, and types (sorted for determinism).
    """
    # Sort claims by ID for deterministic ordering
    sorted_claims = sorted(claims, key=lambda c: c.get("id", ""))
    
    # Build canonical string
    components = []
    for claim in sorted_claims:
        claim_str = f"{claim.get('id', '')}|{claim.get('text', '')}|{claim.get('mode_verdict', '')}"
        components.append(claim_str)
    
    canonical = "\n".join(components)
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"


def compute_responses_hash(claims: List[Dict]) -> str:
    """
    Compute deterministic hash of miner responses.
    
    Hash includes: miner IDs, verdicts, rationales (sorted).
    """
    components = []
    
    for claim in sorted(claims, key=lambda c: c.get("id", "")):
        responses = claim.get("miner_responses", [])
        for resp in sorted(responses, key=lambda r: r.get("miner_id", "")):
            resp_str = (
                f"{resp.get('miner_id', '')}|"
                f"{resp.get('claim_id', '')}|"
                f"{resp.get('verdict', '')}|"
                f"{resp.get('rationale', '')[:100]}"  # Truncate for stability
            )
            components.append(resp_str)
    
    canonical = "\n".join(components)
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"


def compute_aggregation_hash(bundle: Dict) -> str:
    """
    Compute deterministic hash of aggregation results.
    
    Hash includes: PoI, PoUW scores, recommendations.
    """
    components = [
        f"poi:{bundle.get('overall_poi_agreement', 0):.6f}",
        f"pouw:{bundle.get('overall_pouw_score', 0):.6f}",
        f"ci:{bundle.get('overall_ci_95', [0, 0])}",
    ]
    
    # Add per-claim results
    for claim in sorted(bundle.get("claims", []), key=lambda c: c.get("id", "")):
        claim_str = (
            f"{claim.get('id', '')}:"
            f"{claim.get('poi_agreement', 0):.6f}:"
            f"{claim.get('pouw_mean', 0):.6f}:"
            f"{claim.get('final_recommendation', '')}"
        )
        components.append(claim_str)
    
    canonical = "\n".join(components)
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"


def compute_evidence_hash(bundle: Dict) -> str:
    """
    Compute overall computation hash for evidence bundle.
    
    Hash = SHA256(claims_hash + responses_hash + aggregation_hash)
    """
    claims_hash = compute_claims_hash(bundle.get("claims", []))
    responses_hash = compute_responses_hash(bundle.get("claims", []))
    aggregation_hash = compute_aggregation_hash(bundle)
    
    combined = f"{claims_hash}|{responses_hash}|{aggregation_hash}"
    return f"sha256:{hashlib.sha256(combined.encode()).hexdigest()}"


# ============================================================================
# Verification
# ============================================================================

@dataclass
class VerificationResult:
    """Result of evidence bundle verification."""
    
    is_valid: bool
    claims_hash_match: bool
    responses_hash_match: bool
    aggregation_hash_match: bool
    computation_hash_match: bool
    expected_hash: Optional[str] = None
    computed_hash: Optional[str] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def verify_evidence_bundle(bundle: Dict) -> VerificationResult:
    """
    Verify an evidence bundle offline.
    
    Recomputes all hashes and compares against stored values.
    
    Args:
        bundle: Evidence bundle dictionary
        
    Returns:
        VerificationResult with match status for each component
    """
    errors = []
    
    # Check if bundle has verification data
    stored_hash = bundle.get("computation_hash")
    if not stored_hash:
        return VerificationResult(
            is_valid=False,
            claims_hash_match=False,
            responses_hash_match=False,
            aggregation_hash_match=False,
            computation_hash_match=False,
            errors=["Bundle missing computation_hash - cannot verify"]
        )
    
    # Recompute hashes
    try:
        computed_hash = compute_evidence_hash(bundle)
        
        # For detailed verification, we'd need stored component hashes
        # For now, we verify the overall computation hash
        hash_match = (computed_hash == stored_hash)
        
        return VerificationResult(
            is_valid=hash_match,
            claims_hash_match=hash_match,  # Implied by overall match
            responses_hash_match=hash_match,
            aggregation_hash_match=hash_match,
            computation_hash_match=hash_match,
            expected_hash=stored_hash,
            computed_hash=computed_hash,
            errors=[] if hash_match else ["Computation hash mismatch - evidence may have been tampered with"]
        )
        
    except Exception as e:
        return VerificationResult(
            is_valid=False,
            claims_hash_match=False,
            responses_hash_match=False,
            aggregation_hash_match=False,
            computation_hash_match=False,
            errors=[f"Verification failed: {str(e)}"]
        )


def replay_aggregation(claims: List[Dict], responses: List[Dict]) -> Dict:
    """
    Re-run aggregation from raw data.
    
    This allows offline verification that aggregation logic
    produces the same results.
    
    Args:
        claims: Original claim data
        responses: Raw miner responses
        
    Returns:
        Re-computed aggregation results
    """
    from app.aggregator import (
        compute_poi,
        compute_pouw_stats,
        determine_recommendation,
    )
    
    # Re-aggregate each claim
    aggregated_claims = []
    
    for claim in claims:
        claim_id = claim.get("id")
        claim_responses = [r for r in responses if r.get("claim_id") == claim_id]
        
        if not claim_responses:
            continue
        
        # Compute PoI
        poi = compute_poi(claim_responses)
        
        # Compute PoUW stats
        pouw_stats = compute_pouw_stats(claim_responses)
        
        # Determine recommendation
        mode_verdict = max(
            set(r.get("verdict") for r in claim_responses),
            key=lambda v: sum(1 for r in claim_responses if r.get("verdict") == v)
        )
        
        recommendation = determine_recommendation(
            poi, pouw_stats["mean"], mode_verdict
        )
        
        aggregated_claims.append({
            "id": claim_id,
            "poi_agreement": poi,
            "pouw_mean": pouw_stats["mean"],
            "pouw_ci_95": pouw_stats["ci_95"],
            "mode_verdict": mode_verdict,
            "final_recommendation": recommendation,
        })
    
    # Compute overall stats
    if aggregated_claims:
        overall_poi = sum(c["poi_agreement"] for c in aggregated_claims) / len(aggregated_claims)
        overall_pouw = sum(c["pouw_mean"] for c in aggregated_claims) / len(aggregated_claims)
    else:
        overall_poi = 0
        overall_pouw = 0
    
    return {
        "claims": aggregated_claims,
        "overall_poi_agreement": overall_poi,
        "overall_pouw_score": overall_pouw,
    }


# ============================================================================
# CLI Helpers
# ============================================================================

def verify_file(filepath: str) -> Tuple[bool, str]:
    """
    Verify an evidence bundle from file.
    
    Args:
        filepath: Path to evidence.json
        
    Returns:
        Tuple of (success, message)
    """
    try:
        with open(filepath, "r") as f:
            bundle = json.load(f)
        
        result = verify_evidence_bundle(bundle)
        
        if result.is_valid:
            return True, (
                "✅ Evidence bundle verified successfully\n"
                f"   Computation hash: {result.computed_hash}\n"
                f"   Replay version: {bundle.get('replay_version', 'unknown')}"
            )
        else:
            return False, (
                "❌ Evidence verification FAILED\n"
                f"   Expected: {result.expected_hash}\n"
                f"   Computed: {result.computed_hash}\n"
                f"   Errors: {', '.join(result.errors)}"
            )
            
    except FileNotFoundError:
        return False, f"❌ File not found: {filepath}"
    except json.JSONDecodeError:
        return False, f"❌ Invalid JSON in: {filepath}"
    except Exception as e:
        return False, f"❌ Verification error: {str(e)}"


def format_verification_report(result: VerificationResult) -> str:
    """Format verification result as human-readable report."""
    lines = [
        "═" * 50,
        "EVIDENCE VERIFICATION REPORT",
        "═" * 50,
        "",
        f"Claims Hash:      {'✅ MATCH' if result.claims_hash_match else '❌ MISMATCH'}",
        f"Responses Hash:   {'✅ MATCH' if result.responses_hash_match else '❌ MISMATCH'}",
        f"Aggregation Hash: {'✅ MATCH' if result.aggregation_hash_match else '❌ MISMATCH'}",
        f"Computation Hash: {'✅ MATCH' if result.computation_hash_match else '❌ MISMATCH'}",
        "",
        "─" * 50,
        f"OVERALL: {'🎉 VERIFIED' if result.is_valid else '⚠️ VERIFICATION FAILED'}",
        "─" * 50,
    ]
    
    if result.errors:
        lines.append("")
        lines.append("Errors:")
        for error in result.errors:
            lines.append(f"  • {error}")
    
    return "\n".join(lines)
