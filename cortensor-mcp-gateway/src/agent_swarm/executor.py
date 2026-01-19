"""Executor Agent - Executes individual tasks through Cortensor."""

from __future__ import annotations

from datetime import datetime, timezone

from .base import AgentTask, BaseAgent
from ..cortensor_client import CortensorClient, CortensorResponse


class ExecutorAgent(BaseAgent):
    """Agent responsible for executing tasks via Cortensor inference."""

    def __init__(self, client: CortensorClient):
        super().__init__("ExecutorAgent", client)
        self._last_response: CortensorResponse | None = None

    def get_system_prompt(self) -> str:
        return """You are the Executor Agent in a verifiable AI system.
Your role is to execute specific tasks and produce clear, actionable outputs.

Guidelines:
1. Focus on the specific task given
2. Be thorough but concise
3. Structure your output clearly
4. If the task requires analysis, provide evidence-based reasoning
5. If the task requires synthesis, combine information logically

Always aim for accuracy and clarity."""

    async def execute(self, task: AgentTask) -> AgentTask:
        """Execute a single task through Cortensor."""
        task.status = "in_progress"

        task_type = task.input_data.get("type", "analysis")

        prompt = f"""{self.get_system_prompt()}

Task Type: {task_type}
Task Description: {task.description}

Additional Context:
{self._format_context(task.input_data)}

Execute this task and provide your output:"""

        try:
            # Execute through Cortensor for verifiable inference
            response = await self.client.inference(prompt)
            self._last_response = response

            task.result = {
                "content": response.content,
                "cortensor_task_id": response.task_id,
                "consensus_score": response.consensus.score,
                "is_verified": response.is_verified,
                "num_miners": response.consensus.total_miners,
                "miner_responses": [
                    {
                        "miner_id": mr.miner_id,
                        "model": mr.model,
                        "latency_ms": mr.latency_ms,
                    }
                    for mr in response.miner_responses
                ],
            }
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc)

        except Exception as e:
            task.status = "failed"
            task.error = str(e)

        return task

    def _format_context(self, input_data: dict) -> str:
        """Format input data as context string."""
        context_parts = []
        for key, value in input_data.items():
            if key not in ("type", "dependencies", "priority"):
                context_parts.append(f"- {key}: {value}")
        return "\n".join(context_parts) if context_parts else "No additional context"

    def get_last_response(self) -> CortensorResponse | None:
        """Get the last Cortensor response for auditing."""
        return self._last_response
