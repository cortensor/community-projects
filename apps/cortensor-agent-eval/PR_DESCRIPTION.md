## Summary

Adds `apps/cortensor-agent-eval` (`v0.1.0`, **MIT License**, pinned `openminion==0.1.24`) for **Cortensor Hackathon #5**.

**Cortensor Agent Eval** is a deterministic multi-agent benchmark and endpoint readiness evaluator built on OpenMinion `0.1.24`:
- **Isolated Runtime & Diagnostics**: uses `ProviderSetupRequest`, `build_provider_setup`, and `atomic_save_setup_config` to spin up isolated `APIRuntime` instances for `cortensor-portal`, `cortensor-router`, `openrouter`, `openai`, `groq`, and `ollama`, capturing `runtime_posture()`, `capability_report()`, `runtime_self_model()`, and `tool_inventory_report(readiness=True)` (`106` tools).
- **Security Hardening**: SSRF-protected endpoint probing (blocks private/loopback/link-local hosts and disables redirects by default), path-traversal guard on `FailClosedApprovalGate`, and atomic artifact writes (`1 MiB` cap).
- **5-Case Benchmark Pipeline**:
  1. `case_probe_tool` (`Collector Agent` + `@tool(min_scope="READ_ONLY", idempotent=True)` `probe_inference_endpoint`)
  2. `case_subagent_delegation` (`openminion.subagent` read-only child `reviewer` calling `score_case_output`)
  3. `case_approval_gated_write` (`Writer Agent` + `forced_tools=["write_eval_artifact"]` + `FailClosedApprovalGate` allowing single-use artifact writes and denying unlisted/`@tool(dangerous=True)` tools)
  4. `case_session_continuity` (same-`session_id` SQLite turn continuity via `Agent.run_stream` + `on_delta` capturing `PhaseStatus` events)
  5. `case_structured_judge` (`Judge Agent(output_type=EvalReport)` Pydantic v2 structured output)
- **Portable State & Diagnostics**: exports/re-validates `MemoryBundle` (`save_bundle`, `load_bundle`, `import_bundle`), records `runtime.runtime_posture()`, and handles `ProviderError` / `TurnTimeoutError` with deterministic offline fallback.

## Submission Checklist
- Public source & setup/run instructions: `apps/cortensor-agent-eval/README.md`
- Verified examples:
  - `apps/cortensor-agent-eval/examples/e2e-verified-run/` (`READY`, `100/100`, `5/5` cases passing)
  - `apps/cortensor-agent-eval/examples/cortensor-portal-probe/` (`https://api.cortensor.app/v1/models` -> `HTTP 401` reachable in `1075.51 ms`, clean `ProviderError` fallback)
- Building Blocks Tested: `apps/cortensor-agent-eval/BUILDING_BLOCKS_TESTED.md`
- What We Learned (actionable OpenMinion `0.1.24` SDK findings): `apps/cortensor-agent-eval/WHAT_WE_LEARNED.md`
- Automated tests: `6/6` passing via `pytest -v` (SSRF defense, path traversal defense, fail-closed single-use approval gate, OpenMinion `subagent` `agent_id` reproducer, full 5-case OpenAI-compatible E2E run with `run_stream` + `capability_report` + `runtime_self_model`, and HTTP 500 fallback test).
