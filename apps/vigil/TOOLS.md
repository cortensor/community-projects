# Agent Tools & Capabilities

## What the Agent Can Do

### 1. Monitoring Tools
- **Metrics Collection**: Continuously gather network health data
  - Latency measurements (ms)
  - Error rate tracking (%)
  - Validator score monitoring (0-1)
  - Uptime percentage
  - Request count
- **Historical Analysis**: Store and query metrics history
- **Real-time Streaming**: WebSocket-based live metrics feed

### 2. Detection Tools
- **Threshold-based Detection**: Identify anomalies using configurable thresholds
  - High latency: > 2x baseline
  - High error rate: > 5x baseline
  - Validator score drop: < 80% baseline
- **Pattern Recognition**: Detect trends and correlations across metrics
- **Severity Classification**: Categorize incidents (low, medium, high, critical)

### 3. Analysis Tools (Cortensor Integration)
- **Multi-Model Validation (PoI)**: Run same analysis across 3+ models
  - gpt-4
  - claude-3
  - gemini-pro
- **Consensus Calculation**: Majority vote across model outputs
- **Confidence Scoring**: Weighted average of model confidences
- **Validator Scoring (PoUW)**: Use validator scores to weight results
- **Session Management**: Track all Cortensor session IDs for audit

### 4. Action Tools
- **GitHub Integration**:
  - Create issues with full incident details
  - Add labels (incident, severity)
  - Include metrics, analysis, and evidence
- **Discord Integration**:
  - Send webhook alerts with embedded metrics
  - Color-coded by severity
  - Real-time notifications
- **Logging**:
  - Console output
  - Database persistence
  - Structured JSON logs

### 5. Evidence Tools
- **Bundle Generation**: Create complete audit trails
  - Incident metadata
  - Metrics snapshots
  - Cortensor analysis results
  - Actions taken
  - Timeline of events
- **JSON Export**: Structured, machine-readable format
- **IPFS Ready**: Format compatible with IPFS storage

### 6. Demo Tools
- **Incident Simulation**: Generate synthetic anomalies
  - High latency
  - High error rate
  - Validator score drop
- **Replay Mode**: Re-run historical incidents
- **Speed Controls**: Adjust playback speed for demos

## Safety Constraints

### What the Agent CANNOT Do

❌ **Modify Router Configuration**
- Cannot change router settings
- Cannot update validator parameters
- Cannot alter network topology

❌ **Delete or Alter Historical Data**
- Cannot modify past incidents
- Cannot delete metrics history
- Cannot tamper with evidence bundles

❌ **Execute Arbitrary Code**
- Cannot run shell commands
- Cannot modify system files
- Cannot install packages

❌ **Access Sensitive Credentials**
- Cannot read environment variables beyond configured ones
- Cannot access filesystem outside data directory
- Cannot make unauthorized API calls

❌ **Bypass Safety Mechanisms**
- Cannot override rate limits
- Cannot skip multi-model consensus
- Cannot act without validation

❌ **Spam or Abuse**
- Rate limited to 1 action per incident type per 5 minutes
- Cannot create duplicate issues
- Cannot flood Discord channels

### Required Conditions for Actions

✅ **GitHub Issue Creation**:
- Multi-model consensus (≥2 models agree)
- Severity: high or critical
- Rate limit not exceeded
- Valid GitHub token configured

✅ **Discord Alerts**:
- Multi-model consensus
- Rate limit not exceeded
- Valid webhook URL configured

✅ **Incident Logging**:
- Always allowed (read-only)
- No rate limits

### Human-in-Loop Points

🔒 **Manual Approval Required For**:
- None by default (fully autonomous)
- Can be configured via approval thresholds

🔍 **Human Review Recommended For**:
- Critical severity incidents
- Repeated incidents of same type
- Incidents with low confidence (<70%)
- Incidents without consensus

### Rate Limits

| Action Type | Limit | Window |
|-------------|-------|--------|
| GitHub Issue | 1 per incident type | 5 minutes |
| Discord Alert | 1 per incident type | 5 minutes |
| Logging | Unlimited | N/A |
| Cortensor API | Unlimited | N/A |

### Dry-Run Mode

When `DRY_RUN=true`:
- All actions are simulated
- No external API calls made
- Results logged as "would execute"
- Safe for testing and demos

## Tool Interface Specification

### Input Format
```typescript
interface IncidentInput {
  metrics: MetricsSnapshot;
  type: 'high_latency' | 'high_error_rate' | 'validator_score_drop';
  severity: 'low' | 'medium' | 'high' | 'critical';
}
```

### Output Format
```typescript
interface IncidentOutput {
  id: string;
  status: 'detected' | 'analyzing' | 'confirmed' | 'acting' | 'resolved';
  analysis: AnalysisResult;
  actions: Action[];
  evidenceBundle: EvidenceBundle;
}
```

### API Endpoints

**Read Operations** (Always Allowed):
- `GET /api/metrics/current`
- `GET /api/metrics/history`
- `GET /api/incidents`
- `GET /api/incidents/:id`
- `GET /api/health`

**Write Operations** (Rate Limited):
- `POST /api/simulate` (demo mode only)

**External Integrations** (Conditional):
- GitHub API (if token configured)
- Discord Webhooks (if URL configured)
- Cortensor Router (always)

## Observability

### Logs
- All actions logged with timestamps
- Structured JSON format
- Includes session IDs for traceability

### Metrics
- Success/failure rates per action type
- Average confidence scores
- Consensus rates
- Response times

### Audit Trail
- Complete evidence bundles
- Cortensor session IDs
- Model outputs
- Validator scores
- Timeline of events

## Extension Points

### Adding New Tools
1. Create new action executor in `src/actions/`
2. Register in `ActionExecutor` class
3. Add rate limiting
4. Update evidence bundler
5. Document in this file

### Adding New Models
1. Add model name to `MODELS` array in `src/detectors/cortensor.ts`
2. Update consensus logic if needed
3. Test with existing incidents

### Adding New Metrics
1. Update `MetricsSnapshot` interface
2. Add collection logic in `MetricsMonitor`
3. Update anomaly detection thresholds
4. Update UI components

## Security Considerations

### API Keys
- Stored in environment variables
- Never logged or exposed
- Rotated regularly

### Database
- SQLite with file permissions
- No remote access
- Regular backups

### Network
- HTTPS in production
- CORS configured
- Rate limiting enabled

### Code Execution
- No eval() or dynamic imports
- No shell command execution
- Sandboxed environment

## Compliance

### Data Retention
- Metrics: 30 days (configurable)
- Incidents: Indefinite
- Logs: 7 days

### Privacy
- No PII collected
- No user tracking
- Anonymous metrics only

### Licensing
- MIT License
- Open source
- Free to use and modify
