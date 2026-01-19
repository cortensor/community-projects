# Cortensor Governance Agent

**Hackathon #4 Submission** - MCP Client for DeFi Governance Analysis

An intelligent agent that analyzes DeFi governance proposals using the Cortensor decentralized AI network, with built-in verification and cryptographic audit trails.

## Highlights

- **MCP 2024-11-05 Protocol** - Full HTTP stream implementation
- **Dual-Mode Client** - MCP and REST API support
- **Trust & Verification** - Uses `cortensor_validate` for consensus validation
- **Evidence Bundles** - SHA-256 integrity hashes for audit trail
- **Production Ready** - Self-hosted router support with API key auth

## Architecture

```
+-----------------------------------------------------------+
|                   Governance Agent                         |
|  +------------+   +------------+   +------------------+   |
|  |  Analyze   |-->|  Delegate  |-->|    Validate      |   |
|  |  Proposal  |   |  to Miners |   |    Results       |   |
|  +------------+   +------------+   +------------------+   |
+-----------------------------------------------------------+
         |              MCP / REST API              |
         v                                          v
+-----------------------------------------------------------+
|              Cortensor Router Network                      |
|                                                           |
|   MCP Endpoint: router1-t0.cortensor.app/mcp              |
|   REST API:     http://<your-router>:5010/api/v1/         |
|                                                           |
|   Tools:                                                  |
|   - cortensor_completions (delegate inference)            |
|   - cortensor_validate (verify results)                   |
|   - cortensor_create_session (initialize)                 |
|   - cortensor_miners (list nodes)                         |
+-----------------------------------------------------------+
         |
         v
+-----------------------------------------------------------+
|              Cortensor Miner Network                       |
|        Decentralized LLM inference with PoI + PoUW        |
+-----------------------------------------------------------+
```

## Quick Start

```bash
# Install
pip install -e .

# Run demo
python demo.py
```

## Usage

### MCP Mode (Public Router)

```python
from cortensor_agent import CortensorClient, GovernanceAgent

# Connect via MCP protocol
client = CortensorClient(mode="mcp")
client.connect()

# List available tools
tools = client.list_tools()
print(f"Available: {[t['name'] for t in tools]}")
```

### REST Mode (Self-Hosted Router)

```python
from cortensor_agent import CortensorClient

# Connect via REST API
client = CortensorClient(
    mode="rest",
    rest_endpoint="http://your-router:5010",
    api_key="your-api-key"
)
client.connect()

# Check status
status = client.get_status()
print(f"Miners: {status.data['connected_miners']}")
```

### Governance Analysis

```python
from cortensor_agent import GovernanceAgent

agent = GovernanceAgent()
agent.connect(session_name="governance-analysis")

# Analyze a proposal
result = agent.analyze_proposal("""
    Proposal: Increase Protocol Fee from 0.3% to 0.5%
    - Additional revenue for treasury
    - Fund security audits
""", validate=True)

print(f"Analysis: {result.analysis}")
print(f"Validated: {result.validated}")
print(f"Score: {result.validation_score}")

# Generate evidence bundle
evidence = agent.generate_evidence_bundle(result)
print(f"Bundle ID: {evidence.bundle_id}")
print(f"Integrity Hash: {evidence.integrity_hash}")
```

## MCP Protocol Implementation

Key implementation details for HTTP stream MCP:

1. **Initialize** - Send `initialize` request, capture `Mcp-Session-Id` from response header
2. **Notification** - Send `notifications/initialized` (no response expected)
3. **Tool Calls** - Include `Mcp-Session-Id` header in all subsequent requests

```python
# MCP initialization sequence
resp = POST("/mcp", {"method": "initialize", ...})
session_id = resp.headers["Mcp-Session-Id"]

POST("/mcp", {"method": "notifications/initialized"},
     headers={"Mcp-Session-Id": session_id})

POST("/mcp", {"method": "tools/call", "params": {"name": "cortensor_completions", ...}},
     headers={"Mcp-Session-Id": session_id})
```

## Available Tools

| Tool | Method | Description |
|------|--------|-------------|
| `cortensor_completions` | POST | Delegate inference to network |
| `cortensor_delegate` | POST | Alias for completions |
| `cortensor_validate` | POST | Validate results through LLM verification |
| `cortensor_create_session` | POST | Initialize session with nodes |
| `cortensor_tasks` | GET | Query task history |
| `cortensor_miners` | GET | List available nodes |
| `cortensor_status` | GET | Router status |
| `cortensor_about` | GET | Router metadata |

## Safety & Constraints

The agent enforces strict boundaries for responsible operation:

### What the Agent Does
- Analyzes governance proposals for technical feasibility, economic impact, and security risks
- Delegates inference to Cortensor's decentralized network
- Validates results through consensus mechanisms
- Generates tamper-proof evidence bundles

### What the Agent Refuses
- **No execution of transactions** - Analysis only, no on-chain actions
- **No private key handling** - Never requests or stores wallet credentials
- **No financial advice** - Provides structured analysis, not investment recommendations
- **No automated voting** - Human decision required for governance participation
- **No external API calls** - Only communicates with configured Cortensor endpoints
- **No persistent storage of proposals** - Stateless operation, data not retained

### Rate Limiting & Resource Protection
- Configurable timeout (default 60s) prevents runaway requests
- Session-based operation limits scope of each analysis
- Evidence bundles provide audit trail for all operations

## Evidence Bundle

Cryptographic audit trail for transparency:

```json
{
  "bundle_id": "eb-abc123def456",
  "analysis": {
    "task_id": "abc123def456",
    "proposal": "Proposal text...",
    "analysis": "Structured analysis...",
    "validation_score": 0.95,
    "validated": true,
    "timestamp": "2026-01-19T10:00:00Z"
  },
  "cortensor_session_id": 12345,
  "raw_responses": [...],
  "validation_responses": [...],
  "integrity_hash": "sha256:a1b2c3d4..."
}
```

## Agent Runtime Proof

### Sample Demo Output

```
============================================================
   CORTENSOR GOVERNANCE AGENT DEMO
   Hackathon #4 Submission
============================================================

============================================================
Demo: MCP Connection to Cortensor Public Router
============================================================

1. Connecting to Cortensor MCP server...
   Session ID: 83f5ef1f-d805-490c-b86f-0293a56c759f
   Protocol: 2024-11-05

2. Listing available tools...
   - cortensor_completions
   - cortensor_delegate
   - cortensor_validate
   - cortensor_create_session
   - cortensor_tasks
   - cortensor_miners
   - cortensor_status
   - cortensor_about
   - cortensor_ping
   - cortensor_info

3. Getting router info...
   Backend status: True

   Connection closed.

============================================================
Demo: REST API Connection to Self-Hosted Router
============================================================

1. Connecting to VPS router...
   Connected!

2. Getting router status...
   Uptime: 86400 seconds
   Active sessions: 0
   Connected miners: 0

3. Getting router info...
   Router address: 0x804191e9bf2aa622A7b1D658e2594320e433CEeF
   x402 enabled: True
   Endpoints: 20

   Connection closed.

============================================================
Demo completed!
============================================================
```

### Replay Command

```bash
cd apps/cortensor-governance-agent
pip install -e .
python demo.py
```

## Project Structure

```
cortensor-governance-agent/
├── src/cortensor_agent/
│   ├── __init__.py       # Package exports
│   ├── client.py         # CortensorClient (MCP + REST)
│   └── agent.py          # GovernanceAgent
├── demo.py               # Demo script
├── examples/             # Usage examples
├── tests/                # Test suite
├── docs/                 # Documentation
├── pyproject.toml        # Package config
└── README.md
```

## Technical Specifications

- **Protocol**: MCP 2024-11-05 (HTTP stream, not SSE)
- **Network**: Arbitrum Sepolia testnet (Chain ID: 421614)
- **Language**: Python 3.10+
- **Dependencies**: `requests`

## Hackathon Evaluation Alignment

| Criteria | Weight | Implementation |
|----------|--------|---------------|
| **Agent capability & workflow** | 30% | Complete analysis workflow: parse -> delegate -> validate -> evidence bundle |
| **Cortensor Integration** | 25% | MCP protocol, `cortensor_completions`, `cortensor_validate`, session management |
| **Reliability & safety** | 20% | Error handling, type safety, dual-mode failover, strict constraints |
| **Usability & demo** | 15% | Simple API, demo.py, clear README, architecture diagram |
| **Public good impact** | 10% | MIT license, comprehensive docs, reusable client library |

### Bonus Features
- MCP 2024-11-05 protocol (HTTP stream with `notifications/initialized`)
- `/validate` endpoint integration via `cortensor_validate`
- x402-enabled router support

## License

MIT

---

**Built for Cortensor Hackathon #4**
