# Vigil Agent - Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Dashboard │  │Incidents │  │ Evidence │  │  Demo    │   │
│  │          │  │   List   │  │  Viewer  │  │ Controls │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │              │             │          │
│       └─────────────┴──────────────┴─────────────┘          │
│                         │                                    │
│                    WebSocket + REST API                      │
└─────────────────────────┼───────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────┐
│                    Backend (Node.js)                         │
│                         │                                    │
│  ┌──────────────────────┴─────────────────────────────┐    │
│  │              API Layer (Express)                    │    │
│  │  - REST endpoints                                   │    │
│  │  - WebSocket server (real-time metrics)            │    │
│  └──────────────────────┬─────────────────────────────┘    │
│                         │                                    │
│  ┌──────────────────────┴─────────────────────────────┐    │
│  │         Incident Manager (Orchestrator)            │    │
│  │  - State machine: detected → analyzing →           │    │
│  │    confirmed → acting → resolved                   │    │
│  └──┬────────┬────────┬────────┬────────┬────────────┘    │
│     │        │        │        │        │                   │
│  ┌──▼──┐ ┌──▼──┐ ┌───▼───┐ ┌──▼──┐ ┌──▼──────┐           │
│  │Metr │ │Cort │ │Action │ │Evid │ │Simulator│           │
│  │ics  │ │ensor│ │Execut │ │ence │ │         │           │
│  │Monit│ │Detec│ │  or   │ │Bundl│ │         │           │
│  │or   │ │tor  │ │       │ │ er  │ │         │           │
│  └──┬──┘ └──┬──┘ └───┬───┘ └──┬──┘ └─────────┘           │
│     │       │        │        │                             │
│  ┌──▼───────▼────────▼────────▼──────────────────┐        │
│  │           Database (SQLite)                    │        │
│  │  - incidents                                   │        │
│  │  - metrics_history                             │        │
│  │  - cortensor_sessions                          │        │
│  └────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────┐
│              External Integrations                           │
│                         │                                    │
│  ┌──────────┐  ┌───────▼──────┐  ┌──────────┐             │
│  │ GitHub   │  │  Cortensor   │  │ Discord  │             │
│  │  Issues  │  │   Router     │  │ Webhooks │             │
│  │          │  │  (PoI/PoUW)  │  │          │             │
│  └──────────┘  └──────────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Metrics Monitor
**Purpose:** Continuously collect network health metrics

**Metrics Tracked:**
- Latency (ms)
- Error rate (%)
- Validator score (0-1)
- Uptime (%)
- Request count

**Anomaly Detection:**
- High latency: > 2x baseline
- High error rate: > 5x baseline
- Validator score drop: < 80% baseline

**Storage:** Saves all metrics to `metrics_history` table

### 2. Cortensor Detector
**Purpose:** Validate anomalies using multi-model inference (PoI)

**Process:**
1. Receives anomaly from monitor
2. Generates analysis prompt with metrics
3. Sends to 3 different models via Cortensor router
4. Collects outputs + validator scores
5. Calculates consensus (majority vote)
6. Returns analysis result with session IDs

**PoI Implementation:**
- Models: gpt-4, claude-3, gemini-pro
- Consensus: ≥2 models must agree
- Confidence: Average of all model confidences
- PoUW: Uses validator scores to weight results

### 3. Action Executor
**Purpose:** Execute automated responses to confirmed incidents

**Actions:**
- **GitHub Issue:** Creates issue with full incident details
- **Discord Alert:** Sends webhook with embedded metrics
- **Log:** Records to console and database

**Safety Features:**
- Rate limiting: Max 1 action per incident type per 5 minutes
- Dry-run mode: Simulate actions without execution
- Error handling: Graceful failure with logging

### 4. Evidence Bundler
**Purpose:** Generate complete audit trails

**Bundle Contents:**
- Incident metadata (ID, type, severity, timestamps)
- Metrics snapshot
- Cortensor analysis (session IDs, model outputs, consensus)
- Actions taken (with results)
- Timeline of events

**Format:** JSON (exportable to IPFS)

### 5. Incident Manager
**Purpose:** Orchestrate the full workflow

**State Machine:**
```
detected → analyzing → confirmed → acting → resolved
                ↓
           (no consensus)
                ↓
            resolved
```

**Workflow:**
1. Receive metrics from monitor
2. Detect anomaly
3. Create incident record
4. Analyze with Cortensor (PoI)
5. If consensus: execute actions
6. Generate evidence bundle
7. Mark resolved

### 6. Simulator
**Purpose:** Demo mode for seamless demonstrations

**Capabilities:**
- Inject synthetic anomalies
- Simulate: high_latency, high_error_rate, validator_score_drop
- Trigger full incident cycle on demand

## Data Flow

### Normal Monitoring Loop
```
1. Monitor collects metrics (every 10s)
2. Check for anomalies
3. If none: save to history, continue
4. If anomaly: create incident → analyze → act → resolve
```

### Demo Mode Flow
```
1. User clicks "Simulate Incident" button
2. Frontend POST /api/simulate with type
3. Backend generates synthetic metrics
4. Incident manager processes (same as normal)
5. Frontend polls for updates
6. Display full cycle in real-time
```

## Database Schema

### incidents
```sql
id TEXT PRIMARY KEY
type TEXT (high_latency | high_error_rate | validator_score_drop)
status TEXT (detected | analyzing | confirmed | acting | resolved)
severity TEXT (low | medium | high | critical)
detected_at INTEGER
resolved_at INTEGER
metrics TEXT (JSON)
analysis TEXT (JSON)
actions TEXT (JSON)
evidence_bundle TEXT (JSON)
```

### metrics_history
```sql
id INTEGER PRIMARY KEY
timestamp INTEGER
latency REAL
error_rate REAL
validator_score REAL
uptime REAL
request_count INTEGER
```

### cortensor_sessions
```sql
session_id TEXT PRIMARY KEY
model TEXT
created_at INTEGER
incident_id TEXT
```

## API Endpoints

### REST
- `GET /api/metrics/current` - Current metrics
- `GET /api/metrics/history?limit=100` - Historical metrics
- `GET /api/incidents` - All incidents
- `GET /api/incidents/active` - Active incidents only
- `GET /api/incidents/:id` - Specific incident
- `POST /api/simulate` - Trigger demo incident
- `GET /api/health` - Health check

### WebSocket
- `ws://localhost:3001/ws` - Real-time metrics stream
- Sends metrics every 2 seconds
- Auto-reconnect on disconnect

## Safety Constraints

### What the Agent CAN Do:
✅ Monitor metrics (read-only)
✅ Analyze with Cortensor
✅ Create GitHub issues (if configured)
✅ Send Discord alerts (if configured)
✅ Log incidents to database

### What the Agent CANNOT Do:
❌ Modify router configuration
❌ Delete or alter historical data
❌ Execute arbitrary code
❌ Access sensitive credentials
❌ Bypass rate limits
❌ Act without multi-model consensus

### Rate Limits:
- Max 1 GitHub issue per incident type per 5 minutes
- Max 1 Discord alert per incident type per 5 minutes
- No limit on logging

### Human-in-Loop:
- All actions are logged with timestamps
- Evidence bundles provide full audit trail
- Dry-run mode available for testing
- Manual approval can be added via config

## Deployment

### Development
```bash
# Terminal 1
cd backend && npm install && npm run dev

# Terminal 2
cd frontend && npm install && npm run dev
```

### Production (Docker)
```bash
docker-compose up -d
```

### Environment Variables
See `backend/.env.example` for required configuration.

## Cortensor Integration Points

1. **Session Management:** Creates persistent sessions per model
2. **PoI Validation:** Runs same prompt across 3+ models
3. **PoUW Scoring:** Uses validator scores to weight confidence
4. **Evidence Trails:** Stores all session IDs for audit
5. **Router Health:** Monitors router metrics directly

## Future Enhancements

- [ ] ERC-8004 agent identity artifacts
- [ ] x402 payment flows for premium alerts
- [ ] MCP tool interface compatibility
- [ ] /validate endpoint integration
- [ ] IPFS storage for evidence bundles
- [ ] Telegram bot integration
- [ ] Custom alert rules engine
- [ ] Multi-router monitoring
