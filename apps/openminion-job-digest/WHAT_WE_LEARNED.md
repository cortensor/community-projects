# What We Learned - OpenMinion 0.1 building-block notes

Concrete findings from building this digest agent against `openminion` 0.1.24
with free-tier hosted models (Groq: qwen3.8-27b, gpt-oss-20b, gpt-oss-120b;
8k tokens/min per model).

## What worked well

- `openminion setup --no-chat --provider groq --model <id>` is a smooth
  non-interactive path; config lands in a predictable `agents.json`.
- The `Agent` + `@tool` + `forced_tools` pattern (as in
  `examples/sdk/tool_agent.py`) is reliable even with small free models: the
  forced first call makes the tool invocation verifiable, which is exactly
  what a reproducible demo needs.
- `ProviderError` exposes a stable `code` (e.g. `RATE_LIMITED`), which made
  backoff logic straightforward.
- Pydantic `output_type` validation is strict in a good way: markdown-fenced
  or prose replies raise `AgentOutputValidationError` with the raw text
  attached, so bad output is never silently accepted.

## What broke or surprised us

1. **Model-choice tool routing fails with small free models.** When tools
   are offered and the model chooses the calls, the brain loop expects a
   well-formed internal `task_update`; weak models emit a malformed one, and
   the run ends in a canned clarify response ("I could not safely update the
   task conditions...") instead of executing tools. This reproduced on
   qwen3.8-27b and gpt-oss-120b. Forcing the first tool call avoids the path
   entirely. Suggestion: document the minimum model tier for model-choice
   tool routing, or fall back to forced execution when the task_update parse
   fails.
2. **Write-scope tools gate on an interactive confirmation.** A `@tool` with
   `min_scope="WRITE"` triggers a "Policy confirmation required - reply
   yes/allow_once" exchange that a headless script cannot answer, and the
   turn's final text then fails `output_type` validation. A programmatic
   pre-authorization option on `Agent` (e.g. `allow_scopes=["WRITE"]`) would
   make write tools usable from the SDK without a human in the loop.
3. **A killed process leaves a session turn-lease behind.** After SIGKILL,
   re-entering the same `session_id` raised
   `RuntimeSessionTurnBusyError` ("session already has an active turn") for
   ~15-30s. Retry guidance in the error message helped; a lease TTL note in
   the SDK docs would too.
4. **Free-tier token budgets collide with the brain's context size.** On an
   8k input-tokens/min plan, back-to-back `Agent.run` calls in the same
   process can each 413 ("Request too large ... tokens per minute"); spacing
   runs ~70s apart and keeping sessions short fixed most of it. The
   `output_type` structured-output path was the first to cross the budget on
   reasoning models, so the demo keeps a plain-JSON fallback. Suggestion: a
   documented rough size of the default system/context envelope would help
   capacity planning on small quotas.

## Free-tier provider notes (added 2026-11-27)

- OpenRouter free models: 50 requests/day per account. After that every call returns 429 (`free-models-per-day`). Plan for a fallback provider.
- Reasoning models (nemotron-3.5-lightning) spend the default completion budget on thinking and can return empty content. Passing `max_tokens=4096` fixed it; 8192 errored.
- Groq free tier caps each request budget (about 8k tokens per minute). The full brain-loop prompt gets HTTP 413, so the digest uses the runtime LLM client for generation and the Agent only for the verifiable forced tool call.
- Provider fallback chain in `job_digest.py`: primary config first, then `--fallback-config` (Groq qwen/qwen3.8-27b). Check `GET /openai/v1/models` for live model ids; a stale id gives 404.
- Free job feeds are thin (Remotive about 16 listings, mostly non-engineering). Added the Hacker News "Who is hiring" thread via the Algolia API as a third source, which gave real engineering leads.

## Actionable product feedback

1. Document the minimum model tier for model-choice tool routing, or fall back to forced execution when the task_update parse fails.
2. Add a programmatic way to pre-authorize WRITE-scope tools from the SDK (for example allow_scopes on Agent).
3. Note the session turn-lease TTL after a killed process in the SDK docs.
4. Document the rough size of the default prompt envelope for small token quotas.
5. Give reasoning models an SDK-level completion cap or reasoning-effort option so default budgets are not consumed by thinking (empty content with default budget; 8192 errored on one OpenRouter model, 4096 worked).
