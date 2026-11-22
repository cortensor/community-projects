# Minionbench Ops — OpenMinion 0.1.24 Release & Triage Guard + Runtime Diagnostic Workbench

Built for **Cortensor Hackathon #5** ([DoraHacks #2418](https://dorahacks.io/hackathon/2418/detail)). Minionbench Ops embeds the official [`openminion`](https://github.com/openminion/openminion) `0.1.24` Python SDK inside a strict vertical-slice architecture (`Invariants -> Schema -> Ledger -> State Engine -> Pipe -> Paint`) to execute repeatable Cortensor builder release-and-triage audits alongside a 6-probe empirical SDK diagnostic suite.

## Why Minionbench Ops Matters for Cortensor Builders

Cortensor Hackathon #5 evaluates working OpenMinion 0.1 workflows (`45%`), reproducibility (`20%`), Cortensor builder relevance (`10%`), and concrete **Building Blocks Tested + What We Learned** engineering feedback (`25%`). Minionbench Ops automates pre-release workspace triage while testing OpenMinion's runtime boundaries with real neural model execution and reproducible local HTTP fault probes.

## Vertical-Slice Architecture

Each feature brick under `src/features/` imports only Python 3.12 standard library modules, `openminion` / `pydantic`, and `src/kernel/event_bus.py` (enforced via AST tests with zero sibling imports):

1. `src/kernel/event_bus.py` — Immutable append-only `EventBus`, secret-redaction filter (`redact_secrets`), frozen receipt/probe schemas (`TriageTarget`, `MinionTurnReceipt`, `BuildingBlockProbeResult`, `DiagnosticReport`), and `CORRUPT_GATE_CONTROL=1` negative-control tripwire.
2. `src/features/triage_tools/` — Three `@tool(min_scope="READ_ONLY", idempotent=True)` tools (`inspect_workspace_manifest`, `audit_python_module_risks`, `check_cortensor_config_posture`) plus one bare policy-gated write `@tool` (`stage_release_brief`).
3. `src/features/minion_runner/` — Isolated `.openminion_runtime/{home,data}` lifecycle (`APIRuntime.from_config_path` + `Agent`), supporting hosted Gemini OpenAI-compatible execution (`GEMINI_API_KEY`), live local Ollama `/v1` neural execution (`qwen2.5:1.5b`), Cortensor Portal/Router `agents.json` posture generation, and a real TCP `127.0.0.1` `http.server` OpenAI-compatible loopback endpoint for deterministic tests.
4. `src/features/runtime_diagnostics/` — Six empirical OpenMinion `0.1.24` probes covering action-policy confirmation pauses, `session_id` vs `thread_id` resumption, Pydantic `output_type` + `AgentOutputValidationError`, `ProviderError` + `TurnTimeoutError`, CLI `setup --list-providers --json` + `status readiness`, and reproducible `0.1.24` config tripwires.
5. `src/features/report_exporter/` & `web/diagnostic_console.html` — Writes sanitized JSON/Markdown artifacts (`outputs/`, [BUILDING_BLOCKS_TESTED.md](BUILDING_BLOCKS_TESTED.md), [WHAT_WE_LEARNED.md](WHAT_WE_LEARNED.md)) and powers the Dark Studio (`noir`) interactive Diagnostic Console.

## Quickstart & Reproducible Verification

### 1. Environment Setup (Python 3.11+)

```bash
python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install "openminion>=0.1.24" "pytest>=8.0.0"
```

### 2. Run the Live Model-Backed Triage Workflow & 6 SDK Probes

Configure either `GEMINI_API_KEY` in your shell environment or run a local `ollama` model (`qwen2.5:1.5b` on `127.0.0.1:11434`). Zero API keys are ever written to disk:

```bash
.venv/bin/python -m src.cli
```

For offline deterministic verification without external model dependencies:

```bash
.venv/bin/python -m src.cli --mode loopback --no-write
```

### 3. Run the Deterministic Test Suite & Negative-Control Tripwire

```bash
.venv/bin/pytest tests -q
CORRUPT_GATE_CONTROL=1 .venv/bin/pytest tests -q  # Expected to exit non-zero
```

### 4. Open the Interactive Dark Studio Diagnostic Console

```bash
python3 -m http.server 8765
# Visit http://127.0.0.1:8765/web/diagnostic_console.html
```

## Key Deliverables

- [BUILDING_BLOCKS_TESTED.md](BUILDING_BLOCKS_TESTED.md) — Live model receipt summary, tool execution table, 6 empirical SDK probe results, and Cortensor Portal/Router posture matrix.
- [WHAT_WE_LEARNED.md](WHAT_WE_LEARNED.md) — Five source-verified OpenMinion `0.1.24` findings (`OM-FINDING-01` through `OM-FINDING-05`) with line numbers and upstream fix proposals.
- `outputs/live_model_run_receipt.json` & `outputs/building_blocks_tested.json` — Machine-verifiable sanitized run receipts.
- `web/diagnostic_console.html` — Anti-slop Dark Studio (`noir`) OpenMinion Diagnostic Console with interactive 6-axis radar and PNG receipt export.

## License

Apache-2.0. OpenMinion is an independent Apache-2.0 open-source runtime; this submission does not claim official OpenMinion brand endorsement.
