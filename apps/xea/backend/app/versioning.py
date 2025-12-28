"""
Xea Governance Oracle - Versioning Module

Handles proposal version tracking, claim diffing, and selective revalidation.
"""

import json
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.config import settings
from app.schemas import (
    Claim,
    ClaimStatus,
    ClaimDiff,
    ClaimDiffItem,
    ProposalVersion,
    ProposalHistory,
)


# ============================================================================
# Version Storage
# ============================================================================

def get_versions_dir() -> Path:
    """Get the versions data directory."""
    versions_dir = Path(settings.data_dir) / "versions"
    if not versions_dir.exists():
        # Fallback to local directory
        versions_dir = Path(__file__).parent.parent.parent / "data" / "versions"
    versions_dir.mkdir(parents=True, exist_ok=True)
    return versions_dir


def generate_proposal_id() -> str:
    """Generate a unique proposal ID."""
    return f"prop_{uuid.uuid4().hex[:12]}"


def _load_proposal_file(proposal_id: str) -> Optional[Dict]:
    """Load proposal history from file."""
    file_path = get_versions_dir() / f"{proposal_id}.json"
    if file_path.exists():
        with open(file_path, "r") as f:
            return json.load(f)
    return None


def _save_proposal_file(proposal_id: str, data: Dict) -> None:
    """Save proposal history to file."""
    file_path = get_versions_dir() / f"{proposal_id}.json"
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ============================================================================
# Version Management
# ============================================================================

def create_proposal_version(
    proposal_id: Optional[str],
    proposal_hash: str,
    claims: List[Claim],
    canonical_text: str,
    previous_hash: Optional[str] = None,
) -> ProposalVersion:
    """
    Create a new version for a proposal.
    
    Args:
        proposal_id: Existing proposal ID or None for new proposal
        proposal_hash: SHA-256 hash of this version
        claims: Extracted claims for this version
        canonical_text: The canonical text
        previous_hash: Hash of previous version (if updating)
        
    Returns:
        ProposalVersion with version details
    """
    if proposal_id:
        # Load existing history
        history_data = _load_proposal_file(proposal_id)
        if history_data:
            versions = history_data.get("versions", [])
            version_number = len(versions) + 1
        else:
            versions = []
            version_number = 1
    else:
        # New proposal
        proposal_id = generate_proposal_id()
        versions = []
        version_number = 1
    
    # Create version record
    version = ProposalVersion(
        proposal_id=proposal_id,
        version_number=version_number,
        proposal_hash=proposal_hash,
        previous_hash=previous_hash,
        created_at=datetime.now(timezone.utc),
        claim_ids=[c.id for c in claims],
    )
    
    # Store version with claims
    version_record = {
        "version_number": version_number,
        "proposal_hash": proposal_hash,
        "previous_hash": previous_hash,
        "created_at": version.created_at.isoformat(),
        "claim_ids": version.claim_ids,
        "claims": [c.model_dump() for c in claims],
        "canonical_text": canonical_text,
    }
    
    versions.append(version_record)
    
    # Save to file
    history_data = {
        "proposal_id": proposal_id,
        "latest_version": version_number,
        "versions": versions,
    }
    _save_proposal_file(proposal_id, history_data)
    
    return version


def get_proposal_history(proposal_id: str) -> Optional[ProposalHistory]:
    """
    Get complete version history for a proposal.
    
    Args:
        proposal_id: The proposal identifier
        
    Returns:
        ProposalHistory or None if not found
    """
    history_data = _load_proposal_file(proposal_id)
    if not history_data:
        return None
    
    versions = []
    for v in history_data.get("versions", []):
        versions.append(ProposalVersion(
            proposal_id=proposal_id,
            version_number=v["version_number"],
            proposal_hash=v["proposal_hash"],
            previous_hash=v.get("previous_hash"),
            created_at=datetime.fromisoformat(v["created_at"]),
            claim_ids=v.get("claim_ids", []),
        ))
    
    return ProposalHistory(
        proposal_id=proposal_id,
        versions=versions,
        latest_version=history_data.get("latest_version", 0),
    )


def get_latest_version(proposal_id: str) -> Optional[Tuple[ProposalVersion, List[Claim]]]:
    """
    Get the latest version and its claims for a proposal.
    
    Args:
        proposal_id: The proposal identifier
        
    Returns:
        Tuple of (ProposalVersion, claims) or None if not found
    """
    history_data = _load_proposal_file(proposal_id)
    if not history_data or not history_data.get("versions"):
        return None
    
    latest = history_data["versions"][-1]
    
    version = ProposalVersion(
        proposal_id=proposal_id,
        version_number=latest["version_number"],
        proposal_hash=latest["proposal_hash"],
        previous_hash=latest.get("previous_hash"),
        created_at=datetime.fromisoformat(latest["created_at"]),
        claim_ids=latest.get("claim_ids", []),
    )
    
    # Reconstruct claims from stored data
    claims = []
    for claim_data in latest.get("claims", []):
        claims.append(Claim(**claim_data))
    
    return version, claims


def get_version_claims(proposal_id: str, version_number: int) -> Optional[List[Claim]]:
    """
    Get claims for a specific version.
    
    Args:
        proposal_id: The proposal identifier
        version_number: Version number to retrieve
        
    Returns:
        List of Claims or None if not found
    """
    history_data = _load_proposal_file(proposal_id)
    if not history_data:
        return None
    
    for v in history_data.get("versions", []):
        if v["version_number"] == version_number:
            return [Claim(**c) for c in v.get("claims", [])]
    
    return None


# ============================================================================
# Claim Diffing
# ============================================================================

def compute_claim_diff(
    prev_claims: List[Claim],
    curr_claims: List[Claim],
    similarity_threshold: float = 0.7,
) -> ClaimDiff:
    """
    Compute diff between two versions of claims.
    
    Uses text-based matching first, then semantic similarity for modified claims.
    
    Args:
        prev_claims: Claims from previous version
        curr_claims: Claims from current version
        similarity_threshold: Below this, claim is considered "new" not "modified"
        
    Returns:
        ClaimDiff with categorized changes
    """
    prev_map = {c.id: c for c in prev_claims}
    curr_map = {c.id: c for c in curr_claims}
    
    prev_texts = {c.text: c for c in prev_claims}
    curr_texts = {c.text: c for c in curr_claims}
    
    unchanged = []
    modified = []
    new_claims = []
    removed = []
    
    # Track which previous claims have been matched
    matched_prev_ids = set()
    
    # First pass: exact text matching
    for curr_claim in curr_claims:
        if curr_claim.text in prev_texts:
            # Exact match = unchanged
            prev_match = prev_texts[curr_claim.text]
            unchanged.append(curr_claim.id)
            matched_prev_ids.add(prev_match.id)
        elif curr_claim.id in prev_map:
            # Same ID but different text = modified
            prev_claim = prev_map[curr_claim.id]
            similarity = _compute_text_similarity(prev_claim.text, curr_claim.text)
            
            # Compute numeric deltas
            numeric_delta = _compute_numeric_delta(prev_claim, curr_claim)
            
            modified.append(ClaimDiffItem(
                claim_id=curr_claim.id,
                status=ClaimStatus.MODIFIED,
                similarity_score=similarity,
                prev_claim_text=prev_claim.text,
                curr_claim_text=curr_claim.text,
                numeric_delta=numeric_delta,
            ))
            matched_prev_ids.add(prev_claim.id)
        else:
            # No ID match, try to find semantic match
            best_match = _find_best_semantic_match(curr_claim, prev_claims, matched_prev_ids)
            
            if best_match and best_match[1] >= similarity_threshold:
                # Found a semantic match
                prev_claim, similarity = best_match
                numeric_delta = _compute_numeric_delta(prev_claim, curr_claim)
                
                modified.append(ClaimDiffItem(
                    claim_id=curr_claim.id,
                    status=ClaimStatus.MODIFIED,
                    similarity_score=similarity,
                    prev_claim_text=prev_claim.text,
                    curr_claim_text=curr_claim.text,
                    numeric_delta=numeric_delta,
                ))
                matched_prev_ids.add(prev_claim.id)
            else:
                # Truly new claim
                new_claims.append(curr_claim.id)
    
    # Find removed claims
    for prev_claim in prev_claims:
        if prev_claim.id not in matched_prev_ids:
            removed.append(prev_claim.id)
    
    return ClaimDiff(
        unchanged=unchanged,
        modified=modified,
        new=new_claims,
        removed=removed,
    )


def _compute_text_similarity(text1: str, text2: str) -> float:
    """
    Compute similarity between two texts.
    
    Uses simple Jaccard similarity on words for now.
    Can be upgraded to use embeddings from Groq.
    """
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1 & words2
    union = words1 | words2
    
    return len(intersection) / len(union)


def _compute_numeric_delta(prev_claim: Claim, curr_claim: Claim) -> Optional[Dict[str, float]]:
    """Compute changes in numeric values between claims."""
    prev_nums = prev_claim.canonical.numbers if prev_claim.canonical else []
    curr_nums = curr_claim.canonical.numbers if curr_claim.canonical else []
    
    if not prev_nums and not curr_nums:
        return None
    
    delta = {}
    
    # Compare paired numbers
    for i, (p, c) in enumerate(zip(prev_nums, curr_nums)):
        if p != c:
            delta[f"num_{i}"] = c - p
    
    # Handle added/removed numbers
    if len(curr_nums) > len(prev_nums):
        for i in range(len(prev_nums), len(curr_nums)):
            delta[f"num_{i}_added"] = curr_nums[i]
    elif len(prev_nums) > len(curr_nums):
        for i in range(len(curr_nums), len(prev_nums)):
            delta[f"num_{i}_removed"] = prev_nums[i]
    
    return delta if delta else None


def _find_best_semantic_match(
    curr_claim: Claim,
    prev_claims: List[Claim],
    excluded_ids: set,
) -> Optional[Tuple[Claim, float]]:
    """Find the best semantic match for a claim."""
    best_match = None
    best_score = 0.0
    
    for prev_claim in prev_claims:
        if prev_claim.id in excluded_ids:
            continue
        
        score = _compute_text_similarity(prev_claim.text, curr_claim.text)
        if score > best_score:
            best_score = score
            best_match = prev_claim
    
    if best_match:
        return (best_match, best_score)
    return None


# ============================================================================
# Selective Revalidation
# ============================================================================

def get_claims_requiring_validation(
    claim_diff: ClaimDiff,
    curr_claims: List[Claim],
) -> List[Claim]:
    """
    Determine which claims need validation vs which can inherit results.
    
    Args:
        claim_diff: The computed diff
        curr_claims: All claims in current version
        
    Returns:
        List of claims that need to be validated
    """
    claims_to_validate = []
    curr_map = {c.id: c for c in curr_claims}
    
    # New claims need validation
    for claim_id in claim_diff.new:
        if claim_id in curr_map:
            claims_to_validate.append(curr_map[claim_id])
    
    # Modified claims need validation
    for diff_item in claim_diff.modified:
        if diff_item.claim_id in curr_map:
            claims_to_validate.append(curr_map[diff_item.claim_id])
    
    return claims_to_validate


def get_unchanged_claim_ids(claim_diff: ClaimDiff) -> List[str]:
    """Get IDs of claims that don't need revalidation."""
    return claim_diff.unchanged


# ============================================================================
# Risk Flags
# ============================================================================

def generate_mutation_flags(
    claim_diff: Optional[ClaimDiff],
    is_update: bool = False,
) -> List[str]:
    """
    Generate risk flags based on mutation patterns.
    
    Args:
        claim_diff: The computed diff (None for new proposals)
        is_update: Whether this is an update to existing proposal
        
    Returns:
        List of flag strings
    """
    if not claim_diff or not is_update:
        return []
    
    flags = []
    
    # Flag: New claims added
    if claim_diff.new:
        flags.append(f"⚠️ New claim(s) added after discussion: {', '.join(claim_diff.new)}")
    
    # Flag: Claims removed
    if claim_diff.removed:
        flags.append(f"⚠️ Previously validated claim(s) removed: {', '.join(claim_diff.removed)}")
    
    # Flag: Modified claims with significant changes
    for mod in claim_diff.modified:
        if mod.similarity_score and mod.similarity_score < 0.5:
            flags.append(f"⚠️ Claim {mod.claim_id} substantially modified (similarity: {mod.similarity_score:.2f})")
        
        # Check for numeric increases
        if mod.numeric_delta:
            for key, delta in mod.numeric_delta.items():
                if "removed" not in key and delta > 0:
                    flags.append(f"⚠️ Numeric parameter increased in claim {mod.claim_id}: +{delta}")
    
    return flags
