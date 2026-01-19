"""Validator Agent - Validates task results and consensus."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .base import AgentTask, BaseAgent
from ..cortensor_client import CortensorClient


@dataclass
class ValidationResult:
    """Result of validation."""

    is_valid: bool
    confidence: float
    issues: list[str]
    recommendations: list[str]


class ValidatorAgent(BaseAgent):
    """Agent responsible for validating execution results."""

    def __init__(self, client: CortensorClient):
        super().__init__("ValidatorAgent", client)

    def get_system_prompt(self) -> str:
        return """You are the Validator Agent in a verifiable AI system.
Your role is to:
1. Verify that task outputs meet quality standards
2. Check for logical consistency
3. Identify potential issues or gaps
4. Assess confidence in the results

Output your validation as JSON:
{
    "is_valid": true/false,
    "confidence": 0.0-1.0,
    "issues": ["list of issues found"],
    "recommendations": ["list of recommendations"]
}

Be rigorous but fair in your assessment."""

    async def execute(self, task: AgentTask) -> AgentTask:
        """Validate a completed task's results."""
        task.status = "in_progress"

        # Get the content to validate from input_data
        content_to_validate = task.input_data.get("content", "")
        original_task_desc = task.input_data.get("original_task", "")
        consensus_score = task.input_data.get("consensus_score", 0)

        prompt = f"""{self.get_system_prompt()}

Original Task: {original_task_desc}

Content to Validate:
{content_to_validate}

Cortensor Consensus Score: {consensus_score}

Validate this output and provide your assessment as JSON:"""

        try:
            response = await self.inference(prompt)
            validation = self._parse_validation(response, consensus_score)

            task.result = {
                "validation": {
                    "is_valid": validation.is_valid,
                    "confidence": validation.confidence,
                    "issues": validation.issues,
                    "recommendations": validation.recommendations,
                },
                "consensus_verified": consensus_score >= 0.66,
            }
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc)

        except Exception as e:
            task.status = "failed"
            task.error = str(e)

        return task

    def _parse_validation(self, response: str, consensus_score: float) -> ValidationResult:
        """Parse validation result from LLM response."""
        import json

        try:
            # Extract JSON from response
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "{" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
            else:
                # Default based on consensus
                return ValidationResult(
                    is_valid=consensus_score >= 0.66,
                    confidence=consensus_score,
                    issues=[],
                    recommendations=[],
                )

            data = json.loads(json_str)
            return ValidationResult(
                is_valid=data.get("is_valid", consensus_score >= 0.66),
                confidence=data.get("confidence", consensus_score),
                issues=data.get("issues", []),
                recommendations=data.get("recommendations", []),
            )

        except json.JSONDecodeError:
            return ValidationResult(
                is_valid=consensus_score >= 0.66,
                confidence=consensus_score,
                issues=["Could not parse validation response"],
                recommendations=[],
            )

    async def validate_consensus(self, miner_responses: list[dict]) -> dict[str, Any]:
        """Validate consensus across miner responses."""
        if not miner_responses:
            return {
                "valid": False,
                "reason": "No miner responses to validate",
            }

        # Check for sufficient miners
        if len(miner_responses) < 2:
            return {
                "valid": False,
                "reason": "Insufficient miners for consensus",
            }

        # Calculate response similarity (simplified)
        # In production, use semantic similarity
        unique_responses = set()
        for mr in miner_responses:
            content = mr.get("content", "")[:100]  # Compare first 100 chars
            unique_responses.add(content)

        agreement_ratio = 1.0 - (len(unique_responses) - 1) / len(miner_responses)

        return {
            "valid": agreement_ratio >= 0.66,
            "agreement_ratio": agreement_ratio,
            "unique_responses": len(unique_responses),
            "total_miners": len(miner_responses),
        }
