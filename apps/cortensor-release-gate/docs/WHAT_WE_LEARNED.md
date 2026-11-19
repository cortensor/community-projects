# What We Learned (OpenMinion 0.1.23 & Cortensor)

Findings below are directly observed from running `openminion==0.1.23` on Windows 11 with Python 3.12.6 and inspecting the installed SDK source.

## 1. `Agent._build_payload()` omits `channel`, causing `invalid_channel` even in `warn` mode

- **Observed behavior:** Calling `Agent(..., runtime=APIRuntime.from_config_path(...)).run(...)` with a minimal `agents.json` raises `RuntimeError: inbound authenticity denied (reason=invalid_channel, mode=warn)`.
- **Root cause in `openminion==0.1.23`:** `Agent._build_payload()` constructs `{"message", "session_id", "deliver", "inbound_metadata"}` without a `"channel"` key. In `openminion/services/runtime/ingress/requests.py`, `channel` falls back to `agent_profile.default_channel`, which defaults to `""`. In `openminion/modules/controlplane/channels/authenticity.py`, `evaluate_inbound_authenticity()` rejects an empty `channel` with `allowed=False, reason_code="invalid_channel"` before checking whether `mode == "warn"`.
- **Workaround used:** Set `"default_channel": "console"` inside `agents.<id>` in `agents.json`.
- **Suggested SDK improvement:** Default `"channel"` to `"console"` (or `agent_profile.default_channel or "console"`) in `Agent._build_payload()` for local Python API calls, or allow empty internal API channels when `mode="warn"`.

## 2. `Handoff` tools default to `WRITE_SAFE` and require confirmation

- **Observed behavior:** Calling `Agent(handoffs=[Handoff(...)]).run(...)` without an `approval_callback` returns a text prompt (`Policy confirmation required for transfer_to_triage_planner...`) instead of invoking the handoff target.
- **Root cause in `openminion==0.1.23`:** `build_delegate_family_spec()` in `openminion/api/handoff.py` sets `min_scope_default="WRITE_SAFE"`, and `ActionPolicyConfig.default_action` defaults to `"require_confirm"`.
- **Workaround used:** Pass an `approval_callback` that explicitly allows read-only handoff names (`tool_name == "transfer_to_triage_planner"`).
- **Suggested SDK improvement:** Allow configuring `min_scope` or `read_only=True` directly on `Handoff(...)` when delegating to a read-only subagent.

## 3. `OpenMinionConfig.to_dict()` vs `from_dict()` key asymmetry for `default_agent`

- **Observed behavior:** `OpenMinionConfig.from_dict()` reads top-level `"default_agent"`, whereas `to_dict()` emits `"system"` and `"agents"` without mirroring `system.default_agent` back on load.
- **Workaround used:** Place `"default_agent": "release_gate"` at the top level of the generated `agents.json`.

## 4. `save_bundle` argument order differs from `Path.write_text`

- **Observed behavior:** In `openminion/modules/memory/portability`, `save_bundle(bundle, path)` takes `bundle` first and `path` second, and `import_bundle(bundle)` returns summary metadata (`item_count`, `bundle_version`, `trust_mode`) rather than the `items` list itself.
- **Workaround used:** Validate trust with `import_bundle(bundle, trust_mode="direct")` and read items from `bundle.items`.

## 5. Multi-step `submit_output` overhead per `Agent.run()` turn

- **Observed behavior:** A single tool-using turn triggers extra LLM round-trips for internal `submit_output` calls (`FinalizationStatus` and `ClosureJudgment`) after the assistant reply (`session_continuity_turns` averaged `4.4s` per turn even on local loopback).
- **Impact for Cortensor inference:** On decentralized routers or rate-limited Portal endpoints, those extra structured calls multiply latency and token consumption by 2x to 3x per turn.
- **Suggested SDK improvement:** Provide a lightweight `Agent(..., verification_mode="minimal")` option for deterministic or single-shot tool pipelines.

## 6. `CortensorProvider._complete_via_openai_chat_mode()` omits `http_client`

- **Observed behavior:** In `openminion/modules/llm/providers/cortensor/adapter.py`, `_complete_via_completion_mode()` passes `http_client=http_client_for_config(self._http_client, config)` to `_post_with_retries()`, whereas `_complete_via_openai_chat_mode()` omits `http_client`.
- **Suggested SDK improvement:** Pass `http_client=http_client_for_config(self._http_client, config)` consistently in both modes so connection pooling settings apply to Cortensor Portal (`/v1/chat/completions`) as well as direct Router V2 (`/api/v2/completions`).

## 7. `subagent()` helper does not accept or forward `forced_tools`

- **Observed behavior:** `Agent(...)` accepts `forced_tools=[...]`, but calling `subagent(parent, ..., forced_tools=[...])` raises `TypeError: subagent() got an unexpected keyword argument 'forced_tools'`.
- **Suggested SDK improvement:** Forward `forced_tools: Sequence[str] = ()` in `openminion/api/handoff.py` (`subagent()`) to the child `Agent(...)` constructor so single-purpose audit subagents can deterministically require tool invocation.

## 8. `APIRuntime.tool_schema_report()` requires keyword-only `tool_name` and omits agent-local `@tool` functions

- **Observed behavior:** Calling `runtime.tool_schema_report()` without arguments raises `TypeError: APIRuntime.tool_schema_report() missing 1 required keyword-only argument: 'tool_name'`. Passing `tool_name="scan_docs_tool"` (an agent-local `@tool` passed to `Agent(tools=[...])`) returns `None`.
- **Suggested SDK improvement:** Index agent-registered `@tool` schemas in the runtime schema registry alongside built-in registrar tools, or allow `tool_schema_report(tool_name: str | None = None)` to summarize all registered schemas.

## 9. `subagent(..., memory_posture="read_only_bounded")` raises a v1 boundary error when called directly

- **Observed behavior:** Passing `memory_posture="read_only_bounded"` to `subagent(...)` raises `ValueError: developer subagent memory grants are not bound in v1` in `openminion/api/handoff.py` unless a `DelegatedMemoryReadRequest` object is materialized internally.
- **Workaround used:** Keep `memory_posture="none"` on child subagents and pass prior blockers across runs via `MemoryBundle` snapshots.
