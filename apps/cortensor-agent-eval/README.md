# Cortensor Agent Eval

Deterministic multi-agent benchmark and endpoint evaluator built on **OpenMinion (`openminion==0.1.24`)** for **Cortensor Hackathon #5**.

It evaluates OpenMinion agent workflows across five repeatable benchmark cases against any OpenAI-compatible or Cortensor inference endpoint (`cortensor-portal`, `cortensor-router`, `openrouter`, `openai`, `groq`, `ollama`), enforces a fail-closed single-use write approval gate, exports portable `MemoryBundle` state, and emits structured `facts.json` + `report.md` artifacts.

## Workflow (OpenMinion 0.1.24 SDK)

1. **Isolated Runtime Bootstrap (`ProviderSetupRequest` + `APIRuntime.from_config_path`)**:
   - Generates an isolated `agents.json` and SQLite database inside a scoped temp directory (`home_root` / `data_root`) and calls `runtime.runtime_posture()` before executing turns.
2. **Collector `Agent` (`@tool(min_scope="READ_ONLY", idempotent=True)`)**:
   - Exercises `probe_inference_endpoint` (non-destructive HTTP `/models` reachability and latency check) and maintains `session_id` continuity across follow-up turns.
3. **Bounded `subagent` Delegation (`openminion.subagent`)**:
   - Spawns a read-only `reviewer` child agent constrained to `score_case_output` with an explicit `timeout_seconds` budget.
4. **Policy-Gated Writer `Agent` (`forced_tools=["write_eval_artifact"]` + `FailClosedApprovalGate`)**:
   - Intercepts tool confirmation via `approval_callback`, approves exactly one artifact write (`summary_note.txt`), and fails closed on subsequent writes or `@tool(dangerous=True)` (`purge_eval_history`).
5. **Judge `Agent` (`output_type=EvalReport`) + Portable `MemoryBundle`**:
   - Validates structured JSON verdicts against Pydantic v2 (`EvalReport`), handles `ProviderError` / `TurnTimeoutError` / `AgentOutputValidationError` with optional deterministic fallback, and verifies `MemoryBundle` (`save_bundle` / `load_bundle` / `import_bundle`) round-trip persistence.

## Setup and Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

Run tests (starts an in-process OpenAI-compatible mock server, no external API key required):

```bash
pytest -v
```

Run against Cortensor Portal or Router (set `CORTENSOR_API_KEY` in environment):

```bash
cortensor-eval --provider cortensor-portal --model oss-20b --out-dir eval-out --json
```

Run against a local OpenAI-compatible server or test offline fallback:

```bash
cortensor-eval --provider cortensor-portal --out-dir eval-out
```

## Outputs

- `eval-out/facts.json`: full structured benchmark telemetry, probe metrics, approval audit records, and runtime posture keys.
- `eval-out/report.md`: human-readable verdict scorecard.
- `eval-out/memory_bundle.json`: portable `MemoryBundle` export verified via `import_bundle(..., trust_mode="candidate")`.
- `eval-out/summary_note.txt`: single-use policy-gated artifact produced during `case_approval_gated_write`.
