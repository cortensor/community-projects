# How to Validate Xea Output

This guide explains how to verify the integrity and correctness of Xea Governance Oracle outputs.

## Overview

Xea produces three levels of verifiable output:

1. **Proposal Hash** — Deterministic hash of canonical proposal text
2. **Evidence Bundle** — Aggregated miner responses with metrics
3. **On-chain Attestation** — Immutable commitment to evidence hash

## 1. Verifying Proposal Hash

The proposal hash is a SHA-256 hash of the canonicalized proposal text.

### Manual Verification

```bash
# Given canonical_text from /ingest response
echo -n "Your canonical text here" | sha256sum
```

### Programmatic Verification

```python
import hashlib

def verify_proposal_hash(canonical_text: str, claimed_hash: str) -> bool:
    """Verify proposal hash matches canonical text."""
    computed = "sha256:" + hashlib.sha256(
        canonical_text.encode("utf-8")
    ).hexdigest()
    return computed == claimed_hash
```

### Acceptance Criteria

- Same text always produces same hash
- Hash format: `sha256:<64 hex characters>`
- Canonicalization is deterministic (trailing whitespace stripped)

## 2. Verifying Evidence Bundle

The evidence bundle contains all miner responses and aggregated metrics.

### PoI Agreement Verification

```python
def verify_poi_agreement(responses: list, claim_id: str) -> float:
    """Manually verify PoI agreement score."""
    claim_responses = [r for r in responses if r["claim_id"] == claim_id]
    
    if not claim_responses:
        return 0.0
    
    verdicts = [r["verdict"] for r in claim_responses]
    verdict_counts = {}
    for v in verdicts:
        verdict_counts[v] = verdict_counts.get(v, 0) + 1
    
    max_count = max(verdict_counts.values())
    return max_count / len(verdicts)
```

### PoUW Score Verification

```python
WEIGHTS = {
    "accuracy": 0.4,
    "omission_risk": 0.3,
    "evidence_quality": 0.2,
    "governance_relevance": 0.1,
}

def verify_pouw_composite(scores: dict) -> float:
    """Manually verify PoUW composite score."""
    return sum(WEIGHTS[k] * scores[k] for k in WEIGHTS)
```

### Confidence Interval Verification

```python
import statistics

def verify_confidence_interval(values: list, confidence: float = 0.95) -> tuple:
    """Verify 95% confidence interval calculation."""
    if len(values) < 2:
        return (values[0] if values else 0, values[0] if values else 0)
    
    mean = statistics.mean(values)
    stdev = statistics.stdev(values)
    n = len(values)
    
    # z-score for 95% CI
    z = 1.96
    margin = z * (stdev / (n ** 0.5))
    
    return (max(0, mean - margin), min(1, mean + margin))
```

## 3. Verifying IPFS CID

If the evidence bundle is stored on IPFS:

```bash
# Fetch and verify content matches
ipfs cat <CID> > bundle.json

# Compute hash and compare
sha256sum bundle.json
```

## 4. Verifying On-chain Attestation

### Read from Contract

```javascript
const contract = new ethers.Contract(ATTESTATION_ADDRESS, ABI, provider);

const { exists, timestamp, signer } = await contract.verify(evidenceHash);

console.log("Attestation exists:", exists);
console.log("Created at:", new Date(timestamp * 1000));
console.log("Signed by:", signer);
```

### Verify Signature

```python
from eth_account import Account
from eth_account.messages import encode_defunct

def verify_attestation_signature(
    evidence_hash: str,
    signature: str,
    expected_signer: str
) -> bool:
    """Verify evidence was signed by expected address."""
    message = encode_defunct(text=evidence_hash)
    recovered = Account.recover_message(message, signature=signature)
    return recovered.lower() == expected_signer.lower()
```

## Validation Checklist

### For Judges/Auditors

| Check | Method | Expected |
|-------|--------|----------|
| Hash stability | Ingest same text twice | Identical hashes |
| Claim extraction | Count claims for typical proposal | 6-12 claims |
| Claim structure | Inspect claim objects | All required fields present |
| PoI calculation | Manual calculation | Matches reported value |
| PoUW calculation | Apply weights formula | Matches reported composite |
| CI calculation | Statistical verification | Contains actual mean |
| IPFS content | Fetch and hash | Matches evidence_cid |
| Signature | Recover signer | Matches reported address |

### Automated Validation

Run the test suite:

```bash
cd tests
pytest -v

# Specific validation tests
pytest test_aggregator.py -v
pytest test_e2e_mock.py -v
```

## Common Issues

### Hash Mismatch

- Check text encoding (must be UTF-8)
- Verify canonicalization (trailing whitespace)
- Ensure no invisible characters

### PoUW Mismatch

- Verify weight values (0.4, 0.3, 0.2, 0.1)
- Check rounding (3 decimal places)
- Ensure all score components present

### Signature Invalid

- Verify evidence hash format
- Check signer address case sensitivity
- Ensure correct chain/network

## Support

For validation issues, file a GitHub issue with:
1. Input data used
2. Expected vs actual output
3. Verification steps attempted
