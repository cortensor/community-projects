# Cortensor PoI Rubric and Validation

## Anomaly Detection Rubric

This document describes the rubric used by the agent to validate anomalies through Cortensor's Proof of Inference (PoI).

### Prompt Template

```
Analyze this network incident:
Type: {incident_type}
Metrics: {metrics_json}

Is this a genuine anomaly requiring action? Respond with JSON:
{
  "isAnomaly": boolean,
  "confidence": number (0-1),
  "reasoning": string
}
```

### Example Prompts

#### High Latency Incident
```
Analyze this network incident:
Type: high_latency
Metrics: {
  "timestamp": 1709012755458,
  "latency": 342.7,
  "errorRate": 0.012,
  "validatorScore": 0.908,
  "uptime": 99.9,
  "requestCount": 1047,
  "baseline": {
    "latency": 100,
    "errorRate": 0.01,
    "validatorScore": 0.9
  }
}

Is this a genuine anomaly requiring action? Respond with JSON:
{
  "isAnomaly": boolean,
  "confidence": number (0-1),
  "reasoning": string
}
```

#### High Error Rate Incident
```
Analyze this network incident:
Type: high_error_rate
Metrics: {
  "timestamp": 1709012650123,
  "latency": 105.3,
  "errorRate": 0.089,
  "validatorScore": 0.905,
  "uptime": 99.8,
  "requestCount": 1023,
  "baseline": {
    "latency": 100,
    "errorRate": 0.01,
    "validatorScore": 0.9
  }
}

Is this a genuine anomaly requiring action? Respond with JSON:
{
  "isAnomaly": boolean,
  "confidence": number (0-1),
  "reasoning": string
}
```

---

## Scoring Policy

### Multi-Model Consensus

The agent uses **majority voting** across 3 models:
- gpt-4
- claude-3
- gemini-pro

**Consensus Rules:**
- ✅ **Action Taken:** ≥2 models agree it's an anomaly
- ❌ **No Action:** <2 models agree
- 📊 **Confidence:** Average of all model confidence scores

### Validator Score Weighting (PoUW)

Each model's output is weighted by its validator score:

```typescript
weightedConfidence = (
  model1.confidence * model1.validatorScore +
  model2.confidence * model2.validatorScore +
  model3.confidence * model3.validatorScore
) / (
  model1.validatorScore +
  model2.validatorScore +
  model3.validatorScore
)
```

**Example:**
```
Model 1: confidence=0.87, validatorScore=0.923
Model 2: confidence=0.91, validatorScore=0.918
Model 3: confidence=0.84, validatorScore=0.915

Weighted = (0.87*0.923 + 0.91*0.918 + 0.84*0.915) / (0.923 + 0.918 + 0.915)
         = (0.803 + 0.835 + 0.769) / 2.756
         = 2.407 / 2.756
         = 0.873
```

### Severity Classification

Based on deviation from baseline:

| Metric | Medium | High | Critical |
|--------|--------|------|----------|
| Latency | 2x baseline | 3x baseline | 5x baseline |
| Error Rate | 5x baseline | 10x baseline | 20x baseline |
| Validator Score | <85% baseline | <70% baseline | <50% baseline |

**Example:**
- Baseline latency: 100ms
- Current latency: 342ms
- Deviation: 3.42x
- **Severity: HIGH**

---

## Cross-Run Validation

### Multiple Incident Types

The agent validates consistency across different incident types:

```json
{
  "incident_1": {
    "type": "high_latency",
    "consensus": true,
    "confidence": 0.873,
    "models_agree": 3
  },
  "incident_2": {
    "type": "high_error_rate",
    "consensus": true,
    "confidence": 0.891,
    "models_agree": 3
  },
  "incident_3": {
    "type": "validator_score_drop",
    "consensus": false,
    "confidence": 0.623,
    "models_agree": 1
  }
}
```

**Validation:**
- ✅ Incidents 1 & 2: High confidence + consensus → Action taken
- ❌ Incident 3: Low confidence + no consensus → No action

### Temporal Validation

Check for repeated incidents of same type:

```json
{
  "incident_type": "high_latency",
  "occurrences": [
    {
      "timestamp": 1709012755458,
      "consensus": true,
      "action_taken": true
    },
    {
      "timestamp": 1709012855458,
      "consensus": true,
      "action_taken": false,
      "reason": "Rate limited (5 min window)"
    },
    {
      "timestamp": 1709013055458,
      "consensus": true,
      "action_taken": true,
      "reason": "Rate limit expired"
    }
  ]
}
```

---

## Evidence Bundle Validation

### Required Fields

Every evidence bundle must contain:

```typescript
interface EvidenceBundle {
  incidentId: string;              // ✅ Required
  timestamp: number;               // ✅ Required
  metrics: MetricsSnapshot;        // ✅ Required
  analysis: {
    sessionIds: string[];          // ✅ Required (Cortensor sessions)
    modelOutputs: ModelOutput[];   // ✅ Required (≥2 models)
    consensus: boolean;            // ✅ Required
    confidence: number;            // ✅ Required (0-1)
    validatorScores: number[];     // ✅ Required (PoUW)
  };
  actions: Action[];               // ✅ Required
  timeline: TimelineEvent[];       // ✅ Required
}
```

### Validation Checks

1. **Session ID Format:**
   ```
   session_{timestamp}_{model_name}
   Example: session_1709012756234_gpt4
   ```

2. **Consensus Logic:**
   ```typescript
   const anomalyVotes = modelOutputs.filter(m => m.isAnomaly).length;
   const consensus = anomalyVotes >= 2; // Majority
   ```

3. **Confidence Range:**
   ```typescript
   0 <= confidence <= 1
   ```

4. **Validator Score Range:**
   ```typescript
   0 <= validatorScore <= 1
   ```

5. **Timeline Ordering:**
   ```typescript
   timeline.every((event, i) => 
     i === 0 || event.timestamp >= timeline[i-1].timestamp
   )
   ```

---

## Verification Examples

### Valid Evidence Bundle
```json
{
  "incidentId": "incident_1709012755458",
  "timestamp": 1709012759750,
  "metrics": {
    "latency": 342.7,
    "errorRate": 0.012,
    "validatorScore": 0.908
  },
  "analysis": {
    "sessionIds": [
      "session_1709012756234_gpt4",
      "session_1709012757123_claude3",
      "session_1709012758012_geminipro"
    ],
    "modelOutputs": [
      {"model": "gpt-4", "isAnomaly": true, "confidence": 0.87, "validatorScore": 0.923},
      {"model": "claude-3", "isAnomaly": true, "confidence": 0.91, "validatorScore": 0.918},
      {"model": "gemini-pro", "isAnomaly": true, "confidence": 0.84, "validatorScore": 0.915}
    ],
    "consensus": true,
    "confidence": 0.873,
    "validatorScores": [0.923, 0.918, 0.915]
  },
  "actions": [
    {"type": "github_issue", "status": "executed"},
    {"type": "discord_alert", "status": "executed"},
    {"type": "log", "status": "executed"}
  ],
  "timeline": [
    {"timestamp": 1709012755458, "event": "Incident Detected"},
    {"timestamp": 1709012758503, "event": "Analysis Completed"},
    {"timestamp": 1709012759235, "event": "Action: github_issue"},
    {"timestamp": 1709012759568, "event": "Action: discord_alert"},
    {"timestamp": 1709012759601, "event": "Action: log"},
    {"timestamp": 1709012759801, "event": "Incident Resolved"}
  ]
}
```

**Validation Result:** ✅ PASS
- All required fields present
- 3 session IDs (PoI)
- Consensus achieved (3/3 models)
- Confidence in valid range (0.873)
- Validator scores present (PoUW)
- Timeline properly ordered
- Actions executed

### Invalid Evidence Bundle (No Consensus)
```json
{
  "incidentId": "incident_1709012850000",
  "analysis": {
    "sessionIds": ["session_1", "session_2", "session_3"],
    "modelOutputs": [
      {"model": "gpt-4", "isAnomaly": true, "confidence": 0.65},
      {"model": "claude-3", "isAnomaly": false, "confidence": 0.72},
      {"model": "gemini-pro", "isAnomaly": false, "confidence": 0.68}
    ],
    "consensus": false,
    "confidence": 0.683
  },
  "actions": []
}
```

**Validation Result:** ✅ PASS (but no action taken)
- Consensus: NO (1/3 models)
- Actions: None (correct behavior)
- Incident logged for review

---

## IPFS Storage Format

Evidence bundles are formatted for IPFS storage:

```bash
# Generate IPFS-ready bundle
cat evidence-bundle.json | ipfs add

# Result
added QmXxxx... evidence-bundle.json
```

**Metadata:**
```json
{
  "version": "1.0",
  "agent": "incident-commander",
  "cortensor_network": "mainnet",
  "ipfs_hash": "QmXxxx...",
  "timestamp": 1709012759750,
  "incident_id": "incident_1709012755458"
}
```

---

## Audit Trail Verification

### Verify Cortensor Sessions

```bash
# Check session exists on Cortensor router
curl https://api.cortensor.network/sessions/session_1709012756234_gpt4

# Response
{
  "sessionId": "session_1709012756234_gpt4",
  "model": "gpt-4",
  "timestamp": 1709012756234,
  "validatorScore": 0.923,
  "status": "completed"
}
```

### Verify GitHub Issue

```bash
# Check issue was created
curl https://api.github.com/repos/cortensor/network/issues/42

# Response
{
  "number": 42,
  "title": "[Incident] HIGH LATENCY",
  "state": "open",
  "created_at": "2026-02-27T06:52:39Z",
  "labels": ["incident", "high"]
}
```

### Verify Discord Alert

Check Discord channel for webhook message with:
- Incident type
- Severity color
- Metrics snapshot
- Timestamp

---

## Summary

The agent uses a **multi-layered validation approach**:

1. **Threshold Detection:** Initial anomaly identification
2. **Multi-Model PoI:** 3 models validate independently
3. **Consensus Voting:** Majority agreement required
4. **Validator Weighting:** PoUW scores weight confidence
5. **Rate Limiting:** Prevents spam
6. **Evidence Bundles:** Complete audit trails
7. **External Verification:** Cortensor sessions, GitHub issues, Discord alerts

This ensures **high confidence, low false positives, and complete auditability**.
