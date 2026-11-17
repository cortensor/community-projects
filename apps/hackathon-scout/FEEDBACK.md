# OpenMinion 0.1.22: Building Blocks Tested and What We Learned

**Environment:**
- Windows 10, Python 3.12, `pip install openminion` (0.1.22).
- Providers:
  - Groq free tier (`openai/gpt-oss-20b`, 8k tokens/min).
  - Google Gemini free tier via the built-in `gemini` preset (`gemini-3.5-flash`, then `gemini-3.5-flash-lite`).
- A typical Hackathon Scout run (3 tool calls) uses **7 to 9 LLM calls, about 22k to 33k input tokens, and 10 to 30 s** on Gemini.

## Building blocks tested

| Block | Used for | Result |
|---|---|---|
| `Agent(instructions=..., tools=[...])` | Main agent loop | ✅ Works. `allowed_tools` keeps the run to our three tools. |
| `@tool(min_scope="READ_ONLY")` | `fetch_page`, `submit_brief` | ✅ Runs without confirmation, as documented. |
| `@tool` with default scope | `save_checklist` (local write) | ✅ Correctly gated. The approval callback receives `(tool_name, args, approval_id)`. |
| `approval_callback` on `Agent.run` | Human-in-the-loop file write | ✅ Works. Denying it blocks the write. |
| `@tool` with typed parameters (`list[str]`, `int`) | `submit_brief` structured output | ✅ Reliable channel for typed results. |
| `output_type=<pydantic model>` | Typed brief (first attempt) | ❌ Not usable for us. See finding 4. |
| Sessions, `AgentRunResult.run_id/session_id/stats` | Per-page runs, metrics | ✅ Populated. `stats` (llm_calls, tool_calls, tokens, duration) is very useful. |
| `openminion setup --provider groq/gemini --no-chat` | Non-interactive provider setup | ⚠️ Works, but the defaults have gone stale. See finding 3. |
| Runtime config via env (`OPENMINION_TURN_TIMEOUT_SECONDS`) | Longer turns on free tiers | ✅ Works. See finding 6 for why it was needed. |

## Findings (what broke, with suggested fixes)

1. **Windows long paths break runtime bootstrap.**
   - `openminion setup` fails `runtime.bootstrap` with `WinError 206` when the working directory is deep, because it creates `.openminion\browser-playwright\artifacts\screenshots` under the CWD.
   - *Fix:* create runtime directories under `OPENMINION_HOME`/`OPENMINION_DATA_ROOT`, use `\\?\` long-path prefixes on Windows, and make `doctor` name the cause.

2. **Some runtime state is created relative to the CWD even when `OPENMINION_HOME` is set.**
   - The browser-artifacts path above is one example.
   - *Fix:* route every runtime path through a single resolver tied to `OPENMINION_HOME`.

3. **Provider preset defaults go stale.**
   - `--provider groq` defaults to `llama-3.3-70b-versatile`, which now returns HTTP 404.
   - The `gemini` preset recommends a model whose free tier allows only **20 requests per day**. At 7 to 9 LLM calls per turn, that is two or three agent runs per day.
   - `gemini-2.5-flash` and `gemini-2.5-flash-lite` return 404 for new keys.
   - *Fix:* have `--check-provider` validate the model against `/models` and list live options. Show the free-tier request budget next to each recommended model.

4. **`output_type` is validated but never shown to the model, and the runtime wraps final replies in its own envelope.**
   - The pydantic schema never reaches the prompt, so the model invents keys.
   - Even with the keys spelled out in `instructions`, replies came back as `openminion: {"answer": "...", "freshness": ...}` or ended with `</finalization_status>`, and failed validation.
   - *Fix:* inject `model_json_schema()` into the final-answer step, or use provider-native structured output, and skip the answer envelope when `output_type` is set.
   - *Workaround:* the `submit_brief` capture tool.

5. **There is no backoff on provider 429s, even when the provider says how long to wait.**
   - Groq answers `Please try again in 26.8s`, but the turn ends at once with `RATE_LIMITED`.
   - On an 8k TPM tier, one turn (about 4k prompt tokens per call, several calls) always crosses the limit mid-loop.
   - *Fix:* bounded retry in the provider transport that honours `retry-after` and Gemini's `RetryInfo.retryDelay`, and that fails fast on daily-quota errors.
   - *Workaround:* `install_rate_limit_backoff()` wraps `httpx.Client.send`. Note that the provider transport streams responses, so the body must be `read()` before parsing.

6. **`Agent.run(timeout_seconds=...)` does not raise the runtime's 300 s brain turn budget.**
   - The turn stops at `runtime.brain_turn_timeout_seconds`.
   - The stop comes back as a *normal reply*, `Stopped: turn time limit reached (300s/300s)`, rather than raising `TurnTimeoutError`.
   - *Fix:* let the per-run timeout raise the turn budget, and raise a typed error for budget stops.

7. **Parallel tool calls trip the task-context guard.**
   - Gemini often emits several tool calls in one response, each carrying a `task_update`.
   - `resolve_entry_task_update` requires exactly one, raises `ValueError`, and the runtime replies to the user with `I could not safely update the task conditions. Please restate the current task...` instead of retrying.
   - It also fires when a second bare URL is sent in the same session.
   - *Fix:* merge or keep the first `task_update` when calls are parallel, and use the existing `build_entry_retry_message` nudge rather than a user-facing clarify.
   - *Workaround:* the instructions ask for one tool call per response, and the agent retries once in a fresh session.

8. **Prompt overhead is high for bounded agents.**
   - About 3.9k tokens go out per call with only three tools allowed, and a 3-tool task takes 7 to 9 LLM calls.
   - *Fix:* add a documented "lean" profile for single-purpose agents with fewer entry or decide round trips.

9. **There is no visibility while a turn is stuck.**
   - One Groq run consumed the full 900 s budget with no progress output.
   - *Fix:* `run_stream` or a progress callback example in the SDK docs that shows per-step tool and LLM events.

10. **Small models miss requirements buried in long pages.**
    - This is our own finding, not an SDK bug.
    - `gemini-3.5-flash-lite` repeatedly missed "Fund your agent wallet with at least 20 USDC" until `fetch_page` moved gating lines to the top.
    - *Lesson:* do cheap, deterministic extraction in tools, and keep the model for judgement.

## What we learned

- The tool and approval layer is the strongest part of the SDK. Scopes behave as documented, the approval callback drops neatly into a CLI, and typed tool parameters are the most reliable way to get structured output today.
- Free-tier providers are where builders start. Retry and backoff, a configurable turn budget, and up-to-date presets decide whether a multi-step agent finishes at all on them.
- Combine a deterministic policy with the model's judgement. The "own capital at risk means SKIP" rule in `submit_brief` makes verdicts consistent, whichever model writes them.
