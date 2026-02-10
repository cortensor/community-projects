"""Planner Agent - Decomposes complex tasks into sub-tasks."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from .base import AgentTask, BaseAgent
from ..cortensor_client import CortensorClient


class PlannerAgent(BaseAgent):
    """Agent responsible for task decomposition and planning."""

    def __init__(self, client: CortensorClient):
        super().__init__("PlannerAgent", client)

    def get_system_prompt(self) -> str:
        return """You are the Planner Agent in a verifiable AI system.
Your role is to:
1. Analyze complex tasks and break them into clear, actionable sub-tasks
2. Identify dependencies between sub-tasks
3. Estimate the type of analysis needed for each sub-task

Output your plan as JSON with the following structure:
{
    "goal": "overall goal description",
    "sub_tasks": [
        {
            "id": "task_1",
            "description": "what needs to be done",
            "type": "analysis|extraction|synthesis|validation",
            "dependencies": [],
            "priority": 1
        }
    ],
    "execution_order": ["task_1", "task_2", ...]
}

Be concise and practical. Focus on actionable steps."""

    async def execute(self, task: AgentTask) -> AgentTask:
        """Decompose a task into sub-tasks."""
        task.status = "in_progress"

        prompt = f"""{self.get_system_prompt()}

Task to decompose:
{task.description}

Input context:
{json.dumps(task.input_data, indent=2)}

Output the plan as JSON:"""

        try:
            response = await self.inference(prompt)

            # Parse the response as JSON
            plan = self._parse_plan(response)

            task.result = {
                "plan": plan,
                "sub_tasks": self._create_sub_tasks(plan, task.task_id),
            }
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc)

        except Exception as e:
            task.status = "failed"
            task.error = str(e)

        return task

    def _parse_plan(self, response: str) -> dict:
        """Parse the plan from LLM response."""
        # Try to extract JSON from the response
        try:
            # Look for JSON block in response
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "{" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
            else:
                # Fallback: create a simple plan
                return {
                    "goal": "Execute the given task",
                    "sub_tasks": [
                        {
                            "id": "task_1",
                            "description": "Analyze and respond",
                            "type": "analysis",
                            "dependencies": [],
                            "priority": 1,
                        }
                    ],
                    "execution_order": ["task_1"],
                }

            return json.loads(json_str)

        except json.JSONDecodeError:
            # Fallback plan
            return {
                "goal": "Execute the given task",
                "sub_tasks": [
                    {
                        "id": "task_1",
                        "description": response[:200],
                        "type": "analysis",
                        "dependencies": [],
                        "priority": 1,
                    }
                ],
                "execution_order": ["task_1"],
            }

    def _create_sub_tasks(self, plan: dict, parent_id: str) -> list[AgentTask]:
        """Create AgentTask objects from plan."""
        sub_tasks = []
        for st in plan.get("sub_tasks", []):
            sub_tasks.append(
                AgentTask(
                    task_id=str(uuid4()),
                    description=st.get("description", ""),
                    input_data={
                        "type": st.get("type", "analysis"),
                        "dependencies": st.get("dependencies", []),
                        "priority": st.get("priority", 1),
                    },
                    parent_task_id=parent_id,
                )
            )
        return sub_tasks
