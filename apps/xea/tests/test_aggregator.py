"""
Xea Governance Oracle - Aggregator Tests

Tests for aggregation, PoI/PoUW metrics, outlier detection, and evidence bundles.
"""

import json
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile


# ============================================================================
# Stats Module Tests
# ============================================================================

class TestCosineDistance:
    """Test cosine similarity and distance calculations."""

    def test_identical_vectors_similarity_one(self):
        """Identical vectors should have similarity of 1."""
        from app.stats import cosine_similarity
        
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([1.0, 2.0, 3.0])
        
        sim = cosine_similarity(a, b)
        assert abs(sim - 1.0) < 0.0001

    def test_orthogonal_vectors_similarity_zero(self):
        """Orthogonal vectors should have similarity of 0."""
        from app.stats import cosine_similarity
        
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        
        sim = cosine_similarity(a, b)
        assert abs(sim) < 0.0001

    def test_opposite_vectors_similarity_negative(self):
        """Opposite vectors should have similarity of -1."""
        from app.stats import cosine_similarity
        
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([-1.0, -2.0, -3.0])
        
        sim = cosine_similarity(a, b)
        assert abs(sim + 1.0) < 0.0001

    def test_mean_pairwise_distance_identical(self):
        """Identical embeddings should have zero mean distance."""
        from app.stats import mean_pairwise_cosine_distance
        
        embeddings = [
            [1.0, 2.0, 3.0],
            [1.0, 2.0, 3.0],
            [1.0, 2.0, 3.0],
        ]
        
        dist = mean_pairwise_cosine_distance(embeddings)
        assert abs(dist) < 0.0001

    def test_mean_pairwise_distance_diverse(self):
        """Diverse embeddings should have positive mean distance."""
        from app.stats import mean_pairwise_cosine_distance
        
        embeddings = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
        
        dist = mean_pairwise_cosine_distance(embeddings)
        assert dist > 0.5  # Should be high for orthogonal vectors


class TestBootstrapCI:
    """Test bootstrap confidence interval calculation."""

    def test_single_value_returns_same(self):
        """Single value should return that value as both bounds."""
        from app.stats import bootstrap_ci
        
        low, high = bootstrap_ci([0.8], n_iter=100, seed=42)
        assert low == 0.8
        assert high == 0.8

    def test_ci_contains_mean(self):
        """CI should contain the sample mean."""
        from app.stats import bootstrap_ci
        
        values = [0.8, 0.85, 0.82, 0.88, 0.79]
        mean_val = np.mean(values)
        
        low, high = bootstrap_ci(values, n_iter=1000, seed=42)
        
        assert low <= mean_val <= high

    def test_narrow_ci_for_consistent_values(self):
        """Consistent values should produce narrow CI."""
        from app.stats import bootstrap_ci
        
        # Very consistent values
        values = [0.80, 0.81, 0.80, 0.79, 0.80]
        
        low, high = bootstrap_ci(values, n_iter=1000, seed=42)
        
        # CI should be narrow (less than 0.05 width)
        assert (high - low) < 0.05

    def test_wide_ci_for_variable_values(self):
        """Variable values should produce wider CI."""
        from app.stats import bootstrap_ci
        
        # Highly variable values
        values = [0.3, 0.9, 0.4, 0.85, 0.5]
        
        low, high = bootstrap_ci(values, n_iter=1000, seed=42)
        
        # CI should be wider
        assert (high - low) > 0.1

    def test_deterministic_with_seed(self):
        """Same seed should produce same result."""
        from app.stats import bootstrap_ci
        
        values = [0.8, 0.85, 0.82, 0.88, 0.79]
        
        ci1 = bootstrap_ci(values, n_iter=1000, seed=42)
        ci2 = bootstrap_ci(values, n_iter=1000, seed=42)
        
        assert ci1 == ci2


class TestMahalanobisOutliers:
    """Test Mahalanobis distance outlier detection."""

    def test_no_outliers_in_uniform_data(self):
        """Uniform data should have no outliers."""
        from app.stats import detect_mahalanobis_outliers
        
        # All scores very similar
        score_vectors = np.array([
            [0.8, 0.1, 0.85, 0.9],
            [0.82, 0.12, 0.84, 0.88],
            [0.79, 0.09, 0.86, 0.91],
            [0.81, 0.11, 0.83, 0.89],
            [0.80, 0.10, 0.85, 0.90],
        ])
        
        outliers = detect_mahalanobis_outliers(score_vectors, threshold=3.0)
        assert len(outliers) == 0

    def test_detects_clear_outlier(self):
        """Should detect a clear outlier."""
        from app.stats import detect_mahalanobis_outliers
        
        # Four very similar, one extreme outlier with completely different pattern
        score_vectors = np.array([
            [0.85, 0.10, 0.88, 0.90],
            [0.83, 0.11, 0.87, 0.89],
            [0.84, 0.09, 0.89, 0.91],
            [0.82, 0.12, 0.86, 0.88],
            [0.86, 0.08, 0.90, 0.92],
            [0.84, 0.10, 0.88, 0.90],
            [0.05, 0.95, 0.05, 0.05],  # Clear extreme outlier - completely opposite
        ])
        
        outliers = detect_mahalanobis_outliers(score_vectors, threshold=2.0)
        assert 6 in outliers  # Last index should be flagged

    def test_returns_empty_for_insufficient_samples(self):
        """Should return empty for < 2 samples."""
        from app.stats import detect_mahalanobis_outliers
        
        score_vectors = np.array([[0.8, 0.1, 0.85, 0.9]])
        outliers = detect_mahalanobis_outliers(score_vectors)
        assert len(outliers) == 0


class TestModeAgreement:
    """Test mode verdict and agreement calculation."""

    def test_unanimous_agreement(self):
        """All same verdict should give 1.0 agreement."""
        from app.stats import compute_mode_agreement
        
        verdicts = ["verified", "verified", "verified", "verified", "verified"]
        mode, agreement = compute_mode_agreement(verdicts)
        
        assert mode == "verified"
        assert agreement == 1.0

    def test_majority_agreement(self):
        """Majority verdict should be mode with correct ratio."""
        from app.stats import compute_mode_agreement
        
        verdicts = ["verified", "verified", "verified", "refuted", "refuted"]
        mode, agreement = compute_mode_agreement(verdicts)
        
        assert mode == "verified"
        assert agreement == 0.6

    def test_empty_list(self):
        """Empty list should return unknown with 0 agreement."""
        from app.stats import compute_mode_agreement
        
        verdicts = []
        mode, agreement = compute_mode_agreement(verdicts)
        
        assert mode == "unknown"
        assert agreement == 0.0


# ============================================================================
# Aggregator Tests
# ============================================================================

class TestAggregateClaimResponses:
    """Test per-claim aggregation."""

    def test_high_agreement_high_pouw_supported(self):
        """High agreement + high PoUW should give 'supported'."""
        from app.aggregator import aggregate_claim_responses
        
        responses = [
            {"miner_id": "m1", "verdict": "verified", "scores": {"accuracy": 0.9, "omission_risk": 0.1, "evidence_quality": 0.9, "governance_relevance": 0.9, "composite": 0.88}, "embedding": [0.1] * 64},
            {"miner_id": "m2", "verdict": "verified", "scores": {"accuracy": 0.85, "omission_risk": 0.12, "evidence_quality": 0.88, "governance_relevance": 0.85, "composite": 0.85}, "embedding": [0.1] * 64},
            {"miner_id": "m3", "verdict": "verified", "scores": {"accuracy": 0.88, "omission_risk": 0.08, "evidence_quality": 0.92, "governance_relevance": 0.88, "composite": 0.87}, "embedding": [0.1] * 64},
            {"miner_id": "m4", "verdict": "verified", "scores": {"accuracy": 0.87, "omission_risk": 0.11, "evidence_quality": 0.89, "governance_relevance": 0.87, "composite": 0.86}, "embedding": [0.1] * 64},
            {"miner_id": "m5", "verdict": "verified", "scores": {"accuracy": 0.9, "omission_risk": 0.09, "evidence_quality": 0.91, "governance_relevance": 0.9, "composite": 0.89}, "embedding": [0.1] * 64},
        ]
        
        result = aggregate_claim_responses("c1", responses, bootstrap_seed=42)
        
        assert result["poi_agreement"] == 1.0
        assert result["pouw_mean"] > 0.75
        assert result["final_recommendation"] == "supported"

    def test_mixed_responses_disputed(self):
        """Mixed/low agreement should give 'disputed' or 'supported_with_caution'."""
        from app.aggregator import aggregate_claim_responses
        
        responses = [
            {"miner_id": "m1", "verdict": "verified", "scores": {"accuracy": 0.9, "omission_risk": 0.1, "evidence_quality": 0.9, "governance_relevance": 0.9, "composite": 0.88}, "embedding": [0.1] * 64},
            {"miner_id": "m2", "verdict": "refuted", "scores": {"accuracy": 0.7, "omission_risk": 0.3, "evidence_quality": 0.6, "governance_relevance": 0.7, "composite": 0.55}, "embedding": [0.2] * 64},
            {"miner_id": "m3", "verdict": "refuted", "scores": {"accuracy": 0.65, "omission_risk": 0.35, "evidence_quality": 0.55, "governance_relevance": 0.65, "composite": 0.5}, "embedding": [0.3] * 64},
            {"miner_id": "m4", "verdict": "refuted", "scores": {"accuracy": 0.6, "omission_risk": 0.4, "evidence_quality": 0.5, "governance_relevance": 0.6, "composite": 0.45}, "embedding": [0.4] * 64},
            {"miner_id": "m5", "verdict": "unverifiable", "scores": {"accuracy": 0.5, "omission_risk": 0.2, "evidence_quality": 0.5, "governance_relevance": 0.5, "composite": 0.5}, "embedding": [0.5] * 64},
        ]
        
        result = aggregate_claim_responses("c1", responses, bootstrap_seed=42)
        
        # Majority is refuted, so should be disputed
        assert result["final_recommendation"] == "disputed"
        assert result["poi_agreement"] < 1.0

    def test_detects_outlier_miner(self):
        """Should detect miner with anomalous scores."""
        from app.aggregator import aggregate_claim_responses
        
        responses = [
            {"miner_id": "m1", "verdict": "verified", "scores": {"accuracy": 0.9, "omission_risk": 0.1, "evidence_quality": 0.9, "governance_relevance": 0.9, "composite": 0.88}, "embedding": [0.1] * 64},
            {"miner_id": "m2", "verdict": "verified", "scores": {"accuracy": 0.88, "omission_risk": 0.12, "evidence_quality": 0.88, "governance_relevance": 0.88, "composite": 0.86}, "embedding": [0.1] * 64},
            {"miner_id": "m3", "verdict": "verified", "scores": {"accuracy": 0.87, "omission_risk": 0.11, "evidence_quality": 0.89, "governance_relevance": 0.87, "composite": 0.86}, "embedding": [0.1] * 64},
            {"miner_id": "m4", "verdict": "verified", "scores": {"accuracy": 0.89, "omission_risk": 0.09, "evidence_quality": 0.91, "governance_relevance": 0.89, "composite": 0.87}, "embedding": [0.1] * 64},
            {"miner_id": "m5_outlier", "verdict": "verified", "scores": {"accuracy": 0.1, "omission_risk": 0.9, "evidence_quality": 0.1, "governance_relevance": 0.1, "composite": 0.1}, "embedding": [0.9] * 64},
        ]
        
        result = aggregate_claim_responses("c1", responses, bootstrap_seed=42)
        
        # m5_outlier should be flagged
        assert "m5_outlier" in result["outliers"]


class TestAggregateJob:
    """Test full job aggregation."""

    @pytest.fixture
    def temp_dirs(self, tmp_path):
        """Create temporary data directories."""
        responses_dir = tmp_path / "responses"
        evidence_dir = tmp_path / "evidence"
        jobs_dir = tmp_path / "jobs"
        responses_dir.mkdir()
        evidence_dir.mkdir()
        jobs_dir.mkdir()
        return {
            "responses": responses_dir,
            "evidence": evidence_dir,
            "jobs": jobs_dir,
        }

    def test_aggregates_multiple_claims(self, temp_dirs):
        """Should aggregate all claims in a job."""
        from app.aggregator import aggregate_job
        
        job_id = "test_job_123"
        
        # Create mock job file
        job_data = {
            "job_id": job_id,
            "proposal_hash": "sha256:abc123",
            "status": "completed",
            "claim_ids": ["c1", "c2"],
        }
        with open(temp_dirs["jobs"] / f"{job_id}.json", "w") as f:
            json.dump(job_data, f)
        
        # Create mock responses file
        responses_data = {
            "job_id": job_id,
            "responses": [
                {"timestamp": "2025-01-01T00:00:00", "claim_id": "c1", "response": {"miner_id": "m1", "verdict": "verified", "scores": {"accuracy": 0.9, "omission_risk": 0.1, "evidence_quality": 0.9, "governance_relevance": 0.9, "composite": 0.88}, "embedding": [0.1] * 64}},
                {"timestamp": "2025-01-01T00:00:01", "claim_id": "c1", "response": {"miner_id": "m2", "verdict": "verified", "scores": {"accuracy": 0.85, "omission_risk": 0.12, "evidence_quality": 0.88, "governance_relevance": 0.85, "composite": 0.85}, "embedding": [0.1] * 64}},
                {"timestamp": "2025-01-01T00:00:02", "claim_id": "c1", "response": {"miner_id": "m3", "verdict": "verified", "scores": {"accuracy": 0.88, "omission_risk": 0.08, "evidence_quality": 0.92, "governance_relevance": 0.88, "composite": 0.87}, "embedding": [0.1] * 64}},
                {"timestamp": "2025-01-01T00:00:03", "claim_id": "c2", "response": {"miner_id": "m1", "verdict": "verified", "scores": {"accuracy": 0.8, "omission_risk": 0.15, "evidence_quality": 0.85, "governance_relevance": 0.8, "composite": 0.8}, "embedding": [0.2] * 64}},
                {"timestamp": "2025-01-01T00:00:04", "claim_id": "c2", "response": {"miner_id": "m2", "verdict": "verified", "scores": {"accuracy": 0.82, "omission_risk": 0.14, "evidence_quality": 0.83, "governance_relevance": 0.82, "composite": 0.81}, "embedding": [0.2] * 64}},
                {"timestamp": "2025-01-01T00:00:05", "claim_id": "c2", "response": {"miner_id": "m3", "verdict": "refuted", "scores": {"accuracy": 0.6, "omission_risk": 0.3, "evidence_quality": 0.6, "governance_relevance": 0.6, "composite": 0.55}, "embedding": [0.5] * 64}},
            ],
        }
        with open(temp_dirs["responses"] / f"{job_id}.json", "w") as f:
            json.dump(responses_data, f)
        
        # Run aggregation
        with patch('app.aggregator.get_responses_dir', return_value=temp_dirs["responses"]):
            with patch('app.aggregator.get_evidence_dir', return_value=temp_dirs["evidence"]):
                with patch('app.aggregator.get_jobs_dir', return_value=temp_dirs["jobs"]):
                    bundle = aggregate_job(job_id, bootstrap_seed=42)
        
        assert bundle is not None
        assert bundle["job_id"] == job_id
        assert bundle["proposal_hash"] == "sha256:abc123"
        assert len(bundle["claims"]) == 2
        
        # Check overall metrics exist
        assert "overall_poi_agreement" in bundle
        assert "overall_pouw_score" in bundle
        assert "overall_ci_95" in bundle
        assert "critical_flags" in bundle
        assert "timestamp" in bundle

    def test_saves_evidence_bundle(self, temp_dirs):
        """Should save evidence bundle to file."""
        from app.aggregator import aggregate_job, load_evidence_bundle
        
        job_id = "test_job_456"
        
        # Create mock data
        job_data = {"job_id": job_id, "proposal_hash": "sha256:def456", "status": "completed"}
        with open(temp_dirs["jobs"] / f"{job_id}.json", "w") as f:
            json.dump(job_data, f)
        
        responses_data = {
            "job_id": job_id,
            "responses": [
                {"claim_id": "c1", "response": {"miner_id": "m1", "verdict": "verified", "scores": {"accuracy": 0.9, "omission_risk": 0.1, "evidence_quality": 0.9, "governance_relevance": 0.9, "composite": 0.88}, "embedding": [0.1] * 64}},
            ],
        }
        with open(temp_dirs["responses"] / f"{job_id}.json", "w") as f:
            json.dump(responses_data, f)
        
        # Run aggregation
        with patch('app.aggregator.get_responses_dir', return_value=temp_dirs["responses"]):
            with patch('app.aggregator.get_evidence_dir', return_value=temp_dirs["evidence"]):
                with patch('app.aggregator.get_jobs_dir', return_value=temp_dirs["jobs"]):
                    aggregate_job(job_id, bootstrap_seed=42)
                    
                    # Check file exists
                    evidence_file = temp_dirs["evidence"] / f"{job_id}.json"
                    assert evidence_file.exists()
                    
                    # Load and verify
                    loaded = load_evidence_bundle(job_id)
                    assert loaded is not None
                    assert loaded["job_id"] == job_id


class TestCriticalFlags:
    """Test critical flag generation."""

    def test_flags_disputed_claims(self):
        """Should flag disputed claims."""
        from app.aggregator import generate_critical_flags
        
        claims = [
            {"id": "c1", "final_recommendation": "supported", "outliers": [], "poi_agreement": 0.9},
            {"id": "c2", "final_recommendation": "disputed", "outliers": [], "poi_agreement": 0.4},
        ]
        
        flags = generate_critical_flags(claims)
        
        assert any("c2" in f and "disputed" in f for f in flags)

    def test_flags_outliers(self):
        """Should flag outlier miners."""
        from app.aggregator import generate_critical_flags
        
        claims = [
            {"id": "c1", "final_recommendation": "supported", "outliers": ["miner_bad"], "poi_agreement": 0.9},
        ]
        
        flags = generate_critical_flags(claims)
        
        assert any("miner_bad" in f and "outlier" in f for f in flags)

    def test_flags_low_agreement(self):
        """Should flag low agreement claims."""
        from app.aggregator import generate_critical_flags
        
        claims = [
            {"id": "c1", "final_recommendation": "supported_with_caution", "outliers": [], "poi_agreement": 0.55},
        ]
        
        flags = generate_critical_flags(claims)
        
        assert any("c1" in f and "agreement" in f.lower() for f in flags)
