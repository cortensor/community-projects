"""Tests for evidence bundle."""

import pytest
from datetime import datetime, timezone
from src.evidence import EvidenceBundle, create_evidence_bundle


def test_create_evidence_bundle():
    """Test evidence bundle creation."""
    bundle = create_evidence_bundle(
        task_id="test-task-001",
        task_description="Test task",
        execution_steps=[{"step": 1, "action": "test"}],
        miner_responses=[{"miner_id": "m1", "content": "response"}],
        consensus_info={"score": 0.95},
        validation_result={"is_valid": True},
        final_output="Test output",
    )

    assert bundle.task_id == "test-task-001"
    assert bundle.bundle_id.startswith("eb-")
    assert bundle.task_description == "Test task"
    assert len(bundle.execution_steps) == 1
    assert len(bundle.miner_responses) == 1


def test_evidence_bundle_hash():
    """Test evidence bundle hash computation."""
    bundle = create_evidence_bundle(
        task_id="test-task-001",
        task_description="Test task",
        execution_steps=[],
        miner_responses=[],
        consensus_info={},
        validation_result={},
        final_output="Test output",
    )

    hash1 = bundle.compute_hash()
    hash2 = bundle.compute_hash()

    # Same content should produce same hash
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex length


def test_evidence_bundle_to_dict():
    """Test evidence bundle serialization."""
    bundle = create_evidence_bundle(
        task_id="test-task-001",
        task_description="Test task",
        execution_steps=[],
        miner_responses=[],
        consensus_info={},
        validation_result={},
        final_output="Test output",
    )

    data = bundle.to_dict()

    assert "bundle_id" in data
    assert "task_id" in data
    assert "created_at" in data
    assert "integrity_hash" in data
    assert data["task_id"] == "test-task-001"


def test_evidence_bundle_verify_integrity():
    """Test evidence bundle integrity verification."""
    bundle = create_evidence_bundle(
        task_id="test-task-001",
        task_description="Test task",
        execution_steps=[],
        miner_responses=[],
        consensus_info={},
        validation_result={},
        final_output="Test output",
    )

    expected_hash = bundle.compute_hash()

    # Correct hash should verify
    assert bundle.verify_integrity(expected_hash) is True

    # Wrong hash should fail
    assert bundle.verify_integrity("wrong-hash") is False


def test_evidence_bundle_to_json():
    """Test evidence bundle JSON serialization."""
    bundle = create_evidence_bundle(
        task_id="test-task-001",
        task_description="Test task",
        execution_steps=[],
        miner_responses=[],
        consensus_info={},
        validation_result={},
        final_output="Test output",
    )

    json_str = bundle.to_json()

    assert isinstance(json_str, str)
    assert "test-task-001" in json_str
    assert "Test task" in json_str
