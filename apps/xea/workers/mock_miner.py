"""
Xea Governance Oracle - Mock Miner Server

A small HTTP server that simulates miner behavior for local development and testing.
"""

import argparse
import hashlib
import json
import logging
import random
import time
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}',
)
logger = logging.getLogger(__name__)


# ============================================================================
# Models
# ============================================================================

class ClaimPayload(BaseModel):
    id: str
    text: str
    type: str


class TaskPayload(BaseModel):
    id: str
    question: str
    rubric: List[Dict[str, Any]]


class MinerRequest(BaseModel):
    request_id: str
    proposal_hash: str
    claim: ClaimPayload
    tasks: List[TaskPayload]
    meta: Dict[str, Any] = Field(default_factory=dict)


class ScoreResponse(BaseModel):
    accuracy: float
    omission_risk: float
    evidence_quality: float
    governance_relevance: float
    composite: float


class MinerResponseModel(BaseModel):
    miner_id: str
    claim_id: str
    verdict: str
    rationale: str
    evidence_links: List[str]
    embedding: List[float]
    scores: ScoreResponse


# ============================================================================
# Mock Miner Logic
# ============================================================================

class MockMinerLogic:
    """Deterministic mock miner logic."""
    
    def __init__(self, miner_id: str = None, base_seed: int = 42):
        self.miner_id = miner_id or f"mock_miner_{uuid.uuid4().hex[:8]}"
        self.base_seed = base_seed
    
    def _get_seeded_random(self, claim_id: str) -> random.Random:
        """Get deterministic random based on claim and miner IDs."""
        seed_str = f"{self.miner_id}:{claim_id}:{self.base_seed}"
        seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        return random.Random(seed)
    
    def compute_embedding(self, text: str, dims: int = 64) -> List[float]:
        """Compute deterministic embedding."""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        embedding = []
        for i in range(dims):
            idx = (i * 2) % 30
            chunk = text_hash[idx:idx + 2]
            value = (int(chunk, 16) / 255.0) * 2 - 1
            embedding.append(round(value, 4))
        return embedding
    
    def determine_verdict(self, claim: ClaimPayload, rng: random.Random) -> str:
        """Determine verdict based on claim content."""
        text_lower = claim.text.lower()
        
        # Numeric claims -> likely supported
        if claim.type == "numeric":
            if rng.random() < 0.85:
                return "supported"
        
        # Uncertainty markers -> maybe disputed
        uncertainty_markers = ["risk", "unclear", "uncertain", "maybe"]
        if any(marker in text_lower for marker in uncertainty_markers):
            roll = rng.random()
            if roll < 0.4:
                return "disputed"
            elif roll < 0.6:
                return "unknown"
        
        # Default bias toward supported
        roll = rng.random()
        if roll < 0.7:
            return "supported"
        elif roll < 0.85:
            return "unknown"
        else:
            return "disputed"
    
    def generate_scores(self, verdict: str, rng: random.Random) -> ScoreResponse:
        """Generate PoUW scores."""
        base = {"supported": 0.85, "disputed": 0.70, "unknown": 0.50}.get(verdict, 0.6)
        
        accuracy = min(1.0, max(0.0, base + rng.uniform(-0.1, 0.1)))
        omission_risk = rng.uniform(0.05, 0.25)
        evidence_quality = rng.uniform(0.6, 0.95)
        governance_relevance = rng.uniform(0.7, 0.95)
        
        composite = (
            0.4 * accuracy +
            0.3 * (1 - omission_risk) +
            0.2 * evidence_quality +
            0.1 * governance_relevance
        )
        
        return ScoreResponse(
            accuracy=round(accuracy, 3),
            omission_risk=round(omission_risk, 3),
            evidence_quality=round(evidence_quality, 3),
            governance_relevance=round(governance_relevance, 3),
            composite=round(composite, 3),
        )
    
    def generate_rationale(self, claim: ClaimPayload, verdict: str, rng: random.Random) -> str:
        """Generate mock rationale."""
        rationales = {
            "supported": [
                f"Claim verified: '{claim.text[:40]}...'",
                "Cross-referenced with on-chain data. Values match.",
                "Evidence supports the claim.",
            ],
            "disputed": [
                f"Claim disputed: '{claim.text[:40]}...'",
                "Evidence contradicts the stated values.",
                "Unable to verify accuracy.",
            ],
            "unknown": [
                f"Insufficient data for claim: '{claim.text[:40]}...'",
                "No authoritative sources found.",
                "Requires additional context.",
            ],
        }
        return rng.choice(rationales.get(verdict, rationales["unknown"]))
    
    def generate_evidence_links(self, claim: ClaimPayload, verdict: str) -> List[str]:
        """Generate mock evidence links."""
        if verdict == "unknown":
            return []
        
        text_hash = hashlib.md5(claim.text.encode()).hexdigest()
        return [f"ipfs://Qm{text_hash[:40]}"]
    
    def process_request(self, request: MinerRequest) -> MinerResponseModel:
        """Process a validation request."""
        rng = self._get_seeded_random(request.claim.id)
        
        # Simulate processing delay
        delay = rng.uniform(0.05, 0.2)
        time.sleep(delay)
        
        verdict = self.determine_verdict(request.claim, rng)
        scores = self.generate_scores(verdict, rng)
        rationale = self.generate_rationale(request.claim, verdict, rng)
        evidence_links = self.generate_evidence_links(request.claim, verdict)
        embedding = self.compute_embedding(request.claim.text)
        
        return MinerResponseModel(
            miner_id=self.miner_id,
            claim_id=request.claim.id,
            verdict=verdict,
            rationale=rationale,
            evidence_links=evidence_links,
            embedding=embedding,
            scores=scores,
        )


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Xea Mock Miner",
    description="Mock miner server for local development",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global miner instance
miner_logic = MockMinerLogic()


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy", "miner_id": miner_logic.miner_id}


@app.post("/validate", response_model=MinerResponseModel)
def validate_claim(request: MinerRequest):
    """
    Validate a claim.
    
    This endpoint simulates miner behavior with deterministic responses.
    """
    logger.info(f"Received validation request: {request.request_id}")
    
    try:
        response = miner_logic.process_request(request)
        
        logger.info(
            f"Validation complete",
            extra={
                "request_id": request.request_id,
                "claim_id": request.claim.id,
                "verdict": response.verdict,
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/validate", response_model=MinerResponseModel)
def validate_claim_v1(request: MinerRequest):
    """V1 API endpoint for compatibility."""
    return validate_claim(request)


def run_server(host: str = "0.0.0.0", port: int = 8001):
    """Run the mock miner server."""
    logger.info(f"Starting mock miner server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mock Miner Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8001, help="Port to bind")
    args = parser.parse_args()
    
    run_server(host=args.host, port=args.port)
