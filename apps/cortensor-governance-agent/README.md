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

| Criteria | Implementation |
|----------|---------------|
| **Technical Excellence (40%)** | Full MCP protocol, dual-mode client, proper error handling |
| **Trust & Verification (25%)** | `cortensor_validate` integration, evidence bundles with SHA-256 |
| **User Experience (20%)** | Simple API, comprehensive demo, clear documentation |
| **Production Readiness (15%)** | Self-hosted router support, API key auth, configurable endpoints |

## License

MIT

---

**Built for Cortensor Hackathon #4**
