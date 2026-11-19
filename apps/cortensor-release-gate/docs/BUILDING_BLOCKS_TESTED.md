# OpenMinion 0.1.23 Building Blocks Tested

Every block below was exercised in code and automated tests against `openminion==0.1.23` on Python 3.12.6 (Windows 11) via `cortensor-release-gate probe . --json` (`artifacts/probe_matrix.json`).

**Summary:** `10/10` probes passed (`all_passed: true`, total duration `22,586.74 ms`).

| # | Probe ID | Building Block | Latency (ms) | Status | Observed Evidence |
|---:|---|---|---:|---|---|
| 1 | `runtime_diagnostics` | `APIRuntime.from_config_path`, `tool_inventory_report`, `runtime_posture`, `runtime_self_model` | `33.72` | **PASS** | Loaded `104` built-in tools, `9` posture keys, and `11` self-model keys in isolated SQLite storage |
| 2 | `agent_tool_and_output_type` | `Agent`, `@tool(min_scope="READ_ONLY")`, `output_type=SecurityAuditReport` | `4,843.67` | **PASS** | Executed `scan_security_tool` and coerced response into `SecurityAuditReport` (`run_state=completed`, `files_scanned=29`) |
| 3 | `subagent_isolation` | `subagent()` child session isolation | `1,508.47` | **PASS** | Spawned child `probe_docs_child` with scoped `[scan_docs_tool]`; verified `5` required community files |
| 4 | `handoff_delegation` | `Handoff` delegation & `approval_callback` | `2,327.09` | **PASS** | Compiled `transfer_to_triage_planner`, delegated triage generation (`decision=CHANGES_REQUIRED`, `actions_count=1`) |
| 5 | `approval_callback_gate` | `ActionPolicyConfig(default_action="require_confirm")` + `WRITE_SAFE` tool | `1,763.85` | **PASS** | Intercepted `write_release_gate_report` (`approvals_triggered=1`, `report_written=True`) |
| 6 | `memory_bundle_portability` | `MemoryBundle` export, save, load, import & blocker diff | `8.14` | **PASS** | Verified round-trip serialization and cross-run blocker diffing (`loaded_blockers=0`) |
| 7 | `cortensor_completion_mode` | `CortensorProvider` (`api_mode="cortensor_completion"`, `session_id=7`) | `1,314.17` | **PASS** | Completed full `GatewayService` turn against `/api/v2/completions` (`mode=cortensor_completion`, `ok=True`) |
| 8 | `subagent_memory_guard` | `subagent(..., memory_posture="read_only_bounded")` v1 negative contract | `0.02` | **PASS** | Raised expected `ValueError("developer subagent memory grants are not bound in v1")` |
| 9 | `forced_tools_and_capabilities` | `Agent(forced_tools=...)`, `capability_report()`, `tool_schema_report()` | `1,908.68` | **PASS** | Forced `scan_docs_tool` execution (`present_files=5`), verified `7` capability keys, and observed `tool_schema_report(tool_name="scan_docs_tool") == None` for custom `@tool` |
| 10 | `session_continuity_turns` | Multi-turn persistence sharing explicit `session_id` | `8,878.93` | **PASS** | Ran 2 consecutive turns under `session_id="probe-continuity-1"` (`turns_matched=True`, `second_files_scanned=29`) |
