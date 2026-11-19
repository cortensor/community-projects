# OpenMinion 0.1.23 Building Blocks Tested

Every block below was exercised in code and automated tests against `openminion==0.1.23` on Python 3.12.6 (Windows 11).

| Building Block | How Exercised | Observed Result |
| --- | --- | --- |
| `APIRuntime.from_config_path` & diagnostics | Isolated `home_root`, `data_root`, and SQLite storage; inspected `tool_inventory_report()`, `runtime_posture()`, and `runtime_self_model()` | Loaded 104 built-in tools, 9 posture keys, and 11 self-model keys cleanly |
| `@tool` with `min_scope` | Registered `scan_security_tool`, `scan_docs_tool`, `scan_cortensor_wiring_tool` (`READ_ONLY`), and `write_release_gate_report` (`WRITE_SAFE`, `dangerous=True`) | Scoped tool calls executed and serialized typed dictionaries inside OpenMinion tool result envelopes |
| `Agent` with `output_type` | Ran `Agent(..., output_type=SecurityAuditReport / DocsAuditReport / TriagePlan / ReleaseGateVerdict)` | Coerced JSON responses from `raw["body"]` into Pydantic v2 models via `Agent._coerce_output()` |
| `subagent()` isolation | Spawned `security_auditor` and `docs_auditor` from coordinator with scoped tool lists | Each subagent executed in its own `session_id` with only its assigned `READ_ONLY` scanner tool |
| `Handoff` delegation | Configured `Handoff(target=triage_planner, name="transfer_to_triage_planner")` | Compiled into `transfer_to_triage_planner` tool; executed when authorized via `approval_callback` |
| `approval_callback` gating | Gated `write_release_gate_report` using `ActionPolicyConfig(default_action="require_confirm")` | Returning `False` prevented file writes; returning `True` allowed artifact generation |
| `MemoryBundle` portability | Used `export_bundle`, `save_bundle`, `load_bundle`, and `import_bundle` across consecutive runs | Persisted prior blocker IDs and reported `resolved_since_last_run` when issues were fixed |
| `CortensorProvider` (`openai_chat` & `cortensor_completion`) | Tested `providers.cortensor` against local HTTP loopback `/v1/chat/completions` and `/api/v2/completions` | Both request formats completed full `GatewayService` turns and returned valid payloads |
