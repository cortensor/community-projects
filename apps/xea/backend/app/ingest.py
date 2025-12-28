"""
Xea Governance Oracle - Ingest Module

Handles proposal ingestion from URLs and raw text.
"""

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Optional, List

import httpx

from app.schemas import Claim, ClaimCanonical, IngestRequest, IngestResponse
from app.utils import (
    extract_paragraphs,
    mock_extract_claims,
    call_llm,
    CLAIM_EXTRACTION_PROMPT,
    canonicalize_number,
    canonicalize_eth_address,
    canonicalize_url,
)


# Data directory for persisting claims
DATA_DIR = Path("/data/claims")
# Fallback for local development
LOCAL_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "claims"


def get_data_dir() -> Path:
    """Get the data directory, creating if needed."""
    if DATA_DIR.exists() or os.access(DATA_DIR.parent, os.W_OK):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return DATA_DIR
    else:
        LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
        return LOCAL_DATA_DIR


def canonicalize_text(raw_text: str) -> str:
    """
    Canonicalize proposal text for consistent hashing and processing.
    
    Operations:
    - Normalize whitespace
    - Strip HTML tags
    - Strip markdown comments
    - Remove quoted signatures
    - Remove diff markers
    - Extract main proposal body from Snapshot format
    
    Args:
        raw_text: Raw proposal text
        
    Returns:
        Canonicalized text string
    """
    text = raw_text
    
    # Strip HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Strip markdown comments <!-- ... -->
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    
    # Remove quoted signatures (lines starting with >)
    lines = text.split('\n')
    filtered_lines = []
    in_signature_block = False
    
    for line in lines:
        # Detect signature blocks
        if re.match(r'^>\s*-{2,}', line) or re.match(r'^>\s*Sent from', line, re.IGNORECASE):
            in_signature_block = True
            continue
        
        # Skip lines in signature block that start with >
        if in_signature_block and line.startswith('>'):
            continue
        else:
            in_signature_block = False
        
        # Remove inline quote markers but keep content
        if line.startswith('> '):
            line = line[2:]
        
        filtered_lines.append(line)
    
    text = '\n'.join(filtered_lines)
    
    # Remove diff markers (+, -, @@)
    text = re.sub(r'^[+\-]{3}\s+.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^@@.*@@$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[+\-](?=[^\s+\-])', '', text, flags=re.MULTILINE)
    
    # Extract Snapshot proposal body markers
    # Common patterns: "## Abstract", "## Motivation", "## Specification"
    # If we detect these, we're in a structured proposal
    snapshot_markers = [
        r'#{1,3}\s*Abstract',
        r'#{1,3}\s*Summary',
        r'#{1,3}\s*Motivation',
        r'#{1,3}\s*Specification',
        r'#{1,3}\s*Proposal',
    ]
    
    has_snapshot_format = any(
        re.search(marker, text, re.IGNORECASE) 
        for marker in snapshot_markers
    )
    
    if has_snapshot_format:
        # Remove frontmatter if present (YAML between ---)
        text = re.sub(r'^---\n.*?\n---\n', '', text, flags=re.DOTALL)
    
    # Normalize whitespace
    # - Convert tabs to spaces
    text = text.replace('\t', '    ')
    
    # - Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # - Strip trailing whitespace from each line
    lines = [line.rstrip() for line in text.split('\n')]
    
    # - Collapse multiple blank lines into one
    result_lines = []
    prev_blank = False
    for line in lines:
        is_blank = not line.strip()
        if is_blank and prev_blank:
            continue
        result_lines.append(line)
        prev_blank = is_blank
    
    # - Strip leading/trailing blank lines
    text = '\n'.join(result_lines).strip()
    
    return text


def compute_proposal_hash(canonical_text: str, proposal_uri: Optional[str] = None) -> str:
    """
    Compute deterministic SHA-256 hash of canonical text with URI.
    
    Format: sha256(proposal_uri + '|' + canonical_text)
    
    Args:
        canonical_text: Canonicalized proposal text
        proposal_uri: Optional proposal URL/URI
        
    Returns:
        Hash string in format "sha256:<hex>"
    """
    uri = proposal_uri or ""
    hash_input = f"{uri}|{canonical_text}"
    hash_bytes = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
    return f"sha256:{hash_bytes}"


async def fetch_proposal_from_url(url: str) -> str:
    """
    Fetch proposal content from URL.
    
    Supports:
    - Snapshot.org proposals
    - Tally proposals
    - Raw markdown/text URLs
    
    Args:
        url: Proposal URL
        
    Returns:
        Raw proposal text
        
    Raises:
        ValueError: If URL is unsupported or fetch fails
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '')
            
            # If it's HTML, try to extract text content
            if 'text/html' in content_type:
                # For Snapshot URLs, try to extract proposal content
                if 'snapshot.org' in url or 'snapshot.page' in url:
                    # Snapshot uses client-side rendering, so direct fetch won't work well
                    # Return the raw HTML for now - in production, use their API
                    return response.text
                else:
                    # Basic HTML text extraction
                    text = re.sub(r'<script[^>]*>.*?</script>', '', response.text, flags=re.DOTALL)
                    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
                    text = re.sub(r'<[^>]+>', ' ', text)
                    text = re.sub(r'\s+', ' ', text)
                    return text.strip()
            else:
                # Assume plain text or markdown
                return response.text
                
        except httpx.HTTPError as e:
            raise ValueError(f"Failed to fetch URL: {e}")


def extract_claims_llm(canonical_text: str) -> List[Claim]:
    """
    Extract atomic claims from proposal text using LLM or mock extractor.
    
    Args:
        canonical_text: Canonicalized proposal text
        
    Returns:
        List of Claim objects
    """
    # Build the full prompt
    full_prompt = f"{CLAIM_EXTRACTION_PROMPT}\n\n---\nPROPOSAL TEXT:\n{canonical_text}\n---"
    
    # Try LLM call first
    try:
        llm_response = call_llm(full_prompt)
        if llm_response and llm_response.strip() != "[]":
            # Parse LLM response
            parsed = json.loads(llm_response)
            
            # Handle different response formats:
            # 1. Direct array: [{"id": "c1", ...}, ...]
            # 2. Wrapped in object: {"claims": [{"id": "c1", ...}, ...]}
            if isinstance(parsed, list):
                claims_data = parsed
            elif isinstance(parsed, dict):
                # Try common keys that LLMs might use
                claims_data = parsed.get("claims") or parsed.get("extracted_claims") or parsed.get("data") or []
                if not claims_data and len(parsed) == 1:
                    # If only one key, use its value if it's a list
                    first_val = list(parsed.values())[0]
                    if isinstance(first_val, list):
                        claims_data = first_val
            else:
                claims_data = []
            
            if claims_data:
                claims = []
                for claim_dict in claims_data:
                    canonical = ClaimCanonical(
                        numbers=claim_dict.get("canonical", {}).get("numbers", []),
                        addresses=claim_dict.get("canonical", {}).get("addresses", []),
                        urls=claim_dict.get("canonical", {}).get("urls", []),
                    )
                    claims.append(Claim(
                        id=claim_dict["id"],
                        text=claim_dict["text"],
                        paragraph_index=claim_dict["paragraph_index"],
                        char_range=claim_dict["char_range"],
                        type=claim_dict["type"],
                        canonical=canonical,
                    ))
                return claims
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    
    # Fallback to mock extractor
    claims_data = mock_extract_claims(canonical_text)
    claims = []
    
    for claim_dict in claims_data:
        canonical = ClaimCanonical(
            numbers=claim_dict.get("canonical", {}).get("numbers", []),
            addresses=claim_dict.get("canonical", {}).get("addresses", []),
            urls=claim_dict.get("canonical", {}).get("urls", []),
        )
        claims.append(Claim(
            id=claim_dict["id"],
            text=claim_dict["text"],
            paragraph_index=claim_dict["paragraph_index"],
            char_range=claim_dict["char_range"],
            type=claim_dict["type"],
            canonical=canonical,
        ))
    
    return claims


def persist_claims(proposal_hash: str, claims: List[Claim], canonical_text: str) -> Path:
    """
    Persist claims to JSON file.
    
    Args:
        proposal_hash: The proposal hash (used as filename)
        claims: List of claims to persist
        canonical_text: The canonical text
        
    Returns:
        Path to the saved file
    """
    data_dir = get_data_dir()
    
    # Use hash without prefix for filename
    hash_value = proposal_hash.replace("sha256:", "")
    file_path = data_dir / f"{hash_value}.json"
    
    data = {
        "proposal_hash": proposal_hash,
        "canonical_text": canonical_text,
        "claims": [claim.model_dump() for claim in claims],
    }
    
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
    
    return file_path


def load_claims(proposal_hash: str) -> Optional[dict]:
    """
    Load claims from JSON file.
    
    Args:
        proposal_hash: The proposal hash
        
    Returns:
        Dictionary with claims data or None if not found
    """
    data_dir = get_data_dir()
    hash_value = proposal_hash.replace("sha256:", "")
    file_path = data_dir / f"{hash_value}.json"
    
    if not file_path.exists():
        return None
    
    with open(file_path, "r") as f:
        return json.load(f)


async def process_ingest(request: IngestRequest) -> IngestResponse:
    """
    Process an ingest request.
    
    Args:
        request: IngestRequest with url or text, optionally previous_proposal_id
        
    Returns:
        IngestResponse with hash, canonical text, claims, and versioning info
    """
    from app.versioning import (
        create_proposal_version,
        get_latest_version,
        compute_claim_diff,
        generate_proposal_id,
    )
    
    # Get raw text from URL or direct input
    if request.url:
        raw_text = await fetch_proposal_from_url(request.url)
        proposal_uri = request.url
    else:
        raw_text = request.text or ""
        proposal_uri = None
    
    # Canonicalize
    canonical_text = canonicalize_text(raw_text)
    
    # Compute hash
    proposal_hash = compute_proposal_hash(canonical_text, proposal_uri)
    
    # Extract claims
    claims = extract_claims_llm(canonical_text)
    
    # Persist to disk (legacy)
    persist_claims(proposal_hash, claims, canonical_text)
    
    # Versioning logic
    claim_diff = None
    previous_hash = None
    
    if request.previous_proposal_id:
        # Updating existing proposal
        prev_result = get_latest_version(request.previous_proposal_id)
        
        if prev_result:
            prev_version, prev_claims = prev_result
            previous_hash = prev_version.proposal_hash
            
            # Compute diff between versions
            claim_diff = compute_claim_diff(prev_claims, claims)
            
            # Create new version
            version = create_proposal_version(
                proposal_id=request.previous_proposal_id,
                proposal_hash=proposal_hash,
                claims=claims,
                canonical_text=canonical_text,
                previous_hash=previous_hash,
            )
            proposal_id = version.proposal_id
            version_number = version.version_number
        else:
            # Previous not found, treat as new proposal
            version = create_proposal_version(
                proposal_id=request.previous_proposal_id,  # Use provided ID
                proposal_hash=proposal_hash,
                claims=claims,
                canonical_text=canonical_text,
            )
            proposal_id = version.proposal_id
            version_number = version.version_number
    else:
        # New proposal
        version = create_proposal_version(
            proposal_id=None,  # Generate new ID
            proposal_hash=proposal_hash,
            claims=claims,
            canonical_text=canonical_text,
        )
        proposal_id = version.proposal_id
        version_number = version.version_number
    
    return IngestResponse(
        proposal_id=proposal_id,
        version_number=version_number,
        proposal_hash=proposal_hash,
        previous_hash=previous_hash,
        canonical_text=canonical_text,
        claims=claims,
        claim_diff=claim_diff,
    )
