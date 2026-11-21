# Cortensor Release Gate

`cortensor-release-gate` is a local-first QA and submission gate agent built on **`openminion==0.1.23`** for Cortensor Hackathon #5 and `cortensor/community-projects` contributors.

It inspects a target project directory before a pull request or release and produces a typed `ReleaseGateVerdict` (`READY`, `CHANGES_REQUIRED`, or `BLOCKED`), an ordered `TriagePlan`, and an approval-gated Markdown/JSON report.

## Architecture

```
Target Repo
  |
  +--> subagent("security_auditor", READ_ONLY) --> scan_security_tool
  +--> subagent("docs_auditor", READ_ONLY)     --> scan_docs_tool
  +--> deterministic wiring scan               --> scan_cortensor_wiring
  +--> MemoryBundle diff                       --> resolved / persistent blockers
  |
  v
Coordinator Agent
  |-- (if findings exist) --> Handoff("transfer_to_triage_planner") --> TriagePlan
  |-- (if --write-report) --> approval_callback --> write_release_gate_report (WRITE_SAFE)
```

## OpenMinion 0.1.23 Workflow

1. `create_isolated_runtime` writes an isolated `agents.json`, `home_root`, and `data_root` under `.openminion/` so runs never modify `~/.openminion`.
2. `subagent()` spawns two `READ_ONLY` worker agents (`security_auditor` and `docs_auditor`) that execute `@tool` scanners and validate replies against Pydantic `output_type` models.
3. `memory_store` persists blocker check IDs using OpenMinion's `MemoryBundle` portability helpers (`export_bundle`, `save_bundle`, `load_bundle`, `import_bundle`) and diffs current blockers against the prior run.
4. When findings exist, `Handoff` (`transfer_to_triage_planner`) produces an ordered remediation plan.
5. Writing `RELEASE_GATE_REPORT.md` and `release-gate-summary.json` runs through `write_release_gate_report` (`min_scope="WRITE_SAFE"`, `dangerous=True`) guarded by `approval_callback`.

## Setup

Requires Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Usage

### 1. Run offline with the built-in loopback server ($0 capital, no API key)

```powershell
cortensor-release-gate audit . --demo-local
```

Write the report artifacts after approving the gated tool:

```powershell
cortensor-release-gate audit . --demo-local --write-report --yes --output-dir ./out
```

### 2. Run the OpenMinion 0.1.23 building-block probe suite

```powershell
cortensor-release-gate probe .
```

### 3. Run against Cortensor Portal or a direct Router node

Copy `.env.example` to `.env` (or export environment variables):

```powershell
$env:CORTENSOR_API_KEY="your-portal-or-router-key"
$env:CORTENSOR_API_URL="https://api.cortensor.app/v1"
$env:CORTENSOR_MODEL="gpt-oss-20b"
cortensor-release-gate audit . --provider cortensor
```

### 4. Inspect saved MemoryBundle history

```powershell
cortensor-release-gate memory ./out/audit_memory.json
```

## Verification

Run lint, strict typecheck, and all unit/integration tests:

```powershell
ruff check src tests
mypy --config-file pyproject.toml src
pytest -v tests
```

## Hackathon #5 Documentation

- [Building Blocks Tested](docs/BUILDING_BLOCKS_TESTED.md)
- [What We Learned](docs/WHAT_WE_LEARNED.md)
- [Project Status](STATUS.md)
- [Release Notes](RELEASE.md)
