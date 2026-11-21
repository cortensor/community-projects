# What We Learned (OpenMinion 0.1.23 & Cortensor Builder Findings)

Captured during real-model verification on **`openminion==0.1.23`** using `gemini` (`gemini-flash-lite-latest`).

## 1. Verified `openminion==0.1.23` SDK Findings

1. **Preset Model Timeout & Free-Tier Quota Variance (`openminion setup --list-providers --json`)**
   - **Observed:** The `gemini` preset lists `recommended_models: ["gemini-3.6-flash"]`, which timed out (`ReadTimeout` at 15s) on live `/v1beta/openai/chat/completions`, while `gemini-2.5-flash` exhausted free-tier quota rapidly (`HTTP 429`). `gemini-3.5-flash` and `gemini-flash-lite-latest` responded `HTTP 200`.
   - **Workaround:** Explicitly configure working low-latency model IDs and support split `--model` / `--bench-model` flags across probes and multi-agent consensus.
   - **Suggested Fix:** Validate preset defaults against active endpoints and expose `--check-provider` model-catalog probing.

2. **Hidden `reflect` / `freshness_classify` Calls Exhausting 45s `api_turn_timeout_seconds`**
   - **Observed (`telemetry.db` `chat.phase_timing`):** A single subagent turn triggered hidden `reflect` (3 internal attempts totaling 77.9s) and `freshness_classify` calls before/around `entry`, exceeding the default 45s gateway turn timeout (and a 90s subagent timeout) with `TurnTimeoutError`.
   - **Workaround:** `ensure_openminion_config()` sets `gateway.api_turn_timeout_seconds = 180` and `workflow.py` uses `timeout_seconds = 180` on isolated subagents.
   - **Suggested Fix:** Allow API `Agent` / `subagent` callers to disable internal reflection/classification steps cleanly for deterministic low-latency workflows.

3. **Mandatory `TASK_UPDATE_INSTRUCTIONS` Envelope & Session Turn-2 Rejections**
   - **Observed (`openminion/modules/brain/loop/context/task_entry.py` & `task_context.py:95`):** Every `Agent.run()` injects ~12.7k input tokens of CLI `TASK_UPDATE_INSTRUCTIONS` and rejects turns when `task_update.user_quote` is not an exact substring of the latest user input (`INVALID_TASK_CONTEXT_UPDATE`: `'I could not safely update the task conditions.'`), impacting toolless single turns and Turn-2 session recall on lightweight models.
   - **Suggested Fix:** Provide a stateless API-turn mode for programmatic `Agent` invocations that skips interactive coding-task state parsing.

4. **Unattended `Handoff` Blocked by `UNKNOWN_REVERSIBILITY` & JSON-Inside-`.yaml` Config File**
   - **Observed (`modules/policy/runtime/service.py:545` & `base/config/io.py:59`):** `Handoff` compiles `transfer_to_*` without registering a safe/reversible risk spec, blocking unattended handoffs with `Policy confirmation required (UNKNOWN_REVERSIBILITY)`. Additionally, `openminion`'s default config path `.openminion/config.yaml` is actually loaded and parsed strictly with `json.loads()`, failing on YAML syntax.
   - **Workaround:** `ensure_openminion_config()` patches `.openminion/config.yaml` via `json.loads`/`json.dumps` with exact-tool `action_policy.rules` (`mode: "auto"`) overrides for declared `transfer_to_*` tools.
   - **Suggested Fix:** Register `transfer_to_*` internal delegation tools cleanly and align the default config extension (`.json`) or support YAML natively.

5. **`Agent(output_type=PydanticModel)` Missing Schema Injection & Response Envelope Wrapping**
   - **Observed (`api/agent.py` `_build_payload` & `services/brain/post_execution/postprocess_response.py:276`):** `_build_payload` does not forward `response_format` or inject `output_type.model_json_schema()`, while `postprocess_response.py:276` wraps non-noop text with `f"{agent_name}: {response_text}"`. While `Agent._coerce_output()` strips single-line `openminion: ` prefixes on clean JSON, code fences or prose trigger `AgentOutputValidationError`.
   - **Workaround:** Use `json_schema_instruction()` plus `parse_structured_reply()` to strip `<agent_name>: ` envelopes, code fences, and extract balanced JSON safely.
   - **Suggested Fix:** Inject optional JSON schema guidance when `output_type` is provided and preserve clean raw payload output before channel display prefixing.

6. **Hardcoded `'openai'` Telemetry/Error Labels, Missing Built-In Retry, & Windows `doctor` Advice**
   - **Observed (`services/agent/service.py:700`, `telemetry.db`, & `openminion doctor`):** Transient `HTTP 429` aborts without exponential backoff and emits `(openai rate limited: HTTP 429)` even for `--provider gemini`; `chat.phase_timing` and `doctor` also report `provider='openai'` and POSIX `chmod 750` advice on Windows NTFS.
   - **Workaround:** `run_with_backoff()` adds jittered exponential backoff and `probe`/`bench` pacing.
   - **Suggested Fix:** Surface the configured preset ID consistently, add built-in transient retry policies, and tailor path permission advice on Windows (`os.name == 'nt'`).

## 2. Cortensor Route Compatibility Lessons

- **Portal Non-Tool-Calling Constraint:** Cortensor Docs v2 explicitly notes hosted compatibility routes (`api.cortensor.app/v1`) expose text-in/text-out only without native tool calling. Applications targeting both OpenAI-compatible providers and Cortensor Portal should inspect `supports_native_tool_calling` via preflight and fall back cleanly to single-turn synthesis or prompt-based tool loops.
- **Hidden Reasoning Token Budgets:** Reasoning-capable models (like `gemini-2.5-flash` and `gemini-3.5-flash`) can exhaust tight `max_tokens` or per-request HTTP timeouts (`60s` on `reflect`/`act`) during internal thinking, whereas `gemini-flash-lite-latest` delivers predictable 1.2s–4.1s step latency for multi-agent verification loops.
