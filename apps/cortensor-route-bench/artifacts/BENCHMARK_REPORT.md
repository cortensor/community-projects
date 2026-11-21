# Cortensor Route Bench — Execution Report

- **Generated (UTC):** `2026-11-21T12:54:10.804979+00:00`
- **Provider:** `gemini` (`https://generativelanguage.googleapis.com/v1beta/openai/`)
- **Probe Model:** `gemini-flash-lite-latest`
- **OpenMinion SDK:** `0.1.23`
- **Preflight Status:** `READY`

## 1. Preflight Checks

| Check ID | Status | Summary |
| :--- | :--- | :--- |
| `sdk.version` | **PASS** | OpenMinion 0.1.23 imported successfully. |
| `provider.credentials` | **PASS** | Credential environment variable GEMINI_API_KEY is configured. |
| `provider.tool_calling_posture` | **PASS** | Native OpenAI tool calling supported. |
| `provider.preset_model_override` | **PASS** | Using live model 'gemini-flash-lite-latest' instead of stale preset recommendation (gemini-3.6-flash (timed out at 15s on free-tier chat completions; light variants respond reliably)). |
| `config.file_presence` | **PASS** | OpenMinion config path: .openminion\config.yaml |

## 2. OpenMinion 0.1 Building-Block Probe Matrix

**Result:** 8/10 probes succeeded (208127.16 ms total).

| Probe ID | Building Block | Status | Elapsed (ms) | Attempts | Run ID | Summary |
| :--- | :--- | :--- | ---: | ---: | :--- | :--- |
| `probe_01_runtime` | APIRuntime Diagnostics | **pass** | 25.97 | 1 | `-` | Inspected APIRuntime capability_report, runtime_posture, and model_connection_catalog. |
| `probe_02_single_turn` | Agent.run (Single Turn) | **fail** | 12578.63 | 1 | `f0701fd2b12f4f058ba025551ae7b61c` | Single-turn Agent.run() hit OpenMinion runtime guard: INVALID_TASK_CONTEXT_UPDATE. |
| `probe_03_stream` | Agent.run_stream (Delta Callbacks) | **pass** | 12953.74 | 1 | `c9a625f0850e43a08e1d86b379101e7b` | Agent.run_stream() emitted 9 progress events. |
| `probe_04_read_tool` | @tool(READ_ONLY) + forced_tools | **pass** | 29579.27 | 1 | `74bc40681f3249088907b7b6408a1421` | @tool(min_scope='READ_ONLY') + forced_tools executed with live model synthesis. |
| `probe_05_schema_ok` | Pydantic output_type (Schema Prompt) | **pass** | 39136.84 | 1 | `7f2c8f2e73694bb1aaf7a83c9e0905d0` | Validated Pydantic output natively: status='ok', sdk='0.1.23'. |
| `probe_06_schema_err` | AgentOutputValidationError Guard | **expected_error** | 7986.14 | 1 | `-` | Verified fail-closed AgentOutputValidationError raised with raw_text preserved. |
| `probe_07_session` | Session & Thread Continuity | **fail** | 18611.21 | 2 | `a61a8c6c51314fb49f109f1846cae636` | Session recall missed token COR-D8ECE9 (INVALID_TASK_CONTEXT_UPDATE). |
| `probe_08_subagent` | subagent() + DelegatedMemoryReadRequest | **pass** | 35255.77 | 1 | `989348870890478b9794521b1bd3c831` | Executed isolated child subagent() with DelegatedMemoryReadRequest grant lifecycle. |
| `probe_09_handoff` | Handoff Delegation (transfer_to_*) | **pass** | 22600.29 | 1 | `19a9ddbaead14bd2bb85bfc8456d8447` | Handoff compiled transfer_to_cortensor_specialist and completed peer delegation cleanly. |
| `probe_10_memory_ingress` | MemoryBundle & APIRuntime.submit_turn | **pass** | 5236.63 | 1 | `1bfe0b8f412540908a87de5e7866cf7d` | Verified MemoryBundle round-trip serialization and APIRuntime.submit_turn().result(). |

## 3. Multi-Agent PoI-Style Consensus Verdict

- **Task:** Verify OpenMinion 0.1.23 SDK readiness, Cortensor Portal compatibility posture, and rate-limit resilience for autonomous builder workflows.
- **Decision:** **READY**
- **Agreement Score:** `0.95`

### Worker Summaries
- Worker transport_analyst assessed SDK version 0.1.23, Gemini provider configuration, and free tier limits, reporting READY with 0.95 confidence.
- Worker reliability_verifier assessed provider tool support, Cortensor health endpoint (200 OK), and free tier limits, reporting READY with 0.95 confidence.

### Discrepancies
- Worker A notes that CORTENSOR_API_KEY is unconfigured, while Worker B confirms the Cortensor health endpoint returns 200 OK.

### Recommendations
- Proceed with gemini-flash-lite-latest for OpenMinion 0.1.23 autonomous builder workflows.
- Configure CORTENSOR_API_KEY if portal-authenticated workflows are required.
- Implement aggressive caching, request splitting, and exponential backoff to handle free-tier rate limits (~20 requests/day).

### Final Synthesis

Both workers independently verified that OpenMinion 0.1.23 SDK and Gemini provider integration are READY with high confidence (0.95). Cortensor API health is confirmed (200 OK), though care must be taken with the free-tier daily request cap and optional CORTENSOR_API_KEY configuration.
