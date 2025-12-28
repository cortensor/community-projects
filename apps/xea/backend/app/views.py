"""
Xea Governance Oracle - Views Module

Transforms evidence bundles into role-specific views without re-running inference.
"""

from typing import Dict, List, Literal, Optional, Any

from app.schemas import (
    ViewRole,
    VoterView,
    DelegateView,
    DelegateClaimView,
    Rubric,
)


# ============================================================================
# View Transformation
# ============================================================================

def transform_evidence_for_role(
    bundle: Dict[str, Any],
    role: ViewRole,
    rubric: Optional[Rubric] = None,
) -> Dict[str, Any]:
    """
    Transform an evidence bundle into a role-specific view.
    
    Args:
        bundle: Full evidence bundle from aggregation
        role: Target role (VOTER, DELEGATE, AUDITOR)
        rubric: Optional rubric for threshold customization
        
    Returns:
        Transformed view as dictionary
    """
    if role == ViewRole.VOTER:
        return _transform_voter_view(bundle, rubric)
    elif role == ViewRole.DELEGATE:
        return _transform_delegate_view(bundle, rubric)
    else:
        # AUDITOR gets full bundle with metadata
        return _transform_auditor_view(bundle)


def _transform_voter_view(bundle: Dict, rubric: Optional[Rubric]) -> Dict:
    """
    Create simplified voter view.
    
    - Risk badge (LOW/MEDIUM/HIGH)
    - Single recommendation (Approve/Caution/Reject)
    - 1-2 key flags
    """
    risk_level = _compute_risk_level(bundle, rubric)
    recommendation = _compute_recommendation(bundle, rubric)
    
    # Get top 2 most important flags
    flags = bundle.get("critical_flags", [])
    key_flags = flags[:2] if flags else []
    
    return VoterView(
        proposal_hash=bundle.get("proposal_hash", ""),
        risk_level=risk_level,
        recommendation=recommendation,
        key_flags=key_flags,
        rubric_id=bundle.get("rubric_id"),
        rubric_version=bundle.get("rubric_version"),
    ).model_dump()


def _transform_delegate_view(bundle: Dict, rubric: Optional[Rubric]) -> Dict:
    """
    Create detailed delegate view.
    
    - Claim-level breakdown
    - Disagreement indicators
    - Confidence intervals
    """
    claims = []
    
    for claim in bundle.get("claims", []):
        poi = claim.get("poi_agreement", 0)
        
        claims.append(DelegateClaimView(
            id=claim.get("id", ""),
            text=claim.get("text", ""),
            verdict=claim.get("mode_verdict", "unknown"),
            recommendation=claim.get("final_recommendation", ""),
            poi_agreement=poi,
            pouw_mean=claim.get("pouw_mean", 0),
            pouw_ci_95=claim.get("pouw_ci_95", [0, 0]),
            has_disagreement=poi < 0.8,
        ))
    
    return DelegateView(
        proposal_hash=bundle.get("proposal_hash", ""),
        claims=claims,
        overall_poi_agreement=bundle.get("overall_poi_agreement", 0),
        overall_pouw_score=bundle.get("overall_pouw_score", 0),
        overall_ci_95=bundle.get("overall_ci_95", [0, 0]),
        flags=bundle.get("critical_flags", []),
        rubric_id=bundle.get("rubric_id"),
        rubric_version=bundle.get("rubric_version"),
    ).model_dump()


def _transform_auditor_view(bundle: Dict) -> Dict:
    """
    Return full bundle for auditors with replay metadata.
    """
    # Add auditor-specific metadata
    auditor_bundle = bundle.copy()
    auditor_bundle["view_type"] = "auditor"
    auditor_bundle["includes_miner_responses"] = "claims" in bundle and any(
        c.get("miner_responses") for c in bundle.get("claims", [])
    )
    
    return auditor_bundle


# ============================================================================
# Risk & Recommendation Computation
# ============================================================================

def _compute_risk_level(
    bundle: Dict,
    rubric: Optional[Rubric],
) -> Literal["LOW", "MEDIUM", "HIGH"]:
    """
    Compute overall risk level from evidence bundle.
    
    Thresholds:
    - LOW: score >= 0.75, flags == 0, agreement >= 0.9
    - MEDIUM: score >= 0.5, flags <= 2
    - HIGH: otherwise
    """
    score = bundle.get("overall_pouw_score", 0)
    flags = len(bundle.get("critical_flags", []))
    agreement = bundle.get("overall_poi_agreement", 0)
    
    # Custom thresholds from rubric if available
    if rubric and rubric.presets:
        # Could use proposal-type specific thresholds
        pass
    
    if score >= 0.75 and flags == 0 and agreement >= 0.9:
        return "LOW"
    elif score >= 0.5 and flags <= 2:
        return "MEDIUM"
    else:
        return "HIGH"


def _compute_recommendation(
    bundle: Dict,
    rubric: Optional[Rubric],
) -> Literal["Approve", "Caution", "Reject"]:
    """
    Compute voting recommendation from evidence bundle.
    
    Logic:
    - Approve: score >= 0.75, agreement >= 0.8, no critical flags
    - Reject: score < 0.4 OR agreement < 0.5 OR has refuted claims
    - Caution: otherwise
    """
    score = bundle.get("overall_pouw_score", 0)
    agreement = bundle.get("overall_poi_agreement", 0)
    flags = bundle.get("critical_flags", [])
    
    # Check for refuted claims
    has_refuted = any(
        c.get("mode_verdict") == "refuted"
        for c in bundle.get("claims", [])
    )
    
    # Check for disputed recommendations
    has_disputed = any(
        c.get("final_recommendation") == "disputed"
        for c in bundle.get("claims", [])
    )
    
    if has_refuted or score < 0.4 or agreement < 0.5:
        return "Reject"
    elif score >= 0.75 and agreement >= 0.8 and not has_disputed:
        return "Approve"
    else:
        return "Caution"


# ============================================================================
# Utility Functions
# ============================================================================

def get_available_roles() -> List[str]:
    """Return list of available view roles."""
    return [r.value for r in ViewRole]


def validate_role(role_str: str) -> ViewRole:
    """Validate and convert role string to ViewRole enum."""
    try:
        return ViewRole(role_str.lower())
    except ValueError:
        raise ValueError(f"Invalid role: {role_str}. Must be one of: {get_available_roles()}")
