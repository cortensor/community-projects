# Vigil

**Cortensor Hackathon #4 Submission**

An autonomous agent that monitors Cortensor network health, detects anomalies using multi-model validation (Proof of Inference), and automatically responds to incidents with complete audit trails.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Node.js](https://img.shields.io/badge/node-%3E%3D18.0.0-brightgreen)](https://nodejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3-blue)](https://www.typescriptlang.org/)

---

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Agent Capabilities](#agent-capabilities)
- [Safety Constraints](#safety-constraints)
- [Cortensor Integration](#cortensor-integration)
- [Configuration](#configuration)
- [Testing](#testing)
- [Deployment](#deployment)
- [Documentation](#documentation)
- [License](#license)

---

## Overview

Vigil is a production-ready autonomous agent designed to maintain the health and reliability of Cortensor network infrastructure. The system continuously monitors network metrics, detects anomalies through multi-model validation, and executes automated responses while maintaining complete audit trails for compliance and verification.

**Live Demo**: [https://vigil-j1mo5b288-marvy247s-projects.vercel.app/](https://vigil-j1mo5b288-marvy247s-projects.vercel.app/)

**Demo Video**: [https://youtu.be/QDhwuFRhrcQ](https://youtu.be/QDhwuFRhrcQ)

### Core Features

- **Real-time Monitoring**: Continuous tracking of router health, latency, error rates, and validator scores
- **Multi-Model Anomaly Detection**: Leverages Cortensor Proof of Inference (PoI) across 3+ models for redundant validation
- **Automated Response**: Creates GitHub issues, sends Discord alerts, and maintains comprehensive incident logs
- **Evidence Bundles**: Complete audit trails with Cortensor session IDs and validator scores
- **Safety Guardrails**: Rate limiting, consensus requirements, and human-in-loop approval mechanisms
- **Demo Mode**: Incident simulation capabilities for testing and demonstrations

---

## Quick Start

### Prerequisites

- Node.js 18 or higher
- npm or yarn
- Cortensor API access (optional for demo mode)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/vigil.git
cd vigil

# Install backend dependencies
cd backend
npm install
cp .env.example .env
# Edit .env with your credentials (optional for demo mode)

# Install frontend dependencies
cd ../frontend
npm install
```

### Running the Application

**Development Mode:**

```bash
# Terminal 1 - Backend
cd backend
npm run dev

# Terminal 2 - Frontend
cd frontend
npm run dev
```

Access the application at `http://localhost:5173`

**Production Mode (Docker):**

```bash
cp backend/.env.example .env
# Edit .env with your credentials
docker-compose up -d
```

### Runbook

**Starting Services:**
```bash
./start.sh
```

**Stopping Services:**
```bash
./stop.sh
```

**Viewing Logs:**
```bash
# Backend logs
tail -f backend/backend.log

# Frontend logs
tail -f frontend/frontend.log
```

**Running Tests:**
```bash
./examples/test-agent.sh
```

**Simulating Incidents:**
```bash
curl -X POST http://localhost:3001/api/simulate \
  -H "Content-Type: application/json" \
  -d '{"type":"high_latency"}'
```

---

## Architecture

### System Design

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

### Workflow

The agent follows a complete autonomous loop:

1. **Monitor**: Continuously collect network health metrics (latency, error rates, validator scores)
2. **Detect**: Identify anomalies using threshold-based detection
3. **Analyze**: Validate anomalies with Cortensor PoI across 3+ models
4. **Act**: Execute automated responses (GitHub issues, Discord alerts)
5. **Report**: Generate complete evidence bundles with audit trails

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed system design.

---

## Agent Capabilities

### Monitoring Tools

- **Metrics Collection**: Continuously gather network health data
  - Latency measurements (milliseconds)
  - Error rate tracking (percentage)
  - Validator score monitoring (0-1 scale)
  - Uptime percentage
  - Request count
- **Historical Analysis**: Store and query metrics history
- **Real-time Streaming**: WebSocket-based live metrics feed

### Detection Tools

- **Threshold-based Detection**: Identify anomalies using configurable thresholds
  - High latency: > 2x baseline
  - High error rate: > 5x baseline
  - Validator score drop: < 80% baseline
- **Pattern Recognition**: Detect trends and correlations across metrics
- **Severity Classification**: Categorize incidents (low, medium, high, critical)

### Analysis Tools (Cortensor Integration)

- **Multi-Model Validation (PoI)**: Run same analysis across 3+ models
  - gpt-4
  - claude-3
  - gemini-pro
- **Consensus Calculation**: Majority vote across model outputs
- **Confidence Scoring**: Weighted average of model confidences
- **Validator Scoring (PoUW)**: Use validator scores to weight results
- **Session Management**: Track all Cortensor session IDs for audit

### Action Tools

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

### Evidence Tools

- **Bundle Generation**: Create complete audit trails
  - Incident metadata (ID, type, severity, timestamps)
  - Metrics snapshots
  - Cortensor analysis results
  - Actions taken
  - Timeline of events
- **JSON Export**: Structured, machine-readable format
- **IPFS Ready**: Format compatible with IPFS storage

### Demo Tools

- **Incident Simulation**: Generate synthetic anomalies
  - High latency
  - High error rate
  - Validator score drop
- **Replay Mode**: Re-run historical incidents

See [TOOLS.md](./TOOLS.md) for complete tool documentation.

---

## Safety Constraints

### Prohibited Operations

The agent is explicitly designed to prevent dangerous operations:

- **Cannot modify router configuration**: No access to change router settings or parameters
- **Cannot delete or alter historical data**: All metrics and incident records are immutable
- **Cannot execute arbitrary code**: No shell command execution or dynamic code evaluation
- **Cannot access sensitive credentials**: Limited to configured environment variables only
- **Cannot bypass safety mechanisms**: Rate limits and consensus requirements are enforced
- **Cannot spam or abuse**: Rate limited to 1 action per incident type per 5 minutes

### Required Conditions for Actions

**GitHub Issue Creation:**
- Multi-model consensus (≥2 models agree)
- Severity: high or critical
- Rate limit not exceeded
- Valid GitHub token configured

**Discord Alerts:**
- Multi-model consensus
- Rate limit not exceeded
- Valid webhook URL configured

**Incident Logging:**
- Always allowed (read-only)
- No rate limits

### Rate Limits

| Action Type | Limit | Window |
|-------------|-------|--------|
| GitHub Issue | 1 per incident type | 5 minutes |
| Discord Alert | 1 per incident type | 5 minutes |
| Logging | Unlimited | N/A |
| Cortensor API | Unlimited | N/A |

### Human-in-Loop Points

**Manual Approval Recommended For:**
- Critical severity incidents
- Repeated incidents of same type
- Incidents with low confidence (<70%)
- Incidents without consensus

### Audit Trail

All actions are logged with:
- Complete timestamps
- Cortensor session IDs
- Model outputs and validator scores
- Action results and errors
- Timeline of events

See [TOOLS.md](./TOOLS.md) for complete safety documentation.

---

## Cortensor Integration

### Proof of Inference (PoI)

Vigil leverages Cortensor's Proof of Inference to ensure high-confidence anomaly detection:

- Runs anomaly detection across 3 models: gpt-4, claude-3, gemini-pro
- Compares outputs for consensus (majority vote)
- Requires ≥2 models to agree before taking action
- Reduces false positives through redundant validation

### Proof of Useful Work (PoUW)

The system uses validator scores to weight detection confidence:

- Each model's output includes a validator score (0-1)
- Higher validator scores indicate higher trust in model output
- Average validator score included in evidence bundle
- Weighted confidence calculation based on validator scores

### Session Management

- Maintains persistent sessions with Cortensor router
- Stores all session IDs for audit trails
- Links sessions to specific incidents
- Enables verification of all AI-generated decisions

### Evidence Trails

Complete audit logs include:
- Request/response pairs for all Cortensor calls
- Model outputs with confidence scores
- Validator scores per model
- Timeline of all events
- Session IDs for external verification

---

## Configuration

### Backend Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CORTENSOR_API_URL` | No* | Cortensor router URL |
| `CORTENSOR_API_KEY` | No* | Your Cortensor API key |
| `GITHUB_TOKEN` | No | GitHub personal access token |
| `GITHUB_REPO` | No | Repository in format `owner/repo` |
| `DISCORD_WEBHOOK_URL` | No | Discord webhook URL |
| `PORT` | No | Backend port (default: 3001) |
| `NODE_ENV` | No | Environment (development/production) |
| `DRY_RUN` | No | Simulate actions without executing (default: false) |

*Demo mode works without Cortensor credentials (uses mock responses)

### GitHub Token Setup

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Select scopes: `repo` (for private repos) or `public_repo` (for public repos)
4. Copy token and add to `.env`

### Discord Webhook Setup

1. Go to Discord Server Settings → Integrations → Webhooks
2. Create New Webhook
3. Copy webhook URL
4. Add to `.env`

---

## Testing

### Automated Test Suite

Run the complete test suite:

```bash
./examples/test-agent.sh
```

Tests cover:
- Health checks
- Metrics collection
- Incident simulation (3 types)
- Cortensor analysis
- Evidence generation

### Manual Testing

**Test Health Endpoint:**
```bash
curl http://localhost:3001/api/health
```

**Test Metrics Collection:**
```bash
curl http://localhost:3001/api/metrics/current
```

**Simulate Incident:**
```bash
curl -X POST http://localhost:3001/api/simulate \
  -H "Content-Type: application/json" \
  -d '{"type":"high_latency"}'
```

**View Incidents:**
```bash
curl http://localhost:3001/api/incidents
```

---

## Deployment

### Docker Deployment

```bash
cp backend/.env.example .env
# Edit .env with your credentials
docker-compose up -d
```

### Cloud Deployment

**Vercel (Frontend):**
```bash
cd frontend
vercel --prod
```

**Railway (Backend):**
```bash
cd backend
railway up
```

**AWS EC2:**
See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed instructions.

---

## Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Detailed system design and data flow
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment guides for multiple platforms
- [DEMO.md](./DEMO.md) - Demo script and presentation tips
- [TOOLS.md](./TOOLS.md) - Complete agent capabilities and safety constraints
- [CONTRIBUTING.md](./CONTRIBUTING.md) - Contribution guidelines
- [examples/](./examples/) - Sample evidence bundles and test scripts

---

## Project Structure

```
vigil/
├── backend/              # Node.js/TypeScript backend
│   ├── src/
│   │   ├── monitors/     # Metrics collection
│   │   ├── detectors/    # Cortensor PoI integration
│   │   ├── actions/      # GitHub, Discord, logging
│   │   ├── evidence/     # Audit trail generation
│   │   ├── managers/     # Incident orchestration
│   │   ├── simulator/    # Demo mode
│   │   └── api/          # REST + WebSocket
│   └── data/             # SQLite database
├── frontend/             # React/TypeScript UI
│   └── src/
│       ├── components/   # Dashboard, incidents, evidence
│       └── hooks/        # WebSocket, API integration
├── examples/             # Sample evidence bundles, tests
├── ARCHITECTURE.md       # Detailed system design
├── DEPLOYMENT.md         # Deployment guides
├── DEMO.md              # Demo script and Q&A
├── TOOLS.md             # Agent capabilities and constraints
└── docker-compose.yml   # Production deployment
```

---

## Hackathon Criteria Coverage

| Criteria | Weight | Implementation |
|----------|--------|----------------|
| **Agent capability** | 30% | Full monitor → detect → act → report loop |
| **Cortensor integration** | 25% | PoI, PoUW, session management, validator scoring |
| **Reliability** | 20% | Safety guardrails, error handling, rate limiting |
| **Usability** | 15% | Live dashboard, one-click demo, clear documentation |
| **Public good** | 10% | Open source, deployable by any project |

**Bonus features:**
- Complete evidence bundles (JSON + IPFS ready)
- Automated test suite
- Docker deployment
- CI/CD pipeline
- Comprehensive documentation

---

## License

MIT License - See [LICENSE](./LICENSE) file

---

## Links

- **Cortensor Discord**: [discord.gg/cortensor](https://discord.gg/cortensor)
- **Cortensor Documentation**: [docs.cortensor.network](https://docs.cortensor.network)
- **Hackathon #4**: [Hackathon Details](https://docs.cortensor.network/community-and-ecosystem/hackathon/hackathon-4)

---

## Acknowledgments

Built for Cortensor Hackathon #4 - Pushing agentic applications into production-ready workflows.

**Made for the Cortensor community**
