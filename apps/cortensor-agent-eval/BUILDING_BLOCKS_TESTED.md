# OpenMinion Building Blocks Tested (`openminion==0.1.24`)

| Building Block | Where Used | Purpose | Verification Status |
| --- | --- | --- | --- |
| `ProviderSetupRequest`, `build_provider_setup`, `atomic_save_setup_config` | `src/cortensor_agent_eval/policy.py` | Generates isolated `agents.json` for `cortensor-portal`, `cortensor-router`, `openrouter`, `openai`, `groq`, `ollama`. | Verified (unit + e2e) |
| `APIRuntime.from_config_path` & `runtime.close()` | `src/cortensor_agent_eval/runner.py` | Initializes SQLite session/memory runtime in isolated `home_root`/`data_root` and cleans up in `finally`. | Verified (Windows temp dir cleanup) |
| `runtime.runtime_posture`, `capability_report`, `runtime_self_model`, `tool_inventory_report` | `src/cortensor_agent_eval/runner.py` | Captures canonical turn path, capability keys, self-model health, and 106-tool readiness inventory. | Verified (`facts.json`) |
| `Agent.run_stream` + `on_delta` | `src/cortensor_agent_eval/runner.py` | Exercises `PhaseStatus` streaming progress callbacks during session continuity turn. | Verified (`stream_events_observed > 0`) |
| `Agent` + `session_id` | `src/cortensor_agent_eval/runner.py` | Multi-turn collector, writer, and judge agents sharing one runtime and session ID. | Verified (`case_session_continuity`) |
| `openminion.subagent` | `src/cortensor_agent_eval/runner.py` | Delegates `score_case_output` to a bounded read-only child agent (`timeout_seconds`). | Verified (`case_subagent_delegation`) |
| `@tool(min_scope="READ_ONLY", idempotent=True)` | `src/cortensor_agent_eval/tools.py` | `probe_inference_endpoint` and `score_case_output`. | Verified (e2e mock server) |
| `@tool(idempotent=True)` + `forced_tools` + `approval_callback` | `src/cortensor_agent_eval/tools.py`, `policy.py` | Gates `write_eval_artifact` via `FailClosedApprovalGate` (single-use allow, deny unlisted/dangerous tools). | Verified (unit + e2e) |
| `@tool(dangerous=True)` | `src/cortensor_agent_eval/tools.py` | `purge_eval_history` explicitly blocked by fail-closed gate. | Verified (`test_fail_closed_approval_gate_single_use`) |
| `Agent(output_type=EvalReport)` | `src/cortensor_agent_eval/runner.py`, `models.py` | Pydantic v2 structured output coercion and validation. | Verified (`case_structured_judge`) |
| `MemoryBundle`, `export_bundle`, `save_bundle`, `load_bundle`, `import_bundle` | `src/cortensor_agent_eval/runner.py` | Exports and re-validates portable run telemetry (`trust_mode="candidate"`). | Verified (`memory_bundle.json`) |
| `ProviderError`, `TurnTimeoutError`, `AgentOutputValidationError` | `src/cortensor_agent_eval/runner.py` | Explicit error handling with deterministic offline fallback when `--no-fallback` is omitted. | Verified (`test_provider_error_fallback_mode` + Portal probe) |
