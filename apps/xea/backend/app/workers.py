"""
Xea Governance Oracle - Worker Jobs

RQ worker job definitions for background processing.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from redis import Redis

from app.config import settings
from app.ingest import load_claims
from app.cortensor_client import validate_with_cortensor
from app.schemas import Claim, ClaimCanonical, MinerResponse, MinerScores
from app.utils import generate_job_id

logger = logging.getLogger(__name__)


# ============================================================================
# Validation Stage Enum (for progress visibility)
# ============================================================================

class ValidationStage:
    """Canonical validation stages - monotonic, never go backward."""
    RECEIVED = "received"              # Job created
    CLAIMS_EXTRACTED = "claims_extracted"  # Claims ready
    DISPATCHING = "dispatching"        # Sending to Cortensor
    WAITING_FOR_MINERS = "waiting"     # Awaiting miner responses
    PARTIAL_RESPONSES = "partial"      # Some responses received
    QUORUM_REACHED = "quorum_reached"  # Enough responses
    AGGREGATING = "aggregating"        # Computing evidence
    COMPLETED = "completed"            # Done
    FAILED = "failed"                  # Error with reason

# ============================================================================
# PoUW Rubric (Governance Specific)
# ============================================================================

POUW_RUBRIC = [
    {"id": "accuracy", "desc": "0-1", "weight": 0.4},
    {"id": "omission_risk", "desc": "0-1", "weight": 0.3},
    {"id": "evidence_quality", "desc": "0-1", "weight": 0.2},
    {"id": "governance_relevance", "desc": "0-1", "weight": 0.1},
]

# Configure structured JSON logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='{"time":"%(asctime)s","level":"%(levelname)s","message":"%(message)s","module":"%(module)s"}',
)


# Data directory for job responses
def get_responses_dir() -> Path:
    """Get the responses data directory."""
    responses_dir = Path(settings.data_dir) / "responses"
    if not responses_dir.exists():
        # Fallback to local directory
        responses_dir = Path(__file__).parent.parent.parent / "data" / "responses"
    responses_dir.mkdir(parents=True, exist_ok=True)
    return responses_dir


def get_jobs_dir() -> Path:
    """Get the jobs data directory."""
    jobs_dir = Path(settings.data_dir) / "jobs"
    if not jobs_dir.exists():
        jobs_dir = Path(__file__).parent.parent.parent / "data" / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    return jobs_dir


# ============================================================================
# Job State Management
# ============================================================================

class JobStateManager:
    """Manage job state in Redis and file system."""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.redis_url
        self._redis: Optional[Redis] = None
    
    @property
    def redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(self.redis_url, decode_responses=True)
        return self._redis
    
    def create_job(self, job_id: str, proposal_hash: str, claims: List[dict]) -> dict:
        """Create a new job record."""
        job_data = {
            "job_id": job_id,
            "proposal_hash": proposal_hash,
            "status": "queued",
            "claims_total": len(claims),
            "claims_validated": 0,
            "miners_contacted": 0,
            "miners_responded": 0,
            "created_at": datetime.utcnow().isoformat(),
            "started_at": None,
            "completed_at": None,
            "claim_ids": [c.get("id", f"c{i+1}") for i, c in enumerate(claims)],
            "responses": {},  # claim_id -> [responses]
            
            # Stage tracking (NEW for progress visibility)
            "current_stage": ValidationStage.RECEIVED,
            "stage_history": [{"stage": ValidationStage.RECEIVED, "timestamp": datetime.utcnow().isoformat()}],
            "retries_attempted": 0,
            "last_heartbeat": datetime.utcnow().isoformat(),
            "quorum_target": 3,  # Minimum responses needed per claim
            "error_message": None,
        }
        
        # Store in Redis
        self.redis.hset(f"job:{job_id}", mapping={
            k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) if v is not None else ""
            for k, v in job_data.items()
        })
        self.redis.expire(f"job:{job_id}", 86400)  # 24h TTL
        
        # Also persist to file for durability
        self._save_job_to_file(job_id, job_data)
        
        return job_data
    
    def get_job(self, job_id: str) -> Optional[dict]:
        """Get job data from Redis or file."""
        # Try Redis first
        data = self.redis.hgetall(f"job:{job_id}")
        if data:
            return self._parse_job_data(data)
        
        # Fallback to file
        return self._load_job_from_file(job_id)
    
    def update_job(self, job_id: str, updates: dict):
        """Update job fields."""
        for key, value in updates.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif value is None:
                value = ""
            else:
                value = str(value)
            self.redis.hset(f"job:{job_id}", key, value)
        
        # Sync to file
        job_data = self.get_job(job_id)
        if job_data:
            self._save_job_to_file(job_id, job_data)
    
    def transition_stage(self, job_id: str, new_stage: str, message: str = None):
        """
        Transition job to new stage with timestamp.
        
        Stages are monotonic - logged but never go backward.
        """
        now = datetime.utcnow().isoformat()
        job_data = self.get_job(job_id)
        if not job_data:
            return
        
        # Append to stage history
        history = job_data.get("stage_history", [])
        history.append({
            "stage": new_stage,
            "timestamp": now,
            "message": message,
        })
        
        # Update job
        self.update_job(job_id, {
            "current_stage": new_stage,
            "stage_history": history,
            "last_heartbeat": now,
        })
        
        logger.info(f"Job {job_id} transitioned to stage: {new_stage}", extra={
            "job_id": job_id,
            "stage": new_stage,
            "stage_message": message,
        })
    
    def heartbeat(self, job_id: str):
        """Update heartbeat timestamp to indicate job is still alive."""
        self.update_job(job_id, {
            "last_heartbeat": datetime.utcnow().isoformat(),
        })
    
    def increment_retries(self, job_id: str):
        """Increment retry counter."""
        job_data = self.get_job(job_id)
        if job_data:
            retries = job_data.get("retries_attempted", 0) + 1
            self.update_job(job_id, {
                "retries_attempted": retries,
                "last_heartbeat": datetime.utcnow().isoformat(),
            })
    
    def add_response(self, job_id: str, claim_id: str, response: dict):
        """Add a miner response for a claim."""
        job_data = self.get_job(job_id)
        if not job_data:
            return
        
        responses = job_data.get("responses", {})
        if claim_id not in responses:
            responses[claim_id] = []
        responses[claim_id].append(response)
        
        # Update counts
        miners_responded = sum(len(r) for r in responses.values())
        
        self.update_job(job_id, {
            "responses": responses,
            "miners_responded": miners_responded,
        })
        
        # Also append to raw responses file
        self._append_raw_response(job_id, claim_id, response)
    
    def _parse_job_data(self, data: dict) -> dict:
        """Parse job data from Redis strings."""
        parsed = {}
        for key, value in data.items():
            if key in ("claims_total", "claims_validated", "miners_contacted", "miners_responded", "retries_attempted", "quorum_target"):
                parsed[key] = int(value) if value else 0
            elif key in ("claim_ids", "responses", "stage_history"):
                try:
                    parsed[key] = json.loads(value) if value else ([] if key != "responses" else {})
                except json.JSONDecodeError:
                    parsed[key] = [] if key != "responses" else {}
            else:
                parsed[key] = value if value else None
        return parsed
    
    def _save_job_to_file(self, job_id: str, job_data: dict):
        """Save job data to JSON file."""
        jobs_dir = get_jobs_dir()
        file_path = jobs_dir / f"{job_id}.json"
        with open(file_path, "w") as f:
            json.dump(job_data, f, indent=2, default=str)
    
    def _load_job_from_file(self, job_id: str) -> Optional[dict]:
        """Load job data from JSON file."""
        jobs_dir = get_jobs_dir()
        file_path = jobs_dir / f"{job_id}.json"
        if not file_path.exists():
            return None
        with open(file_path, "r") as f:
            return json.load(f)
    
    def _append_raw_response(self, job_id: str, claim_id: str, response: dict):
        """Append raw response to audit file."""
        responses_dir = get_responses_dir()
        file_path = responses_dir / f"{job_id}.json"
        
        # Load existing or create new
        if file_path.exists():
            with open(file_path, "r") as f:
                raw_data = json.load(f)
        else:
            raw_data = {"job_id": job_id, "responses": []}
        
        raw_data["responses"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "claim_id": claim_id,
            "response": response,
        })
        
        with open(file_path, "w") as f:
            json.dump(raw_data, f, indent=2, default=str)


# Global job state manager
job_state = JobStateManager()


def _parse_text_format_response(text: str) -> Optional[dict]:
    """
    Parse Markdown/text format miner response into structured data.
    
    Handles responses like:
    * verdict: 'verified'
    * rationale: The claim is accurate...
    * confidence: 0.8
    """
    import re
    
    result = {
        "verdict": "unverifiable",
        "rationale": "Unable to parse miner response",
        "confidence": 0.5,
        "evidence_links": [],
    }
    
    try:
        # Extract verdict (look for variations: 'verified', "verified", verified)
        verdict_patterns = [
            r"\*?\s*verdict:?\s*['\"]?(verified|refuted|unverifiable)['\"]?",
            r"verdict\s*[:=]\s*['\"]?(verified|refuted|unverifiable)['\"]?",
        ]
        for pattern in verdict_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["verdict"] = match.group(1).lower()
                break
        
        # Extract rationale
        rationale_patterns = [
            r"\*?\s*rationale:?\s*(.+?)(?=\*\s|\n\*|evidence|confidence|$)",
            r"rationale\s*[:=]\s*(.+?)(?=\n|evidence|confidence|$)",
        ]
        for pattern in rationale_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                rationale = match.group(1).strip()
                # Clean up rationale
                rationale = re.sub(r'\s+', ' ', rationale)  # Normalize whitespace
                rationale = rationale.rstrip('.') + '.'  # Ensure ends with period
                result["rationale"] = rationale[:500]  # Limit length
                break
        
        # Extract confidence
        confidence_patterns = [
            r"\*?\s*confidence:?\s*([\d.]+)",
            r"confidence\s*[:=]\s*([\d.]+)",
        ]
        for pattern in confidence_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    result["confidence"] = float(match.group(1))
                except ValueError:
                    pass
                break
        
        # Extract evidence links
        link_pattern = r'<?(https?://[^\s<>]+)>?'
        links = re.findall(link_pattern, text)
        result["evidence_links"] = links[:5]  # Limit to 5 links
        
        # If we found a valid verdict, return the parsed result
        if result["verdict"] != "unverifiable" or "verified" in text.lower() or "refuted" in text.lower():
            logger.info(f"Text parser extracted: verdict={result['verdict']}, confidence={result['confidence']}")
            return result
        
        return result  # Return with defaults if parsing was partial
        
    except Exception as e:
        logger.error(f"Text format parser error: {e}")
        return None


# ============================================================================
# Validation Worker Jobs
# ============================================================================

async def _validate_single_claim(
    claim: Claim,
    proposal_hash: str,
    job_id: str,
) -> List[MinerResponse]:
    """
    Validate a single claim using Cortensor Testnet.
    
    Strictly uses the Real Cortensor Router.
    """
    start_time = time.time()
    
    # 1. Build Verification Prompts
    system_prompt = (
        "You are a specialized governance auditor running on the Cortensor decentralized network. "
        "Your task is to verify claims in governance proposals with high precision. "
        "You must output valid JSON."
    )
    
    user_prompt = (
        f"Verify the following claim:\n\n'{claim.text}'\n\n"
        f"Context: Proposal Hash {proposal_hash}\n\n"
        "Analyze the claim for factual accuracy. "
        "Return a JSON object with the following fields:\n"
        "- verdict: 'verified', 'refuted', or 'unverifiable'\n"
        "- rationale: A brief explanation of your finding\n"
        "- evidence_links: A list of URLs or citations found\n"
        "- confidence: A float between 0.0 and 1.0\n"
        "- collection_timestamp: ISO8601 string"
    )

    try:
        # 2. Call Cortensor Testnet
        # usage: validate_with_cortensor(sys, user, rubric) -> raw_dict
        raw_response = await validate_with_cortensor(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            rubric=POUW_RUBRIC
        )

        # DEBUG: Dump Raw Response to debug scoring
        logger.info(f"RAW CORTENSOR RESPONSE: {json.dumps(raw_response)}")
        
        # 3. Parse Response
        # Cortensor returns text completion format (not chat format)
        choices = raw_response.get("choices", [])
        if not choices:
            raise ValueError("Empty choices in Cortensor response")
        
        # Cortensor uses "text" field (text completion), not "message.content" (chat)
        first_choice = choices[0]
        content_str = first_choice.get("text") or first_choice.get("message", {}).get("content", "{}")
        
        # Parse the JSON content from the miner
        try:
            # Clean potential markdown code blocks and leading/trailing whitespace
            clean_content = content_str.replace("```json", "").replace("```", "").strip()
            # Also handle leading </s> tokens from some models
            if clean_content.endswith("</s>"):
                clean_content = clean_content[:-4].strip()
            miner_data = json.loads(clean_content)
        except json.JSONDecodeError:
            # Attempt to parse text format response (Markdown bullets)
            logger.warning(f"JSON parse failed for claim {claim.id}, trying text format parser")
            miner_data = _parse_text_format_response(content_str)
            if miner_data is None:
                logger.warning(f"Text format parse also failed for claim {claim.id}. Using fallback.")
                miner_data = {"verdict": "unverifiable", "rationale": "Miner output malformed"}

        # 4. Extract Scores (PoUW)
        # Cortensor testnet may not include proof_of_useful_work yet
        # Derive scores from miner's confidence if PoUW not present
        pouw = raw_response.get("proof_of_useful_work", {})
        scores_data = pouw.get("rubric_scores", {})
        composite_score = pouw.get("score", None)
        
        # If no PoUW scores, derive from miner's response quality
        if composite_score is None or composite_score == 0:
            # Use miner's confidence as base score
            miner_confidence = float(miner_data.get("confidence", 0.5))
            verdict = miner_data.get("verdict", "unverifiable")
            
            # Give meaningful scores based on verdict and confidence
            if verdict == "verified":
                # Verified claims get high scores based on confidence
                # Minimum 0.75 for verified, up to 1.0 with confidence
                base_score = max(0.75, min(1.0, miner_confidence + 0.3))
            elif verdict == "refuted":
                # Refuted claims also get decent scores - miner did work to disprove
                base_score = max(0.6, min(1.0, miner_confidence + 0.2))
            else:  # unverifiable
                # Unverifiable gets moderate score - miner analyzed and determined uncertainty
                # This represents the work done to evaluate, not empty failure
                base_score = max(0.4, min(0.7, 0.5 + miner_confidence * 0.2))
            
            scores = MinerScores(
                accuracy=base_score,
                omission_risk=1.0 - base_score,  # Lower is better for omission risk
                evidence_quality=base_score * 0.8,  # Slightly lower since no explicit evidence
                governance_relevance=base_score * 0.9,
                composite=base_score
            )
        else:
            scores = MinerScores(
                accuracy=float(scores_data.get("accuracy", 0.0)),
                omission_risk=float(scores_data.get("omission_risk", 0.0)),
                evidence_quality=float(scores_data.get("evidence_quality", 0.0)),
                governance_relevance=float(scores_data.get("governance_relevance", 0.0)),
                composite=float(composite_score)
            )
        
        # 5. Construct Response
        response = MinerResponse(
            miner_id=f"cortensor-{settings.cortensor_session_id}", # Traceable 
            claim_id=claim.id,
            verdict=miner_data.get("verdict", "unverifiable"),
            rationale=miner_data.get("rationale", "No rationale provided"),
            evidence_links=miner_data.get("evidence_links", []),
            embedding=None, # Router doesn't guarantee embeddings yet
            scores=scores,
            cortensor_raw=raw_response # Audit Trail
        )
        
        # Log success
        logger.info(
            f"Cortensor verification complete",
            extra={
                "job_id": job_id,
                "claim_id": claim.id,
                "verdict": response.verdict,
                "score": response.scores.composite,
                "elapsed_ms": round((time.time() - start_time) * 1000),
            }
        )
        
        # Persist
        job_state.add_response(job_id, claim.id, response.model_dump())
        
        return [response]

    except Exception as e:
        logger.error(f"Cortensor validation failed for claim {claim.id}: {e}")
        # Return error response so pipeline continues
        error_response = MinerResponse(
            miner_id="error",
            claim_id=claim.id,
            verdict="unverifiable",
            rationale=f"System Error: {str(e)}",
            evidence_links=[],
            scores=MinerScores(accuracy=0, omission_risk=0, evidence_quality=0, governance_relevance=0, composite=0),
            cortensor_raw={"error": str(e)}
        )
        job_state.add_response(job_id, claim.id, error_response.model_dump())
        return [error_response]


async def _run_validation_async(
    job_id: str,
    proposal_hash: str,
    claims: List[Claim],
) -> dict:
    """Run the async validation loop."""
    # Validating claims via Cortensor Testnet
    # No local fan-out; Route provides access to the decentralized network
    
    # Stage: DISPATCHING
    job_state.transition_stage(job_id, ValidationStage.DISPATCHING, "Sending to Cortensor network")
    job_state.update_job(job_id, {
        "status": "running",
        "started_at": datetime.utcnow().isoformat(),
        "miners_contacted": len(claims),  # One router request per claim
    })
    
    logger.info(
        f"Starting Cortensor validation",
        extra={
            "job_id": job_id,
            "claims_count": len(claims),
            "router_url": settings.cortensor_router_url,
        }
    )
    
    # Stage: WAITING_FOR_MINERS
    job_state.transition_stage(job_id, ValidationStage.WAITING_FOR_MINERS, f"Validating {len(claims)} claims")
    
    # Validate each claim
    all_responses = {}
    claims_validated = 0
    
    for claim in claims:
        logger.info(f"Validating claim {claim.id} on Testnet")
        
        # Heartbeat before each claim
        job_state.heartbeat(job_id)
        
        # Strict sequential validation to avoid rate limits and ensure stability
        # The router itself handles distribution
        responses = await _validate_single_claim(
            claim=claim,
            proposal_hash=proposal_hash,
            job_id=job_id,
        )
        
        all_responses[claim.id] = [r.model_dump() for r in responses]
        claims_validated += 1
        
        # Update progress
        job_state.update_job(job_id, {
            "claims_validated": claims_validated,
            "miners_responded": claims_validated,  # One response per claim from router
        })
        
        # Transition to PARTIAL after first response
        if claims_validated == 1 and len(claims) > 1:
            job_state.transition_stage(
                job_id, 
                ValidationStage.PARTIAL_RESPONSES, 
                f"{claims_validated}/{len(claims)} claims validated"
            )
    
    # Stage: AGGREGATING
    job_state.transition_stage(job_id, ValidationStage.AGGREGATING, "Computing evidence bundle")
    
    # Mark complete
    job_state.update_job(job_id, {
        "status": "completed",
        "completed_at": datetime.utcnow().isoformat(),
    })
    
    # Stage: COMPLETED
    job_state.transition_stage(job_id, ValidationStage.COMPLETED, "Validation complete")
    
    logger.info(
        f"Validation completed",
        extra={
            "job_id": job_id,
            "claims_validated": claims_validated,
        }
    )
    
    return {"job_id": job_id, "status": "completed", "responses": all_responses}


def validate_claims_job(proposal_hash: str, job_id: str = None) -> dict:
    """
    RQ worker job to validate all claims for a proposal.
    
    Args:
        proposal_hash: Hash of the proposal to validate
        job_id: Optional existing job ID. If not provided, a new one is generated.
        
    Returns:
        Job result with status and responses
    """
    # Load claims for proposal
    claims_data = load_claims(proposal_hash)
    if not claims_data:
        logger.error(f"Proposal not found: {proposal_hash}")
        return {"error": "Proposal not found", "proposal_hash": proposal_hash}
    
    # Parse claims
    claims = []
    for claim_dict in claims_data.get("claims", []):
        canonical_data = claim_dict.get("canonical", {})
        canonical = ClaimCanonical(
            numbers=canonical_data.get("numbers", []),
            addresses=canonical_data.get("addresses", []),
            urls=canonical_data.get("urls", []),
        )
        claims.append(Claim(
            id=claim_dict["id"],
            text=claim_dict["text"],
            paragraph_index=claim_dict.get("paragraph_index", 0),
            char_range=claim_dict.get("char_range", [0, 0]),
            type=claim_dict.get("type", "factual"),
            canonical=canonical,
        ))
    
    if not claims:
        logger.error(f"No claims found for proposal: {proposal_hash}")
        return {"error": "No claims found", "proposal_hash": proposal_hash}
    
    # Use provided job ID or generate new one
    if not job_id:
        job_id = generate_job_id()
        # Create job record only if we generated the ID (new job)
        job_state.create_job(job_id, proposal_hash, claims_data.get("claims", []))
    else:
        # Ensure job exists if ID provided
        if not job_state.get_job(job_id):
             job_state.create_job(job_id, proposal_hash, claims_data.get("claims", []))
    
    # Run async validation
    # Handle both sync and async contexts
    try:
        loop = asyncio.get_running_loop()
        # Already in async context - use a thread to run our async code
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                lambda: asyncio.run(_run_validation_async(job_id, proposal_hash, claims))
            )
            result = future.result()
    except RuntimeError:
        # No running loop - create one
        result = asyncio.run(_run_validation_async(job_id, proposal_hash, claims))
    
    return result


def validate_proposal_job(proposal_hash: str) -> dict:
    """Alias for validate_claims_job."""
    return validate_claims_job(proposal_hash)


def aggregate_results_job(job_id: str) -> dict:
    """
    RQ worker job to aggregate miner responses.
    
    TODO: Implement full aggregation logic.
    """
    job_data = job_state.get_job(job_id)
    if not job_data:
        return {"error": "Job not found", "job_id": job_id}
    
    # TODO: Implement aggregation
    return {
        "job_id": job_id,
        "status": "aggregated",
        "aggregated_at": datetime.utcnow().isoformat(),
    }


def attest_evidence_job(evidence_bundle: dict) -> dict:
    """
    RQ worker job to create attestation.
    
    TODO: Implement attestation logic.
    """
    # TODO: Implement attestation
    return {
        "status": "attested",
        "attested_at": datetime.utcnow().isoformat(),
    }
