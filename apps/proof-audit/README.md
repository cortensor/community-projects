# ProofAudit Minion

**ProofAudit Minion** (`apps/proof-audit`) is a bounded, read-only/gated repository readiness auditor built on **OpenMinion (`openminion==0.1.24`)** for **Cortensor Hackathon #5**.

It inspects a local OpenMinion / Cortensor project directory, checks submission hygiene and SDK surface usage, probes an OpenAI-compatible inference endpoint, runs a bounded `py_compile` smoke check behind `approval_callback`, and produces a Pydantic-validated `ProofAuditReport` (`READY`, `WARNINGS`, or `BLOCKED`).

## Architecture (2-Stage OpenMinion Workflow)

1. **Shared `APIRuntime`**:
   - Generates an isolated `agents.json` in a temporary directory via `openminion.services.bootstrap.provider_setup` (`openrouter`, `cortensor-portal`, `cortensor-router`, or `custom-openai-compatible`) and initializes `APIRuntime.from_config_path(...)`.
2. **Stage 1 — Collector `Agent`**:
   - Uses `session_id` and `approval_callback` with 4 deterministic tools:
     - `inspect_repo_manifest` (`@tool(min_scope="READ_ONLY", idempotent=True)`): checks `LICENSE` (MIT/Apache-2.0), `README.md`, `requirements.txt` (`openminion==` pin), `.gitignore`, and scans for accidental secrets.
     - `scan_sdk_surface` (`@tool(min_scope="READ_ONLY", idempotent=True)`): AST-scans `.py` files for `APIRuntime`, `Agent`, `@tool`, `output_type`, `session_id`, `approval_callback`, `ProviderError`, and CLI/doctor usage.
     - `probe_openai_compatible_endpoint` (`@tool(min_scope="READ_ONLY", idempotent=True)`): read-only HTTP reachability + latency probe against `/models`.
     - `run_repo_smoke_check` (`@tool(idempotent=True)`): bounded `py_compile` across `.py` files, gated by `approval_callback`.
3. **Stage 2 — Verdict Judge `Agent`**:
   - Reuses the same `APIRuntime` and `session_id` with `output_type=ProofAuditReport` (Pydantic v2) to produce a structured verdict, score (`0-100`), findings, and remediation steps.
   - Catches `ProviderError`, `AgentOutputValidationError`, and `TurnTimeoutError`, falling back cleanly to a deterministic offline report when a remote model is unavailable or refuses structured JSON.

## Setup

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
# .\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Verify your local OpenMinion CLI installation:

```bash
openminion setup --list-providers
openminion doctor --check-turn --json
```

## Usage

Set the credential environment variable for your chosen provider (for example `OPENROUTER_API_KEY`, `CORTENSOR_API_KEY`, or `OPENAI_COMPATIBLE_API_KEY`), then run:

```bash
# Audit current repo with OpenRouter
python audit.py . --provider openrouter --out-dir audit-out

# Audit with Cortensor Portal
python audit.py . --provider cortensor-portal --model oss-20b --out-dir audit-out

# Audit with a custom OpenAI-compatible endpoint
python audit.py . --provider custom-openai-compatible --base-url http://127.0.0.1:8080/v1 --model gpt-oss-20b --out-dir audit-out
```

Generated artifacts in `--out-dir`:
- `facts.json`: raw tool outputs, approval log, session metadata, and structured report JSON.
- `report.md`: human-readable audit report with verdict, score, findings table, and remediation steps.
- `run.txt`: concise execution trace.

## Running Tests

```bash
python -m unittest discover -s tests -v
```

## Demo

- Demo Video: `[Placeholder — Demo Recording Link]`

## License

MIT License — see [LICENSE](LICENSE).

## Demo Video
- **YouTube (75s, 720p)**: https://www.youtube.com/watch?v=vxuguQVx3Ng
- **GitHub Release (`v1.0.0`)**: https://github.com/devbox-zero-ops/cortensor-proof-audit/releases/tag/v1.0.0
