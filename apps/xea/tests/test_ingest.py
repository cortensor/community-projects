"""
Xea Governance Oracle - Ingest Tests

Unit tests for proposal ingestion functionality.
"""

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
import tempfile
import os

# Sample proposal for testing
SAMPLE_PROPOSAL = """
# Proposal: Treasury Allocation for Developer Grants

## Summary

This proposal requests 50,000 USDC from the DAO treasury to fund developer grants for Q1 2025.

## Background

The DAO treasury currently holds approximately 500,000 USDC. This allocation represents 10% of total treasury funds. The treasury address is 0x742d35Cc6634C0532925a3b844Bc9e7595f5bC12.

## Specification

### Grant Distribution
- Smart Contract Development: 20,000 USDC
- Frontend Development: 15,000 USDC
- Documentation and Tutorials: 10,000 USDC
- Security Audits: 5,000 USDC

### Timeline
- Grant applications open: January 15, 2025
- Application deadline: February 15, 2025
- Grant disbursement: March 1, 2025

### Oversight
A 3-of-5 multisig will manage grant disbursements.

## Rationale

Developer grants have historically provided 3x ROI in terms of protocol value added.
The previous grant program funded 12 projects, 8 of which are now live on mainnet.
More details at https://dao.example.org/grants
"""


class TestCanonicalization:
    """Test text canonicalization."""

    def test_strips_html_tags(self):
        """Canonicalization should strip HTML tags."""
        from app.ingest import canonicalize_text
        
        text = "<p>Hello <strong>World</strong></p>"
        canonical = canonicalize_text(text)
        
        assert "<" not in canonical
        assert ">" not in canonical
        assert "Hello" in canonical
        assert "World" in canonical

    def test_strips_markdown_comments(self):
        """Canonicalization should strip markdown comments."""
        from app.ingest import canonicalize_text
        
        text = "Before <!-- hidden comment --> After"
        canonical = canonicalize_text(text)
        
        assert "hidden comment" not in canonical
        assert "Before" in canonical
        assert "After" in canonical

    def test_strips_trailing_whitespace(self):
        """Canonicalization should strip trailing whitespace."""
        from app.ingest import canonicalize_text
        
        text = "Line 1   \nLine 2  \n\n"
        canonical = canonicalize_text(text)
        
        # Lines should not end with spaces
        for line in canonical.split('\n'):
            assert not line.endswith(' ')

    def test_removes_diff_markers(self):
        """Canonicalization should remove diff markers."""
        from app.ingest import canonicalize_text
        
        text = "+++ added\n--- removed\n@@ -1,2 +1,2 @@\n+new line\n-old line"
        canonical = canonicalize_text(text)
        
        assert "+++" not in canonical
        assert "---" not in canonical
        assert "@@" not in canonical


class TestHashStability:
    """Test that hashing is deterministic."""

    def test_same_text_produces_same_hash(self):
        """Same text input should produce identical hash."""
        from app.ingest import compute_proposal_hash, canonicalize_text
        
        text1 = canonicalize_text(SAMPLE_PROPOSAL)
        text2 = canonicalize_text(SAMPLE_PROPOSAL)
        
        hash1 = compute_proposal_hash(text1)
        hash2 = compute_proposal_hash(text2)
        
        assert hash1 == hash2
        assert hash1.startswith("sha256:")
        assert len(hash1) == 71  # "sha256:" + 64 hex chars

    def test_hash_includes_uri(self):
        """Hash should incorporate URI when provided."""
        from app.ingest import compute_proposal_hash
        
        text = "test proposal"
        hash_without_uri = compute_proposal_hash(text, None)
        hash_with_uri = compute_proposal_hash(text, "https://example.com/proposal/1")
        
        assert hash_without_uri != hash_with_uri

    def test_hash_format(self):
        """Hash should have correct format."""
        from app.ingest import compute_proposal_hash, canonicalize_text
        
        canonical = canonicalize_text(SAMPLE_PROPOSAL)
        hash_value = compute_proposal_hash(canonical)
        
        assert hash_value.startswith("sha256:")
        hex_part = hash_value[7:]
        assert len(hex_part) == 64
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_different_text_produces_different_hash(self):
        """Different text should produce different hash."""
        from app.ingest import compute_proposal_hash, canonicalize_text
        
        hash1 = compute_proposal_hash(canonicalize_text("Proposal A"))
        hash2 = compute_proposal_hash(canonicalize_text("Proposal B"))
        
        assert hash1 != hash2


class TestClaimExtraction:
    """Test claim extraction logic."""

    def test_extracts_claims_from_proposal(self):
        """Should extract claims from a typical proposal."""
        from app.ingest import extract_claims_llm, canonicalize_text
        
        canonical = canonicalize_text(SAMPLE_PROPOSAL)
        claims = extract_claims_llm(canonical)
        
        # Should extract between 5 and 12 claims for this proposal
        assert 5 <= len(claims) <= 12

    def test_claims_have_correct_id_format(self):
        """Claims should have IDs in c1, c2, ... format."""
        from app.ingest import extract_claims_llm, canonicalize_text
        
        canonical = canonicalize_text(SAMPLE_PROPOSAL)
        claims = extract_claims_llm(canonical)
        
        for i, claim in enumerate(claims, 1):
            assert claim.id == f"c{i}"

    def test_claims_have_required_fields(self):
        """Each claim should have all required fields."""
        from app.ingest import extract_claims_llm, canonicalize_text
        
        canonical = canonicalize_text(SAMPLE_PROPOSAL)
        claims = extract_claims_llm(canonical)
        
        for claim in claims:
            assert hasattr(claim, 'id')
            assert hasattr(claim, 'text')
            assert hasattr(claim, 'paragraph_index')
            assert hasattr(claim, 'char_range')
            assert hasattr(claim, 'type')
            assert hasattr(claim, 'canonical')
            
            # Validate types
            assert isinstance(claim.id, str)
            assert isinstance(claim.text, str)
            assert isinstance(claim.paragraph_index, int)
            assert len(claim.char_range) == 2
            assert claim.type in ["factual", "numeric", "normative"]

    def test_numeric_claims_have_canonical_numbers(self):
        """Numeric claims should have canonicalized numbers."""
        from app.ingest import extract_claims_llm, canonicalize_text
        
        canonical = canonicalize_text(SAMPLE_PROPOSAL)
        claims = extract_claims_llm(canonical)
        
        numeric_claims = [c for c in claims if c.type == "numeric"]
        
        # Should have at least some numeric claims
        assert len(numeric_claims) > 0
        
        # Each numeric claim should have numbers
        for claim in numeric_claims:
            assert len(claim.canonical.numbers) > 0

    def test_extracts_eth_addresses(self):
        """Should extract Ethereum addresses."""
        from app.ingest import extract_claims_llm, canonicalize_text
        
        canonical = canonicalize_text(SAMPLE_PROPOSAL)
        claims = extract_claims_llm(canonical)
        
        # Find claims with addresses
        claims_with_addresses = [
            c for c in claims 
            if len(c.canonical.addresses) > 0
        ]
        
        # Should find the treasury address
        assert len(claims_with_addresses) > 0
        
        # Address should be lowercased
        for claim in claims_with_addresses:
            for addr in claim.canonical.addresses:
                assert addr == addr.lower()

    def test_extracts_urls(self):
        """Should extract URLs."""
        from app.ingest import extract_claims_llm, canonicalize_text
        
        canonical = canonicalize_text(SAMPLE_PROPOSAL)
        claims = extract_claims_llm(canonical)
        
        # Find claims with URLs
        claims_with_urls = [
            c for c in claims 
            if len(c.canonical.urls) > 0
        ]
        
        # Should find the URL in the proposal
        assert len(claims_with_urls) > 0


class TestNumberCanonicalization:
    """Test number canonicalization utilities."""

    def test_percentage_to_decimal(self):
        """10% should become 0.10."""
        from app.utils import canonicalize_number
        
        numbers = canonicalize_number("unlock 10% of treasury")
        assert 0.10 in numbers

    def test_percent_word(self):
        """10 percent should become 0.10."""
        from app.utils import canonicalize_number
        
        numbers = canonicalize_number("allocate 10 percent")
        assert 0.10 in numbers

    def test_comma_separated_numbers(self):
        """1,000,000 should become 1000000."""
        from app.utils import canonicalize_number
        
        numbers = canonicalize_number("total of 1,000,000 tokens")
        assert 1000000.0 in numbers

    def test_million_multiplier(self):
        """1.5 million should become 1500000."""
        from app.utils import canonicalize_number
        
        numbers = canonicalize_number("worth 1.5 million dollars")
        assert 1500000.0 in numbers


class TestAddressCanonicalization:
    """Test Ethereum address canonicalization."""

    def test_lowercases_address(self):
        """Addresses should be lowercased."""
        from app.utils import canonicalize_eth_address
        
        text = "Send to 0xABCdef1234567890ABCdef1234567890ABCdef12"
        addresses = canonicalize_eth_address(text)
        
        assert len(addresses) == 1
        assert addresses[0] == "0xabcdef1234567890abcdef1234567890abcdef12"

    def test_extracts_multiple_addresses(self):
        """Should extract multiple addresses."""
        from app.utils import canonicalize_eth_address
        
        text = "From 0x1234567890123456789012345678901234567890 to 0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
        addresses = canonicalize_eth_address(text)
        
        assert len(addresses) == 2


class TestURLCanonicalization:
    """Test URL canonicalization."""

    def test_normalizes_url(self):
        """URLs should be normalized."""
        from app.utils import canonicalize_url
        
        text = "Visit HTTPS://EXAMPLE.COM/Path/"
        urls = canonicalize_url(text)
        
        assert len(urls) == 1
        # Should have lowercase scheme and host, no trailing slash
        assert urls[0] == "https://example.com/Path"


class TestIngestEndpoint:
    """Test the /ingest API endpoint."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create a temporary data directory."""
        data_dir = tmp_path / "claims"
        data_dir.mkdir()
        return data_dir

    @pytest.mark.asyncio
    async def test_ingest_with_text(self, temp_data_dir):
        """Ingest should work with raw text."""
        from app.ingest import process_ingest, get_data_dir
        from app.schemas import IngestRequest
        
        # Patch the data directory
        with patch('app.ingest.get_data_dir', return_value=temp_data_dir):
            request = IngestRequest(text=SAMPLE_PROPOSAL)
            response = await process_ingest(request)
        
        assert response.proposal_hash.startswith("sha256:")
        assert len(response.claims) >= 5
        assert len(response.canonical_text) > 0

    @pytest.mark.asyncio
    async def test_ingest_deterministic_hash(self, temp_data_dir):
        """Same input should produce same hash."""
        from app.ingest import process_ingest
        from app.schemas import IngestRequest
        
        with patch('app.ingest.get_data_dir', return_value=temp_data_dir):
            request1 = IngestRequest(text=SAMPLE_PROPOSAL)
            request2 = IngestRequest(text=SAMPLE_PROPOSAL)
            
            response1 = await process_ingest(request1)
            response2 = await process_ingest(request2)
        
        assert response1.proposal_hash == response2.proposal_hash

    @pytest.mark.asyncio
    async def test_ingest_persists_claims(self, temp_data_dir):
        """Ingest should persist claims to disk."""
        from app.ingest import process_ingest, load_claims
        from app.schemas import IngestRequest
        
        with patch('app.ingest.get_data_dir', return_value=temp_data_dir):
            request = IngestRequest(text=SAMPLE_PROPOSAL)
            response = await process_ingest(request)
            
            # Load claims from disk
            loaded = load_claims(response.proposal_hash)
        
        assert loaded is not None
        assert loaded["proposal_hash"] == response.proposal_hash
        assert len(loaded["claims"]) == len(response.claims)

    @pytest.mark.asyncio
    async def test_ingest_with_url_mock(self, temp_data_dir):
        """Ingest should work with URL (mocked fetch)."""
        from app.ingest import process_ingest
        from app.schemas import IngestRequest
        
        with patch('app.ingest.get_data_dir', return_value=temp_data_dir):
            with patch('app.ingest.fetch_proposal_from_url', new_callable=AsyncMock) as mock_fetch:
                mock_fetch.return_value = SAMPLE_PROPOSAL
                
                request = IngestRequest(url="https://snapshot.org/example/proposal/1")
                response = await process_ingest(request)
        
        assert response.proposal_hash.startswith("sha256:")
        assert len(response.claims) >= 5
        mock_fetch.assert_called_once()


class TestClaimPersistence:
    """Test claim persistence functionality."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create a temporary data directory."""
        data_dir = tmp_path / "claims"
        data_dir.mkdir()
        return data_dir

    def test_persist_and_load_claims(self, temp_data_dir):
        """Should persist and load claims correctly."""
        from app.ingest import persist_claims, load_claims
        from app.schemas import Claim, ClaimCanonical
        
        with patch('app.ingest.get_data_dir', return_value=temp_data_dir):
            proposal_hash = "sha256:abc123"
            canonical_text = "Test proposal"
            claims = [
                Claim(
                    id="c1",
                    text="Test claim",
                    paragraph_index=0,
                    char_range=[0, 10],
                    type="factual",
                    canonical=ClaimCanonical(numbers=[], addresses=[], urls=[])
                )
            ]
            
            persist_claims(proposal_hash, claims, canonical_text)
            loaded = load_claims(proposal_hash)
        
        assert loaded is not None
        assert loaded["proposal_hash"] == proposal_hash
        assert len(loaded["claims"]) == 1
        assert loaded["claims"][0]["id"] == "c1"
