"""
Xea Governance Oracle - Miner Client [DEPRECATED]

DEPRECATION WARNING:
This module contains legacy mock/simulated miner logic.
It is strictly FORBIDDEN for use in production validation paths.
All real validation must go through `app.cortensor_client`.

Abstract and concrete implementations for communicating with decentralized inference miners.
"""

import asyncio
import hashlib
import json
import logging
import random
import time
import uuid
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

import httpx

from app.config import settings
from app.schemas import Claim, MinerResponse, MinerScores

logger = logging.getLogger(__name__)


# ============================================================================
# PoUW Rubric for miner requests
# ============================================================================

POUW_RUBRIC = [
    {"id": "accuracy", "desc": "0-1", "weight": 0.4},
    {"id": "omission_risk", "desc": "0-1", "weight": 0.3},
    {"id": "evidence_quality", "desc": "0-1", "weight": 0.2},
    {"id": "governance_relevance", "desc": "0-1", "weight": 0.1},
]


def compute_composite_score(scores: Dict[str, float]) -> float:
    """Compute composite PoUW score from individual scores."""
    weights = {r["id"]: r["weight"] for r in POUW_RUBRIC}
    return sum(weights.get(k, 0) * v for k, v in scores.items() if k in weights)


def build_miner_request_payload(
    claim: Claim,
    proposal_hash: str,
    demo_mode: bool = True,
) -> Dict[str, Any]:
    """
    Build the exact JSON payload to send to miners.
    
    Args:
        claim: The claim to validate
        proposal_hash: Hash of the proposal
        demo_mode: Whether this is a demo request
        
    Returns:
        Miner request payload dict
    """
    request_id = str(uuid.uuid4())
    
    return {
        "request_id": request_id,
        "proposal_hash": proposal_hash,
        "claim": {
            "id": claim.id,
            "text": claim.text,
            "type": claim.type,
        },
        "tasks": [
            {
                "id": "t1",
                "question": f"Verify the following claim: {claim.text}. Is it supported, disputed, or unknown based on the proposal and linked artifacts? Answer in JSON with verdict and supporting evidence lines.",
                "rubric": POUW_RUBRIC,
            }
        ],
        "meta": {"demo_mode": demo_mode},
    }


# ============================================================================
# Abstract Miner Client
# ============================================================================

class MinerClient(ABC):
    """Abstract base class for miner clients."""
    
    @abstractmethod
    async def validate_claim(
        self,
        claim: Claim,
        proposal_hash: str,
        rubric: Optional[List[Dict]] = None,
    ) -> MinerResponse:
        """
        Send claim to miner for validation.
        
        Args:
            claim: Claim to validate
            proposal_hash: Hash of the proposal
            rubric: Optional custom rubric (defaults to POUW_RUBRIC)
            
        Returns:
            MinerResponse with verdict and scores
        """
        pass
    
    @abstractmethod
    def get_miner_id(self) -> str:
        """Get the miner's unique identifier."""
        pass


# ============================================================================
# Mock Miner Client
# ============================================================================

class MockMinerClient(MinerClient):
    """
    Mock miner client for local development and testing.
    
    Provides deterministic, repeatable responses based on claim content.
    """
    
    def __init__(self, miner_id: Optional[str] = None, seed: Optional[int] = None):
        """
        Initialize mock miner.
        
        Args:
            miner_id: Custom miner ID or auto-generated
            seed: Random seed for deterministic responses
        """
        self.miner_id = miner_id or f"mock_miner_{uuid.uuid4().hex[:8]}"
        self.seed = seed
        self._rng = random.Random(seed)
    
    def get_miner_id(self) -> str:
        return self.miner_id
    
    def _compute_deterministic_embedding(self, text: str, dims: int = 64) -> List[float]:
        """
        Compute a deterministic embedding for repeatability.
        
        Uses a simple hash-based approach for mock purposes.
        In production, use sentence-transformers or similar.
        """
        # Create deterministic embedding from text hash
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        embedding = []
        for i in range(dims):
            # Use different parts of hash to generate each dimension
            # Properly cycle through the 32-character hex string
            idx = (i * 2) % 30  # 30 to ensure we always have 2 chars
            chunk = text_hash[idx:idx + 2]
            value = (int(chunk, 16) / 255.0) * 2 - 1  # Normalize to [-1, 1]
            embedding.append(round(value, 4))
        
        return embedding
    
    def _determine_verdict(self, claim: Claim) -> str:
        """
        Determine verdict based on claim content heuristics.
        
        - Claims with canonical numbers tend to be "supported"
        - Claims with "risk", "unclear", "uncertain" may be "disputed"
        - Otherwise random with bias toward "supported"
        """
        text_lower = claim.text.lower()
        
        # If claim has numeric canonical values -> likely supported
        if claim.canonical and claim.canonical.numbers:
            if self._rng.random() < 0.85:
                return "supported"
        
        # Check for uncertainty markers
        uncertainty_markers = ["risk", "unclear", "uncertain", "maybe", "might", "potential"]
        has_uncertainty = any(marker in text_lower for marker in uncertainty_markers)
        
        if has_uncertainty:
            roll = self._rng.random()
            if roll < 0.4:
                return "disputed"
            elif roll < 0.6:
                return "unknown"
            else:
                return "supported"
        
        # Default behavior - bias toward supported
        roll = self._rng.random()
        if roll < 0.7:
            return "supported"
        elif roll < 0.85:
            return "unknown"
        else:
            return "disputed"
    
    def _generate_scores(self, verdict: str, claim: Claim) -> Dict[str, float]:
        """Generate PoUW scores based on verdict and claim."""
        base_accuracy = {
            "supported": 0.85,
            "disputed": 0.70,
            "unknown": 0.50,
        }.get(verdict, 0.6)
        
        # Add variance
        accuracy = min(1.0, max(0.0, base_accuracy + self._rng.uniform(-0.1, 0.1)))
        
        # Generate other scores
        omission_risk = self._rng.uniform(0.05, 0.25)
        evidence_quality = self._rng.uniform(0.6, 0.95)
        governance_relevance = self._rng.uniform(0.7, 0.95)
        
        scores = {
            "accuracy": round(accuracy, 3),
            "omission_risk": round(omission_risk, 3),
            "evidence_quality": round(evidence_quality, 3),
            "governance_relevance": round(governance_relevance, 3),
        }
        scores["composite"] = round(compute_composite_score(scores), 3)
        
        return scores
    
    def _generate_rationale(self, claim: Claim, verdict: str) -> str:
        """Generate a mock rationale for the verdict."""
        rationales = {
            "supported": [
                f"The claim '{claim.text[:50]}...' is supported by available data.",
                f"Verified: numerical values in the claim match known sources.",
                f"Cross-referenced claim content with on-chain data. Claim is accurate.",
            ],
            "disputed": [
                f"The claim '{claim.text[:50]}...' contains inaccuracies.",
                f"Evidence suggests the stated values may be incorrect.",
                f"Unable to verify claim accuracy - conflicting data sources.",
            ],
            "unknown": [
                f"Insufficient data to verify claim '{claim.text[:50]}...'",
                f"No authoritative sources found to confirm or deny this claim.",
                f"Claim requires additional context for verification.",
            ],
        }
        
        options = rationales.get(verdict, rationales["unknown"])
        return self._rng.choice(options)
    
    def _generate_evidence_links(self, claim: Claim, verdict: str) -> List[str]:
        """Generate mock evidence links."""
        if verdict == "unknown":
            return []
        
        links = []
        if claim.canonical and claim.canonical.addresses:
            for addr in claim.canonical.addresses[:2]:
                links.append(f"https://etherscan.io/address/{addr}")
        
        links.append(f"ipfs://Qm{hashlib.md5(claim.text.encode()).hexdigest()[:40]}")
        
        return links
    
    async def validate_claim(
        self,
        claim: Claim,
        proposal_hash: str,
        rubric: Optional[List[Dict]] = None,
    ) -> MinerResponse:
        """Validate claim using mock heuristics."""
        # Simulate network latency
        await asyncio.sleep(self._rng.uniform(0.1, 0.5))
        
        # Determine verdict
        verdict = self._determine_verdict(claim)
        
        # Map verdict to schema values
        verdict_map = {
            "supported": "verified",
            "disputed": "refuted",
            "unknown": "unverifiable",
        }
        schema_verdict = verdict_map.get(verdict, "unverifiable")
        
        # Generate scores
        scores_dict = self._generate_scores(verdict, claim)
        scores = MinerScores(**scores_dict)
        
        # Generate embedding
        embedding = self._compute_deterministic_embedding(claim.text)
        
        # Generate rationale and evidence
        rationale = self._generate_rationale(claim, verdict)
        evidence_links = self._generate_evidence_links(claim, verdict)
        
        return MinerResponse(
            miner_id=self.miner_id,
            claim_id=claim.id,
            verdict=schema_verdict,
            rationale=rationale,
            evidence_links=evidence_links,
            embedding=embedding,
            scores=scores,
        )


# ============================================================================
# Cortensor Router Miner Client (Scaffold)
# ============================================================================

class CortensorRouterMinerClient(MinerClient):
    """
    Client for interacting with Cortensor Router API.
    
    This is a scaffold implementation with TODOs for integrating
    with the actual Cortensor Router SDK/REST API.
    """
    
    def __init__(
        self,
        router_url: Optional[str] = None,
        api_key: Optional[str] = None,
        miner_id: Optional[str] = None,
    ):
        """
        Initialize Cortensor router client.
        
        Args:
            router_url: Cortensor router URL
            api_key: API key for authentication
            miner_id: Specific miner ID to use, or None for router selection
        """
        self.router_url = router_url or settings.cortensor_router_url
        self.api_key = api_key
        self._miner_id = miner_id or f"cortensor_{uuid.uuid4().hex[:8]}"
        self.http_client: Optional[httpx.AsyncClient] = None
        
        # Retry settings
        self.max_retries = settings.max_retries
        self.timeout = settings.miner_timeout_seconds
    
    def get_miner_id(self) -> str:
        return self._miner_id
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers=self._build_headers(),
            )
        return self.http_client
    
    def _build_headers(self) -> Dict[str, str]:
        """Build request headers."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Xea-Governance-Oracle/0.1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    async def _make_request_with_retry(
        self,
        method: str,
        url: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Make HTTP request with exponential backoff retry.
        
        - 5xx errors: retry with backoff
        - 4xx errors: log and return error
        - Timeout: retry
        """
        client = await self._get_client()
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.time()
                
                if method.upper() == "POST":
                    response = await client.post(url, json=payload)
                else:
                    response = await client.get(url)
                
                elapsed = time.time() - start_time
                
                logger.info(
                    "Cortensor request",
                    extra={
                        "url": url,
                        "method": method,
                        "status": response.status_code,
                        "elapsed_ms": round(elapsed * 1000),
                        "attempt": attempt + 1,
                    }
                )
                
                if response.status_code >= 500:
                    # Server error - retry
                    last_error = f"Server error: {response.status_code}"
                    if attempt < self.max_retries:
                        backoff = (2 ** attempt) + random.uniform(0, 1)
                        await asyncio.sleep(backoff)
                        continue
                    raise httpx.HTTPStatusError(
                        last_error, request=response.request, response=response
                    )
                
                elif response.status_code >= 400:
                    # Client error - log and return error response
                    logger.warning(
                        "Cortensor client error",
                        extra={
                            "status": response.status_code,
                            "body": response.text[:500],
                        }
                    )
                    return {"error": True, "status": response.status_code, "verdict": "unknown"}
                
                return response.json()
                
            except httpx.TimeoutException as e:
                last_error = f"Timeout: {e}"
                logger.warning(f"Request timeout (attempt {attempt + 1})", extra={"error": str(e)})
                if attempt < self.max_retries:
                    backoff = (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(backoff)
                    continue
                    
            except httpx.RequestError as e:
                last_error = f"Request error: {e}"
                logger.error(f"Request failed", extra={"error": str(e)})
                if attempt < self.max_retries:
                    backoff = (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(backoff)
                    continue
        
        # All retries exhausted
        logger.error(f"All retries exhausted: {last_error}")
        return {"error": True, "message": last_error, "verdict": "unknown"}
    
    async def validate_claim(
        self,
        claim: Claim,
        proposal_hash: str,
        rubric: Optional[List[Dict]] = None,
    ) -> MinerResponse:
        """
        Validate claim through Cortensor Router using Route/Poll pattern.
        """
        # If no router configured, fallback to mock (safety)
        if not self.router_url:
            logger.warning("Cortensor router URL not configured, falling back to mock")
            mock_client = MockMinerClient(miner_id=self._miner_id)
            return await mock_client.validate_claim(claim, proposal_hash, rubric)

        # 1. Build Payload
        # We use a UUID for the client-side request ID, but the Router will also assign a task ID
        payload = build_miner_request_payload(claim, proposal_hash, demo_mode=True)
        
        # 2. Dispatch Task (POST /route)
        route_url = f"{self.router_url}/route"
        dispatch_response = await self._make_request_with_retry("POST", route_url, payload)
        
        if dispatch_response.get("error"):
            return self._create_error_response(claim, f"Dispatch failed: {dispatch_response.get('message')}")
            
        task_id = dispatch_response.get("task_id") or dispatch_response.get("request_id")
        if not task_id:
            return self._create_error_response(claim, "Router did not return task_id")
            
        # 3. Poll for Results (GET /status/{task_id})
        status_url = f"{self.router_url}/status/{task_id}"
        start_time = time.time()
        
        while (time.time() - start_time) < self.timeout:
            status_response = await self._make_request_with_retry("GET", status_url, {})
            
            if status_response.get("error"):
                logger.warning(f"Poll error for task {task_id}: {status_response.get('message')}")
                # Continue polling if it's just a transient error, or break if fatal?
                # _make_request_with_retry already handles transient errors.
                # If it returns error here, it's likely 4xx or persistent 5xx.
                return self._create_error_response(claim, f"Poll failed: {status_response.get('message')}")
            
            status = status_response.get("status")
            if status == "completed":
                # Task done! Map result
                return self._map_router_response(claim, status_response, self._miner_id)
            
            elif status in ("failed", "error"):
                return self._create_error_response(claim, f"Router task failed: {status_response.get('message')}")
            
            # Still pending/processing
            await asyncio.sleep(1.0)
            
        # 4. Timeout
        return self._create_error_response(claim, "Validation timed out waiting for Router")

    def _create_error_response(self, claim: Claim, message: str) -> MinerResponse:
        """Helper to create error/unverifiable response."""
        logger.error(f"Cortensor Router Error: {message}")
        return MinerResponse(
            miner_id=self._miner_id,
            claim_id=claim.id,
            verdict="unverifiable",
            rationale=f"System Error: {message}",
            evidence_links=[],
            embedding=None,
            scores=MinerScores(accuracy=0, omission_risk=0, evidence_quality=0, governance_relevance=0, composite=0),
        )

    def _map_router_response(self, claim: Claim, data: Dict[str, Any], miner_id: str) -> MinerResponse:
        """Map Router JSON response to internal MinerResponse schema."""
        try:
            # Flexible mapping to handle potential schema variations
            result = data.get("result", data) # Some routers wrap result in "result" key
            
            verdict_raw = result.get("verdict", "unknown").lower()
            verdict_map = {"supported": "verified", "disputed": "refuted", "unknown": "unverifiable"}
            verdict = verdict_map.get(verdict_raw, "unverifiable")
            
            scores_data = result.get("scores", {})
            scores = MinerScores(
                accuracy=float(scores_data.get("accuracy", 0.5)),
                omission_risk=float(scores_data.get("omission_risk", 0.1)),
                evidence_quality=float(scores_data.get("evidence_quality", 0.5)),
                governance_relevance=float(scores_data.get("governance_relevance", 0.5)),
                composite=float(scores_data.get("composite", 0.5)),
            )
            
            return MinerResponse(
                miner_id=result.get("miner_id", miner_id),
                claim_id=claim.id,
                verdict=verdict,
                rationale=result.get("rationale", "No rationale provided."),
                evidence_links=result.get("evidence_links", []),
                embedding=result.get("embedding"), # Optional
                scores=scores,
            )
        except Exception as e:
            logger.error(f"Failed to map router response: {e}")
            return self._create_error_response(claim, f"Response mapping error: {e}")

    async def close(self):
        """Close HTTP client."""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None


# ============================================================================
# Miner Client Factory
# ============================================================================

def create_miner_clients(count: int = None, use_mock: bool = None) -> List[MinerClient]:
    """
    Create a list of miner clients.
    
    Args:
        count: Number of miners to create
        use_mock: Whether to use mock miners (defaults to settings.use_mock_miners)
        
    Returns:
        List of MinerClient instances
    """
    count = count or settings.miner_count
    use_mock = use_mock if use_mock is not None else settings.use_mock_miners
    
    clients = []
    for i in range(count):
        if use_mock:
            # Use deterministic seed for reproducibility
            clients.append(MockMinerClient(
                miner_id=f"mock_miner_{i:03d}",
                seed=42 + i,
            ))
        else:
            clients.append(CortensorRouterMinerClient(
                miner_id=f"cortensor_miner_{i:03d}",
            ))
    
    return clients
