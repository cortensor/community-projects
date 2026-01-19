# Cortensor Governance Agent

An MCP client agent that analyzes DeFi governance proposals using the Cortensor decentralized network.

## Overview

This agent connects to Cortensor's MCP server (`router1-t0.cortensor.app`) as a client, delegating inference tasks to the network and validating results through consensus.

**Key Features:**
- MCP 2024-11-05 protocol client (HTTP streaming)
- Delegates inference via `cortensor_completions`
- Validates results via `cortensor_validate`
- Generates cryptographic evidence bundles (SHA-256)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Governance Agent                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Analyze    │─>│   Delegate   │─>│     Validate     │  │
│  │   Proposal   │  │   to Miners  │  │     Results      │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
              │                                    │
              │         MCP Protocol               │
              ▼                                    ▼
┌─────────────────────────────────────────────────────────────┐
│               Cortensor MCP Server                          │
│           router1-t0.cortensor.app/mcp                      │
│                                                             │
│   Tools: cortensor_completions, cortensor_validate,         │
│          cortensor_create_session, cortensor_tasks, etc.    │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│              Cortensor Miner Network                        │
│        Decentralized LLM inference with consensus           │
└─────────────────────────────────────────────────────────────┘
```

## Workflow

1. **Connect** - Initialize MCP session with Cortensor router
2. **Create Session** - Request nodes from the network
3. **Analyze** - Delegate governance proposal analysis via `cortensor_completions`
4. **Validate** - Verify results via `cortensor_validate`
5. **Evidence** - Generate tamper-proof evidence bundle

## Quick Start

```bash
# Install
pip install -e .

# Run demo
python examples/demo.py
```

## Usage

```python
from cortensor_agent import GovernanceAgent

# Create and connect agent
agent = GovernanceAgent()
agent.connect(session_name="my-analysis", min_nodes=2)

# Analyze a proposal
result = agent.analyze_proposal("""
    Proposal: Implement quadratic voting for protocol upgrades
    - sqrt(tokens) voting power
    - 7-day voting period
""", validate=True)

print(f"Analysis: {result.analysis}")
print(f"Validated: {result.validated}")
print(f"Score: {result.validation_score}")

# Generate evidence bundle
evidence = agent.generate_evidence_bundle(result)
print(f"Integrity Hash: {evidence.integrity_hash}")

agent.close()
```

## MCP Tools Used

| Tool | Purpose |
|------|---------|
| `cortensor_completions` | Delegate inference to network |
| `cortensor_validate` | Validate results through consensus |
| `cortensor_create_session` | Initialize session with nodes |
| `cortensor_tasks` | Query task history |
| `cortensor_miners` | List available nodes |

## Evidence Bundle Format

```json
{
  "bundle_id": "eb-abc123",
  "analysis": {
    "task_id": "abc123",
    "proposal": "...",
    "analysis": "...",
    "validation_score": 0.95,
    "validated": true
  },
  "cortensor_session_id": 12345,
  "raw_responses": [...],
  "validation_responses": [...],
  "integrity_hash": "sha256..."
}
```

## Safety Constraints

- All inference delegated to Cortensor network (no local execution)
- Results validated through `cortensor_validate` before acceptance
- Cryptographic evidence bundle for audit trail
- No private keys or sensitive data in prompts

## Requirements

- Python 3.10+
- `requests` library
- Network access to Cortensor router

## License

MIT
