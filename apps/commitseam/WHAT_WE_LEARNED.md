# What We Learned Building on OpenMinion `0.1.24`

CommitSeam started from a single question for Cortensor Hackathon #5: **what happens when an OpenMinion tool commits a local side effect, and the turn fails before returning?**

Testing pinned **`openminion==0.1.24`** end-to-end against both a deterministic loopback transport and a live Groq model (`openai/gpt-oss-20b`) surfaced seven actionable lessons for OpenMinion SDK maintainers and agent builders.

## 1. The Post-Commit Atomicity Gap Is Real — And Hit Us Organically in Live Runs

- **What we verified in SDK source**: OpenMinion's gateway request deduplication (`services/gateway/service.py:428-501`) and in-memory `RuntimeEngine` tool cache (`services/runtime/engine.py:250-268`) record completion only **after** the tool returns and the turn finishes.
- **What happened live without fault injection**: During our live Groq run ([`docs/live-sdk-receipts.json`](./docs/live-sdk-receipts.json)), `enqueue_rerun` received approval (`fc_0bc35612-169e-49fe-a3eb-21dd16a421d3`), committed `job-d8f135b36452` to SQLite, and returned — and then OpenMinion's post-tool LLM synthesis call hit a real `ProviderError: RATE_LIMITED` (`8K` TPM on Groq free tier) before `Agent.run(...)` could return!
- **Builder takeaway**: Never rely on in-memory SDK turn caches or agent prose replies as the source of truth for side effects. Persist an expected worklist before turn 1, key every write by `(request_id, item_id)` with `UNIQUE` + `payload_digest` in SQLite WAL, and return `action="reused"` + original `job_id` on matching replay.
- **SDK suggestion**: Support an optional caller-provided idempotency key / durable tool-journal hook that persists tool-call start/commit markers before the post-tool LLM synthesis step.

## 2. Validate `@tool(min_scope=...)` Eagerly at Decoration Time

- **Observed behavior**: `openminion==0.1.24` only recognizes `{"READ_ONLY", "WRITE_SAFE", "POWER_USER", "UI_AUTOMATION"}` (`modules/tool/registry_toolspec.py:462`). Writing `@tool(min_scope="WRITE")` silently succeeds at import time and explodes late during turn execution with `KeyError('WRITE')`.
- **SDK suggestion**: Validate `min_scope` inside `@tool(...)` (using a `Literal` or `Enum`) so typos fail immediately at import time with a clear list of valid scopes.

## 3. Approval Denial Should Not Crash `Agent(..., output_type=BaseModel)`

- **Observed behavior**: When `ActionPolicyConfig(mode="confirm")` is active and `Agent.run(approval_callback=decide)` returns `False`, OpenMinion correctly blocks the tool (`0` tool calls) and returns plain prose `'coord: Confirmation denied. The action was not run.'`. If the agent also declared `output_type=MyModel`, `Agent._coerce_output` tries to parse that prose as JSON and raises `AgentOutputValidationError`.
- **SDK suggestion**: Represent policy/approval denial as a first-class status on `AgentRunResult` (e.g. `run_state="denied"`, `output=None`) rather than routing a human-readable refusal string into Pydantic JSON coercion.

## 4. `output_type=BaseModel` Should Inject Its Schema Into the Request

- **Observed behavior**: `Agent._build_payload` (`api/agent.py:158-194`) never passes `self.output_type` (or its JSON schema) to the provider or system prompt, and runtime replies are prefixed with `f"{agent_id}: "`. On tool-calling turns, live models frequently respond in natural language unless the JSON contract is explicitly engineered into instructions (and putting raw `{...}` braces inside user messages can trigger `task_entry.py:154` `invalid_task_context_update`).
- **SDK suggestion**: When `output_type` is a Pydantic `BaseModel`, pass structured output / JSON schema constraints to providers that support it (or append a concise schema block automatically) and strip the `f"{agent_id}: "` display prefix before `_coerce_output`.

## 5. `Handoff` Needs Explicit Approval Propagation or a Loud Capability Guard

- **Observed behavior**: `Handoff` (`api/handoff.py:162`) invokes `target.run(message)` without forwarding the parent turn's `approval_callback` (matching upstream `#774`/`#776`).
- **Builder takeaway**: Keep `Handoff` peers strictly `READ_ONLY` (`min_scope="READ_ONLY"`) and keep all `WRITE_SAFE` / `dangerous=True` tools on the top-level coordinator `Agent` where `approval_callback` is enforced.

## 6. Headless Ergonomics: `default_channel`, Built-In Tool Bootstrap, and `GroqProviderConfig` Defaults

- **`AgentProfileConfig.default_channel`**: Defaults to `""`, failing headless `APIRuntime.from_config` turns with `inbound authenticity denied (reason=invalid_channel)` until `default_channel="console"` is set explicitly.
- **Built-in tool bootstrap overhead**: `APIRuntime.from_config` auto-registers 40+ built-in tool families (`File`, `Code`, `Browser`, `K8s`, `IaC`, `GWS`, etc.) even for a minimal 2-tool agent, inflating bootstrap logs and token budgets (`~2.4K–7.7K` tokens/turn). An opt-in `builtin_tools=False` flag on `OpenMinionConfig` would make headless SDK agents dramatically faster and cheaper.
- **`GroqProviderConfig.model` default**: Defaults to `llama-3.3-70b-versatile` (HTTP 404 on Groq) and `tool_call_strategy="hybrid"` (which allowed `openai/gpt-oss-20b` to exit with `tool_calls=0` despite `forced_tools`). Switching to `tool_call_strategy="native"` and an active model (`openai/gpt-oss-20b`) made tool calling and `approval_callback` reliable.

## 7. Keep Recovery Storage Isolated and Always Close `APIRuntime`

- **`APIRuntime.close()`**: `with Agent(runtime=...)` does not close a caller-owned `APIRuntime` (`api/agent.py:425`); always close in `finally`.
- **Fresh `session_id` per retry**: Opening a fresh SDK `session_id` (`-s1` → `-s2`) under the same business `request_id` avoids `SESSION_TURN_BUSY` lease contention while preserving prior sessions read-only in `openminion.sqlite` for `commitseam diagnose`.
- **Harness-injected vs SDK behavior**: In CommitSeam's receipts, `INJECTED_PRE_COMMIT` and `INJECTED_POST_COMMIT` are explicitly labeled harness seams; `RATE_LIMITED` (`ProviderError`), `Confirmation denied`, `default_channel="console"`, `min_scope="WRITE_SAFE"`, `Handoff` approval isolation, and `context_traces` (`0` `context.manifest.created` events out of `52` recorded session events under default config) are genuine `openminion==0.1.24` behaviors.
