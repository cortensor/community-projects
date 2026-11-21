# What We Learned Building with OpenMinion 0.1.24

## 1. Keep Deterministic Rules Separate From Model Judgment

Running rule-based checks inside `@tool(min_scope="READ_ONLY")` first gives maintainers reproducible severity ratings, reproduction completeness scores, and release checklist blocks even offline. Passing only the compact structured fact pack to an OpenAI-compatible model endpoint cuts token overhead, lowers latency, and isolates provider failures cleanly.

## 2. Reasoning Models Need Higher Token Caps & Cleanup

When running against real OpenAI-compatible endpoints (such as `openai/gpt-oss-120b`), a tight `max_tokens=160` setting can leave reasoning models with empty final text or `<think>` wrappers. Increasing completion capacity to `512`, stripping `<think>...</think>` tags, and raising `ModelError("empty model response")` guarantees crisp two-sentence maintainer notes.

## 3. Session Event Counting Needs Filtering

`SQLiteSessionStore.create_session()` emits an initial `agent.bound` row in `session_events` alongside application events (`triage.issue.loaded`, `triage.release.loaded`, `triage.tool.completed`). Downstream monitors should filter explicit event types rather than treating `len(list_events(...))` as one-to-one with user tool calls.

## 4. Persist Both Execution Paths Symmetrically

In our initial draft, `triage_issue()` saved the final assistant turn in `SQLiteSessionStore` while `triage_release()` returned the report object directly. Adding symmetric `append_turn()` persistence to `triage_release()` ensured `turns == sessions` (`3/3`) in `.triage_demo/demo.db` for mixed issue and release runs.
