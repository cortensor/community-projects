"""Data models for Cortensor client."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class PromptType(Enum):
    """Prompt type for Cortensor inference."""

    RAW = 1
    CHAT = 2


@dataclass
class MinerResponse:
    """Response from a single miner."""

    miner_id: str
    content: str
    latency_ms: float
    model: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "miner_id": self.miner_id,
            "content": self.content,
            "latency_ms": self.latency_ms,
            "model": self.model,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class ConsensusResult:
    """Result of PoI consensus verification."""

    score: float  # 0.0 - 1.0
    agreement_count: int
    total_miners: int
    majority_response: str
    divergent_miners: list[str] = field(default_factory=list)

    @property
    def is_consensus(self) -> bool:
        """Check if consensus threshold is met (>= 0.66)."""
        return self.score >= 0.66

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "agreement_count": self.agreement_count,
            "total_miners": self.total_miners,
            "majority_response": self.majority_response,
            "divergent_miners": self.divergent_miners,
            "is_consensus": self.is_consensus,
        }


@dataclass
class InferenceRequest:
    """Request for Cortensor inference."""

    prompt: str
    session_id: int
    prompt_type: PromptType = PromptType.RAW
    stream: bool = False
    timeout: int = 360
    max_tokens: int = 4096

    def to_payload(self) -> dict[str, Any]:
        """Convert to API payload format per official docs."""
        return {
            "session_id": self.session_id,
            "prompt": self.prompt,
            "stream": self.stream,
            "timeout": self.timeout,
        }


@dataclass
class CortensorResponse:
    """Aggregated response from Cortensor Network."""

    task_id: str
    content: str  # Best/majority response
    miner_responses: list[MinerResponse]
    consensus: ConsensusResult
    total_latency_ms: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_verified(self) -> bool:
        """Check if response passed PoI verification."""
        return self.consensus.is_consensus

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "content": self.content,
            "miner_responses": [m.to_dict() for m in self.miner_responses],
            "consensus": self.consensus.to_dict(),
            "total_latency_ms": self.total_latency_ms,
            "timestamp": self.timestamp.isoformat(),
            "is_verified": self.is_verified,
        }
