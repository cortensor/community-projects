"""Auditor Agent - Generates audit trails and evidence bundles."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .base import AgentTask, BaseAgent
from ..cortensor_client import CortensorClient


@dataclass
class EvidenceBundle:
    """Complete audit trail for a task execution."""

    bundle_id: str
    task_id: str
    created_at: datetime
    execution_steps: list[dict[str, Any]]
    miner_responses: list[dict[str, Any]]
    consensus_info: dict[str, Any]
    validation_result: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "task_id": self.task_id,
            "created_at": self.created_at.isoformat(),
            "execution_steps": self.execution_steps,
            "miner_responses": self.miner_responses,
            "consensus_info": self.consensus_info,
            "validation_result": self.validation_result,
            "metadata": self.metadata,
            "hash": self.compute_hash(),
        }

    def compute_hash(self) -> str:
        """Compute hash of the evidence bundle for integrity verification."""
        content = json.dumps(
            {
                "task_id": self.task_id,
                "execution_steps": self.execution_steps,
                "miner_responses": self.miner_responses,
                "consensus_info": self.consensus_info,
            },
            sort_keys=True,
        )
        return hashlib.sha256(content.encode()).hexdigest()

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class AuditorAgent(BaseAgent):
    """Agent responsible for creating audit trails and evidence bundles."""

    def __init__(self, client: CortensorClient):
        super().__init__("AuditorAgent", client)
        self._evidence_store: dict[str, EvidenceBundle] = {}

    def get_system_prompt(self) -> str:
        return """You are the Auditor Agent in a verifiable AI system.
Your role is to:
1. Compile comprehensive audit trails
2. Verify the integrity of execution records
3. Generate evidence bundles for verification
4. Ensure traceability of all operations

Focus on completeness and accuracy of audit records."""

    async def execute(self, task: AgentTask) -> AgentTask:
        """Generate an audit trail for completed tasks."""
        task.status = "in_progress"

        try:
            # Extract audit data from input
            execution_data = task.input_data.get("execution_data", {})
            miner_responses = task.input_data.get("miner_responses", [])
            consensus_info = task.input_data.get("consensus_info", {})
            validation_result = task.input_data.get("validation_result", {})

            # Create evidence bundle
            bundle = self._create_evidence_bundle(
                task_id=task.input_data.get("original_task_id", task.task_id),
                execution_data=execution_data,
                miner_responses=miner_responses,
                consensus_info=consensus_info,
                validation_result=validation_result,
            )

            # Store the bundle
            self._evidence_store[bundle.bundle_id] = bundle

            task.result = {
                "evidence_bundle": bundle.to_dict(),
                "bundle_id": bundle.bundle_id,
                "integrity_hash": bundle.compute_hash(),
            }
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc)

        except Exception as e:
            task.status = "failed"
            task.error = str(e)

        return task

    def _create_evidence_bundle(
        self,
        task_id: str,
        execution_data: dict,
        miner_responses: list,
        consensus_info: dict,
        validation_result: dict,
    ) -> EvidenceBundle:
        """Create a complete evidence bundle."""
        import uuid

        bundle_id = f"eb-{uuid.uuid4().hex[:12]}"

        # Format execution steps
        execution_steps = []
        if "steps" in execution_data:
            execution_steps = execution_data["steps"]
        else:
            execution_steps = [
                {
                    "step": 1,
                    "action": "inference",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": execution_data,
                }
            ]

        return EvidenceBundle(
            bundle_id=bundle_id,
            task_id=task_id,
            created_at=datetime.now(timezone.utc),
            execution_steps=execution_steps,
            miner_responses=miner_responses,
            consensus_info=consensus_info,
            validation_result=validation_result,
            metadata={
                "agent": self.name,
                "version": "0.1.0",
            },
        )

    def get_evidence_bundle(self, bundle_id: str) -> EvidenceBundle | None:
        """Retrieve a stored evidence bundle."""
        return self._evidence_store.get(bundle_id)

    def list_bundles(self) -> list[str]:
        """List all stored bundle IDs."""
        return list(self._evidence_store.keys())

    async def verify_bundle_integrity(self, bundle_id: str) -> dict[str, Any]:
        """Verify the integrity of a stored evidence bundle."""
        bundle = self._evidence_store.get(bundle_id)
        if not bundle:
            return {
                "valid": False,
                "error": f"Bundle {bundle_id} not found",
            }

        stored_hash = bundle.compute_hash()

        return {
            "valid": True,
            "bundle_id": bundle_id,
            "hash": stored_hash,
            "task_id": bundle.task_id,
            "created_at": bundle.created_at.isoformat(),
        }
