# Xea Governance Oracle — Specification

## 1. Project Overview

### Objective

Xea produces **verifiable governance intelligence** by decomposing DAO proposals into atomic claims, validating them via redundant decentralized inference (PoI/PoUW), and producing signed, machine-verifiable evidence bundles and attestations.

### Core Concepts

- **Proposal Ingestion**: Parse and canonicalize DAO proposals from various sources (URLs, raw text)
- **Claim Extraction**: Decompose proposals into atomic, verifiable claims
- **Decentralized Validation**: Fan-out claims to multiple miners for independent validation
- **Proof of Inference (PoI)**: Measure agreement between miner responses
- **Proof of Useful Work (PoUW)**: Score miner responses based on quality rubric
- **Evidence Aggregation**: Combine miner responses into signed evidence bundles
- **On-chain Attestation**: Commit evidence hashes to blockchain for immutability

---

## 2. Data Models

### 2.1 Proposal Ingestion Response

Returned by `POST /ingest` endpoint.

```json
{
  "proposal_hash": "sha256:a3f2b8c9d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1",
  "canonical_text": "# Proposal Title\n\nThis proposal aims to allocate 50,000 USDC from the treasury...",
  "claims": [
    {
      "id": "claim_001",
      "text": "The treasury currently holds 500,000 USDC",
      "paragraph_index": 2,
      "char_range": [145, 189],
      "type": "factual",
      "canonical": "treasury_balance_usdc_500000"
    },
    {
      "id": "claim_002",
      "text": "This allocation represents 10% of total treasury funds",
      "paragraph_index": 2,
      "char_range": [191, 246],
      "type": "mathematical",
      "canonical": "allocation_percentage_10"
    }
  ]
}
```

### 2.2 Claim Object Schema

```json
{
  "id": {
    "type": "string",
    "description": "Unique identifier for the claim",
    "pattern": "^claim_[0-9]{3,}$",
    "example": "claim_001"
  },
  "text": {
    "type": "string",
    "description": "The verbatim claim text extracted from the proposal",
    "example": "The treasury currently holds 500,000 USDC"
  },
  "paragraph_index": {
    "type": "integer",
    "description": "Zero-indexed paragraph number where the claim appears",
    "minimum": 0,
    "example": 2
  },
  "char_range": {
    "type": "array",
    "description": "Character start and end positions [start, end] within the canonical text",
    "items": { "type": "integer" },
    "minItems": 2,
    "maxItems": 2,
    "example": [145, 189]
  },
  "type": {
    "type": "string",
    "description": "Classification of the claim type",
    "enum": ["factual", "mathematical", "temporal", "comparative", "procedural", "conditional"],
    "example": "factual"
  },
  "canonical": {
    "type": "string",
    "description": "Normalized identifier for the claim for deduplication",
    "example": "treasury_balance_usdc_500000"
  }
}
```

### 2.3 Miner Response Schema

Returned by individual miners during validation.

```json
{
  "miner_id": "miner_cortensor_0x1a2b3c",
  "claim_id": "claim_001",
  "verdict": "verified",
  "rationale": "Cross-referenced with on-chain treasury balance at block 18,234,567. The treasury contract 0x... shows a balance of 500,127 USDC, which rounds to the stated 500,000 USDC.",
  "evidence_links": [
    "https://etherscan.io/address/0x...",
    "ipfs://QmXyZ123..."
  ],
  "embedding": [0.123, -0.456, 0.789, "..."],
  "scores": {
    "accuracy": 0.95,
    "omission_risk": 0.10,
    "evidence_quality": 0.88,
    "governance_relevance": 0.92,
    "composite": 0.856
  }
}
```

#### Verdict Values

| Verdict | Description |
|---------|-------------|
| `verified` | Claim is factually accurate with supporting evidence |
| `refuted` | Claim is demonstrably false or misleading |
| `unverifiable` | Insufficient data to verify or refute |
| `partial` | Claim is partially correct; details in rationale |

### 2.4 Aggregated Evidence Bundle Schema

Final output combining all miner responses.

```json
{
  "proposal_hash": "sha256:a3f2b8c9d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1",
  "claims": [
    {
      "id": "claim_001",
      "text": "The treasury currently holds 500,000 USDC",
      "paragraph_index": 2,
      "char_range": [145, 189],
      "type": "factual",
      "canonical": "treasury_balance_usdc_500000"
    }
  ],
  "miners": [
    {
      "miner_id": "miner_cortensor_0x1a2b3c",
      "claim_id": "claim_001",
      "verdict": "verified",
      "rationale": "Cross-referenced with on-chain treasury balance...",
      "evidence_links": ["https://etherscan.io/address/0x..."],
      "embedding": [0.123, -0.456, 0.789],
      "scores": {
        "accuracy": 0.95,
        "omission_risk": 0.10,
        "evidence_quality": 0.88,
        "governance_relevance": 0.92,
        "composite": 0.856
      }
    }
  ],
  "aggregated_metrics": {
    "poi_agreement": 0.92,
    "poi_confidence_interval": [0.87, 0.97],
    "pouw_score": 0.834,
    "pouw_confidence_interval": [0.79, 0.88],
    "total_miners": 5,
    "responding_miners": 5,
    "consensus_verdict": "verified",
    "claim_coverage": 1.0
  },
  "recommendation": {
    "action": "approve",
    "confidence": 0.89,
    "risk_flags": [],
    "summary": "All claims verified by miner consensus with high confidence."
  },
  "ipfs_cid": "QmXyZ123abc456def789...",
  "signature": "0x1234567890abcdef..."
}
```

---

## 3. PoUW Rubric

The Proof of Useful Work (PoUW) scoring rubric evaluates miner response quality.

### 3.1 Scoring Weights

```json
{
  "rubric_version": "1.0.0",
  "weights": {
    "accuracy": 0.4,
    "omission_risk": 0.3,
    "evidence_quality": 0.2,
    "governance_relevance": 0.1
  },
  "criteria": {
    "accuracy": {
      "weight": 0.4,
      "description": "Correctness of the verdict relative to ground truth or consensus",
      "scoring": {
        "1.0": "Verdict matches ground truth with precise supporting evidence",
        "0.75": "Verdict correct but minor inaccuracies in rationale",
        "0.5": "Verdict correct but weak or incomplete justification",
        "0.25": "Verdict ambiguous or partially incorrect",
        "0.0": "Verdict demonstrably wrong"
      }
    },
    "omission_risk": {
      "weight": 0.3,
      "description": "Assessment of critical omissions or blind spots in analysis (inverted: lower is better for risk, but scored as 1 - risk_level)",
      "scoring": {
        "1.0": "Comprehensive analysis with no significant omissions",
        "0.75": "Minor omissions that don't affect verdict",
        "0.5": "Some relevant context missing but verdict still valid",
        "0.25": "Significant omissions that could affect interpretation",
        "0.0": "Critical information ignored leading to flawed analysis"
      }
    },
    "evidence_quality": {
      "weight": 0.2,
      "description": "Quality and verifiability of cited evidence",
      "scoring": {
        "1.0": "Multiple authoritative, verifiable sources with direct links",
        "0.75": "Good sources but some lack direct verifiability",
        "0.5": "Adequate sources but limited depth",
        "0.25": "Weak sources or mostly unverifiable claims",
        "0.0": "No evidence or entirely unverifiable"
      }
    },
    "governance_relevance": {
      "weight": 0.1,
      "description": "Relevance of analysis to governance decision-making",
      "scoring": {
        "1.0": "Directly addresses governance implications and voter concerns",
        "0.75": "Good governance context with minor gaps",
        "0.5": "Some governance relevance but misses key implications",
        "0.25": "Tangential to governance concerns",
        "0.0": "No governance relevance"
      }
    }
  },
  "composite_formula": "SUM(weight_i * score_i) for i in [accuracy, omission_risk, evidence_quality, governance_relevance]",
  "thresholds": {
    "excellent": 0.85,
    "good": 0.70,
    "acceptable": 0.50,
    "poor": 0.0
  }
}
```

### 3.2 Composite Score Calculation

```python
def calculate_pouw_composite(scores: dict) -> float:
    """
    Calculate PoUW composite score from individual criteria scores.
    
    Args:
        scores: Dict with keys accuracy, omission_risk, evidence_quality, governance_relevance
                Each value should be in range [0.0, 1.0]
    
    Returns:
        Composite score in range [0.0, 1.0]
    """
    weights = {
        "accuracy": 0.4,
        "omission_risk": 0.3,
        "evidence_quality": 0.2,
        "governance_relevance": 0.1
    }
    
    composite = sum(weights[k] * scores[k] for k in weights)
    return round(composite, 3)
```

---

## 4. API Endpoints

### 4.1 POST /ingest

Ingest a DAO proposal from URL or raw text and extract atomic claims.

**Request:**

```json
{
  "url": "https://snapshot.org/#/example.eth/proposal/0x123...",
  "text": null
}
```

OR

```json
{
  "url": null,
  "text": "# Proposal: Treasury Allocation\n\nThis proposal requests 50,000 USDC..."
}
```

**Response (200 OK):**

```json
{
  "proposal_hash": "sha256:a3f2b8c9d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1",
  "canonical_text": "# Proposal: Treasury Allocation\n\nThis proposal requests 50,000 USDC...",
  "claims": [
    {
      "id": "claim_001",
      "text": "This proposal requests 50,000 USDC",
      "paragraph_index": 1,
      "char_range": [35, 69],
      "type": "factual",
      "canonical": "request_amount_usdc_50000"
    }
  ]
}
```

**Error Response (400 Bad Request):**

```json
{
  "error": "validation_error",
  "message": "Either 'url' or 'text' must be provided",
  "details": null
}
```

---

### 4.2 POST /validate

Start an asynchronous validation job for a proposal.

**Request:**

```json
{
  "proposal_hash": "sha256:a3f2b8c9d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1"
}
```

**Response (202 Accepted):**

```json
{
  "job_id": "job_20241222_001",
  "proposal_hash": "sha256:a3f2b8c9d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1",
  "status": "queued",
  "created_at": "2024-12-22T00:00:00Z",
  "estimated_completion": "2024-12-22T00:05:00Z"
}
```

---

### 4.3 GET /status/{job_id}

Get the current status and partial results of a validation job.

**Response (200 OK) — In Progress:**

```json
{
  "job_id": "job_20241222_001",
  "status": "running",
  "progress": {
    "claims_total": 8,
    "claims_validated": 5,
    "miners_contacted": 10,
    "miners_responded": 7
  },
  "partial_results": [
    {
      "miner_id": "miner_cortensor_0x1a2b3c",
      "claim_id": "claim_001",
      "verdict": "verified",
      "scores": {
        "accuracy": 0.95,
        "omission_risk": 0.10,
        "evidence_quality": 0.88,
        "governance_relevance": 0.92,
        "composite": 0.856
      }
    }
  ],
  "started_at": "2024-12-22T00:00:05Z",
  "updated_at": "2024-12-22T00:02:30Z"
}
```

**Response (200 OK) — Completed:**

```json
{
  "job_id": "job_20241222_001",
  "status": "completed",
  "progress": {
    "claims_total": 8,
    "claims_validated": 8,
    "miners_contacted": 10,
    "miners_responded": 10
  },
  "completed_at": "2024-12-22T00:04:30Z",
  "ready_for_aggregation": true
}
```

---

### 4.4 POST /aggregate

Aggregate miner responses into a final evidence bundle.

**Request:**

```json
{
  "job_id": "job_20241222_001"
}
```

**Response (200 OK):**

```json
{
  "proposal_hash": "sha256:a3f2b8c9d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1",
  "claims": [ ... ],
  "miners": [ ... ],
  "aggregated_metrics": {
    "poi_agreement": 0.92,
    "poi_confidence_interval": [0.87, 0.97],
    "pouw_score": 0.834,
    "pouw_confidence_interval": [0.79, 0.88],
    "total_miners": 10,
    "responding_miners": 10,
    "consensus_verdict": "verified",
    "claim_coverage": 1.0
  },
  "recommendation": {
    "action": "approve",
    "confidence": 0.89,
    "risk_flags": [],
    "summary": "All claims verified by miner consensus with high confidence."
  },
  "ipfs_cid": "QmXyZ123abc456def789...",
  "signature": null
}
```

---

### 4.5 POST /attest

Create an on-chain attestation for an evidence bundle.

**Request:**

```json
{
  "evidence_cid": "QmXyZ123abc456def789..."
}
```

OR

```json
{
  "bundle": { ... }
}
```

**Response (200 OK):**

```json
{
  "attestation_id": "att_20241222_001",
  "evidence_cid": "QmXyZ123abc456def789...",
  "signature": "0x1234567890abcdef...",
  "signer_address": "0xXeaSignerAddress...",
  "tx_hash": null,
  "status": "signed",
  "created_at": "2024-12-22T00:05:00Z"
}
```

**Response (200 OK) — With Transaction:**

```json
{
  "attestation_id": "att_20241222_001",
  "evidence_cid": "QmXyZ123abc456def789...",
  "signature": "0x1234567890abcdef...",
  "signer_address": "0xXeaSignerAddress...",
  "tx_hash": "0xabcdef123456...",
  "tx_link": "https://etherscan.io/tx/0xabcdef123456...",
  "status": "submitted",
  "created_at": "2024-12-22T00:05:00Z"
}
```

---

## 5. Acceptance Criteria

### 5.1 Ingest Stability

| Test | Expected Result |
|------|-----------------|
| Same text input produces same hash | `proposal_hash` is deterministic SHA-256 of canonical text |
| Same URL fetched twice produces same hash | Hash stable across fetches (content unchanged) |
| Hash format | Prefix `sha256:` followed by 64 hex characters |

```python
# Test: Hash stability
response1 = client.post("/ingest", json={"text": SAMPLE_PROPOSAL})
response2 = client.post("/ingest", json={"text": SAMPLE_PROPOSAL})
assert response1["proposal_hash"] == response2["proposal_hash"]
```

### 5.2 Claim Extraction

| Test | Expected Result |
|------|-----------------|
| Typical DAO proposal (500-2000 words) | Returns 6-12 atomic claims |
| Each claim has required fields | `id`, `text`, `paragraph_index`, `char_range`, `type`, `canonical` |
| Claim types are valid enum values | One of: factual, mathematical, temporal, comparative, procedural, conditional |
| char_range is valid | `[start, end]` where `0 <= start < end <= len(canonical_text)` |

```python
# Test: Claim count and structure
response = client.post("/ingest", json={"text": SAMPLE_PROPOSAL})
claims = response["claims"]
assert 6 <= len(claims) <= 12
for claim in claims:
    assert set(claim.keys()) >= {"id", "text", "paragraph_index", "char_range", "type", "canonical"}
    assert claim["type"] in ["factual", "mathematical", "temporal", "comparative", "procedural", "conditional"]
```

### 5.3 Validation Fan-out

| Test | Expected Result |
|------|-----------------|
| /validate returns job_id | Response contains `job_id` and `status: "queued"` |
| /status shows progress | `progress` object with `claims_total`, `claims_validated`, `miners_contacted`, `miners_responded` |
| Miner responses are structured | Each response has `verdict`, `rationale`, `scores` |
| Multiple miners respond | At least 3 miners respond per claim in production |

```python
# Test: Validation job creation
response = client.post("/validate", json={"proposal_hash": hash})
assert "job_id" in response
assert response["status"] == "queued"

# Test: Status shows progress
status = client.get(f"/status/{response['job_id']}")
assert "progress" in status
assert all(k in status["progress"] for k in ["claims_total", "miners_contacted"])
```

### 5.4 Aggregation Quality

| Test | Expected Result |
|------|-----------------|
| poi_agreement in [0, 1] | Agreement score normalized to 0-1 range |
| poi_confidence_interval provided | 95% CI as `[lower, upper]` |
| pouw_score computed correctly | Weighted sum per rubric: `0.4*acc + 0.3*omit + 0.2*evid + 0.1*gov` |
| pouw_confidence_interval provided | 95% CI as `[lower, upper]` |
| consensus_verdict derived | Majority verdict across miners |

```python
# Test: Aggregation metrics
bundle = client.post("/aggregate", json={"job_id": job_id})
metrics = bundle["aggregated_metrics"]
assert 0 <= metrics["poi_agreement"] <= 1
assert len(metrics["poi_confidence_interval"]) == 2
assert 0 <= metrics["pouw_score"] <= 1
assert len(metrics["pouw_confidence_interval"]) == 2
assert metrics["consensus_verdict"] in ["verified", "refuted", "unverifiable", "partial"]
```

### 5.5 End-to-End Flow

```python
# Full pipeline test
def test_e2e_pipeline():
    # 1. Ingest
    ingest_resp = client.post("/ingest", json={"text": SAMPLE_PROPOSAL})
    assert "proposal_hash" in ingest_resp
    assert len(ingest_resp["claims"]) >= 6
    
    # 2. Validate
    validate_resp = client.post("/validate", json={"proposal_hash": ingest_resp["proposal_hash"]})
    job_id = validate_resp["job_id"]
    
    # 3. Wait for completion
    for _ in range(30):
        status = client.get(f"/status/{job_id}")
        if status["status"] == "completed":
            break
        time.sleep(1)
    assert status["status"] == "completed"
    
    # 4. Aggregate
    bundle = client.post("/aggregate", json={"job_id": job_id})
    assert bundle["aggregated_metrics"]["poi_agreement"] > 0
    assert bundle["aggregated_metrics"]["pouw_score"] > 0
    assert bundle["recommendation"]["action"] in ["approve", "reject", "review"]
```

---

## 6. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Xea Governance Oracle                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐             │
│  │   Frontend   │────▶│   Backend    │────▶│    Redis     │             │
│  │   (React)    │     │   (FastAPI)  │     │   (Queue)    │             │
│  └──────────────┘     └──────────────┘     └──────────────┘             │
│                              │                    │                      │
│                              ▼                    ▼                      │
│                       ┌──────────────┐     ┌──────────────┐             │
│                       │    IPFS      │     │   Workers    │             │
│                       │  (Storage)   │     │    (RQ)      │             │
│                       └──────────────┘     └──────────────┘             │
│                                                   │                      │
│                                                   ▼                      │
│                                          ┌───────────────┐              │
│                                          │   Cortensor   │              │
│                                          │   (Miners)    │              │
│                                          └───────────────┘              │
│                                                   │                      │
│                                                   ▼                      │
│                                          ┌───────────────┐              │
│                                          │  Blockchain   │              │
│                                          │ (Attestation) │              │
│                                          └───────────────┘              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Glossary

| Term | Definition |
|------|------------|
| **PoI** | Proof of Inference — measures agreement between independent miner responses |
| **PoUW** | Proof of Useful Work — quality scoring rubric for miner responses |
| **Claim** | Atomic, verifiable statement extracted from a proposal |
| **Miner** | Decentralized inference node that validates claims |
| **Evidence Bundle** | Aggregated validation results with signatures |
| **Attestation** | On-chain commitment to an evidence bundle hash |

---

## 8. LLM Claim Extraction

### 8.1 Claim Extraction Prompt

The following prompt is used verbatim for LLM-based claim extraction in `extract_claims_llm`:

```
You are a governance claim extractor. Given the canonical proposal text below, extract **only atomic factual and numeric claims** (exclude purely normative sentences). For each claim, produce a JSON entry with these fields:

{
  "id": "c{n}",
  "text": "<exact claim text, trimmed>",
  "paragraph_index": <0-based int>,
  "char_range": [ <start_char_index>, <end_char_index> ],
  "type": "factual" | "numeric",
  "canonical": { "numbers": [<float>], "addresses": [<eth_address>], "urls": [<url>] }
}

Rules:
- Split compound sentences into multiple claims when they assert distinct facts.
- If a sentence contains both a factual statement and a numeric parameter (e.g., "unlock 10% of treasury"), create a single claim with type "numeric" and canonical.numbers = [0.10].
- Do NOT produce commentary or extra text. Output must be a pure JSON array.
```

### 8.2 Example Input and Output

**Example Input Excerpt:**

```
The DAO treasury currently holds 500,000 USDC.
This proposal requests an allocation of 50,000 USDC, representing 10% of total funds.
The treasury address is 0x742d35Cc6634C0532925a3b844Bc9e7595f5bC12.
```

**Expected Claims Output:**

```json
[
  {
    "id": "c1",
    "text": "The DAO treasury currently holds 500,000 USDC.",
    "paragraph_index": 0,
    "char_range": [0, 46],
    "type": "numeric",
    "canonical": {
      "numbers": [500000.0],
      "addresses": [],
      "urls": []
    }
  },
  {
    "id": "c2",
    "text": "This proposal requests an allocation of 50,000 USDC, representing 10% of total funds.",
    "paragraph_index": 0,
    "char_range": [47, 132],
    "type": "numeric",
    "canonical": {
      "numbers": [50000.0, 0.10],
      "addresses": [],
      "urls": []
    }
  },
  {
    "id": "c3",
    "text": "The treasury address is 0x742d35Cc6634C0532925a3b844Bc9e7595f5bC12.",
    "paragraph_index": 0,
    "char_range": [133, 200],
    "type": "factual",
    "canonical": {
      "numbers": [],
      "addresses": ["0x742d35cc6634c0532925a3b844bc9e7595f5bc12"],
      "urls": []
    }
  }
]
```

### 8.3 Numeric Canonicalization Examples

| Input Text | `canonical.numbers` |
|------------|---------------------|
| "unlock 10% of treasury" | `[0.10]` |
| "allocate 50,000 USDC" | `[50000.0]` |
| "representing 10 percent" | `[0.10]` |
| "total of 1.5 million tokens" | `[1500000.0]` |
| "3x ROI" | `[3.0]` |
| "over the next 30 days" | `[30.0]` |

### 8.4 Address Canonicalization

- All Ethereum addresses are lowercased
- Format: `0x` followed by 40 hexadecimal characters
- Example: `0xABCdef1234...` → `0xabcdef1234...`

### 8.5 Updated Claim Schema

The `canonical` field is now an object with structured normalized values:

```json
{
  "id": "c1",
  "text": "The treasury holds 500,000 USDC",
  "paragraph_index": 0,
  "char_range": [0, 31],
  "type": "numeric",
  "canonical": {
    "numbers": [500000.0],
    "addresses": [],
    "urls": []
  }
}
```

This replaces the previous string-based canonical field for better machine processing.
