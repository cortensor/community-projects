# OpenMinion 0.1 Building Blocks Tested

> **Calibration Posture**: [Live LLM Calibrated]

## Execution Summary

- **SDK Version**: `openminion==0.1.21`
- **Preset**: `openai-compatible`
- **Model**: `grok-4.7`
- **Endpoint Host**: `https://<configured-openai-compatible-relay>/v1`
- **Generated At (UTC)**: `2026-11-14T17:06:50.166083+00:00`
- **Result**: `10/10` probes passed (`failed=0`)
- **Total Suite Latency**: `611888.99 ms`

## Probe Matrix (10 Core OpenMinion Building Blocks)

| # | Probe ID | Building Block | Status | Latency (ms) | Observed Evidence |
|---:|---|---|---|---:|---|
| 1 | `agent_runtime_isolation` | Agent & APIRuntime Isolation | **PASS** | 6576.08 | Isolated agents.json verified secret-free; SQLite DB isolated under data_root (14 db file(s)); run_id=2d700e1618cd402c803fd8c2f68ddb2d. |
| 2 | `structured_pydantic_output` | Structured Pydantic Output & Validation Error | **PASS** | 207213.19 | Validated _ProbeStructuredOutput (status=OK, score=0.99) and verified AgentOutputValidationError negative contract. |
| 3 | `tool_and_forced_tools` | @tool Registration & forced_tools Execution | **PASS** | 77598.94 | Executed auto tool (probe_lookup_fact) and forced_tools=(probe_echo_tag) cleanly. |
| 4 | `policy_confirmation_gate` | Policy Gate (@tool dangerous=True Allow & Deny) | **PASS** | 76300.74 | Dangerous @tool(dangerous=True, min_scope='WRITE_SAFE') verified allow, deny, and fail-closed approval_callback=None pause/thread_id allow_once resume. |
| 5 | `session_continuity` | Session Continuity & Cross-Session Isolation | **PASS** | 92405.48 | Session probe-sess-a-5b958e6d (thread probe-sess-a-5b958e6d:e44db35cf831436fab48837c1f5f6be8) recalled marker across turns; isolated session probe-sess-b-c3d87288 had zero leakage. |
| 6 | `memory_bundle_portability` | MemoryBundle Export, Save, Load & Import | **PASS** | 1.99 | Roundtripped MemoryBundle memory_bundle.v1 (1 item) via export_bundle -> save_bundle -> load_bundle -> import_bundle(direct/candidate). |
| 7 | `subagent_delegation` | subagent() & SubagentRunContext Delegation | **PASS** | 30651.67 | Child subagent (probe-corroborator) ran with isolated SubagentRunContext (context_id=subagent-bf6c16b7d24d) without closing parent runtime. |
| 8 | `agent_handoff` | Handoff Peer Agent Transfer Tool | **PASS** | 110097.21 | Handoff registered 'transfer_to_specialist' and executed peer specialist turn cleanly (invocations=1, verbatim_ack=False). |
| 9 | `submit_turn_streaming_telemetry` | submit_turn() Streaming TurnChunk & TurnTelemetry | **PASS** | 6278.02 | Collected 12 TurnChunk(s) (status, final_text); TurnTelemetry(duration_ms=6281, tokens_in=0, tokens_out=0, retries=0, queue_wait_ms=0); stats(input_tokens=11841, output_tokens=430). |
| 10 | `error_and_timeout_contracts` | ProviderError Retries, Timeout & Connection Reuse Policy | **PASS** | 4765.67 | Verified http_connection_reuse_enabled=False; HTTP 500 raised ProviderError after 6 attempt(s); slow stub (1.5s vs 1.0s timeout) raised TurnTimeoutError; verified Anthropic (/v1/messages), Cortensor (/api/v2/completions), and OpenAI SSE usage gating. |

## Per-Probe Telemetry & Metadata

### `agent_runtime_isolation` — Agent & APIRuntime Isolation
- **Passed**: `True` (`6576.08 ms`)
- **Detail**: Isolated agents.json verified secret-free; SQLite DB isolated under data_root (14 db file(s)); run_id=2d700e1618cd402c803fd8c2f68ddb2d.
- **Metadata**: `{"db_count": 14, "run_id": "2d700e1618cd402c803fd8c2f68ddb2d", "secret_free_config": true}`

### `structured_pydantic_output` — Structured Pydantic Output & Validation Error
- **Passed**: `True` (`207213.19 ms`)
- **Detail**: Validated _ProbeStructuredOutput (status=OK, score=0.99) and verified AgentOutputValidationError negative contract.
- **Metadata**: `{"fallback_stub_used": false, "negative_validation_error": true, "score": 0.99, "status": "OK"}`

### `tool_and_forced_tools` — @tool Registration & forced_tools Execution
- **Passed**: `True` (`77598.94 ms`)
- **Detail**: Executed auto tool (probe_lookup_fact) and forced_tools=(probe_echo_tag) cleanly.
- **Metadata**: `{"forced_tool": "probe_echo_tag", "invocations": ["probe_lookup_fact:cortensor-poi", "probe_echo_tag:forced-c3"]}`

### `policy_confirmation_gate` — Policy Gate (@tool dangerous=True Allow & Deny)
- **Passed**: `True` (`76300.74 ms`)
- **Detail**: Dangerous @tool(dangerous=True, min_scope='WRITE_SAFE') verified allow, deny, and fail-closed approval_callback=None pause/thread_id allow_once resume.
- **Metadata**: `{"allow_executed": true, "callback_count": 2, "deny_blocked": true, "executed_ids": ["att-allow", "att-pause-resume"], "pause_blocked": true, "paused_thread_id": "probe-policy-pause-18d3a53ede0:0274e1c9510a48b9b8727e9cfec5f271", "pending_confirmation_id": "call-5a36ca6b-fe80-4d14-8500-59e5a01ea5ef-0", "resume_executed": true}`

### `session_continuity` — Session Continuity & Cross-Session Isolation
- **Passed**: `True` (`92405.48 ms`)
- **Detail**: Session probe-sess-a-5b958e6d (thread probe-sess-a-5b958e6d:e44db35cf831436fab48837c1f5f6be8) recalled marker across turns; isolated session probe-sess-b-c3d87288 had zero leakage.
- **Metadata**: `{"same_session_recalled": true, "second_session_isolated": true, "session_a": "probe-sess-a-5b958e6d", "session_b": "probe-sess-b-c3d87288", "thread_id": "probe-sess-a-5b958e6d:e44db35cf831436fab48837c1f5f6be8"}`

### `memory_bundle_portability` — MemoryBundle Export, Save, Load & Import
- **Passed**: `True` (`1.99 ms`)
- **Detail**: Roundtripped MemoryBundle memory_bundle.v1 (1 item) via export_bundle -> save_bundle -> load_bundle -> import_bundle(direct/candidate).
- **Metadata**: `{"bundle_version": "memory_bundle.v1", "invalid_mode_rejected": true, "item_count": 1}`

### `subagent_delegation` — subagent() & SubagentRunContext Delegation
- **Passed**: `True` (`30651.67 ms`)
- **Detail**: Child subagent (probe-corroborator) ran with isolated SubagentRunContext (context_id=subagent-bf6c16b7d24d) without closing parent runtime.
- **Metadata**: `{"context_id": "subagent-bf6c16b7d24d", "parent_transcript_inherited": false, "subagent_calls": ["subagent-check"], "tool_allowlist": ["probe_subagent_tool"]}`

### `agent_handoff` — Handoff Peer Agent Transfer Tool
- **Passed**: `True` (`110097.21 ms`)
- **Detail**: Handoff registered 'transfer_to_specialist' and executed peer specialist turn cleanly (invocations=1, verbatim_ack=False).
- **Metadata**: `{"handoff_invocations": 1, "run_id": "31660b20ead3480d837e72c95be70f96", "tool_name": "transfer_to_specialist", "verbatim_ack": false}`

### `submit_turn_streaming_telemetry` — submit_turn() Streaming TurnChunk & TurnTelemetry
- **Passed**: `True` (`6278.02 ms`)
- **Detail**: Collected 12 TurnChunk(s) (status, final_text); TurnTelemetry(duration_ms=6281, tokens_in=0, tokens_out=0, retries=0, queue_wait_ms=0); stats(input_tokens=11841, output_tokens=430).
- **Metadata**: `{"chunk_count": 12, "chunk_kinds": ["status", "status", "status", "status", "status", "status", "status", "status", "status", "status", "final_text", "status"], "duration_ms": 6281, "queue_wait_ms": 0, "retries": 0, "stats": {"cache_read_tokens": 1152, "duration_ms": 6149, "input_tokens": 11841, "llm_calls": 1, "output_tokens": 430, "tool_calls": 0, "tool_errors": 0}, "stats_input_tokens": 11841, "stats_output_tokens": 430, "telemetry_metadata_mismatch": true, "tokens_in": 0, "tokens_out": 0}`

### `error_and_timeout_contracts` — ProviderError Retries, Timeout & Connection Reuse Policy
- **Passed**: `True` (`4765.67 ms`)
- **Detail**: Verified http_connection_reuse_enabled=False; HTTP 500 raised ProviderError after 6 attempt(s); slow stub (1.5s vs 1.0s timeout) raised TurnTimeoutError; verified Anthropic (/v1/messages), Cortensor (/api/v2/completions), and OpenAI SSE usage gating.
- **Metadata**: `{"http_500_attempts": 6, "http_connection_reuse_enabled": false, "provider_error_raised": true, "provider_wire_formats": {"anthropic_path": "/anthropic/v1/messages", "anthropic_version_header": true, "anthropic_x_api_key": true, "cortensor_bearer_auth": true, "cortensor_path": "/cortensor/api/v2/completions", "openai_sse_usage_with_vendor": true, "openai_sse_usage_without_vendor": false}, "timeout_exception": "TurnTimeoutError", "timeout_raised": true}`
