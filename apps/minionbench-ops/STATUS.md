# Project Status — Minionbench Ops

**Maintainer:** `@HindsightWise`  
**Current Version:** `v0.1.0`  
**Status:** Active (Cortensor Hackathon #5)  
**DoraHacks Build:** https://dorahacks.io/build/51656  
**Standalone Repo:** https://github.com/HindsightWise/minionbench-ops-openminion  
**Demo Video:** https://github.com/HindsightWise/minionbench-ops-openminion/raw/main/outputs/demo_walkthrough.mp4  

## Current State

- Executes a vertical-slice Release & Triage Guard on OpenMinion `0.1.24` (`APIRuntime`, `Agent`, `@tool`, `SQLiteSessionStore`).
- Verified live neural-model triage run calling all three `READ_ONLY` `@tool` checks plus gated write confirmation (`outputs/live_model_run_receipt.json`).
- Completes all 6 empirical building-block diagnostic probes (`6/6` pytest green, `CORRUPT_GATE_CONTROL=1` negative control verified).
- Includes Dark Studio interactive console (`web/diagnostic_console.html`).

## Known SDK Issues Recorded

- `OM-FINDING-01`: Missing `"default_channel": "console"` triggers `RuntimeError: inbound authenticity denied` (`security.py:132`).
- `OM-FINDING-02`: Display name strings in `agents.<id>.name` trigger `UnknownProfileError` (`timeout.py:54`).
- `OM-FINDING-03`: Sequential `Agent.run(...)` calls on one `session_id` fork threads unless `thread_id` is passed explicitly.
- `OM-FINDING-04`: Cortensor Portal disables retries (`max_retries=0`); Cortensor Router enforces a `455.0s` timeout floor.
- `OM-FINDING-05`: Single bounded tool turn emits 7 internal LLM calls.

## Next Steps

- Track review on the upstream `cortensor/community-projects` PR and DoraHacks Build `#51656` (`https://dorahacks.io/build/51656`).
- Run hosted Cortensor Portal (`oss-20b`) and Gemma4 latency benchmarks upon cohort credential provisioning.
