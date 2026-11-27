# Building Blocks Tested (OpenMinion 0.1.24)

| Block | Used | Result |
|---|---|---|
| `Agent` (Python SDK) with `session_id` | yes | Works. Killed process leaves a turn lease for about 15-30s. |
| `@tool` with `min_scope` / `idempotent` | yes | READ_ONLY tools work. WRITE scope waits on an interactive confirmation that a headless script cannot answer. |
| `forced_tools` | yes | Reliable on every small free model tried. Used for the `load_seen_job_ids` call. |
| Model-choice tool routing | tried | Failed on qwen3.8-27b and gpt-oss-120b (malformed internal task_update, canned clarify reply). |
| `output_type` (Pydantic) | tried | Strict and useful, but its schema injection pushed requests over free-tier budgets on small models. |
| `ProviderError` + `.code` | yes | Stable `RATE_LIMITED` code made backoff simple. |
| `APIRuntime.from_config_path(...).llm.client.complete` | yes | Fits free-tier budgets. Reasoning models need `max_tokens=4096`. |
| `openminion setup --no-chat` | yes | Smooth non-interactive config. |
| Providers | Groq (qwen3.8-27b, gpt-oss-20b/120b), OpenRouter free (nemotron) | OpenRouter free tier: 50 requests/day then 429. Groq free: about 8k tokens/min per model. |
| Portal / Gemma4 | not tested | No access. |

Details: WHAT_WE_LEARNED.md.
