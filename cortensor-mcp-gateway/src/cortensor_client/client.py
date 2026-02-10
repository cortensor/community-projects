"""Cortensor client with Mock mode support."""

from __future__ import annotations

import asyncio
import hashlib
import random
import time
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator

import aiohttp
import structlog

from .config import CortensorConfig
from .models import (
    ConsensusResult,
    CortensorResponse,
    DelegateRequest,
    InferenceRequest,
    MinerResponse,
    PromptType,
    SessionLog,
    SessionLogEntry,
    ValidateRequest,
    ValidationResult,
)

logger = structlog.get_logger()


class CortensorClient:
    """Client for interacting with Cortensor Network.

    Supports both real API calls and mock mode for development.
    Uses /delegate and /validate endpoints for competitive hackathon submission.
    """

    def __init__(self, config: CortensorConfig | None = None):
        self.config = config or CortensorConfig.from_env()
        self._session: aiohttp.ClientSession | None = None
        self._session_log: SessionLog | None = None
        self._mock_models = [
            "DeepSeek-R1-Distill-Llama-8B",
            "Meta-Llama-3.1-8B-Instruct",
            "Qwen2.5-7B-Instruct",
            "Mistral-7B-Instruct-v0.3",
        ]

    async def __aenter__(self) -> CortensorClient:
        if not self.config.mock_mode:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                }
            )
        # Initialize session log
        self._session_log = SessionLog(
            session_id=self.config.session_id,
            session_name=f"hackathon-session-{self.config.session_id}",
            created_at=datetime.now(timezone.utc),
        )
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    def get_session_log(self) -> SessionLog | None:
        """Get the current session log for export."""
        return self._session_log

    def export_session_log(self, filepath: str | None = None) -> str:
        """Export session log as JSON. Optionally save to file."""
        if not self._session_log:
            return "{}"
        json_str = self._session_log.export_json()
        if filepath:
            with open(filepath, "w") as f:
                f.write(json_str)
        return json_str

    async def delegate(
        self,
        prompt: str,
        *,
        prompt_type: PromptType = PromptType.RAW,
        stream: bool = False,
        timeout: int | None = None,
        max_tokens: int | None = None,
        k_redundancy: int = 3,
    ) -> CortensorResponse:
        """Delegate task to Cortensor miners via /delegate endpoint.

        This is the preferred method for hackathon submissions as it
        explicitly uses the delegation pattern recommended by Cortensor.

        Args:
            prompt: The prompt to send for inference.
            prompt_type: Type of prompt (RAW or CHAT).
            stream: Whether to stream the response.
            timeout: Request timeout in seconds.
            max_tokens: Maximum tokens in response.
            k_redundancy: Number of miners for redundant inference.

        Returns:
            CortensorResponse with aggregated results and consensus info.
        """
        request = DelegateRequest(
            prompt=prompt,
            session_id=self.config.session_id,
            prompt_type=prompt_type,
            stream=stream,
            timeout=timeout or self.config.timeout,
            max_tokens=max_tokens or self.config.max_tokens,
            k_redundancy=k_redundancy,
        )

        if self.config.mock_mode:
            return await self._mock_delegate(request)
        return await self._real_delegate(request)

    async def _real_delegate(self, request: DelegateRequest) -> CortensorResponse:
        """Execute real delegation via /delegate endpoint."""
        if not self._session:
            raise RuntimeError("Client session not initialized. Use 'async with' context.")

        start_time = time.perf_counter()
        url = f"{self.config.router_url}/api/v1/delegate"

        try:
            async with self._session.post(url, json=request.to_payload()) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"Cortensor delegate error {resp.status}: {error_text}")

                data = await resp.json()

            total_latency = (time.perf_counter() - start_time) * 1000

            # Parse miner responses from API response
            miner_responses = self._parse_miner_responses(data)
            consensus = self._calculate_consensus(miner_responses)

            response = CortensorResponse(
                task_id=data.get("task_id", str(uuid.uuid4())),
                content=consensus.majority_response,
                miner_responses=miner_responses,
                consensus=consensus,
                total_latency_ms=total_latency,
            )

            # Log the delegation
            if self._session_log:
                self._session_log.add_entry(SessionLogEntry(
                    operation="delegate",
                    timestamp=datetime.now(timezone.utc),
                    request=request.to_payload(),
                    response=response.to_dict(),
                    success=True,
                    latency_ms=total_latency,
                    task_id=response.task_id,
                ))

            return response

        except Exception as e:
            # Log failed delegation
            if self._session_log:
                self._session_log.add_entry(SessionLogEntry(
                    operation="delegate",
                    timestamp=datetime.now(timezone.utc),
                    request=request.to_payload(),
                    response={"error": str(e)},
                    success=False,
                    latency_ms=(time.perf_counter() - start_time) * 1000,
                ))
            raise

    async def _mock_delegate(self, request: DelegateRequest) -> CortensorResponse:
        """Generate mock delegate response for development."""
        start_time = time.perf_counter()
        task_id = f"task-{uuid.uuid4().hex[:12]}"

        # Simulate network delay
        await asyncio.sleep(random.uniform(0.5, 2.0))

        # Generate mock miner responses based on k_redundancy
        num_miners = request.k_redundancy
        miner_responses = []
        base_response = self._generate_mock_response(request.prompt)

        for i in range(num_miners):
            if i < num_miners - 1 or random.random() > 0.2:
                content = base_response
            else:
                content = self._generate_mock_response(request.prompt, variant=True)

            miner_responses.append(
                MinerResponse(
                    miner_id=f"mock-miner-{i:03d}",
                    content=content,
                    latency_ms=random.uniform(100, 500),
                    model=random.choice(self._mock_models),
                )
            )

        total_latency = (time.perf_counter() - start_time) * 1000
        consensus = self._calculate_consensus(miner_responses)

        logger.info(
            "mock_delegate_complete",
            task_id=task_id,
            num_miners=num_miners,
            consensus_score=consensus.score,
        )

        response = CortensorResponse(
            task_id=task_id,
            content=consensus.majority_response,
            miner_responses=miner_responses,
            consensus=consensus,
            total_latency_ms=total_latency,
        )

        # Log the delegation
        if self._session_log:
            self._session_log.add_entry(SessionLogEntry(
                operation="delegate",
                timestamp=datetime.now(timezone.utc),
                request=request.to_payload(),
                response=response.to_dict(),
                success=True,
                latency_ms=total_latency,
                task_id=task_id,
            ))

        return response

    async def validate(
        self,
        task_id: str,
        miner_address: str,
        result_data: str,
        *,
        k_redundancy: int = 3,
    ) -> ValidationResult:
        """Validate task results via /validate endpoint (PoI + PoUW).

        This method uses k-redundant re-inference to verify that the
        result is correct and produces a signed attestation.

        Args:
            task_id: The task ID to validate.
            miner_address: Address of the miner that produced the result.
            result_data: The result data to validate.
            k_redundancy: Number of miners for redundant validation.

        Returns:
            ValidationResult with attestation and confidence score.
        """
        # Convert task_id to int if needed
        task_id_int = int(task_id.split("-")[-1], 16) if "-" in task_id else int(task_id)

        request = ValidateRequest(
            session_id=self.config.session_id,
            task_id=task_id_int,
            miner_address=miner_address,
            result_data=result_data,
            k_redundancy=k_redundancy,
        )

        if self.config.mock_mode:
            return await self._mock_validate(request, task_id)
        return await self._real_validate(request, task_id)

    async def _real_validate(self, request: ValidateRequest, original_task_id: str) -> ValidationResult:
        """Execute real validation via /validate endpoint."""
        if not self._session:
            raise RuntimeError("Client session not initialized. Use 'async with' context.")

        start_time = time.perf_counter()
        url = f"{self.config.router_url}/api/v1/validate"

        try:
            async with self._session.post(url, json=request.to_payload()) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"Cortensor validate error {resp.status}: {error_text}")

                data = await resp.json()

            total_latency = (time.perf_counter() - start_time) * 1000

            result = ValidationResult(
                task_id=original_task_id,
                is_valid=data.get("is_valid", data.get("valid", False)),
                confidence=data.get("confidence", data.get("score", 0.0)),
                attestation=data.get("attestation"),
                k_miners_validated=data.get("k_miners", request.k_redundancy),
                validation_details=data,
            )

            # Log the validation
            if self._session_log:
                self._session_log.add_entry(SessionLogEntry(
                    operation="validate",
                    timestamp=datetime.now(timezone.utc),
                    request=request.to_payload(),
                    response=result.to_dict(),
                    success=True,
                    latency_ms=total_latency,
                    task_id=original_task_id,
                ))

            return result

        except Exception as e:
            # Log failed validation
            if self._session_log:
                self._session_log.add_entry(SessionLogEntry(
                    operation="validate",
                    timestamp=datetime.now(timezone.utc),
                    request=request.to_payload(),
                    response={"error": str(e)},
                    success=False,
                    latency_ms=(time.perf_counter() - start_time) * 1000,
                    task_id=original_task_id,
                ))
            raise

    async def _mock_validate(self, request: ValidateRequest, original_task_id: str) -> ValidationResult:
        """Generate mock validation response."""
        start_time = time.perf_counter()

        # Simulate validation delay
        await asyncio.sleep(random.uniform(0.3, 1.0))

        # Generate mock attestation (JWS-like format)
        attestation_data = {
            "task_id": original_task_id,
            "session_id": request.session_id,
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "k_miners": request.k_redundancy,
        }
        import json
        import base64
        header = base64.urlsafe_b64encode(b'{"alg":"ES256","typ":"JWT"}').decode().rstrip("=")
        payload = base64.urlsafe_b64encode(json.dumps(attestation_data).encode()).decode().rstrip("=")
        signature = hashlib.sha256(f"{header}.{payload}".encode()).hexdigest()[:64]
        mock_attestation = f"{header}.{payload}.{signature}"

        total_latency = (time.perf_counter() - start_time) * 1000

        result = ValidationResult(
            task_id=original_task_id,
            is_valid=True,
            confidence=random.uniform(0.85, 1.0),
            attestation=mock_attestation,
            k_miners_validated=request.k_redundancy,
            validation_details={
                "method": "k-redundant-poi",
                "eval_version": "v3",
            },
        )

        logger.info(
            "mock_validate_complete",
            task_id=original_task_id,
            is_valid=result.is_valid,
            confidence=result.confidence,
        )

        # Log the validation
        if self._session_log:
            self._session_log.add_entry(SessionLogEntry(
                operation="validate",
                timestamp=datetime.now(timezone.utc),
                request=request.to_payload(),
                response=result.to_dict(),
                success=True,
                latency_ms=total_latency,
                task_id=original_task_id,
            ))

        return result

    async def inference(
        self,
        prompt: str,
        *,
        prompt_type: PromptType = PromptType.RAW,
        stream: bool = False,
        timeout: int | None = None,
        max_tokens: int | None = None,
    ) -> CortensorResponse:
        """Execute inference on Cortensor Network.

        Args:
            prompt: The prompt to send for inference.
            prompt_type: Type of prompt (RAW or CHAT).
            stream: Whether to stream the response.
            timeout: Request timeout in seconds.
            max_tokens: Maximum tokens in response.

        Returns:
            CortensorResponse with aggregated results and consensus info.
        """
        request = InferenceRequest(
            prompt=prompt,
            session_id=self.config.session_id,
            prompt_type=prompt_type,
            stream=stream,
            timeout=timeout or self.config.timeout,
            max_tokens=max_tokens or self.config.max_tokens,
        )

        if self.config.mock_mode:
            return await self._mock_inference(request)
        return await self._real_inference(request)

    async def _real_inference(self, request: InferenceRequest) -> CortensorResponse:
        """Execute real inference via Cortensor Router API."""
        if not self._session:
            raise RuntimeError("Client session not initialized. Use 'async with' context.")

        start_time = time.perf_counter()
        url = f"{self.config.router_url}/api/v1/completions"

        async with self._session.post(url, json=request.to_payload()) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise RuntimeError(f"Cortensor API error {resp.status}: {error_text}")

            data = await resp.json()

        total_latency = (time.perf_counter() - start_time) * 1000

        # Parse miner responses from API response
        miner_responses = self._parse_miner_responses(data)
        consensus = self._calculate_consensus(miner_responses)

        return CortensorResponse(
            task_id=data.get("task_id", str(uuid.uuid4())),
            content=consensus.majority_response,
            miner_responses=miner_responses,
            consensus=consensus,
            total_latency_ms=total_latency,
        )

    async def _mock_inference(self, request: InferenceRequest) -> CortensorResponse:
        """Generate mock inference response for development."""
        start_time = time.perf_counter()
        task_id = str(uuid.uuid4())

        # Simulate network delay
        await asyncio.sleep(random.uniform(0.5, 2.0))

        # Generate mock miner responses
        num_miners = random.randint(3, 5)
        miner_responses = []

        base_response = self._generate_mock_response(request.prompt)

        for i in range(num_miners):
            # Most miners return similar responses (for consensus)
            if i < num_miners - 1 or random.random() > 0.2:
                content = base_response
            else:
                # Occasional divergent response
                content = self._generate_mock_response(request.prompt, variant=True)

            miner_responses.append(
                MinerResponse(
                    miner_id=f"mock-miner-{i:03d}",
                    content=content,
                    latency_ms=random.uniform(100, 500),
                    model=random.choice(self._mock_models),
                )
            )

        total_latency = (time.perf_counter() - start_time) * 1000
        consensus = self._calculate_consensus(miner_responses)

        logger.info(
            "mock_inference_complete",
            task_id=task_id,
            num_miners=num_miners,
            consensus_score=consensus.score,
        )

        return CortensorResponse(
            task_id=task_id,
            content=consensus.majority_response,
            miner_responses=miner_responses,
            consensus=consensus,
            total_latency_ms=total_latency,
        )

    def _generate_mock_response(self, prompt: str, variant: bool = False) -> str:
        """Generate a mock response based on the prompt."""
        # Simple mock responses for testing
        prompt_lower = prompt.lower()

        if "analyze" in prompt_lower or "analysis" in prompt_lower:
            base = "Based on my analysis, the key points are:\n1. The proposal addresses important concerns\n2. Implementation appears feasible\n3. Risks are manageable with proper monitoring"
        elif "summarize" in prompt_lower or "summary" in prompt_lower:
            base = "Summary: The content discusses several key aspects including technical implementation, economic implications, and governance considerations."
        elif "evaluate" in prompt_lower or "assessment" in prompt_lower:
            base = "Evaluation: The approach shows merit with a balanced consideration of trade-offs. Recommended action: proceed with monitoring."
        else:
            base = f"Response to query: {prompt[:50]}...\n\nThis is a mock response demonstrating the Cortensor inference pipeline with multi-miner consensus verification."

        if variant:
            base = f"[Alternative perspective] {base}"

        return base

    def _parse_miner_responses(self, data: dict) -> list[MinerResponse]:
        """Parse miner responses from API response data."""
        responses = []

        # Handle different response formats from Cortensor
        if "responses" in data:
            for r in data["responses"]:
                responses.append(
                    MinerResponse(
                        miner_id=r.get("miner_id", "unknown"),
                        content=r.get("content", r.get("text", "")),
                        latency_ms=r.get("latency_ms", 0),
                        model=r.get("model", "unknown"),
                        metadata=r.get("metadata", {}),
                    )
                )
        elif "content" in data:
            # Single response format
            responses.append(
                MinerResponse(
                    miner_id=data.get("miner_id", "primary"),
                    content=data["content"],
                    latency_ms=data.get("latency_ms", 0),
                    model=data.get("model", "unknown"),
                )
            )

        return responses

    def _calculate_consensus(self, responses: list[MinerResponse]) -> ConsensusResult:
        """Calculate PoI consensus from miner responses."""
        if not responses:
            return ConsensusResult(
                score=0.0,
                agreement_count=0,
                total_miners=0,
                majority_response="",
            )

        # Group responses by content hash (for semantic similarity, use hash of normalized content)
        content_groups: dict[str, list[MinerResponse]] = {}
        for r in responses:
            # Normalize and hash content for grouping
            normalized = r.content.strip().lower()
            content_hash = hashlib.md5(normalized.encode()).hexdigest()[:8]
            if content_hash not in content_groups:
                content_groups[content_hash] = []
            content_groups[content_hash].append(r)

        # Find majority group
        majority_group = max(content_groups.values(), key=len)
        majority_response = majority_group[0].content

        # Find divergent miners
        divergent_miners = []
        for group in content_groups.values():
            if group != majority_group:
                divergent_miners.extend([r.miner_id for r in group])

        agreement_count = len(majority_group)
        total_miners = len(responses)
        score = agreement_count / total_miners if total_miners > 0 else 0.0

        return ConsensusResult(
            score=score,
            agreement_count=agreement_count,
            total_miners=total_miners,
            majority_response=majority_response,
            divergent_miners=divergent_miners,
        )

    async def get_task_status(self, task_id: str) -> dict:
        """Get status of a task by ID."""
        if self.config.mock_mode:
            return {"task_id": task_id, "status": "completed"}

        if not self._session:
            raise RuntimeError("Client session not initialized.")

        url = f"{self.config.router_url}/api/v1/tasks/{task_id}"
        async with self._session.get(url) as resp:
            return await resp.json()

    async def get_miners(self) -> list[dict]:
        """Get list of available miners."""
        if self.config.mock_mode:
            return [
                {"id": f"mock-miner-{i:03d}", "model": m, "status": "online"}
                for i, m in enumerate(self._mock_models)
            ]

        if not self._session:
            raise RuntimeError("Client session not initialized.")

        url = f"{self.config.router_url}/api/v1/miners"
        async with self._session.get(url) as resp:
            return await resp.json()

    async def health_check(self) -> bool:
        """Check if Cortensor Router is healthy."""
        if self.config.mock_mode:
            return True

        if not self._session:
            raise RuntimeError("Client session not initialized.")

        try:
            url = f"{self.config.router_url}/health"
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                return resp.status == 200
        except Exception:
            return False
