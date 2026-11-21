# OpenMinion 0.1 Building Blocks Tested

Measured automatically against live provider **`gemini`** (`gemini-flash-lite-latest`) on **`openminion==0.1.23`** at `2026-11-21T12:29:55.300208+00:00`.

**Overall Score:** `8/10` probes passed in `208127.16 ms`.

| # | Probe | Building Block | Outcome | Latency (ms) | Attempts | Notes & Measured Behavior |
| ---: | :--- | :--- | :--- | ---: | ---: | :--- |
| 1 | `probe_01_runtime` | APIRuntime Diagnostics | **pass** | 25.97 | 1 | Inspected APIRuntime capability_report, runtime_posture, and model_connection_catalog. |
| 2 | `probe_02_single_turn` | Agent.run (Single Turn) | **fail** | 12578.63 | 1 | Single-turn Agent.run() hit OpenMinion runtime guard: INVALID_TASK_CONTEXT_UPDATE. |
| 3 | `probe_03_stream` | Agent.run_stream (Delta Callbacks) | **pass** | 12953.74 | 1 | Agent.run_stream() emitted 9 progress events. |
| 4 | `probe_04_read_tool` | @tool(READ_ONLY) + forced_tools | **pass** | 29579.27 | 1 | @tool(min_scope='READ_ONLY') + forced_tools executed with live model synthesis. |
| 5 | `probe_05_schema_ok` | Pydantic output_type (Schema Prompt) | **pass** | 39136.84 | 1 | Validated Pydantic output natively: status='ok', sdk='0.1.23'. |
| 6 | `probe_06_schema_err` | AgentOutputValidationError Guard | **expected_error** | 7986.14 | 1 | Verified fail-closed AgentOutputValidationError raised with raw_text preserved. |
| 7 | `probe_07_session` | Session & Thread Continuity | **fail** | 18611.21 | 2 | Session recall missed token COR-D8ECE9 (INVALID_TASK_CONTEXT_UPDATE). |
| 8 | `probe_08_subagent` | subagent() + DelegatedMemoryReadRequest | **pass** | 35255.77 | 1 | Executed isolated child subagent() with DelegatedMemoryReadRequest grant lifecycle. |
| 9 | `probe_09_handoff` | Handoff Delegation (transfer_to_*) | **pass** | 22600.29 | 1 | Handoff compiled transfer_to_cortensor_specialist and completed peer delegation cleanly. |
| 10 | `probe_10_memory_ingress` | MemoryBundle & APIRuntime.submit_turn | **pass** | 5236.63 | 1 | Verified MemoryBundle round-trip serialization and APIRuntime.submit_turn().result(). |

## Key Architectural Observations

- **Bounded Subagent Isolation (`subagent` + `DelegatedMemoryReadRequest`)**: Child agents start with clean transcripts (`parent_transcript_inherited=False`), bounded `tool_allowlist`, and single-use `read_only_bounded` policy grants that are revoked automatically in `finally`.
- **Fail-Fast `Handoff` Validation**: Duplicate `Handoff.resolved_name()` values are rejected upfront before tool registration, avoiding cryptic runtime exposure-profile collisions.
- **Strict Output Guard (`AgentOutputValidationError`)**: When a model emits prose instead of JSON, `Agent._coerce_output` raises `AgentOutputValidationError` while preserving `.raw_text` and `.validation_error` for debugging.
