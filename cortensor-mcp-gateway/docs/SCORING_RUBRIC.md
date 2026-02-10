# Cortensor MCP Gateway - Scoring Rubric

This document defines the scoring and validation policies used by the Agent Swarm.

## Consensus Scoring

The consensus score determines if miner responses are sufficiently aligned.

### Score Calculation

```
consensus_score = agreement_count / total_miners
```

Where:
- `agreement_count`: Number of miners whose responses match the majority
- `total_miners`: Total number of miners that responded

### Thresholds

| Score | Status | Action |
|-------|--------|--------|
| >= 0.66 | VERIFIED | Accept result, mark as verified |
| 0.50 - 0.65 | WARNING | Accept with warning, flag for review |
| < 0.50 | REJECTED | Reject result, require re-execution |

### Default Threshold

The default consensus threshold is `0.66` (two-thirds majority).

## Validation Rubric

The ValidatorAgent evaluates inference results using the following criteria:

### 1. Response Completeness (25%)

- Does the response address the prompt?
- Are all required components present?
- Is the response appropriately detailed?

### 2. Consensus Quality (25%)

- Is consensus score above threshold?
- Are divergent miners identified?
- Is the agreement count sufficient?

### 3. Response Consistency (25%)

- Do miner responses agree semantically?
- Are there contradictory statements?
- Is the majority response coherent?

### 4. Execution Integrity (25%)

- Did all execution steps complete?
- Are timestamps monotonically increasing?
- Is the audit trail complete?

## Evidence Bundle Validation

Evidence bundles are validated using SHA-256 cryptographic hashing.

### Integrity Check

```python
def verify_integrity(bundle, expected_hash):
    computed_hash = sha256(canonical_json(bundle)).hexdigest()
    return computed_hash == expected_hash
```

### Required Fields

All evidence bundles MUST contain:

| Field | Type | Description |
|-------|------|-------------|
| `bundle_id` | string | Unique identifier (eb-XXXX format) |
| `task_id` | string | Reference to original task |
| `created_at` | ISO8601 | Bundle creation timestamp |
| `execution_steps` | array | List of execution steps |
| `miner_responses` | array | Miner response metadata |
| `consensus_info` | object | Consensus calculation details |
| `validation_result` | object | Validation outcome |
| `hash` | string | SHA-256 integrity hash |

### Hash Computation

The integrity hash is computed over the following fields:
- `bundle_id`
- `task_id`
- `created_at`
- `execution_steps`
- `miner_responses`
- `consensus_info`
- `validation_result`
- `final_output`

## Cross-Run Validation

For high-stakes decisions, multiple independent runs can be compared:

```python
def cross_run_validate(runs, min_agreement=0.8):
    """Validate consistency across multiple inference runs."""
    responses = [r.content for r in runs]
    similarity = compute_semantic_similarity(responses)
    return similarity >= min_agreement
```

## Divergent Miner Handling

When miners disagree:

1. **Identify**: Flag miners with responses that differ from majority
2. **Log**: Record divergent responses in evidence bundle
3. **Analyze**: Check if divergence is semantic or superficial
4. **Report**: Include `divergent_miners` list in consensus info

## Safety Guardrails

### Input Validation

- Reject prompts exceeding max token limit
- Sanitize inputs to prevent injection
- Rate limit requests per session

### Output Validation

- Verify response length within bounds
- Check for prohibited content patterns
- Validate JSON structure for structured outputs

### Execution Constraints

- Timeout after configured duration (default: 60s)
- Maximum retry attempts: 3
- Fail-safe to mock mode if network unavailable

## Example Validation Flow

```
1. Receive inference request
2. Execute on multiple miners (PoI)
3. Collect responses
4. Calculate consensus score
5. If score >= 0.66:
   - Mark as VERIFIED
   - Generate evidence bundle
   - Compute integrity hash
6. If score < 0.66:
   - Mark as UNVERIFIED
   - Flag divergent miners
   - Optionally retry
7. Return result with audit trail
```
