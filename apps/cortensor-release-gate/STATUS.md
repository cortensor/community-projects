# Project Status

- **Project:** `cortensor-release-gate` (`v0.1.0`)
- **Owner:** `@dev-shiki`
- **OpenMinion SDK:** `0.1.23` (`MIT` License)
- **Status:** Active, verified (`9/9` pytest, `10/10` OpenMinion building-block probes, `0` ruff/mypy errors)

## Implemented

- Isolated OpenMinion `APIRuntime` configuration for `cortensor` (Portal `/v1/chat/completions` and Router `/api/v2/completions`), `openai`, and built-in local loopback (`--demo-local`).
- Read-only security, Cortensor `community-projects` manifest/docs, and OpenMinion wiring scanners wrapped as scoped `@tool` functions.
- Dual `subagent()` worker passes, `Handoff` triage planning, `approval_callback` report export gating, and `MemoryBundle` cross-run blocker diffing.
- 10-check `probe` matrix exercising `openminion==0.1.23` primitives with measured latencies saved in `artifacts/probe_matrix.json`.
- Committed sample audit artifacts (`artifacts/RELEASE_GATE_REPORT.md`, `artifacts/release-gate-summary.json`) and standalone visual report viewer (`index.html`).
- Verified live Cortensor Portal (`https://api.cortensor.app/v1`, `gemma4`) execution (`artifacts/live_cortensor_portal_run.json`, `run_id=c9eca6b0b22a458481e0d27b66fdc857`, `161,451.52 ms`) and captured tool-loop `HTTP 502` diagnostics (`artifacts/live_cortensor_tool_run.json`).
- Recorded walkthrough demo: https://youtu.be/Gxa6wyOMosc

## Next Steps

- Optional live run against a local Cortensor Router V2 node (`/api/v2/completions`) when running full node infrastructure.
