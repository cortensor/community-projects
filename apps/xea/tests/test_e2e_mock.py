"""
Xea Governance Oracle - End-to-End Mock Tests

Full pipeline tests using mock miners.
"""

import asyncio
import json
import pytest
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import tempfile

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
- Documentation: 10,000 USDC
- Security Audits: 5,000 USDC

### Timeline
- Grant applications open: January 15, 2025
- Application deadline: February 15, 2025

### Oversight
A 3-of-5 multisig will manage disbursements.

## Rationale

Developer grants have historically provided 3x ROI. The previous grant program funded 12 projects.
More details at https://dao.example.org/grants
"""


class TestMockMinerClient:
    """Test MockMinerClient behavior."""

    def test_creates_deterministic_embedding(self):
        """MockMiner should create deterministic embeddings."""
        from app.miner_client import MockMinerClient
        
        miner1 = MockMinerClient(miner_id="test", seed=42)
        miner2 = MockMinerClient(miner_id="test", seed=42)
        
        emb1 = miner1._compute_deterministic_embedding("test text")
        emb2 = miner2._compute_deterministic_embedding("test text")
        
        assert emb1 == emb2
        assert len(emb1) == 64

    def test_different_text_different_embedding(self):
        """Different text should produce different embeddings."""
        from app.miner_client import MockMinerClient
        
        miner = MockMinerClient(seed=42)
        
        emb1 = miner._compute_deterministic_embedding("text one")
        emb2 = miner._compute_deterministic_embedding("text two")
        
        assert emb1 != emb2

    def test_numeric_claims_bias_supported(self):
        """Claims with canonical numbers should bias toward 'supported'."""
        from app.miner_client import MockMinerClient
        from app.schemas import Claim, ClaimCanonical
        
        miner = MockMinerClient(seed=42)
        
        claim = Claim(
            id="c1",
            text="The treasury holds 500,000 USDC",
            paragraph_index=0,
            char_range=[0, 30],
            type="numeric",
            canonical=ClaimCanonical(numbers=[500000.0], addresses=[], urls=[]),
        )
        
        # Run multiple times to check bias
        verdicts = []
        for i in range(10):
            miner._rng.seed(42 + i)
            verdict = miner._determine_verdict(claim)
            verdicts.append(verdict)
        
        # Should be mostly supported
        supported_count = verdicts.count("supported")
        assert supported_count >= 6  # At least 60% supported

    @pytest.mark.asyncio
    async def test_validate_claim_returns_miner_response(self):
        """validate_claim should return proper MinerResponse."""
        from app.miner_client import MockMinerClient
        from app.schemas import Claim, ClaimCanonical, MinerResponse
        
        miner = MockMinerClient(miner_id="test_miner", seed=42)
        
        claim = Claim(
            id="c1",
            text="Test claim",
            paragraph_index=0,
            char_range=[0, 10],
            type="factual",
            canonical=ClaimCanonical(numbers=[], addresses=[], urls=[]),
        )
        
        response = await miner.validate_claim(claim, "sha256:abc123")
        
        assert isinstance(response, MinerResponse)
        assert response.miner_id == "test_miner"
        assert response.claim_id == "c1"
        assert response.verdict in ["verified", "refuted", "unverifiable", "partial"]
        assert len(response.rationale) > 0
        assert response.scores.accuracy >= 0
        assert response.scores.composite >= 0
        assert len(response.embedding) == 64


class TestMinerClientFactory:
    """Test miner client factory."""

    def test_creates_correct_number_of_miners(self):
        """Factory should create requested number of miners."""
        from app.miner_client import create_miner_clients
        
        miners = create_miner_clients(count=5, use_mock=True)
        assert len(miners) == 5

    def test_miners_have_unique_ids(self):
        """Each miner should have unique ID."""
        from app.miner_client import create_miner_clients
        
        miners = create_miner_clients(count=5, use_mock=True)
        ids = [m.get_miner_id() for m in miners]
        assert len(set(ids)) == 5


class TestBuildMinerPayload:
    """Test miner request payload building."""

    def test_builds_correct_payload_structure(self):
        """Payload should match expected structure."""
        from app.miner_client import build_miner_request_payload
        from app.schemas import Claim, ClaimCanonical
        
        claim = Claim(
            id="c1",
            text="Test claim",
            paragraph_index=0,
            char_range=[0, 10],
            type="factual",
            canonical=ClaimCanonical(numbers=[], addresses=[], urls=[]),
        )
        
        payload = build_miner_request_payload(claim, "sha256:abc123", demo_mode=True)
        
        assert "request_id" in payload
        assert payload["proposal_hash"] == "sha256:abc123"
        assert payload["claim"]["id"] == "c1"
        assert payload["claim"]["text"] == "Test claim"
        assert payload["claim"]["type"] == "factual"
        assert len(payload["tasks"]) == 1
        assert "rubric" in payload["tasks"][0]
        assert payload["meta"]["demo_mode"] is True


class TestValidationPipeline:
    """Test full validation pipeline with mock miners."""

    @pytest.fixture
    def temp_dirs(self, tmp_path):
        """Create temporary data directories."""
        claims_dir = tmp_path / "claims"
        jobs_dir = tmp_path / "jobs"
        responses_dir = tmp_path / "responses"
        claims_dir.mkdir()
        jobs_dir.mkdir()
        responses_dir.mkdir()
        return {
            "claims": claims_dir,
            "jobs": jobs_dir,
            "responses": responses_dir,
            "base": tmp_path,
        }

    @pytest.mark.asyncio
    async def test_ingest_creates_claims(self, temp_dirs):
        """Ingesting proposal should create claims."""
        from app.ingest import process_ingest
        from app.schemas import IngestRequest
        
        with patch('app.ingest.get_data_dir', return_value=temp_dirs["claims"]):
            request = IngestRequest(text=SAMPLE_PROPOSAL)
            response = await process_ingest(request)
        
        assert response.proposal_hash.startswith("sha256:")
        assert len(response.claims) >= 5
        
        # Claims should have proper structure
        for claim in response.claims:
            assert claim.id.startswith("c")
            assert len(claim.text) > 0
            assert claim.type in ["factual", "numeric", "normative"]

    @pytest.mark.asyncio
    async def test_validate_claims_job_processes_all_claims(self, temp_dirs):
        """validate_claims_job should process all claims."""
        from app.ingest import process_ingest
        from app.schemas import IngestRequest
        from app.workers import validate_claims_job, job_state, JobStateManager
        from app.config import settings
        
        # Override settings for faster test
        original_timeout = settings.miner_timeout_seconds
        original_quorum = settings.miner_quorum
        original_count = settings.miner_count
        settings.miner_timeout_seconds = 5
        settings.miner_quorum = 2
        settings.miner_count = 3
        settings.use_mock_miners = True
        
        # Mock Redis entirely
        mock_redis = MagicMock()
        mock_redis.hset = MagicMock()
        mock_redis.hgetall = MagicMock(return_value={})
        mock_redis.expire = MagicMock()
        
        try:
            # Patch data directories and Redis
            with patch('app.ingest.get_data_dir', return_value=temp_dirs["claims"]):
                with patch('app.workers.get_jobs_dir', return_value=temp_dirs["jobs"]):
                    with patch('app.workers.get_responses_dir', return_value=temp_dirs["responses"]):
                        with patch.object(job_state, '_redis', mock_redis):
                            # Ingest proposal
                            request = IngestRequest(text=SAMPLE_PROPOSAL)
                            ingest_response = await process_ingest(request)
                            
                            # Validate
                            result = validate_claims_job(ingest_response.proposal_hash)
        finally:
            settings.miner_timeout_seconds = original_timeout
            settings.miner_quorum = original_quorum
            settings.miner_count = original_count
        
        assert result["status"] == "completed"
        assert "responses" in result
        
        # Each claim should have responses
        for claim in ingest_response.claims:
            assert claim.id in result["responses"]
            assert len(result["responses"][claim.id]) >= 2  # At least quorum

    @pytest.mark.asyncio
    async def test_responses_match_schema(self, temp_dirs):
        """Miner responses should match MinerResponse schema."""
        from app.ingest import process_ingest
        from app.schemas import IngestRequest
        from app.workers import validate_claims_job, job_state
        from app.config import settings
        
        settings.miner_timeout_seconds = 5
        settings.miner_quorum = 2
        settings.miner_count = 3
        settings.use_mock_miners = True
        
        # Mock Redis
        mock_redis = MagicMock()
        mock_redis.hset = MagicMock()
        mock_redis.hgetall = MagicMock(return_value={})
        mock_redis.expire = MagicMock()
        
        with patch('app.ingest.get_data_dir', return_value=temp_dirs["claims"]):
            with patch('app.workers.get_jobs_dir', return_value=temp_dirs["jobs"]):
                with patch('app.workers.get_responses_dir', return_value=temp_dirs["responses"]):
                    with patch.object(job_state, '_redis', mock_redis):
                        request = IngestRequest(text=SAMPLE_PROPOSAL)
                        ingest_response = await process_ingest(request)
                        result = validate_claims_job(ingest_response.proposal_hash)
        
        # Check response schema
        for claim_id, responses in result["responses"].items():
            for resp in responses:
                assert "miner_id" in resp
                assert "claim_id" in resp
                assert "verdict" in resp
                assert resp["verdict"] in ["verified", "refuted", "unverifiable", "partial"]
                assert "rationale" in resp
                assert "scores" in resp
                assert "accuracy" in resp["scores"]
                assert "omission_risk" in resp["scores"]
                assert "evidence_quality" in resp["scores"]
                assert "governance_relevance" in resp["scores"]
                assert "composite" in resp["scores"]

    @pytest.mark.asyncio
    async def test_responses_persisted_to_file(self, temp_dirs):
        """Raw responses should be persisted to JSON file."""
        from app.ingest import process_ingest
        from app.schemas import IngestRequest
        from app.workers import validate_claims_job, job_state
        from app.config import settings
        
        settings.miner_timeout_seconds = 5
        settings.miner_quorum = 2
        settings.miner_count = 3
        settings.use_mock_miners = True
        
        # Mock Redis
        mock_redis = MagicMock()
        mock_redis.hset = MagicMock()
        mock_redis.hgetall = MagicMock(return_value={})
        mock_redis.expire = MagicMock()
        
        with patch('app.ingest.get_data_dir', return_value=temp_dirs["claims"]):
            with patch('app.workers.get_jobs_dir', return_value=temp_dirs["jobs"]):
                with patch('app.workers.get_responses_dir', return_value=temp_dirs["responses"]):
                    with patch.object(job_state, '_redis', mock_redis):
                        request = IngestRequest(text=SAMPLE_PROPOSAL)
                        ingest_response = await process_ingest(request)
                        result = validate_claims_job(ingest_response.proposal_hash)
        
        # Check files exist
        job_files = list(temp_dirs["jobs"].glob("*.json"))
        response_files = list(temp_dirs["responses"].glob("*.json"))
        
        assert len(job_files) >= 1
        assert len(response_files) >= 1
        
        # Load and validate response file
        with open(response_files[0]) as f:
            raw_data = json.load(f)
        
        assert "job_id" in raw_data
        assert "responses" in raw_data
        assert len(raw_data["responses"]) > 0


class TestCortensorClientScaffold:
    """Test CortensorRouterMinerClient scaffold."""

    def test_builds_headers_with_api_key(self):
        """Should include auth header when API key provided."""
        from app.miner_client import CortensorRouterMinerClient
        
        client = CortensorRouterMinerClient(api_key="test-key")
        headers = client._build_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-key"

    def test_falls_back_to_mock_when_no_url(self):
        """Should fall back to mock behavior when router URL not configured."""
        from app.miner_client import CortensorRouterMinerClient
        from app.schemas import Claim, ClaimCanonical
        
        client = CortensorRouterMinerClient(router_url="")
        
        claim = Claim(
            id="c1",
            text="Test",
            paragraph_index=0,
            char_range=[0, 4],
            type="factual",
            canonical=ClaimCanonical(numbers=[], addresses=[], urls=[]),
        )
        
        # Should not raise - falls back to mock
        loop = asyncio.new_event_loop()
        try:
            response = loop.run_until_complete(client.validate_claim(claim, "sha256:test"))
            assert response.miner_id is not None
        finally:
            loop.close()


class TestJobStateManager:
    """Test JobStateManager functionality."""

    def test_creates_job(self):
        """Should create job record."""
        from app.workers import JobStateManager
        from unittest.mock import MagicMock
        
        manager = JobStateManager()
        manager._redis = MagicMock()
        manager._redis.hset = MagicMock()
        manager._redis.expire = MagicMock()
        
        with patch('app.workers.get_jobs_dir', return_value=Path(tempfile.mkdtemp())):
            job = manager.create_job("job_123", "sha256:abc", [{"id": "c1"}])
        
        assert job["job_id"] == "job_123"
        assert job["proposal_hash"] == "sha256:abc"
        assert job["status"] == "queued"
        assert job["claims_total"] == 1

    def test_parses_job_data(self):
        """Should parse Redis data correctly."""
        from app.workers import JobStateManager
        
        manager = JobStateManager()
        
        data = {
            "job_id": "job_123",
            "status": "running",
            "claims_total": "5",
            "claims_validated": "3",
            "miners_contacted": "15",
            "miners_responded": "9",
            "claim_ids": '["c1","c2","c3"]',
            "responses": '{"c1":[]}',
        }
        
        parsed = manager._parse_job_data(data)
        
        assert parsed["claims_total"] == 5
        assert parsed["claims_validated"] == 3
        assert parsed["claim_ids"] == ["c1", "c2", "c3"]
        assert parsed["responses"] == {"c1": []}
