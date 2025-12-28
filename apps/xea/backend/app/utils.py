"""
Xea Governance Oracle - Utility Functions

Common utilities used across the application.
"""

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Optional, List
from urllib.parse import urlparse, urlunparse

import httpx
import logging
from app.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# ID Generation
# ============================================================================

def generate_job_id() -> str:
    """Generate a unique job ID."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    import secrets
    suffix = secrets.token_hex(4)
    return f"job_{timestamp}_{suffix}"


def generate_claim_id(index: int) -> str:
    """Generate a claim ID for a given index (1-based for user-friendly display)."""
    return f"c{index}"


# ============================================================================
# Hashing
# ============================================================================

def sha256_hash(data: str) -> str:
    """Compute SHA-256 hash of string data."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def json_serialize(obj: Any) -> str:
    """Serialize object to canonical JSON string."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


# ============================================================================
# Text Utilities
# ============================================================================

def extract_paragraphs(text: str) -> List[str]:
    """Split text into paragraphs."""
    paragraphs = re.split(r"\n\s*\n", text.strip())
    return [p.strip() for p in paragraphs if p.strip()]


def find_char_range(text: str, substring: str) -> Optional[tuple[int, int]]:
    """Find character range of substring in text."""
    start = text.find(substring)
    if start == -1:
        return None
    return (start, start + len(substring))


def clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Clamp a value to a range."""
    return max(min_val, min(max_val, value))


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """Format datetime to ISO string."""
    if dt is None:
        dt = datetime.utcnow()
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ============================================================================
# Number Canonicalization
# ============================================================================

def canonicalize_number(text: str) -> List[float]:
    """
    Extract and normalize numeric values from text.
    
    Examples:
    - "10%" -> [0.10]
    - "10 percent" -> [0.10]
    - "1,000,000" -> [1000000.0]
    - "1.5 million" -> [1500000.0]
    - "$50,000 USDC" -> [50000.0]
    """
    numbers = []
    
    # Pattern for percentages: 10%, 10 percent, 10pct
    percent_patterns = [
        r'(\d+(?:\.\d+)?)\s*%',
        r'(\d+(?:\.\d+)?)\s*percent',
        r'(\d+(?:\.\d+)?)\s*pct',
    ]
    
    for pattern in percent_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                value = float(match) / 100.0
                if value not in numbers:
                    numbers.append(round(value, 4))
            except ValueError:
                pass
    
    # Pattern for currency/plain numbers: $50,000, 1,000,000, 50000
    # Match numbers with optional commas and decimal points
    number_pattern = r'(?<![.\d])(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)(?![.\d])'
    matches = re.findall(number_pattern, text)
    
    for match in matches:
        try:
            # Remove commas
            clean = match.replace(',', '')
            value = float(clean)
            # Skip if already added as percentage
            if value / 100.0 not in numbers and value not in numbers:
                numbers.append(value)
        except ValueError:
            pass
    
    # Handle "X million", "X billion", etc.
    multiplier_patterns = [
        (r'(\d+(?:\.\d+)?)\s*million', 1_000_000),
        (r'(\d+(?:\.\d+)?)\s*billion', 1_000_000_000),
        (r'(\d+(?:\.\d+)?)\s*thousand', 1_000),
        (r'(\d+(?:\.\d+)?)\s*k\b', 1_000),
        (r'(\d+(?:\.\d+)?)\s*m\b', 1_000_000),
        (r'(\d+(?:\.\d+)?)\s*b\b', 1_000_000_000),
    ]
    
    for pattern, multiplier in multiplier_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                value = float(match) * multiplier
                if value not in numbers:
                    numbers.append(value)
            except ValueError:
                pass
    
    return numbers


# ============================================================================
# Address Canonicalization
# ============================================================================

def canonicalize_eth_address(text: str) -> List[str]:
    """
    Extract and normalize Ethereum addresses from text.
    Returns lowercased addresses.
    
    Example:
    - "0xABC123...def" -> ["0xabc123...def"]
    """
    # Ethereum address pattern: 0x followed by 40 hex characters
    pattern = r'0x[a-fA-F0-9]{40}'
    matches = re.findall(pattern, text)
    
    # Normalize to lowercase and deduplicate
    normalized = list(set(addr.lower() for addr in matches))
    return normalized


# ============================================================================
# URL Canonicalization
# ============================================================================

def canonicalize_url(text: str) -> List[str]:
    """
    Extract and normalize URLs from text.
    
    Normalization:
    - Lowercase scheme and host
    - Remove trailing slashes
    - Remove default ports
    - Sort query parameters
    """
    # URL pattern - case insensitive for scheme
    url_pattern = r'[hH][tT][tT][pP][sS]?://[^\s<>"{}|\\^`\[\]]+'
    matches = re.findall(url_pattern, text)
    
    normalized = []
    for url in matches:
        try:
            parsed = urlparse(url.rstrip('/.,;:!?)'))
            
            # Lowercase scheme and netloc
            scheme = parsed.scheme.lower()
            netloc = parsed.netloc.lower()
            
            # Remove default ports
            if netloc.endswith(':80') and scheme == 'http':
                netloc = netloc[:-3]
            elif netloc.endswith(':443') and scheme == 'https':
                netloc = netloc[:-4]
            
            # Reconstruct URL
            normalized_url = urlunparse((
                scheme,
                netloc,
                parsed.path.rstrip('/') or '/',
                parsed.params,
                parsed.query,
                ''  # Remove fragment
            ))
            
            if normalized_url not in normalized:
                normalized.append(normalized_url)
        except Exception:
            # If parsing fails, include original
            if url not in normalized:
                normalized.append(url)
    
    return normalized


# ============================================================================
# LLM Helper
# ============================================================================

# The exact prompt for claim extraction as specified
CLAIM_EXTRACTION_PROMPT = '''You are a governance claim extractor. Given the canonical proposal text below, extract **only atomic factual and numeric claims** (exclude purely normative sentences). For each claim, produce a JSON entry with these fields:

{
  "id": "c{n}",
  "text": "<exact claim text, trimmed>",
  "paragraph_index": <0-based int>,
  "char_range": [ <start_char_index>, <end_char_index> ],
  "type": "factual" | "numeric",
  "canonical": { "numbers": [<float>], "addresses": [<eth_address>], "urls": [<url>] }
}

Rules:
- Split compound sentences into multiple claims when they assert distinct facts.
- If a sentence contains both a factual statement and a numeric parameter (e.g., "unlock 10% of treasury"), create a single claim with type "numeric" and canonical.numbers = [0.10].
- Do NOT produce commentary or extra text. Output must be a pure JSON array.'''


def call_llm(prompt: str) -> str:
    """
    Call Groq LLM with the given prompt.
    
    Uses Groq's fast inference API with llama-3.3-70b-versatile model.
    Falls back to deterministic extraction (returns "[]") if:
    - No API key is configured
    - API call fails
    - API returns error
    
    Args:
        prompt: The full prompt to send to the LLM
        
    Returns:
        LLM response string (JSON), or "[]" to trigger fallback.
    """
    if not settings.groq_api_key:
        logger.info("Groq API key not configured. Using deterministic fallback.")
        return "[]"
    
    api_url = "https://api.groq.com/openai/v1/chat/completions"
    
    # Groq uses OpenAI-compatible chat completions format
    payload = {
        "model": settings.groq_model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.2,
        "max_tokens": 2048,
        "response_format": {"type": "json_object"}
    }
    
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Extract content from OpenAI-compatible response structure
            # { "choices": [ { "message": { "content": "..." } } ] }
            if "choices" in data and data["choices"]:
                choice = data["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"]
            
            logger.warning("Groq response missing expected content structure.")
            return "[]"
            
    except httpx.RequestError as e:
        logger.error(f"Groq network error: {e}")
        return "[]"
    except httpx.HTTPStatusError as e:
        logger.error(f"Groq API error data: {e.response.text}")
        logger.error(f"Groq HTTP error: {e}")
        return "[]"
    except Exception as e:
        logger.exception(f"Unexpected error calling Groq: {e}")
        return "[]"


def mock_extract_claims(canonical_text: str) -> List[dict]:
    """
    Rule-based mock claim extractor for local development.
    
    This provides deterministic extraction without requiring an LLM.
    It uses heuristics to identify factual and numeric claims.
    
    Args:
        canonical_text: Canonicalized proposal text
        
    Returns:
        List of claim dictionaries matching the schema
    """
    claims = []
    paragraphs = extract_paragraphs(canonical_text)
    claim_index = 1
    current_char = 0
    
    for para_idx, paragraph in enumerate(paragraphs):
        # Split paragraph into sentences
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        
        para_start = canonical_text.find(paragraph, current_char)
        if para_start == -1:
            para_start = current_char
        
        sentence_offset = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:
                continue
            
            # Skip normative sentences (should, must, recommend, propose to)
            normative_patterns = [
                r'\bshould\b', r'\bmust\b', r'\brecommend\b',
                r'\bpropose to\b', r'\bwe believe\b', r'\bwe suggest\b',
                r'\blet\'s\b', r'\bplease\b'
            ]
            
            is_normative = any(
                re.search(p, sentence, re.IGNORECASE) 
                for p in normative_patterns
            )
            
            if is_normative:
                sentence_offset += len(sentence) + 1
                continue
            
            # Check for numeric content
            numbers = canonicalize_number(sentence)
            addresses = canonicalize_eth_address(sentence)
            urls = canonicalize_url(sentence)
            
            # Determine claim type
            if numbers:
                claim_type = "numeric"
            else:
                claim_type = "factual"
            
            # Calculate char range
            sent_start = para_start + sentence_offset
            sent_end = sent_start + len(sentence)
            
            # Only include sentences that look like claims (contain facts/data)
            factual_indicators = [
                r'\d+',  # Contains numbers
                r'\bcurrently\b', r'\bwill\b', r'\bhas\b', r'\bhave\b',
                r'\bis\b', r'\bare\b', r'\bwas\b', r'\bwere\b',
                r'\bholds\b', r'\bcontains\b', r'\ballocate\b',
                r'\bfund\b', r'\btreasury\b', r'\btoken\b',
                r'\bvote\b', r'\bquorum\b', r'\bdeadline\b',
                r'0x[a-fA-F0-9]+',  # ETH addresses
                r'https?://',  # URLs
            ]
            
            has_factual_content = any(
                re.search(p, sentence, re.IGNORECASE)
                for p in factual_indicators
            )
            
            if has_factual_content:
                claims.append({
                    "id": f"c{claim_index}",
                    "text": sentence,
                    "paragraph_index": para_idx,
                    "char_range": [sent_start, sent_end],
                    "type": claim_type,
                    "canonical": {
                        "numbers": numbers,
                        "addresses": addresses,
                        "urls": urls
                    }
                })
                claim_index += 1
            
            sentence_offset += len(sentence) + 1
        
        current_char = para_start + len(paragraph) + 2  # Account for paragraph break
    
    return claims
