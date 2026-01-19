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


@dataclass
class DelegateRequest:
    """Request for delegating task to Cortensor miners."""

    prompt: str
    session_id: int
    prompt_type: PromptType = PromptType.RAW
    stream: bool = False
    timeout: int = 360
    max_tokens: int = 4096
    k_redundancy: int = 3  # Number of miners for redundancy

    def to_payload(self) -> dict[str, Any]:
        """Convert to /delegate API payload."""
        return {
            "session_id": self.session_id,
            "prompt": self.prompt,
            "prompt_type": self.prompt_type.value,
            "stream": self.stream,
            "timeout": self.timeout,
            "max_tokens": self.max_tokens,
        }


@dataclass
class ValidateRequest:
    """Request for validating task results via PoI."""

    session_id: int
    task_id: int
    miner_address: str
    result_data: str
    k_redundancy: int = 3  # k-redundant re-inference

    def to_payload(self) -> dict[str, Any]:
        """Convert to /validate API payload."""
        return {
            "session_id": self.session_id,
            "task_id": self.task_id,
            "miner_address": self.miner_address,
            "result_data": self.result_data,
        }


@dataclass
class ValidationResult:
    """Result from Cortensor validation (PoI + PoUW)."""

    task_id: str
    is_valid: bool
    confidence: float
    attestation: str | None = None  # JWS/EIP-712 signed attestation
    k_miners_validated: int = 0
    validation_details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "is_valid": self.is_valid,
            "confidence": self.confidence,
            "attestation": self.attestation,
            "k_miners_validated": self.k_miners_validated,
            "validation_details": self.validation_details,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SessionLogEntry:
    """Single entry in session log."""

    operation: str  # delegate, validate, create_session, etc.
    timestamp: datetime
    request: dict[str, Any]
    response: dict[str, Any]
    success: bool
    latency_ms: float
    task_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "timestamp": self.timestamp.isoformat(),
            "request": self.request,
            "response": self.response,
            "success": self.success,
            "latency_ms": self.latency_ms,
            "task_id": self.task_id,
        }


@dataclass
class SessionLog:
    """Complete session log for hackathon submission."""

    session_id: int
    session_name: str
    created_at: datetime
    entries: list[SessionLogEntry] = field(default_factory=list)
    total_delegates: int = 0
    total_validates: int = 0
    total_tasks: int = 0

    def add_entry(self, entry: SessionLogEntry) -> None:
        self.entries.append(entry)
        if entry.operation == "delegate":
            self.total_delegates += 1
            self.total_tasks += 1
        elif entry.operation == "validate":
            self.total_validates += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "session_name": self.session_name,
            "created_at": self.created_at.isoformat(),
            "entries": [e.to_dict() for e in self.entries],
            "summary": {
                "total_delegates": self.total_delegates,
                "total_validates": self.total_validates,
                "total_tasks": self.total_tasks,
                "total_entries": len(self.entries),
            },
        }

    def export_json(self) -> str:
        """Export session log as JSON for submission."""
        import json
        return json.dumps(self.to_dict(), indent=2)
