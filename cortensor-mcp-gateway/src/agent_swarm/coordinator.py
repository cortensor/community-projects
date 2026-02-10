"""Agent Coordinator - Orchestrates the multi-agent workflow."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .base import AgentTask
from .planner import PlannerAgent
from .executor import ExecutorAgent
from .validator import ValidatorAgent
from .auditor import AuditorAgent, EvidenceBundle
from ..cortensor_client import CortensorClient


@dataclass
class WorkflowResult:
    """Result of a complete workflow execution."""

    workflow_id: str
    original_task: str
    final_output: str
    is_verified: bool
    consensus_score: float
    evidence_bundle_id: str | None
    execution_time_ms: float
    steps: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "original_task": self.original_task,
            "final_output": self.final_output,
            "is_verified": self.is_verified,
            "consensus_score": self.consensus_score,
            "evidence_bundle_id": self.evidence_bundle_id,
            "execution_time_ms": self.execution_time_ms,
            "steps": self.steps,
        }


class AgentCoordinator:
    """Coordinates the multi-agent workflow for verifiable AI tasks.

    Workflow:
    1. Planner breaks down the task
    2. Executor runs each sub-task through Cortensor
    3. Validator verifies consensus and output quality
    4. Auditor creates evidence bundle
    """

    def __init__(self, client: CortensorClient):
        self.client = client
        self.planner = PlannerAgent(client)
        self.executor = ExecutorAgent(client)
        self.validator = ValidatorAgent(client)
        self.auditor = AuditorAgent(client)

    async def execute_workflow(
        self,
        task_description: str,
        input_data: dict[str, Any] | None = None,
        skip_planning: bool = False,
    ) -> WorkflowResult:
        """Execute a complete workflow for a given task.

        Args:
            task_description: Description of the task to execute
            input_data: Optional additional input data
            skip_planning: If True, skip planning and execute directly

        Returns:
            WorkflowResult with all execution details
        """
        import time

        start_time = time.perf_counter()
        workflow_id = f"wf-{uuid4().hex[:12]}"
        steps = []

        # Step 1: Planning
        if not skip_planning:
            plan_task = AgentTask(
                task_id=f"{workflow_id}-plan",
                description=task_description,
                input_data=input_data or {},
            )
            plan_task = await self.planner.execute(plan_task)
            steps.append({
                "step": "planning",
                "status": plan_task.status,
                "result": plan_task.result,
            })

            if plan_task.status == "failed":
                return self._create_failed_result(
                    workflow_id, task_description, "Planning failed", plan_task.error, start_time, steps
                )

            sub_tasks = plan_task.result.get("sub_tasks", [])
        else:
            # Single task execution
            sub_tasks = [
                AgentTask(
                    task_id=f"{workflow_id}-exec",
                    description=task_description,
                    input_data=input_data or {},
                )
            ]

        # Step 2: Execution
        execution_results = []
        miner_responses_all = []

        for sub_task in sub_tasks:
            exec_task = await self.executor.execute(sub_task)
            execution_results.append(exec_task)

            if exec_task.result:
                miner_responses_all.extend(
                    exec_task.result.get("miner_responses", [])
                )

            steps.append({
                "step": "execution",
                "task_id": sub_task.task_id,
                "status": exec_task.status,
                "consensus_score": exec_task.result.get("consensus_score", 0) if exec_task.result else 0,
            })

        # Aggregate results
        final_content = self._aggregate_results(execution_results)
        avg_consensus = self._calculate_avg_consensus(execution_results)

        # Step 3: Validation
        validate_task = AgentTask(
            task_id=f"{workflow_id}-validate",
            description="Validate execution results",
            input_data={
                "content": final_content,
                "original_task": task_description,
                "consensus_score": avg_consensus,
            },
        )
        validate_task = await self.validator.execute(validate_task)
        steps.append({
            "step": "validation",
            "status": validate_task.status,
            "result": validate_task.result,
        })

        is_verified = (
            validate_task.result.get("validation", {}).get("is_valid", False)
            if validate_task.result
            else False
        )

        # Step 4: Auditing
        audit_task = AgentTask(
            task_id=f"{workflow_id}-audit",
            description="Generate audit trail",
            input_data={
                "original_task_id": workflow_id,
                "execution_data": {"steps": [er.to_dict() for er in execution_results]},
                "miner_responses": miner_responses_all,
                "consensus_info": {"average_score": avg_consensus},
                "validation_result": validate_task.result or {},
            },
        )
        audit_task = await self.auditor.execute(audit_task)
        steps.append({
            "step": "auditing",
            "status": audit_task.status,
            "bundle_id": audit_task.result.get("bundle_id") if audit_task.result else None,
        })

        evidence_bundle_id = (
            audit_task.result.get("bundle_id") if audit_task.result else None
        )

        execution_time = (time.perf_counter() - start_time) * 1000

        return WorkflowResult(
            workflow_id=workflow_id,
            original_task=task_description,
            final_output=final_content,
            is_verified=is_verified,
            consensus_score=avg_consensus,
            evidence_bundle_id=evidence_bundle_id,
            execution_time_ms=execution_time,
            steps=steps,
        )

    def _aggregate_results(self, execution_results: list[AgentTask]) -> str:
        """Aggregate results from multiple execution tasks."""
        contents = []
        for task in execution_results:
            if task.result and task.status == "completed":
                content = task.result.get("content", "")
                if content:
                    contents.append(content)

        if not contents:
            return "No results generated"

        if len(contents) == 1:
            return contents[0]

        # Multiple results: combine them
        return "\n\n---\n\n".join(contents)

    def _calculate_avg_consensus(self, execution_results: list[AgentTask]) -> float:
        """Calculate average consensus score across executions."""
        scores = []
        for task in execution_results:
            if task.result:
                score = task.result.get("consensus_score", 0)
                if score > 0:
                    scores.append(score)

        return sum(scores) / len(scores) if scores else 0.0

    def _create_failed_result(
        self,
        workflow_id: str,
        task_description: str,
        reason: str,
        error: str | None,
        start_time: float,
        steps: list,
    ) -> WorkflowResult:
        """Create a failed workflow result."""
        import time

        return WorkflowResult(
            workflow_id=workflow_id,
            original_task=task_description,
            final_output=f"Workflow failed: {reason}. Error: {error}",
            is_verified=False,
            consensus_score=0.0,
            evidence_bundle_id=None,
            execution_time_ms=(time.perf_counter() - start_time) * 1000,
            steps=steps,
        )

    def get_evidence_bundle(self, bundle_id: str) -> EvidenceBundle | None:
        """Retrieve an evidence bundle by ID."""
        return self.auditor.get_evidence_bundle(bundle_id)
