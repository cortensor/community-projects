# Building Blocks Tested — TriageMinion

SDK: `openminion==0.1.24` · Python 3.12.3 · Model path for recorded runs:
Ollama 0.40.19 + `qwen2.5:3b` (local, no API key). Raw evidence for every claim
below is in `FINDINGS.md` and the run logs under `examples/`.

| Building block | Used? | How | Worked? |
| --- | --- | --- | --- |
| Agent execution | ✅ | `Agent` context manager; one `run()` per issue, per-turn `timeout_seconds` | Yes — after timeout config was raised (F2/F3). Typed `TurnTimeoutError` surfaced cleanly instead of a hang. |
| Models / providers | ✅ | `openminion setup --provider ollama --model qwen2.5:3b` into a project-scoped config; provider swap is two CLI flags | Yes. Setup + config resolution worked exactly as documented. Provider defaults needed patching for local inference (F2, F7). |
| Tools | ✅ | `@tool(min_scope="READ_ONLY", idempotent=True)` read tool; `@tool(dangerous=True)` write tool | Mixed. With the preset's `fallback` strategy the 3B model ignored tools entirely (F7). With `tool_call_strategy: hybrid` (native definitions + fallback parser) the model calls them. Tool *effects* are verified from the staging file, never assumed. |
| Permissions | ✅ | `approval_callback(tool_name, args, approval_id) -> bool` per run; approves only `save_triage_record`, denies anything else; `ask` / `--auto-approve yes|no` modes | Yes. Every write passed through the callback and is visible as `[approval]` lines in the run logs. |
| Sessions | ✅ | One session per target repo (`triageminion-<owner>-<repo>`), continued across all issues in a run; session store persists on disk between runs | Yes. `result.session_id` is stable and the SQLite session store under `.openminion/state/brain/` shows the accumulated turns. |
| Memory | ⚠️ Partial | SDK automatic memory (memory_v2) **plus** an explicit durable state file (issue `updated_at` map) | The state-file memory works and is fully inspectable — run 2 skips unchanged issues and re-triages changed ones. SDK automatic memory extraction was **disabled** (`runtime.memory_enabled=false`) because each extraction is a full extra model request (~10 min/issue on a CPU-local model, F3). Extraction itself functioned when enabled (first smoke run) — it is a cost problem, not a correctness one. |
| Skills | ❌ | — | Not used; the workflow needs no skill packages. Noted honestly rather than forced. |
| Tasks / scheduling | ❌ | — | Not used; runs are operator-invoked. The workflow is cron-shaped (idempotent, stateful) but no SDK task/scheduling surface was exercised. |
| Delegation / subagents | ❌ | — | Not used; a single agent is the right size for this workflow. |
| Diagnostics | ✅ | `openminion doctor --check-turn`, `setup --list-providers`, `config show`; per-issue timing + typed error handling (`ProviderError`, `TurnTimeoutError`, `AgentOutputValidationError`) in code | Mostly. `doctor` gives a thorough security/config posture report. Gap: no per-turn model-request count or latency breakdown, which is exactly what a local-model builder needs (F3). |
| Structured output | ✅ | `output_type=TriageVerdict` (Pydantic: classification/priority enums, labels, justification, draft response) | Mixed. Validation correctly caught a reply missing two fields (F7) — the safety net works. But the model was only told the fields via our `instructions` text (as in the official example); whether 0.1.24 injects the schema itself (cf. #853) is not documented, and the raw error text arrives wrapped in an `openminion: {...}` envelope that hints at the closure-judge path (#720). |
| Cortensor Portal | ❌ | — | Not used: Portal needs a `CORTENSOR_API_KEY` we don't have; the hackathon page states Portal is optional and non-access is not penalized. The same project runs on Portal by changing `--provider cortensor-portal --model oss-20b` with the key set. |

## The one real bug found

**F1 — provider calls die when `NO_PROXY` contains bracketed IPv6 entries.**
Reported with a minimal repro:
https://github.com/openminion/openminion/issues/893 ·
Fix PR (fallback to a direct client + regression tests):
https://github.com/openminion/openminion/pull/894 ·
TriageMinion ships a startup workaround (`sanitize_proxy_env()`).
