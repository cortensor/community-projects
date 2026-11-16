# What We Learned: OpenMinion 0.1 SDK Empirical DX Report

> **Calibration Posture**: [Live LLM Calibrated]

Generated directly from `BuildingBlockProbeRunner.run_all()` against `openminion==0.1.21` (`preset=openai-compatible`, `model=grok-4.7`, `endpoint=https://<configured-openai-compatible-relay>/v1`, `10/10` passed in `611888.99 ms`).

## What Worked Cleanly in OpenMinion 0.1

- **`APIRuntime` isolation & zero-key disk posture**: `create_isolated_runtime()` / `APIRuntime.from_config_path()` bound per-worktree SQLite stores and persisted `agents.json` with zero plaintext API keys or env secrets (`db_count=14, secret_free_config=True, run_id=2d700e1618cd402c803fd8c2f68ddb2d`).
- **Typed Pydantic coercion & validation contract**: `Agent._coerce_output()` / `_extract_json_object()` validated `BaseModel` schemas cleanly and raised `AgentOutputValidationError` on non-JSON outputs (`status=OK, score=0.99, negative_validation_error=True, fallback_stub_used=False`).
- **Scoped `min_scope='READ_ONLY'` `@tool` binding & `tool_choice='forced'`**: Read-only verifier tools registered with `idempotent=True` executed without workspace mutations, and `forced_tools` enforced deterministic single-tool dispatch (`forced_tool=probe_echo_tag, invocations=['probe_lookup_fact:cortensor-poi', 'probe_echo_tag:forced-c3']`).
- **Fail-closed confirmation gate & pause/resume**: `@tool(dangerous=True, min_scope='WRITE_SAFE')` honored boolean `approval_callback` (allow/deny) and paused fail-closed on `approval_callback=None` until resumed via `Agent.run('allow_once', session_id=..., thread_id=...)` (`callback_count=2, allow_executed=True, deny_blocked=True, pause_blocked=True, resume_executed=True, pending_confirmation_id=call-5a36ca6b-fe80-4d14-8500-59e5a01ea5ef-0`).
- **Peer `Handoff` transfer + target `PolicyGrantInput` gating**: `Handoff` compiled `transfer_to_*` delegation tools to route across peer `Agent` runtimes, pairing cleanly with target-runtime `PolicyGrantInput(max_uses=1)` for fail-closed confirmation-gated publication (`tool_name=transfer_to_specialist, handoff_invocations=1, run_id=31660b20ead3480d837e72c95be70f96`).
- **Cross-session isolation & explicit `thread_id` continuity**: Forwarding `thread_id` alongside `session_id` preserved multi-turn recall while distinct sessions remained strictly isolated (`same_session_recalled=True, second_session_isolated=True, session_a=probe-sess-a-5b958e6d, session_b=probe-sess-b-c3d87288, thread_id=probe-sess-a-5b958e6d:e44db35cf831436fab48837c1f5f6be8`).
- **`MemoryBundle` portability & schema validation**: `export_bundle()` -> `save_bundle()` -> `load_bundle()` -> `import_bundle()` roundtripped portable state across runtimes and raised `InvalidArgumentError` on invalid trust modes (`bundle_version=memory_bundle.v1, item_count=1, invalid_mode_rejected=True`).
- **Isolated `subagent()` & `SubagentRunContext` execution**: Child subagents executed with scoped `tool_allowlist` and `parent_transcript_inherited=False`, and `child.close()` left the parent `APIRuntime` open (`context_id=subagent-bf6c16b7d24d, parent_transcript_inherited=False, tool_allowlist=['probe_subagent_tool'], subagent_calls=['subagent-check']`).
- **`APIRuntime.submit_turn()` `TurnChunk` SSE streaming**: `RuntimeTurnHandle.stream()` delivered ordered `TurnChunk` status and `final_text` events alongside populated `TurnResponse.stats` usage counters (`chunk_count=12, duration_ms=6281, stats_input_tokens=11841, stats_output_tokens=430`).
- **Deterministic error, timeout & wire-adapter contracts**: Exhausted retries raised `ProviderError`, exceeded turn deadlines raised `TurnTimeoutError`, `http_connection_reuse_enabled=False` avoided Windows keep-alive pool stalls, and `AnthropicProvider` / `CortensorProvider` / `OpenAIProvider` wire checks passed (`http_500_attempts=6, timeout_exception=TurnTimeoutError, http_connection_reuse_enabled=False`).

## What Broke & Rough Edges Encountered

- **Implicit new thread per `Agent.run(session_id=...)` without explicit `thread_id`**: `Agent._build_payload()` (`openminion/api/agent.py:167-170`) omits `inbound_metadata['thread_id']` unless `thread_id` is passed explicitly, so `resolve_thread_routing_decision()` (`openminion/modules/task/run/status.py:532-539`) treats subsequent turns on a settled session as `settled_without_resume` and forks a fresh `thread_id` (verified with `thread_id=probe-sess-a-5b958e6d:e44db35cf831436fab48837c1f5f6be8`).
- **`TurnTelemetry` token-zero mismatch vs `TurnResponse.stats`**: `_turn_success_response()` (`openminion/services/runtime/daemon.py:549-555`) populates `TurnTelemetry.tokens_in/tokens_out` from `metadata.get('usage_prompt_tokens')` and `metadata.get('usage_completion_tokens')`, whereas brain post-execution writes `total_input_tokens_used` / `total_output_tokens_used` and `turn_result.stats` (`tokens_in=0`, `tokens_out=0` vs `TurnResponse.stats` `input_tokens=11841`, `output_tokens=430`, `telemetry_metadata_mismatch=True`).
- **`handoff.target.run(message)` timeout & approval omission**: `build_delegate_tool()` (`openminion/api/handoff.py:168-170`) invokes `handoff.target.run(message)` without forwarding caller `timeout_seconds` (falling back to the `90.0s` default in `openminion/base/config/runtime/__init__.py:73`) or `approval_callback`, forcing target runtimes to rely on pre-issued `PolicyGrantInput(max_uses=1)` (`verbatim_ack=False` in live calibration as coordinators paraphrase specialist text).
- **SSE `usage` chunk suppression without `service_vendor='openai'`**: `OpenAIProvider.stream()` (`openminion/modules/llm/providers/openai/adapter.py:901-907, 961`) sets `preserve_response_facts=False` unless `service_vendor == 'openai'` or a compat dialect overrides it, causing `_iter_openai_stream_events()` (`adapter.py:505-524`) to skip final `usage`, `finish_reason`, and tool-call deltas for OpenAI-compatible relays (`openai_sse_usage_without_vendor=False` vs `openai_sse_usage_with_vendor=True`).
- **Layered HTTP 500 retry multiplication & Windows connection reuse**: With `http_connection_reuse_enabled=False`, `provider_retry_max_attempts=2` multiplied by transport retries produced `http_500_attempts=6` before raising `ProviderError`.
- **Sequential `subagent()` `task_update` state collision & `90.0s` timeout fallback**: `resolve_entry_task_update()` (`openminion/modules/brain/loop/context/task_context.py:173-191`) raises `ValueError('Missing task_update for a clarification or active request')` or `ValueError('Exactly one task_update is allowed per entry response')` when sequential subagent passes share session task state or emit batched entry tool calls, while omitting explicit `timeout_seconds` falls back to the `90.0s` runtime default (`services/runtime/daemon.py:307`) (isolated `context_id=subagent-bf6c16b7d24d`).
- **Internal `submit_output` classifier turns & `agent_id:` reply prefix**: OpenMinion issues internal `FreshnessContract`, `FinalizationStatus`, and `ClosureJudgment` (`tool_choice='submit_output'`) turns requiring `action_summary` preservation in gateways/stubs, and prefixes replies with `f'{agent_id}: '`, requiring `_extract_json_object()` recovery.

## Actionable SDK Improvement Proposals (Repro + Expected vs. Actual)

### 1. Populate `TurnTelemetry` Token Counts from `turn_result.stats` / `total_*_tokens_used`

- **Target Module**: `openminion/services/runtime/daemon.py:549-555` (`_turn_success_response`)
- **Minimal Repro**: `handle = runtime.submit_turn({'session_id': ..., 'message': ..., 'stream': True}); resp = handle.result()`
- **Expected vs. Actual**: Expected `TurnTelemetry` to match `TurnResponse.stats`; actual run emitted `TurnTelemetry(tokens_in=0, tokens_out=0)` alongside `stats(input_tokens=11841, output_tokens=430)`.
- **Recommended Upstream Fix**: Read `turn_result.stats.input_tokens` / `output_tokens` first (falling back to `metadata.get('usage_prompt_tokens') or metadata.get('total_input_tokens_used')` and `metadata.get('usage_completion_tokens') or metadata.get('total_output_tokens_used')`).

### 2. Forward `timeout_seconds` & Approval Context in `Handoff` / `build_delegate_tool()`

- **Target Module**: `openminion/api/handoff.py:168-170` (`build_delegate_tool._handler_fn`)
- **Minimal Repro**: `Agent(handoffs=[Handoff(target=specialist)]).run('...', timeout_seconds=180, approval_callback=cb)`
- **Expected vs. Actual**: Expected `handoff.target.run(message)` to honor caller `timeout_seconds` and confirmation policy; actual call invokes `handoff.target.run(message)` bare, silently reverting to the `90.0s` runtime default and omitting caller `approval_callback`.
- **Recommended Upstream Fix**: Add optional `timeout_seconds` and `approval_callback` forwarding fields on `Handoff` (defaulting to the active caller run context when unset) and pass them inside `build_delegate_tool()`.

### 3. Guard `resolve_entry_task_update()` Against Shared-Session `subagent()` & Parallel Tool Calls

- **Target Module**: `openminion/modules/brain/loop/context/task_context.py:173-191` (`resolve_entry_task_update`)
- **Minimal Repro**: Run two sequential `subagent(parent, ...)` passes sharing a session or emitting parallel entry tool calls.
- **Expected vs. Actual**: Expected each independent subagent turn or multi-tool entry response to execute cleanly; actual `resolve_entry_task_update()` raises `ValueError('Missing task_update for a clarification or active request')` or `ValueError('Exactly one task_update is allowed per entry response')`, detouring into `invalid_task_context_update` clarify prompts.
- **Recommended Upstream Fix**: Deduplicate identical `task_update` sidecar patches across parallel entry tool calls, and avoid inheriting prior-run `resolved_task_context` when entering an isolated `SubagentRunContext`.

### 4. Explicit Session Thread Continuity Option on `Agent.run(session_id=...)`

- **Target Module**: `openminion/api/agent.py:167-170` & `openminion/modules/task/run/status.py:532-539`
- **Minimal Repro**: `agent.run('Remember token X', session_id='s1'); agent.run('Recall token', session_id='s1')`
- **Expected vs. Actual**: Expected consecutive `Agent.run(..., session_id='s1')` calls to share conversation history; actual second turn lacks `inbound_metadata['thread_id']`, hits `settled_without_resume`, and forks a brand-new thread with zero recall unless callers manually thread `result.thread_id` (`thread_id=probe-sess-a-5b958e6d:e44db35cf831436fab48837c1f5f6be8, same_session_recalled=True`).
- **Recommended Upstream Fix**: Expose `resume_latest_thread: bool = True` (or `continue_session`) on `Agent.run()` / `Agent._build_payload()` or clearly document mandatory `thread_id` propagation in SDK guides.

### 5. Preserve OpenAI SSE `usage` & Tool Deltas Regardless of Relay `service_vendor`

- **Target Module**: `openminion/modules/llm/providers/openai/adapter.py:901-907, 961` & `505-524`
- **Minimal Repro**: `OpenAIProvider().stream(req, {'base_url': 'https://custom-relay/v1', 'api_key': ..., 'model': ...})`
- **Expected vs. Actual**: Expected SSE `done` event `usage` to be parsed for all OpenAI-compatible SSE streams; actual `done.usage` was `None` without `service_vendor='openai'` (`openai_sse_usage_without_vendor=False` vs `openai_sse_usage_with_vendor=True`).
- **Recommended Upstream Fix**: Decouple SSE `usage` / `finish_reason` extraction in `_iter_openai_stream_events()` from `stream_contract_enabled` (only gate outbound `tools`/`tool_choice` on `stream_contract_enabled` while always parsing `chunk.get('usage')` when present in SSE frames).

## Empirical SDK & DX Findings

### 1. Worktree-Isolated home_root / data_root Containment

`create_isolated_runtime()` bound isolated `home_root` and `data_root` SQLite/agents.json directories (`db_count=14`, `secret_free_config=True`, `run_id=2d700e1618cd402c803fd8c2f68ddb2d`), preventing mutation of developer home state on Windows.

### 2. Internal Classifiers (FreshnessContract / FinalizationStatus / ClosureJudgment) & Output Coercion

openminion==0.1.21 issues `tool_choice='submit_output'` internal classifier turns (`FreshnessContract`, `FinalizationStatus`, and `ClosureJudgment` where stubs/gateways must preserve `action_summary`). `Agent._coerce_output()` also strips the `f'{agent_id}: '` reply prefix via `_extract_json_object()`, producing typed schema output (`status=OK`, `score=0.99`, `negative_validation_error=True`, `fallback_stub_used=False`).

### 3. Read-Only @tool Binding & tool_choice='forced' Deterministic Dispatch

Binding `@tool(min_scope='READ_ONLY')` with `tool_choice='forced'` invoked `probe_echo_tag` (call_count=2, forced_invoked=True, invocations=['probe_lookup_fact:cortensor-poi', 'probe_echo_tag:forced-c3']) without filesystem writes.

### 4. approval_callback Boolean Gate & Fail-Closed approval_callback=None Pause/Resume

`@tool(dangerous=True, min_scope='WRITE_SAFE')` recorded `callback_count=2`, `allow_executed=True`, and `deny_blocked=True`. Passing `approval_callback=None` paused fail-closed (`pause_blocked=True`, `pending_confirmation_id=call-5a36ca6b-fe80-4d14-8500-59e5a01ea5ef-0`) and executed only after `Agent.run('allow_once', session_id=..., thread_id=...)` (`resume_executed=True`).

### 5. Explicit thread_id Required for Multi-Turn Agent.run(session_id=...) Continuity

Retaining context across turns on the same session required forwarding `thread_id=probe-sess-a-5b958e6d:e44db35cf831436fab48837c1f5f6be8` alongside `session_id`; a distinct session preserved isolation (`same_session_recalled=True`, `second_session_isolated=True`).

### 6. Cross-Runtime MemoryBundle Export/Import Portability

OpenMinion primitives `export_bundle()`, `save_bundle()`, `load_bundle()`, and `import_bundle()` (wrapped by `export_session_memory()`/`import_session_memory()`) serialized and restored bundle state (`bundle_version=memory_bundle.v1`, `item_count=1`, `invalid_mode_rejected=True`) into a separate APIRuntime SQLite store.

### 7. Isolated Subagent Passes, task_update Collisions & 90s Timeout Forwarding

Separate subagent runtime sessions avoid `resolve_entry_task_update()` `Missing/Duplicate task_update` crashes (`openminion/modules/brain/loop/context/task_context.py:153-191`) when dispatching sequential passes, while explicit `timeout_seconds` prevents falling back to the `90.0s` default (`context_id=subagent-bf6c16b7d24d`, `parent_transcript_inherited=False`, `tool_allowlist=['probe_subagent_tool']`, `subagent_calls=['subagent-check']`).

### 8. Peer Handoff Delegation & build_delegate_tool() Timeout/Approval Gap

Peer handoff reached specialist `transfer_to_specialist` (`handoff_invocations=1`, `verbatim_ack=False`). Notably, `openminion/api/handoff.py:169` invokes `handoff.target.run(message)` without caller `timeout_seconds` or `approval_callback`, so target runtimes need explicit `PolicyGrantInput(max_uses=1)` for autonomous confirmation-gated publication.

### 9. APIRuntime.submit_turn() TurnChunks & TurnTelemetry vs TurnResponse.stats

Collected 12 TurnChunk(s) with `TurnTelemetry(duration_ms=6281, tokens_in=0, tokens_out=0, retries=0, queue_wait_ms=0)` vs `TurnResponse.stats(input_tokens=11841, output_tokens=430)`; `telemetry_metadata_mismatch=True`.

### 10. Provider Wire Formats, Layered HTTP 500 Retries & http_connection_reuse_enabled=False

With `http_connection_reuse_enabled=False`, HTTP 500 produced 6 attempts (`provider_retry_max_attempts=2` * transport retries) before raising `ProviderError`, and slow responses hit `TurnTimeoutError`. Wire checks verified `AnthropicProvider` (`x-api-key` + `anthropic-version` -> `/anthropic/v1/messages`), `CortensorProvider` (`Bearer` -> `/cortensor/api/v2/completions`), and `OpenAIProvider.stream()` SSE usage gating (`without_vendor=False`, `with_service_vendor_openai=True`).

## Observed Runtime Measurements

| Probe ID | Status | Latency (ms) | Key Telemetry |
|---|---|---:|---|
| `agent_runtime_isolation` | PASS | 6576.08 | `db_count=14, run_id=2d700e1618cd402c803fd8c2f68ddb2d, secret_free_config=True` |
| `structured_pydantic_output` | PASS | 207213.19 | `fallback_stub_used=False, negative_validation_error=True, score=0.99, status=OK` |
| `tool_and_forced_tools` | PASS | 77598.94 | `forced_tool=probe_echo_tag, invocations=['probe_lookup_fact:cortensor-poi', 'probe_echo_tag:forced-c3']` |
| `policy_confirmation_gate` | PASS | 76300.74 | `allow_executed=True, callback_count=2, deny_blocked=True, executed_ids=['att-allow', 'att-pause-resume'], pause_blocked=True, paused_thread_id=probe-policy-pause-18d3a53ede0:0274e1c9510a48b9b8727e9cfec5f271, pending_confirmation_id=call-5a36ca6b-fe80-4d14-8500-59e5a01ea5ef-0, resume_executed=True` |
| `session_continuity` | PASS | 92405.48 | `same_session_recalled=True, second_session_isolated=True, session_a=probe-sess-a-5b958e6d, session_b=probe-sess-b-c3d87288, thread_id=probe-sess-a-5b958e6d:e44db35cf831436fab48837c1f5f6be8` |
| `memory_bundle_portability` | PASS | 1.99 | `bundle_version=memory_bundle.v1, invalid_mode_rejected=True, item_count=1` |
| `subagent_delegation` | PASS | 30651.67 | `context_id=subagent-bf6c16b7d24d, parent_transcript_inherited=False, subagent_calls=['subagent-check'], tool_allowlist=['probe_subagent_tool']` |
| `agent_handoff` | PASS | 110097.21 | `handoff_invocations=1, run_id=31660b20ead3480d837e72c95be70f96, tool_name=transfer_to_specialist, verbatim_ack=False` |
| `submit_turn_streaming_telemetry` | PASS | 6278.02 | `chunk_count=12, chunk_kinds=['status', 'status', 'status', 'status', 'status', 'status', 'status', 'status', 'status', 'status', 'final_text', 'status'], duration_ms=6281, queue_wait_ms=0, retries=0, stats={'cache_read_tokens': 1152, 'duration_ms': 6149, 'input_tokens': 11841, 'llm_calls': 1, 'output_tokens': 430, 'tool_calls': 0, 'tool_errors': 0}, stats_input_tokens=11841, stats_output_tokens=430, telemetry_metadata_mismatch=True, tokens_in=0, tokens_out=0` |
| `error_and_timeout_contracts` | PASS | 4765.67 | `http_500_attempts=6, http_connection_reuse_enabled=False, provider_error_raised=True, provider_wire_formats={'anthropic_path': '/anthropic/v1/messages', 'anthropic_x_api_key': True, 'anthropic_version_header': True, 'cortensor_path': '/cortensor/api/v2/completions', 'cortensor_bearer_auth': True, 'openai_sse_usage_without_vendor': False, 'openai_sse_usage_with_vendor': True}, timeout_exception=TurnTimeoutError, timeout_raised=True` |
