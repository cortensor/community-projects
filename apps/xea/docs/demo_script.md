# Xea Governance Oracle - Demo Script

This document provides a step-by-step demonstration of the Xea Governance Oracle.

## Prerequisites

1. Start the services:
   ```bash
   docker-compose up --build
   ```

2. Wait for all services to be healthy:
   - Backend: http://localhost:8000/health
   - Frontend: http://localhost:3000

## Demo Flow

### Step 1: Ingest a Proposal

**Using the API:**

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "text": "# Proposal: Treasury Allocation\n\nThis proposal requests 50,000 USDC from the DAO treasury to fund developer grants.\n\n## Background\nThe treasury currently holds 500,000 USDC. This represents 10% of total funds.\n\n## Timeline\n- Applications open: January 15, 2025\n- Deadline: February 15, 2025"
  }'
```

**Expected Response:**
```json
{
  "proposal_hash": "sha256:a1b2c3...",
  "canonical_text": "# Proposal: Treasury Allocation...",
  "claims": [
    {
      "id": "claim_001",
      "text": "This proposal requests 50,000 USDC",
      "type": "factual",
      ...
    }
  ]
}
```

### Step 2: Start Validation

```bash
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d '{
    "proposal_hash": "sha256:a1b2c3..."
  }'
```

**Expected Response:**
```json
{
  "job_id": "job_20241222_001",
  "status": "queued",
  "created_at": "2024-12-22T00:00:00Z"
}
```

### Step 3: Monitor Progress

```bash
curl http://localhost:8000/status/job_20241222_001
```

**Expected Response (during validation):**
```json
{
  "job_id": "job_20241222_001",
  "status": "running",
  "progress": {
    "claims_total": 6,
    "claims_validated": 3,
    "miners_contacted": 5,
    "miners_responded": 4
  }
}
```

### Step 4: Aggregate Results

Once status is "completed":

```bash
curl -X POST http://localhost:8000/aggregate \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "job_20241222_001"
  }'
```

**Expected Response:**
```json
{
  "proposal_hash": "sha256:a1b2c3...",
  "aggregated_metrics": {
    "poi_agreement": 0.92,
    "pouw_score": 0.834,
    "consensus_verdict": "verified"
  },
  "recommendation": {
    "action": "approve",
    "confidence": 0.89,
    "summary": "All claims verified with high confidence."
  }
}
```

### Step 5: Create Attestation (Optional)

```bash
curl -X POST http://localhost:8000/attest \
  -H "Content-Type: application/json" \
  -d '{
    "evidence_cid": "QmXyZ123..."
  }'
```

## Using the Frontend

1. Open http://localhost:3000
2. Paste proposal text or URL
3. Click "Ingest Proposal"
4. Review extracted claims
5. Click "Validate Claims"
6. Watch live progress
7. View final recommendation

## Sample Proposals

Generate sample proposals for testing:

```bash
./infra/scripts/generate_sample_proposals.sh
```

This creates sample proposals in `./sample_proposals/`:
- `treasury_allocation.md`
- `protocol_upgrade.md`
- `governance_change.md`

## Troubleshooting

### Services not starting
```bash
docker-compose logs -f
```

### Reset everything
```bash
docker-compose down -v
docker-compose up --build
```

### Check Redis
```bash
docker exec -it xea-redis redis-cli
> KEYS *
```
