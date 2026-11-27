# What I Learned: Building Cortensor Task Sentinel on OpenMinion 0.1.24

I built Cortensor Task Sentinel solo on OpenMinion 0.1.24 and reran the checks I had run on 0.1.20. Most of what I found on 0.1.20 was still there. Here is what I verified.

## 1. The model can silently rewrite tool arguments

With model-chosen tool args, the model passed a rewritten exploit to tools in 5 of 10 exploit turns on 0.1.20, and again during my 0.1.24 smoke runs. My verdict logic in `_verdict_from_tools` checks submitted AST parity and rejects every rewrite fail-closed, so none were certified. Caller-bound tool args (`bound_args`) in the SDK would stop rewrites before the tool even runs.

## 2. An empty `default_channel` denies inbound messages

Leaving `default_channel` empty caused inbound authenticity denials even in warn mode. Setting `default_channel: console` fixed it. One more detail: `session_id` stays pinned to the first channel it binds to, so set the channel up front.

## 3. Bare `@tool` returns approval prompts as text

A bare `@tool` triggers an approval prompt. In non-interactive runs the prompt is not raised as an error; it comes back as `AgentRunResult.text`. The run looks fine but the tool never ran. READ_ONLY idempotent scopes fix it.

## 4. Dataclass returns fail invisibly in the stats

When a `@tool` returns a dataclass, the run dies with a JSON serialization error, and the stats report `tool_calls=0` and `tool_errors=0`. The failure does not show up in metrics. Return plain dicts.

## 5. `forced_tools` does not force a tool call

`forced_tools` did not guarantee a tool call. I measured 2 out of 20 runs on 0.1.20, and my 0.1.24 smoke test showed the same problem: 4 LLM calls, 0 tool calls. Treat it as a hint, not a contract.

## 6. The circular import is still in the PyPI package

The circular import in `openminion.modules.tool.executor` (Issue #733, open fix PR #734 rebased onto `dev` `0c99b454` at `d8162d73`) still triggers on the PyPI release `openminion==0.1.24`. The fix is in the open PR, not in the published package.

## 7. Hosted Cortensor Portal latency exposes pre-turn OpenMinion overhead

Testing live against `https://api.cortensor.app/v1` on `openminion==0.1.24` showed that default OpenMinion turns on `gemma4` spent `226.7 s` in `brain.auto_fact_extraction`, `91.9 s` in `entry`, and `95.4 s` in `freshness_classify` (`414.0 s` before any Sentinel tool ran), hitting the `600 s` timeout with a `ProgrammingError` warning in `brain.tool_transcript` recovery. Setting `runtime.memory_enabled: false`, `brain.auto_fact_extraction.enabled: false`, `brain.reflection.enabled: false`, and `900 s` turn timeouts dropped pre-turn extraction to `0.39 s` while leaving agent `thinking` at default (because `thinking: "off"` caused `gemma4` to drop `task_update` and fail `invalid_task_context_update`). Because OpenMinion also disables Portal HTTP retries (`cortensor_portal_no_idempotency`), `sentinel.py` wraps Portal tasks in bounded retries. With that configuration, live Portal `oss-20b` completed both tasks on the first attempt (`task-fibonacci-10` certified in 6 LLM calls / `722.6 s`; `task-exploit-attempt` rejected in 5 LLM calls / `651.6 s`).

## 8. What I would ask for

- Caller-bound arguments (`bound_args`) so the model cannot rewrite tool inputs.
- Explicit errors in non-interactive runs instead of prompts returned as text.
- An optional skip flag for `auto_fact_extraction`, `freshness_classify`, `judge`, and `reflect` on simple tool turns or slow decentralized routers.
- Clean SQLite handle closing in `brain.tool_transcript` recovery when a turn is cancelled on timeout.
- A headless `openminion-core` package without the interactive pieces.

All numbers above come from my own runs on 0.1.20 and 0.1.24 (`outputs/live_model_run_receipt.json` and `outputs/cortensor_portal_run_receipt.json`).
