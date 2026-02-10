# Cortensor MCP Gateway

**MCP-Compatible Verifiable Agent Framework for Cortensor Network**

Built for Cortensor Hackathon #4 - Agentic Applications

## Overview

The first MCP (Model Context Protocol) server implementation for Cortensor's decentralized AI inference network. This project bridges Anthropic's MCP ecosystem with Cortensor's verifiable multi-miner consensus infrastructure.

**Competitive Submission Pattern**: This implementation uses the `/delegate` and `/validate` endpoints recommended by Cortensor for higher hackathon success rates, rather than simple `/completions` calls.

### Core Components

1. **MCP Server** - Exposes Cortensor capabilities through Model Context Protocol
2. **Cortensor Client** - Python client with `/delegate` and `/validate` support
3. **Agent Swarm** - Multi-agent coordination (Planner, Executor, Validator, Auditor)
4. **Session Log Export** - Complete audit trail for hackathon submission
5. **Evidence Bundle** - Verifiable audit trails with cryptographic integrity (SHA-256)

## Features

- **Delegate-Validate Pattern**: Uses `/delegate` for k-redundant inference and `/validate` for PoI verification
- **Verifiable AI Inference**: Every inference is validated through Cortensor's Proof of Inference (PoI)
- **Multi-Miner Consensus**: Aggregates responses from multiple miners for reliability
- **Session Log Export**: Complete audit trail with request/response pairs for submission
- **MCP Integration**: Works with Claude Desktop, Cursor, and other MCP clients
- **Audit Trails**: Complete evidence bundles with cryptographic integrity verification
- **Mock Mode**: Develop and test without running a Cortensor node

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/cortensor/community-projects
cd cortensor-mcp-gateway

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -e ".[dev]"

# Copy environment config
cp .env.example .env
```

### Run Examples (Mock Mode)

```bash
# Set mock mode
export CORTENSOR_MOCK_MODE=true

# Run delegate-validate demo (competitive submission pattern)
python examples/delegate_validate_demo.py

# Run basic example
python examples/basic_usage.py

# Run full workflow demo with Evidence Bundle
python examples/full_workflow_demo.py
```

### Delegate-Validate Workflow (Recommended)

The competitive submission pattern uses `/delegate` and `/validate` endpoints:

```python
from cortensor_client import CortensorClient, CortensorConfig

config = CortensorConfig.from_env()
async with CortensorClient(config) as client:
    # Step 1: Delegate task with k-redundant inference
    result = await client.delegate(
        prompt="Analyze this governance proposal...",
        k_redundancy=3,  # 3 miners for consensus
    )
    print(f"Consensus: {result.consensus.score}")

    # Step 2: Validate via PoI re-inference
    validation = await client.validate(
        task_id=result.task_id,
        miner_address=result.miner_responses[0].miner_id,
        result_data=result.miner_responses[0].content,
    )
    print(f"Valid: {validation.is_valid}, Confidence: {validation.confidence}")

    # Step 3: Export session log for submission
    client.export_session_log("session_log.json")
```

### Run Tests

```bash
# Run all tests (11 tests)
pytest -v

# Expected output:
# tests/test_client.py::test_client_health_check PASSED
# tests/test_client.py::test_client_get_miners PASSED
# tests/test_client.py::test_client_inference PASSED
# tests/test_client.py::test_consensus_calculation PASSED
# tests/test_client.py::test_consensus_result_is_consensus PASSED
# tests/test_client.py::test_miner_response_to_dict PASSED
# tests/test_evidence.py::test_create_evidence_bundle PASSED
# tests/test_evidence.py::test_evidence_bundle_hash PASSED
# tests/test_evidence.py::test_evidence_bundle_to_dict PASSED
# tests/test_evidence.py::test_evidence_bundle_verify_integrity PASSED
# tests/test_evidence.py::test_evidence_bundle_to_json PASSED
# ==================== 11 passed ====================
```

### Use with MCP Client

Add to your Claude Desktop config (`~/.config/claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "cortensor": {
      "command": "python",
      "args": ["-m", "src.mcp_server.server"],
      "cwd": "/path/to/cortensor-mcp-gateway",
      "env": {
        "CORTENSOR_MOCK_MODE": "true"
      }
    }
  }
}
```

## Architecture

```
                    User Request
                         |
                         v
+-------------------------------------------------------------+
|                      MCP Server                              |
|  Tools: cortensor_inference, verify, audit, miners, health   |
+-------------------------------------------------------------+
                         |
                         v
+-------------------------------------------------------------+
|                   Agent Coordinator                          |
|  +----------+  +----------+  +----------+  +----------+     |
|  | Planner  |->| Executor |->| Validator|->| Auditor  |     |
|  +----------+  +----------+  +----------+  +----------+     |
+-------------------------------------------------------------+
                         |
                         v
+-------------------------------------------------------------+
|                   Cortensor Client                           |
|              (Mock Mode / Live Mode)                         |
+-------------------------------------------------------------+
                         |
                         v
+-------------------------------------------------------------+
|                   Cortensor Network                          |
|         Multi-Miner Inference + PoI Consensus               |
+-------------------------------------------------------------+
                         |
                         v
+-------------------------------------------------------------+
|                   Evidence Bundle                            |
|           SHA-256 Hash + Audit Trail                        |
+-------------------------------------------------------------+
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `cortensor_delegate` | Delegate task to k-redundant miners with consensus |
| `cortensor_validate` | Validate results via PoI + PoUW re-inference |
| `cortensor_inference` | Execute verifiable AI inference with PoI consensus |
| `cortensor_verify` | Verify a previous inference by task ID |
| `cortensor_miners` | List available miners and status |
| `cortensor_audit` | Generate evidence bundle for a task |
| `cortensor_health` | Check router health status |

## Safety Constraints

The agent system is designed with the following safety guardrails:

### What the Agent CAN Do
- Execute AI inference through Cortensor's decentralized network
- Generate verifiable evidence bundles with cryptographic integrity
- Query miner status and health information
- Validate consensus across multiple miners
- Create audit trails for all operations

### What the Agent REFUSES to Do
- Execute inference without consensus verification (below threshold)
- Modify or tamper with evidence bundles after creation
- Access external systems beyond Cortensor network
- Execute arbitrary code or shell commands
- Store or transmit sensitive user data outside the audit trail
- Bypass multi-miner consensus for critical operations

### Verification Guarantees
- All inference results include consensus scores from multiple miners
- Evidence bundles are tamper-evident with SHA-256 integrity hashes
- Divergent miner responses are flagged and logged
- Audit trails are immutable once created

## Evidence Bundle Format

Evidence bundles provide cryptographically verifiable audit trails:

```json
{
  "bundle_id": "eb-c992f93b8194",
  "task_id": "wf-312dcfdbfdcc",
  "created_at": "2026-01-19T06:22:02.655892+00:00",
  "execution_steps": [
    {
      "task_id": "ca1393c1-be05-4a40-b0c1-4700ee13aefc",
      "description": "Analyze and respond",
      "status": "completed",
      "result": {
        "content": "Based on my analysis...",
        "consensus_score": 1.0,
        "is_verified": true,
        "num_miners": 5
      }
    }
  ],
  "miner_responses": [
    {
      "miner_id": "mock-miner-000",
      "model": "Qwen2.5-7B-Instruct",
      "latency_ms": 222.57
    },
    {
      "miner_id": "mock-miner-001",
      "model": "Meta-Llama-3.1-8B-Instruct",
      "latency_ms": 197.49
    }
  ],
  "consensus_info": {
    "average_score": 1.0
  },
  "validation_result": {
    "is_valid": true,
    "confidence": 1.0,
    "consensus_verified": true
  },
  "hash": "da7111006bf82ccdcb62fca25e088ff03c9217df8c422143365660d0700353b1"
}
```

### Integrity Verification

```python
from src.evidence import create_evidence_bundle

bundle = create_evidence_bundle(
    task_id="task-001",
    task_description="Test task",
    execution_steps=[],
    miner_responses=[],
    consensus_info={"score": 0.95},
    validation_result={"is_valid": True},
    final_output="Result",
)

# Compute and verify integrity
computed_hash = bundle.compute_hash()
assert bundle.verify_integrity(computed_hash) is True
```

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `CORTENSOR_ROUTER_URL` | Router API endpoint | `http://127.0.0.1:5010` |
| `CORTENSOR_API_KEY` | API authentication key | `default-dev-token` |
| `CORTENSOR_SESSION_ID` | Session identifier | `0` |
| `CORTENSOR_MOCK_MODE` | Enable mock mode | `false` |
| `CORTENSOR_TIMEOUT` | Request timeout (seconds) | `60` |

## Project Structure

```
cortensor-mcp-gateway/
├── src/
│   ├── cortensor_client/    # Cortensor API client
│   │   ├── client.py        # Main client with delegate/validate
│   │   ├── config.py        # Configuration management
│   │   └── models.py        # Data models (SessionLog, ValidationResult)
│   ├── mcp_server/          # MCP server implementation
│   │   └── server.py        # MCP protocol handlers + TaskStore
│   ├── agent_swarm/         # Multi-agent system
│   │   ├── coordinator.py   # Workflow orchestration
│   │   ├── planner.py       # Task decomposition
│   │   ├── executor.py      # Task execution
│   │   ├── validator.py     # Result validation
│   │   └── auditor.py       # Audit trail generation
│   └── evidence/            # Evidence bundle system
│       └── bundle.py        # Evidence creation/verification
├── examples/
│   ├── delegate_validate_demo.py  # Competitive submission pattern
│   ├── basic_usage.py             # Simple inference example
│   └── full_workflow_demo.py      # Complete agent workflow
├── tests/
│   ├── test_client.py       # Client tests (6 tests)
│   └── test_evidence.py     # Evidence bundle tests (5 tests)
└── docs/                    # Documentation
```

## Sample Runtime Transcript

```
$ python examples/full_workflow_demo.py

Cortensor MCP Gateway - Full Workflow Demo
==================================================

=== Phase 1: Initialize Client ===
Router Health: OK
Mode: Mock
Available Miners (5):
  - mock-miner-000: Qwen2.5-7B-Instruct
  - mock-miner-001: Meta-Llama-3.1-8B-Instruct
  - mock-miner-002: Meta-Llama-3.1-8B-Instruct

=== Phase 2: Agent Workflow ===
Running Agent Swarm workflow...
Workflow ID: wf-312dcfdbfdcc

Planning Phase:
  Created 1 sub-task(s)

Execution Phase:
  Task: Analyze and respond
  Consensus: 1.00 (5/5 miners)
  Verified: True

Validation Phase:
  Valid: True
  Confidence: 1.00

=== Phase 3: Generate Evidence Bundle ===
Bundle ID: eb-c992f93b8194
Integrity Hash: da7111006bf82cc...
Saved to: evidence_bundle_eb-c992f93b8194.json

==================================================
Demo completed successfully!
```

## Development

```bash
# Run tests
pytest -v

# Type checking
mypy src

# Linting
ruff check src
```

## Hackathon Submission

### Cortensor Integration (Competitive Pattern)
- Uses `/delegate` endpoint for k-redundant inference
- Uses `/validate` endpoint for PoI + PoUW verification
- Exports session logs for submission evidence
- Mock mode simulates multi-miner consensus

### API Endpoints Used
| Endpoint | Purpose |
|----------|---------|
| `/api/v1/delegate` | Delegate tasks to k miners with consensus |
| `/api/v1/validate` | Validate results via re-inference |
| `/api/v1/completions` | Fallback for simple inference |
| `/api/v1/miners` | Query available miners |

### Session Log Format (Submission Evidence)

```json
{
  "session_id": 12345,
  "session_name": "hackathon-session",
  "created_at": "2026-01-19T11:14:09Z",
  "entries": [
    {
      "operation": "delegate",
      "timestamp": "2026-01-19T11:14:10Z",
      "request": {"prompt": "...", "k_redundancy": 3},
      "response": {"task_id": "task-xxx", "consensus_score": 0.95},
      "success": true,
      "latency_ms": 1085
    },
    {
      "operation": "validate",
      "timestamp": "2026-01-19T11:14:11Z",
      "request": {"task_id": "task-xxx", "miner_address": "..."},
      "response": {"is_valid": true, "confidence": 0.89},
      "success": true,
      "latency_ms": 523
    }
  ],
  "summary": {
    "total_delegates": 2,
    "total_validates": 2,
    "total_tasks": 2
  }
}
```

### Deliverables
- [x] Public repo with MIT license
- [x] README with quickstart + architecture
- [x] Tool list (7 MCP tools)
- [x] Safety constraints documented
- [x] Sample transcript / logs
- [x] Evidence bundle format (JSON)
- [x] Session log export for submission
- [x] Delegate-validate workflow demo
- [x] Replay script (`pytest -v`)
- [x] 11 passing tests

### Demo (Competitive Submission Pattern)
Run the delegate-validate demo:
```bash
export CORTENSOR_MOCK_MODE=true
python examples/delegate_validate_demo.py
```

## License

MIT - See [LICENSE](LICENSE) file

## Links

- Cortensor Network: https://cortensor.network
- Hackathon: Cortensor Hackathon #4 - Agentic Applications
- Discord: discord.gg/cortensor
