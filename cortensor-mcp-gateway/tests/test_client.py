"""Tests for Cortensor client."""

import pytest
from src.cortensor_client import CortensorClient, CortensorConfig
from src.cortensor_client.models import ConsensusResult, MinerResponse


@pytest.fixture
def mock_config():
    """Create a mock mode configuration."""
    return CortensorConfig(mock_mode=True)


@pytest.mark.asyncio
async def test_client_health_check(mock_config):
    """Test health check in mock mode."""
    async with CortensorClient(mock_config) as client:
        is_healthy = await client.health_check()
        assert is_healthy is True


@pytest.mark.asyncio
async def test_client_get_miners(mock_config):
    """Test getting miners list in mock mode."""
    async with CortensorClient(mock_config) as client:
        miners = await client.get_miners()
        assert len(miners) > 0
        assert all("id" in m for m in miners)
        assert all("model" in m for m in miners)


@pytest.mark.asyncio
async def test_client_inference(mock_config):
    """Test inference in mock mode."""
    async with CortensorClient(mock_config) as client:
        response = await client.inference("Test prompt")

        assert response.task_id is not None
        assert response.content is not None
        assert response.consensus is not None
        assert len(response.miner_responses) > 0


@pytest.mark.asyncio
async def test_consensus_calculation(mock_config):
    """Test consensus score calculation."""
    async with CortensorClient(mock_config) as client:
        response = await client.inference("Analyze this")

        # Mock mode should generally achieve consensus
        assert 0.0 <= response.consensus.score <= 1.0
        assert response.consensus.total_miners > 0
        assert response.consensus.agreement_count <= response.consensus.total_miners


def test_consensus_result_is_consensus():
    """Test ConsensusResult.is_consensus property."""
    # Above threshold
    result = ConsensusResult(
        score=0.8,
        agreement_count=4,
        total_miners=5,
        majority_response="test",
    )
    assert result.is_consensus is True

    # Below threshold
    result = ConsensusResult(
        score=0.5,
        agreement_count=2,
        total_miners=4,
        majority_response="test",
    )
    assert result.is_consensus is False


def test_miner_response_to_dict():
    """Test MinerResponse serialization."""
    response = MinerResponse(
        miner_id="test-001",
        content="Test content",
        latency_ms=100.5,
        model="test-model",
    )
    data = response.to_dict()

    assert data["miner_id"] == "test-001"
    assert data["content"] == "Test content"
    assert data["latency_ms"] == 100.5
    assert data["model"] == "test-model"
    assert "timestamp" in data
