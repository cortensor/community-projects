# Building Blocks Tested — Minionbench Ops (`openminion==0.1.24`)

- **Project:** `minionbench-ops` (Cortensor Hackathon #5 / DoraHacks `#2418`)
- **OpenMinion SDK Version:** `0.1.24`
- **Generated (UTC):** `2026-11-21T15:46:22Z`
- **Live Neural Model Turn:** `qwen2.5:1.5b` via `openai (Ollama /v1 neural runtime)` (`session_id=cortensor-release-triage-01-ollama-s3a1`, `run_state=completed`, `197460.22 ms`)

## 1. Live Model-Backed Workflow Summary

Minionbench Ops embeds `APIRuntime` and `Agent` inside a strict vertical-slice Python 3.12 architecture to run repeatable release-and-triage audits for Cortensor builders. During live execution, the agent invoked workspace-confined `@tool(min_scope="READ_ONLY", idempotent=True)` functions across a durable `session_id` and `thread_id` chain while keeping runtime SQLite databases isolated under `.openminion_runtime/`.

| Tool Invoked | Scope | Idempotent | Arguments | Result Excerpt |
| :--- | :--- | :--- | :--- | :--- |
| `inspect_workspace_manifest` | `READ_ONLY` | `True` | `{"workspace_rel_dir": "."}` | `{"committed_env_files": [], "gitignore_guards": [".venv/", ".openminion_runtime/", "__pycache__/", ".pytest_ca` |
| `audit_python_module_risks` | `READ_ONLY` | `True` | `{"target_subpath": "src"}` | `{"architecture_clean": true, "forbidden_mock_or_testclient_imports": [], "python_files_scanned": 14, "scanned_` |
| `check_cortensor_config_posture` | `READ_ONLY` | `True` | `{"profile_mode": "cortensor-portal"}` | `{"agents_json_note": "Always set agents.<id>.default_channel='console' and omit mismatched human display names` |

- **Hosted Endpoint Preflight Note:** Gemini preflight caught PROVIDER_ERROR (PROVIDER_ERROR: The configured model provider failed before it could return a decision (openai request failed with HTTP 400: HTTP 400). Plea); executed live neural fallback on local Ollama qwen2.5:1.5b via /v1 OpenAI transport.
- **Agent Synthesis Excerpt:** ollama-live: The tool call has been confirmed to have executed successfully. Here is the result:  ```json { "package_name": "minionbench-ops", "secret_hygiene_ok": true } ```  ollama-live: The tool execution was successful, with 14 Python files scanned for risks. There were no sibling import violations or import statem

## 2. Six Empirical OpenMinion 0.1.24 Diagnostic Probes

| Probe ID | SDK Surface | Status | Latency (`ms`) | What Worked & Empirical Finding |
| :--- | :--- | :--- | :--- | :--- |
| `probe-01-tool-scope-policy` | `@tool(min_scope='READ_ONLY', idempotent=True) vs @tool + approval_callback` | `PASS` | `2548.0` | READ_ONLY idempotent tools run without operator friction; bare @tool pauses at policy_confirmation_prompt, blocks on callback False, and executes once on True. |
| `probe-02-durable-session-continuity` | `Agent(session_id=...) + Agent.run(..., thread_id=...)` | `PASS` | `822.42` | Passing thread_id=first.thread_id resumes SQLite conversation state (session_history_available='true'), whereas omitting thread_id forks a new settled thread. |
| `probe-03-structured-output-validation` | `Agent(output_type=ReleaseVerdictSchema) & AgentOutputValidationError` | `PASS` | `367.06` | OpenMinion extracts schema-valid JSON even when prefixed with '<agent_id>: ', and raises AgentOutputValidationError carrying raw_text when JSON coercion fails. |
| `probe-04-provider-and-timeout-errors` | `ProviderError (HTTP 503) & TurnTimeoutError (timeout_seconds=0.25)` | `PASS` | `4750.85` | Upstream HTTP 503 failures surface cleanly as ProviderError after bounded retries, and slow turns cancel cleanly with TurnTimeoutError. |
| `probe-05-cli-readiness-and-config-parity` | `openminion setup --list-providers --json & status readiness` | `PASS` | `675.84` | Setup catalog exposes 20 provider presets (including gemini, cortensor-portal, cortensor-router) mapping onto 9 core transport drivers, with Cortensor Portal retries disabled (max_retries=0) and Router timeout floored at 455s. |
| `probe-06-config-tripwires-and-feedback` | `GatewaySecurity.enforce_inbound_authenticity & resolve_agent_config` | `PASS` | `438.2` | Reproduced both 0.1.24 config edge cases (empty default_channel RuntimeError in warn mode and agents.<id>.name UnknownProfileError) and synthesized 5 upstream engineering recommendations. |

## 3. Cortensor Portal, Router & OpenAI-Bridge Posture Matrix

| Profile | Setup Catalog ID | `agents.json` Key | Endpoint | Retries | Turn Timeout Floor |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `cortensor_portal` | `cortensor-portal` | `openai` | `https://api.cortensor.app/v1` | `0` | `45.0s` |
| `cortensor_router` | `cortensor-router` | `cortensor` | `http://127.0.0.1:8080/api/v2/completions` | `0` | `455.0s` |
| `gemini_openai_bridge` | `gemini` | `openai` | `https://generativelanguage.googleapis.com/v1beta/openai` | `2` | `45.0s` |
| `ollama_openai_bridge` | `ollama` | `openai` | `http://127.0.0.1:11434/v1` | `2` | `45.0s` |
