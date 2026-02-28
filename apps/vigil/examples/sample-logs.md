# Sample Agent Runtime Logs

## Incident Detection and Response Cycle

### 1. Initial Detection
```
[2026-02-27T06:52:15.234Z] [INFO] Starting background monitoring...
[2026-02-27T06:52:15.235Z] [INFO] Metrics monitor initialized
[2026-02-27T06:52:15.236Z] [INFO] Cortensor client connected
[2026-02-27T06:52:25.123Z] [METRICS] Latency: 98.5ms, Error Rate: 0.8%, Validator Score: 0.912
[2026-02-27T06:52:35.456Z] [METRICS] Latency: 342.7ms, Error Rate: 1.2%, Validator Score: 0.908
[2026-02-27T06:52:35.457Z] [ALERT] Anomaly detected: high_latency (342.7ms > 200ms threshold)
[2026-02-27T06:52:35.458Z] [INCIDENT] Created incident_1709012755458 - Type: high_latency, Severity: high
```

### 2. Cortensor Analysis (PoI)
```
[2026-02-27T06:52:35.500Z] [CORTENSOR] Starting multi-model analysis...
[2026-02-27T06:52:35.501Z] [CORTENSOR] Sending prompt to gpt-4...
[2026-02-27T06:52:36.234Z] [CORTENSOR] Session created: session_1709012756234_gpt4
[2026-02-27T06:52:36.890Z] [CORTENSOR] gpt-4 response: {"isAnomaly":true,"confidence":0.87,"reasoning":"Latency shows significant deviation..."}
[2026-02-27T06:52:36.891Z] [CORTENSOR] Validator score: 0.923

[2026-02-27T06:52:36.900Z] [CORTENSOR] Sending prompt to claude-3...
[2026-02-27T06:52:37.123Z] [CORTENSOR] Session created: session_1709012757123_claude3
[2026-02-27T06:52:37.678Z] [CORTENSOR] claude-3 response: {"isAnomaly":true,"confidence":0.91,"reasoning":"Analysis confirms anomalous latency pattern..."}
[2026-02-27T06:52:37.679Z] [CORTENSOR] Validator score: 0.918

[2026-02-27T06:52:37.690Z] [CORTENSOR] Sending prompt to gemini-pro...
[2026-02-27T06:52:38.012Z] [CORTENSOR] Session created: session_1709012758012_geminipro
[2026-02-27T06:52:38.456Z] [CORTENSOR] gemini-pro response: {"isAnomaly":true,"confidence":0.84,"reasoning":"Detected high latency event..."}
[2026-02-27T06:52:38.457Z] [CORTENSOR] Validator score: 0.915

[2026-02-27T06:52:38.500Z] [CORTENSOR] Analysis complete
[2026-02-27T06:52:38.501Z] [CORTENSOR] Consensus: YES (3/3 models agree)
[2026-02-27T06:52:38.502Z] [CORTENSOR] Average confidence: 0.873
[2026-02-27T06:52:38.503Z] [CORTENSOR] Average validator score: 0.919
```

### 3. Action Execution
```
[2026-02-27T06:52:38.600Z] [ACTION] Incident confirmed, executing actions...
[2026-02-27T06:52:38.601Z] [ACTION] Checking rate limits...
[2026-02-27T06:52:38.602Z] [ACTION] Rate limit OK for high_latency

[2026-02-27T06:52:38.700Z] [GITHUB] Creating issue for incident_1709012755458...
[2026-02-27T06:52:39.234Z] [GITHUB] Issue created: https://github.com/cortensor/network/issues/42
[2026-02-27T06:52:39.235Z] [ACTION] github_issue: EXECUTED

[2026-02-27T06:52:39.300Z] [DISCORD] Sending alert webhook...
[2026-02-27T06:52:39.567Z] [DISCORD] Alert sent successfully
[2026-02-27T06:52:39.568Z] [ACTION] discord_alert: EXECUTED

[2026-02-27T06:52:39.600Z] [LOG] Incident logged to database
[2026-02-27T06:52:39.601Z] [ACTION] log: EXECUTED
```

### 4. Evidence Bundle Generation
```
[2026-02-27T06:52:39.700Z] [EVIDENCE] Generating evidence bundle...
[2026-02-27T06:52:39.701Z] [EVIDENCE] Collecting metrics snapshot
[2026-02-27T06:52:39.702Z] [EVIDENCE] Collecting analysis results
[2026-02-27T06:52:39.703Z] [EVIDENCE] Collecting action results
[2026-02-27T06:52:39.704Z] [EVIDENCE] Building timeline
[2026-02-27T06:52:39.750Z] [EVIDENCE] Evidence bundle complete
[2026-02-27T06:52:39.751Z] [EVIDENCE] Session IDs: 3
[2026-02-27T06:52:39.752Z] [EVIDENCE] Actions: 3
[2026-02-27T06:52:39.753Z] [EVIDENCE] Timeline events: 6
```

### 5. Resolution
```
[2026-02-27T06:52:39.800Z] [INCIDENT] Incident incident_1709012755458 resolved
[2026-02-27T06:52:39.801Z] [INCIDENT] Duration: 4343ms
[2026-02-27T06:52:39.802Z] [INCIDENT] Status: detected → analyzing → confirmed → acting → resolved
[2026-02-27T06:52:39.803Z] [INCIDENT] Evidence bundle saved to database
```

---

## Sample API Request/Response

### Simulate Incident
```bash
curl -X POST http://localhost:3001/api/simulate \
  -H "Content-Type: application/json" \
  -d '{"type":"high_latency"}'
```

**Response:**
```json
{
  "success": true,
  "incident": {
    "id": "incident_1709012755458",
    "type": "high_latency",
    "status": "detected",
    "severity": "high",
    "detectedAt": 1709012755458,
    "metrics": {
      "timestamp": 1709012755458,
      "latency": 342.7,
      "errorRate": 0.012,
      "validatorScore": 0.908,
      "uptime": 99.9,
      "requestCount": 1047
    },
    "actions": []
  }
}
```

### Get Incident Details
```bash
curl http://localhost:3001/api/incidents/incident_1709012755458
```

**Response:**
```json
{
  "id": "incident_1709012755458",
  "type": "high_latency",
  "status": "resolved",
  "severity": "high",
  "detectedAt": 1709012755458,
  "resolvedAt": 1709012759801,
  "metrics": {
    "timestamp": 1709012755458,
    "latency": 342.7,
    "errorRate": 0.012,
    "validatorScore": 0.908,
    "uptime": 99.9,
    "requestCount": 1047
  },
  "analysis": {
    "sessionIds": [
      "session_1709012756234_gpt4",
      "session_1709012757123_claude3",
      "session_1709012758012_geminipro"
    ],
    "modelOutputs": [
      {
        "model": "gpt-4",
        "output": "{\"isAnomaly\":true,\"confidence\":0.87,\"reasoning\":\"Latency shows significant deviation from baseline...\"}",
        "isAnomaly": true,
        "confidence": 0.87,
        "validatorScore": 0.923
      },
      {
        "model": "claude-3",
        "output": "{\"isAnomaly\":true,\"confidence\":0.91,\"reasoning\":\"Analysis confirms anomalous latency pattern...\"}",
        "isAnomaly": true,
        "confidence": 0.91,
        "validatorScore": 0.918
      },
      {
        "model": "gemini-pro",
        "output": "{\"isAnomaly\":true,\"confidence\":0.84,\"reasoning\":\"Detected high latency event...\"}",
        "isAnomaly": true,
        "confidence": 0.84,
        "validatorScore": 0.915
      }
    ],
    "consensus": true,
    "confidence": 0.873,
    "validatorScores": [0.923, 0.918, 0.915],
    "timestamp": 1709012758503
  },
  "actions": [
    {
      "type": "github_issue",
      "status": "executed",
      "timestamp": 1709012759235,
      "result": {
        "issueUrl": "https://github.com/cortensor/network/issues/42"
      }
    },
    {
      "type": "discord_alert",
      "status": "executed",
      "timestamp": 1709012759568,
      "result": {
        "sent": true
      }
    },
    {
      "type": "log",
      "status": "executed",
      "timestamp": 1709012759601,
      "result": {
        "logged": true
      }
    }
  ],
  "evidenceBundle": {
    "incidentId": "incident_1709012755458",
    "timestamp": 1709012759750,
    "metrics": { /* ... */ },
    "analysis": { /* ... */ },
    "actions": [ /* ... */ ],
    "timeline": [
      {
        "timestamp": 1709012755458,
        "event": "Incident Detected",
        "details": { "type": "high_latency", "severity": "high" }
      },
      {
        "timestamp": 1709012758503,
        "event": "Analysis Completed",
        "details": { "consensus": true, "confidence": 0.873, "models": 3 }
      },
      {
        "timestamp": 1709012759235,
        "event": "Action: github_issue",
        "details": { "status": "executed" }
      },
      {
        "timestamp": 1709012759568,
        "event": "Action: discord_alert",
        "details": { "status": "executed" }
      },
      {
        "timestamp": 1709012759601,
        "event": "Action: log",
        "details": { "status": "executed" }
      },
      {
        "timestamp": 1709012759801,
        "event": "Incident Resolved",
        "details": { "duration": 4343 }
      }
    ]
  }
}
```

---

## WebSocket Stream Sample

```
Connected to ws://localhost:3001/ws

→ {"type":"metrics","data":{"timestamp":1709012755000,"latency":98.5,"errorRate":0.008,"validatorScore":0.912,"uptime":99.9,"requestCount":1045}}

→ {"type":"metrics","data":{"timestamp":1709012757000,"latency":102.3,"errorRate":0.009,"validatorScore":0.910,"uptime":99.9,"requestCount":1046}}

→ {"type":"metrics","data":{"timestamp":1709012759000,"latency":342.7,"errorRate":0.012,"validatorScore":0.908,"uptime":99.9,"requestCount":1047}}

→ {"type":"metrics","data":{"timestamp":1709012761000,"latency":105.1,"errorRate":0.008,"validatorScore":0.911,"uptime":99.9,"requestCount":1048}}
```

---

## Database Queries

### Recent Incidents
```sql
SELECT id, type, status, severity, detected_at, resolved_at
FROM incidents
ORDER BY detected_at DESC
LIMIT 10;
```

**Result:**
```
incident_1709012755458 | high_latency | resolved | high | 1709012755458 | 1709012759801
incident_1709012650123 | high_error_rate | resolved | critical | 1709012650123 | 1709012654567
incident_1709012540789 | validator_score_drop | resolved | medium | 1709012540789 | 1709012543210
```

### Metrics History
```sql
SELECT timestamp, latency, error_rate, validator_score
FROM metrics_history
WHERE timestamp > strftime('%s', 'now', '-1 hour') * 1000
ORDER BY timestamp DESC
LIMIT 100;
```

---

## Performance Metrics

- **Detection Time:** < 1 second
- **Analysis Time:** 2-3 seconds (3 models in parallel)
- **Action Execution:** 1-2 seconds
- **Total Incident Cycle:** 4-5 seconds
- **WebSocket Latency:** < 50ms
- **Database Write:** < 10ms

---

## Error Handling Examples

### Rate Limit Hit
```
[2026-02-27T06:53:00.123Z] [ACTION] Rate limit check failed for high_latency
[2026-02-27T06:53:00.124Z] [ACTION] Last action was 2 minutes ago (limit: 5 minutes)
[2026-02-27T06:53:00.125Z] [ACTION] Skipping GitHub issue creation
[2026-02-27T06:53:00.126Z] [ACTION] Incident logged only
```

### Model Failure
```
[2026-02-27T06:53:10.234Z] [CORTENSOR] Sending prompt to gpt-4...
[2026-02-27T06:53:11.567Z] [ERROR] gpt-4 request failed: Connection timeout
[2026-02-27T06:53:11.568Z] [CORTENSOR] Continuing with remaining models...
[2026-02-27T06:53:11.569Z] [CORTENSOR] Sending prompt to claude-3...
[2026-02-27T06:53:12.123Z] [CORTENSOR] claude-3 response received
[2026-02-27T06:53:12.124Z] [CORTENSOR] Sending prompt to gemini-pro...
[2026-02-27T06:53:12.678Z] [CORTENSOR] gemini-pro response received
[2026-02-27T06:53:12.679Z] [CORTENSOR] Consensus: YES (2/2 models agree)
```

### No Consensus
```
[2026-02-27T06:53:20.123Z] [CORTENSOR] Analysis complete
[2026-02-27T06:53:20.124Z] [CORTENSOR] Consensus: NO (1/3 models agree)
[2026-02-27T06:53:20.125Z] [INCIDENT] No consensus reached, marking as resolved without action
[2026-02-27T06:53:20.126Z] [INCIDENT] Incident logged for review
```
