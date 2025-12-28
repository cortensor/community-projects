"""
Xea Governance Oracle - API Routes

FastAPI router with all API endpoints.
"""

import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from typing import Optional, List

from app.schemas import (
    IngestRequest,
    IngestResponse,
    ValidateRequest,
    ValidateResponse,
    StatusResponse,
    JobProgress,
    AggregateRequest,
    AggregateResponse,
    AttestRequest,
    AttestResponse,
    Claim,
    ClaimCanonical,
    ClaimsEditRequest,
    MinerResponse,
    MinerScores,
    ProposalVersion,
    ProposalHistory,
)
from app.ingest import process_ingest, load_claims, persist_claims, get_data_dir
from app.utils import generate_job_id
from app.workers import job_state, validate_claims_job
from app.aggregator import aggregate_job, load_evidence_bundle
from app.attest import create_attestation as attest_create_attestation
from app import history_service

router = APIRouter()


# ============================================================================
# History Endpoints
# ============================================================================

@router.get("/history")
async def get_validation_history(limit: int = 50, offset: int = 0):
    """
    Get validation history list.
    
    Args:
        limit: Maximum number of items to return (default 50)
        offset: Offset for pagination (default 0)
    
    Returns:
        List of history items
    """
    return history_service.get_history(limit=limit, offset=offset)


@router.get("/history/recent")
async def get_recent_history(limit: int = 3):
    """
    Get most recent history items for home page display.
    
    Args:
        limit: Maximum number of items to return (default 3)
    
    Returns:
        List of recent history items
    """
    return history_service.get_recent_history(limit=limit)


@router.get("/history/{job_id}")
async def get_history_item(job_id: str):
    """
    Get a specific history item by job ID.
    
    Args:
        job_id: The job ID to look up
    
    Returns:
        History item with full details including evidence
    """
    item = history_service.get_history_by_job_id(job_id)
    if not item:
        raise HTTPException(status_code=404, detail="History item not found")
    return item


@router.post("/history")
async def save_history_item(
    job_id: str,
    proposal_hash: str,
    proposal_id: Optional[str] = None,
    version_number: int = 1,
    proposal_title: Optional[str] = None,
    claims_count: int = 0,
    status: str = "pending",
    overall_verdict: Optional[str] = None,
    confidence_score: Optional[float] = None,
    ipfs_cid: Optional[str] = None,
    network_used: Optional[str] = None,
):
    """
    Save or update a history item.
    Called by frontend after validation completes.
    """
    history_service.save_history(
        job_id=job_id,
        proposal_id=proposal_id,
        version_number=version_number,
        proposal_hash=proposal_hash,
        proposal_title=proposal_title,
        claims_count=claims_count,
        status=status,
        overall_verdict=overall_verdict,
        confidence_score=confidence_score,
        ipfs_cid=ipfs_cid,
        network_used=network_used,
    )
    return {"status": "saved"}


# ============================================================================
# Ingest Endpoints
# ============================================================================

@router.post("/ingest", response_model=IngestResponse)
async def ingest_proposal(request: IngestRequest) -> IngestResponse:
    """
    Ingest a DAO proposal from URL or raw text and extract atomic claims.

    Returns:
        IngestResponse with proposal_hash, canonical_text, and extracted claims
    """
    try:
        result = await process_ingest(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/proposal/{proposal_id}/history", response_model=ProposalHistory)
async def get_proposal_history(proposal_id: str) -> ProposalHistory:
    """
    Get version history for a proposal.
    
    Returns list of all versions with their hashes and timestamps.
    """
    from app.versioning import get_proposal_history as fetch_history
    
    history = fetch_history(proposal_id)
    if not history:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    return history


@router.get("/claims/{proposal_hash}")
async def get_claims(proposal_hash: str):
    """
    Get claims for a proposal by hash.
    """
    if not proposal_hash.startswith("sha256:"):
        proposal_hash = f"sha256:{proposal_hash}"
    
    data = load_claims(proposal_hash)
    if not data:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    return data


@router.get("/claims/{proposal_hash}/edit", response_class=HTMLResponse)
async def edit_claims_form(proposal_hash: str):
    """Get HTML form for editing claims."""
    if not proposal_hash.startswith("sha256:"):
        proposal_hash = f"sha256:{proposal_hash}"
    
    data = load_claims(proposal_hash)
    if not data:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    claims = data.get("claims", [])
    canonical_text = data.get("canonical_text", "")
    
    # Build simplified HTML form
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Edit Claims - Xea</title>
    <style>
        body {{ font-family: system-ui; background: #0a0a0f; color: #fff; padding: 2rem; }}
        h1 {{ color: #6366f1; }}
        .claim {{ background: #1a1a24; padding: 1rem; border-radius: 8px; margin: 1rem 0; }}
        textarea, input, select {{ width: 100%; padding: 0.5rem; margin: 0.25rem 0; background: #0a0a0f; border: 1px solid #2a2a3a; color: #fff; border-radius: 4px; }}
        .btn {{ padding: 0.75rem 1.5rem; background: #6366f1; color: white; border: none; border-radius: 8px; cursor: pointer; margin: 0.5rem 0; }}
    </style>
</head>
<body>
    <h1>Edit Claims</h1>
    <p>Proposal Hash: {proposal_hash}</p>
    <form id="form">
        {"".join(f'''
        <div class="claim">
            <strong>{c.get("id")}</strong>
            <select name="type_{i}"><option value="factual" {"selected" if c.get("type")=="factual" else ""}>factual</option><option value="numeric" {"selected" if c.get("type")=="numeric" else ""}>numeric</option></select>
            <textarea name="text_{i}">{c.get("text", "")}</textarea>
        </div>''' for i, c in enumerate(claims))}
        <button type="submit" class="btn">Save</button>
    </form>
    <script>
        document.getElementById('form').onsubmit = async (e) => {{
            e.preventDefault();
            const claims = [];
            document.querySelectorAll('.claim').forEach((el, i) => {{
                claims.push({{
                    id: 'c' + (i+1),
                    text: el.querySelector('textarea').value,
                    type: el.querySelector('select').value,
                    paragraph_index: 0,
                    char_range: [0, 0],
                    canonical: {{numbers: [], addresses: [], urls: []}}
                }});
            }});
            await fetch('/claims/{proposal_hash.replace("sha256:", "")}', {{
                method: 'PUT',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{claims}})
            }});
            alert('Saved!');
        }};
    </script>
</body>
</html>"""
    return html


@router.put("/claims/{proposal_hash}")
async def update_claims(proposal_hash: str, request: ClaimsEditRequest):
    """Update claims for a proposal."""
    if not proposal_hash.startswith("sha256:"):
        proposal_hash = f"sha256:{proposal_hash}"
    
    data = load_claims(proposal_hash)
    if not data:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    persist_claims(proposal_hash, request.claims, data.get("canonical_text", ""))
    return {"status": "success"}


# ============================================================================
# Validation Endpoints
# ============================================================================

def _run_validation_background(proposal_hash: str, job_id: str):
    """Background task to run validation."""
    try:
        validate_claims_job(proposal_hash, job_id=job_id)
    except Exception as e:
        import logging
        logging.error(f"Background validation failed: {e}")


@router.post("/validate", response_model=ValidateResponse)
async def validate_proposal(
    request: ValidateRequest,
    background_tasks: BackgroundTasks,
) -> ValidateResponse:
    """
    Start an asynchronous validation job for a proposal.
    """
    # Normalize hash
    proposal_hash = request.proposal_hash
    if not proposal_hash.startswith("sha256:"):
        proposal_hash = f"sha256:{proposal_hash}"
    
    # Check proposal exists
    claims_data = load_claims(proposal_hash)
    if not claims_data:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    claims = claims_data.get("claims", [])
    if not claims:
        raise HTTPException(status_code=400, detail="No claims to validate")
    
    # Create job
    job_id = generate_job_id()
    job_state.create_job(job_id, proposal_hash, claims)
    
    # Start background validation
    background_tasks.add_task(_run_validation_background, proposal_hash, job_id)
    
    return ValidateResponse(
        job_id=job_id,
        proposal_hash=proposal_hash,
        status="queued",
        created_at=datetime.now(timezone.utc),
        estimated_completion=None,
    )


@router.get("/status/{job_id}", response_model=StatusResponse)
async def get_job_status(job_id: str) -> StatusResponse:
    """
    Get the current status and partial results of a validation job.
    """
    job_data = job_state.get_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Build progress
    progress = JobProgress(
        claims_total=job_data.get("claims_total", 0),
        claims_validated=job_data.get("claims_validated", 0),
        miners_contacted=job_data.get("miners_contacted", 0),
        miners_responded=job_data.get("miners_responded", 0),
    )
    
    # Parse responses into MinerResponse models
    partial_results = []
    responses = job_data.get("responses", {})
    for claim_id, claim_responses in responses.items():
        for resp in claim_responses:
            try:
                scores_data = resp.get("scores", {})
                scores = MinerScores(
                    accuracy=scores_data.get("accuracy", 0),
                    omission_risk=scores_data.get("omission_risk", 0),
                    evidence_quality=scores_data.get("evidence_quality", 0),
                    governance_relevance=scores_data.get("governance_relevance", 0),
                    composite=scores_data.get("composite", 0),
                )
                partial_results.append(MinerResponse(
                    miner_id=resp.get("miner_id", "unknown"),
                    claim_id=resp.get("claim_id", claim_id),
                    verdict=resp.get("verdict", "unverifiable"),
                    rationale=resp.get("rationale", ""),
                    evidence_links=resp.get("evidence_links", []),
                    embedding=resp.get("embedding"),
                    scores=scores,
                ))
            except Exception:
                pass
    
    # Parse datetime fields
    started_at = None
    updated_at = None
    completed_at = None
    
    if job_data.get("started_at"):
        try:
            started_at = datetime.fromisoformat(job_data["started_at"])
        except (ValueError, TypeError):
            pass
    
    if job_data.get("completed_at"):
        try:
            completed_at = datetime.fromisoformat(job_data["completed_at"])
        except (ValueError, TypeError):
            pass
    
    status = job_data.get("status", "unknown")
    ready_for_aggregation = status == "completed" and len(partial_results) > 0
    
    return StatusResponse(
        job_id=job_id,
        status=status,
        progress=progress,
        partial_results=partial_results,
        started_at=started_at,
        updated_at=updated_at,
        completed_at=completed_at,
        ready_for_aggregation=ready_for_aggregation,
        # Stage tracking (NEW)
        current_stage=job_data.get("current_stage", "received"),
        retries_attempted=job_data.get("retries_attempted", 0),
        last_heartbeat=job_data.get("last_heartbeat"),
        quorum_target=job_data.get("quorum_target", 3),
    )


# ============================================================================
# Aggregation & Evidence Endpoints
# ============================================================================

@router.post("/aggregate", response_model=AggregateResponse)
async def aggregate_results(request: AggregateRequest) -> AggregateResponse:
    """
    Aggregate miner responses into a final evidence bundle.
    
    This endpoint:
    1. Loads raw miner responses for the job
    2. Computes per-claim PoI and PoUW metrics
    3. Detects outliers via Mahalanobis distance
    4. Generates critical flags
    5. Saves and returns the evidence bundle
    """
    job_id = request.job_id
    
    # Check job exists
    job_data = job_state.get_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check job is completed
    if job_data.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job not ready for aggregation. Status: {job_data.get('status')}"
        )
    
    # Run aggregation
    bundle = aggregate_job(job_id)
    if not bundle:
        raise HTTPException(status_code=500, detail="Aggregation failed")
    
    # Optionally publish to IPFS
    ipfs_cid = None
    if request.publish:
        from app.attest import publish_bundle_dict
        ipfs_cid = publish_bundle_dict(bundle)
    
    return AggregateResponse(
        job_id=job_id,
        evidence_bundle=bundle,
        ipfs_cid=ipfs_cid,
    )


@router.get("/evidence/{job_id}")
async def get_evidence_bundle(job_id: str, view: Optional[str] = None):
    """
    Get a saved evidence bundle by job ID.
    
    Query Parameters:
        view: Optional role-based view (voter, delegate, auditor)
              - voter: Risk badge, recommendation, key flags
              - delegate: Claim breakdown, disagreement indicators
              - auditor: Full evidence bundle (default)
    """
    from app.views import transform_evidence_for_role, validate_role, ViewRole
    from app.rubrics import get_rubric
    
    bundle = load_evidence_bundle(job_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Evidence bundle not found")
    
    # If no view specified, return full bundle
    if not view:
        return bundle
    
    # Validate and transform to requested view
    try:
        role = validate_role(view)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Get rubric if referenced in bundle
    rubric = None
    if bundle.get("rubric_id"):
        rubric = get_rubric(bundle["rubric_id"], bundle.get("rubric_version"))
    
    return transform_evidence_for_role(bundle, role, rubric)


# ============================================================================
# DAO & Rubric Endpoints
# ============================================================================

from app.schemas import (
    DAO,
    DAORegisterRequest,
    Rubric,
    RubricCreateRequest,
)


@router.post("/dao/register", response_model=DAO)
async def register_dao_endpoint(request: DAORegisterRequest) -> DAO:
    """
    Register a new DAO.
    
    DAOs can define custom rubrics for PoUW scoring.
    """
    from app.rubrics import register_dao
    
    try:
        dao = register_dao(request)
        return dao
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/dao/{dao_id}", response_model=DAO)
async def get_dao_endpoint(dao_id: str) -> DAO:
    """Get a DAO by ID."""
    from app.rubrics import get_dao
    
    dao = get_dao(dao_id)
    if not dao:
        raise HTTPException(status_code=404, detail="DAO not found")
    
    return dao


@router.post("/rubric/create", response_model=Rubric)
async def create_rubric_endpoint(request: RubricCreateRequest) -> Rubric:
    """
    Create a new PoUW rubric for a DAO.
    
    Rubrics define custom weights for accuracy, omission_risk,
    evidence_quality, and governance_relevance. Once used in
    evidence, rubrics become immutable.
    """
    from app.rubrics import create_rubric
    
    try:
        rubric = create_rubric(request)
        return rubric
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/rubric/{rubric_id}", response_model=Rubric)
async def get_rubric_endpoint(rubric_id: str, version: Optional[int] = None) -> Rubric:
    """
    Get a rubric by ID.
    
    Query Parameters:
        version: Specific version number, or latest if omitted
    """
    from app.rubrics import get_rubric
    
    rubric = get_rubric(rubric_id, version)
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
    
    return rubric


@router.get("/dao/{dao_id}/rubrics", response_model=List[Rubric])
async def list_dao_rubrics(dao_id: str) -> List[Rubric]:
    """List all rubrics for a DAO."""
    from app.rubrics import list_rubrics, get_dao
    
    dao = get_dao(dao_id)
    if not dao:
        raise HTTPException(status_code=404, detail="DAO not found")
    
    return list_rubrics(dao_id)


# ============================================================================
# Attestation Endpoints
# ============================================================================

@router.post("/attest", response_model=AttestResponse)
async def create_attestation(request: AttestRequest) -> AttestResponse:
    """
    Create an on-chain attestation for an evidence bundle.
    
    This endpoint:
    1. Loads the evidence bundle for the job
    2. Signs it with ECDSA (or mock if no key configured)
    3. Optionally publishes to IPFS
    4. Returns signature and verification instructions
    """
    job_id = request.job_id
    
    # Load evidence bundle
    bundle = load_evidence_bundle(job_id)
    if not bundle:
        # Try to aggregate first
        bundle = aggregate_job(job_id)
        if not bundle:
            raise HTTPException(status_code=404, detail="Evidence bundle not found")
    
    # Create attestation
    attestation = attest_create_attestation(bundle, publish=request.publish)
    
    return AttestResponse(
        job_id=job_id,
        proposal_hash=bundle.get("proposal_hash", ""),
        ipfs_cid=attestation.get("ipfs_cid"),
        signature=attestation["signature"],
        signer=attestation["signer"],
        message_hash=attestation["message_hash"],
        verification_instructions=attestation["verification_instructions"],
    )
