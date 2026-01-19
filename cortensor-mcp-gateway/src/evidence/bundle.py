"""Evidence bundle creation and management."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class EvidenceBundle:
    """Immutable evidence bundle for audit trails.

    Contains all information needed to verify an AI inference:
    - Task details
    - Miner responses
    - Consensus information
    - Validation results
    - Cryptographic hash for integrity
    """

    bundle_id: str
    task_id: str
    created_at: datetime
    task_description: str
    execution_steps: list[dict[str, Any]]
    miner_responses: list[dict[str, Any]]
    consensus_info: dict[str, Any]
    validation_result: dict[str, Any]
    final_output: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "bundle_id": self.bundle_id,
            "task_id": self.task_id,
            "created_at": self.created_at.isoformat(),
            "task_description": self.task_description,
            "execution_steps": self.execution_steps,
            "miner_responses": self.miner_responses,
            "consensus_info": self.consensus_info,
            "validation_result": self.validation_result,
            "final_output": self.final_output,
            "metadata": self.metadata,
            "integrity_hash": self.compute_hash(),
        }

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of the bundle content for integrity verification."""
        content = {
            "task_id": self.task_id,
            "task_description": self.task_description,
            "execution_steps": self.execution_steps,
            "miner_responses": self.miner_responses,
            "consensus_info": self.consensus_info,
            "final_output": self.final_output,
        }
        serialized = json.dumps(content, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceBundle:
        """Create EvidenceBundle from dictionary."""
        return cls(
            bundle_id=data["bundle_id"],
            task_id=data["task_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            task_description=data.get("task_description", ""),
            execution_steps=data.get("execution_steps", []),
            miner_responses=data.get("miner_responses", []),
            consensus_info=data.get("consensus_info", {}),
            validation_result=data.get("validation_result", {}),
            final_output=data.get("final_output", ""),
            metadata=data.get("metadata", {}),
        )

    def verify_integrity(self, expected_hash: str) -> bool:
        """Verify bundle integrity against expected hash."""
        return self.compute_hash() == expected_hash


def create_evidence_bundle(
    task_id: str,
    task_description: str,
    execution_steps: list[dict[str, Any]],
    miner_responses: list[dict[str, Any]],
    consensus_info: dict[str, Any],
    validation_result: dict[str, Any],
    final_output: str,
    metadata: dict[str, Any] | None = None,
) -> EvidenceBundle:
    """Factory function to create a new evidence bundle.

    Args:
        task_id: Unique task identifier
        task_description: Description of the original task
        execution_steps: List of execution step records
        miner_responses: List of miner response records
        consensus_info: Consensus calculation results
        validation_result: Validation agent results
        final_output: Final aggregated output
        metadata: Optional additional metadata

    Returns:
        New EvidenceBundle instance
    """
    return EvidenceBundle(
        bundle_id=f"eb-{uuid4().hex[:16]}",
        task_id=task_id,
        created_at=datetime.now(timezone.utc),
        task_description=task_description,
        execution_steps=execution_steps,
        miner_responses=miner_responses,
        consensus_info=consensus_info,
        validation_result=validation_result,
        final_output=final_output,
        metadata=metadata or {},
    )
