"""Governance Analyst Agent using Cortensor Network.

This agent analyzes governance proposals by delegating inference to
Cortensor's decentralized network and validating results.
"""

import json
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .client import CortensorMCPClient, ToolResult

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Result of governance analysis."""
    task_id: str
    proposal: str
    analysis: str
    validation_score: float | None = None
    validated: bool = False
    miner_info: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class EvidenceBundle:
    """Cryptographic evidence bundle for audit trail."""
    bundle_id: str
    analysis_result: AnalysisResult
    cortensor_session_id: int | None
    raw_responses: list[dict]
    validation_responses: list[dict]
    integrity_hash: str

    def to_dict(self) -> dict:
        return {
            "bundle_id": self.bundle_id,
            "analysis": {
                "task_id": self.analysis_result.task_id,
                "proposal": self.analysis_result.proposal,
                "analysis": self.analysis_result.analysis,
                "validation_score": self.analysis_result.validation_score,
                "validated": self.analysis_result.validated,
                "timestamp": self.analysis_result.timestamp
            },
            "cortensor_session_id": self.cortensor_session_id,
            "raw_responses": self.raw_responses,
            "validation_responses": self.validation_responses,
            "integrity_hash": self.integrity_hash
        }


class GovernanceAgent:
    """Agent for analyzing DeFi governance proposals using Cortensor.

    Workflow:
    1. Connect to Cortensor MCP server
    2. Create session with multiple nodes
    3. Delegate analysis task via cortensor_completions
    4. Validate results via cortensor_validate
    5. Generate evidence bundle with integrity hash
    """

    ANALYSIS_PROMPT_TEMPLATE = """Analyze the following DeFi governance proposal:

{proposal}

Provide a structured analysis covering:
1. Technical Feasibility - Can this be implemented? What are the technical challenges?
2. Economic Impact - How will this affect token holders, liquidity, and protocol economics?
3. Security Considerations - Are there potential attack vectors or risks?
4. Governance Implications - How does this change power dynamics?
5. Recommendation - Support, Oppose, or Abstain with reasoning.

Be specific and cite relevant precedents if applicable."""

    def __init__(self, client: CortensorMCPClient | None = None):
        self.client = client or CortensorMCPClient()
        self._raw_responses: list[dict] = []
        self._validation_responses: list[dict] = []

    def connect(self, session_name: str = "governance-analysis",
                min_nodes: int = 2, max_nodes: int = 5) -> bool:
        """Connect to Cortensor and create session."""
        try:
            self.client.connect()
            result = self.client.create_session(
                name=session_name,
                min_nodes=min_nodes,
                max_nodes=max_nodes,
                validator_nodes=1
            )
            if result.success:
                logger.info(f"Session created: {result.data}")
                return True
            else:
                logger.error(f"Failed to create session: {result.error}")
                return False
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def analyze_proposal(self, proposal: str, validate: bool = True) -> AnalysisResult:
        """Analyze a governance proposal using Cortensor network.

        Args:
            proposal: The governance proposal text to analyze
            validate: Whether to validate results via cortensor_validate

        Returns:
            AnalysisResult with analysis and optional validation
        """
        self._raw_responses = []
        self._validation_responses = []

        # Generate task ID
        task_id = hashlib.sha256(
            f"{proposal}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        # Build prompt
        prompt = self.ANALYSIS_PROMPT_TEMPLATE.format(proposal=proposal)

        # Delegate to Cortensor
        logger.info(f"Delegating analysis task: {task_id}")
        completion_result = self.client.completions(prompt, max_tokens=2048)

        if not completion_result.success:
            logger.error(f"Completion failed: {completion_result.error}")
            return AnalysisResult(
                task_id=task_id,
                proposal=proposal,
                analysis=f"Analysis failed: {completion_result.error}",
                validated=False
            )

        self._raw_responses.append(completion_result.data)

        # Extract analysis from response
        analysis_text = self._extract_analysis(completion_result.data)

        result = AnalysisResult(
            task_id=task_id,
            proposal=proposal,
            analysis=analysis_text,
            miner_info=completion_result.data.get("miner_info", {})
        )

        # Validate if requested
        if validate:
            validation = self._validate_result(result, completion_result.data)
            result.validation_score = validation.get("score")
            result.validated = validation.get("validated", False)
            self._validation_responses.append(validation)

        return result

    def _extract_analysis(self, response_data: dict) -> str:
        """Extract analysis text from Cortensor response."""
        if "completion" in response_data:
            return response_data["completion"]
        if "text" in response_data:
            return response_data["text"]
        if "content" in response_data:
            return response_data["content"]
        return str(response_data)

    def _validate_result(self, result: AnalysisResult, raw_response: dict) -> dict:
        """Validate analysis result via cortensor_validate."""
        try:
            # Get task info from response
            cortensor_task_id = raw_response.get("task_id", 0)
            miner_address = raw_response.get("miner_address", "")

            if not cortensor_task_id or not miner_address:
                logger.warning("Missing task_id or miner_address for validation")
                return {"validated": False, "reason": "missing_info"}

            validation_result = self.client.validate(
                task_id=cortensor_task_id,
                miner_address=miner_address,
                result_data=result.analysis
            )

            if validation_result.success:
                return {
                    "validated": True,
                    "score": validation_result.data.get("score", 1.0),
                    "details": validation_result.data
                }
            else:
                return {
                    "validated": False,
                    "reason": validation_result.error
                }

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {"validated": False, "reason": str(e)}

    def generate_evidence_bundle(self, result: AnalysisResult) -> EvidenceBundle:
        """Generate cryptographic evidence bundle for audit trail."""
        bundle_id = f"eb-{result.task_id}"

        # Compute integrity hash
        hash_input = json.dumps({
            "bundle_id": bundle_id,
            "task_id": result.task_id,
            "proposal": result.proposal,
            "analysis": result.analysis,
            "validation_score": result.validation_score,
            "timestamp": result.timestamp,
            "raw_responses": self._raw_responses,
            "validation_responses": self._validation_responses
        }, sort_keys=True)

        integrity_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        return EvidenceBundle(
            bundle_id=bundle_id,
            analysis_result=result,
            cortensor_session_id=self.client._session.cortensor_session_id if self.client._session else None,
            raw_responses=self._raw_responses,
            validation_responses=self._validation_responses,
            integrity_hash=integrity_hash
        )

    def close(self):
        """Close connection."""
        if self.client:
            self.client.close()


def run_analysis(proposal: str, validate: bool = True) -> tuple[AnalysisResult, EvidenceBundle]:
    """Convenience function to run a full analysis workflow.

    Args:
        proposal: Governance proposal to analyze
        validate: Whether to validate results

    Returns:
        Tuple of (AnalysisResult, EvidenceBundle)
    """
    agent = GovernanceAgent()

    try:
        if not agent.connect():
            raise RuntimeError("Failed to connect to Cortensor")

        result = agent.analyze_proposal(proposal, validate=validate)
        evidence = agent.generate_evidence_bundle(result)

        return result, evidence

    finally:
        agent.close()
