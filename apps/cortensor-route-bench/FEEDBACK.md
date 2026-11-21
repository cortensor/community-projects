# Engineering Feedback — OpenMinion `0.1.23` & Cortensor Routes

Focused summary of reproducible observations collected while building `cortensor-route-bench` on `openminion==0.1.23` (see `docs/WHAT_WE_LEARNED.md` for full details and code references):

1. **Preset Timeout & Model-Tier Quota Behavior (`openminion setup --list-providers --json`)**:
   - Preset recommends `gemini-3.6-flash`, which timed out (`15s ReadTimeout`) on `/chat/completions`, while `gemini-2.5-flash` hit free-tier `HTTP 429` limits quickly. `gemini-3.5-flash` and `gemini-flash-lite-latest` returned `HTTP 200`.
2. **Hidden `reflect` / `freshness_classify` Calls Exhausting Default 45s `api_turn_timeout_seconds`**:
   - Telemetry (`chat.phase_timing`) showed one `subagent.run()` firing `reflect` (3 attempts, 77.9s) plus `freshness_classify` around `entry`, causing `TurnTimeoutError` until `gateway.api_turn_timeout_seconds` and `subagent(timeout_seconds=...)` were raised to `180s`.
3. **Mandatory `TASK_UPDATE_INSTRUCTIONS` (~12.7k tokens) & Strict `user_quote` Session Turn-2 Rejections**:
   - `task_entry.py` and `task_context.py:95` enforce `task_update.user_quote in user_input` on every turn, rejecting toolless single turns and Turn-2 session recall on lightweight models with `"I could not safely update the task conditions."` (`INVALID_TASK_CONTEXT_UPDATE`).
4. **Unattended `Handoff` Triggering `UNKNOWN_REVERSIBILITY` & JSON-Inside-`.yaml` Config File**:
   - `transfer_to_*` compiles with `Risk: write` / `Reversibility: unknown` (`modules/policy/runtime/service.py:545`), blocking headless handoffs unless exact-tool `action_policy.rules` (`mode: "auto"`) are patched into `.openminion/config.yaml` (which `base/config/io.py:59` loads strictly via `json.loads()`, not YAML).
5. **`Agent(output_type=...)` Missing Schema Auto-Injection & Envelope Wrapping**:
   - `_build_payload` in `openminion/api/agent.py` does not forward Pydantic schemas or `response_format`, while `postprocess_response.py:276` wraps non-noop replies with `f"{agent_name}: ..."` before normalization (handled via `json_schema_instruction()` + `parse_structured_reply()`).
6. **Hardcoded `'openai'` Labels, No Built-In Backoff, & Windows `doctor` Advice**:
   - `services/agent/service.py:700`, `telemetry.db` `chat.phase_timing`, and `openminion doctor --check-turn --json` report `provider='openai'` on `--provider gemini` setups, fail fast on `HTTP 429`, and emit POSIX `chmod 750` advice on Windows NTFS.
