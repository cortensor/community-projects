# Project Status

- **Project:** `cortensor-release-gate` (`v0.1.0`)
- **OpenMinion SDK:** `0.1.23` (`MIT` License)
- **Status:** Active, locally verified

## Implemented

- Isolated OpenMinion `APIRuntime` configuration for `cortensor` (Portal `/v1/chat/completions` and Router `/api/v2/completions`), `openai`, and built-in local loopback (`--demo-local`).
- Read-only security, Cortensor community-projects manifest/docs, and OpenMinion wiring scanners wrapped as scoped `@tool` functions.
- Dual `subagent()` worker passes, `Handoff` triage planning, `approval_callback` report export gating, and `MemoryBundle` cross-run blocker diffing.
- 7-check `probe` command exercising OpenMinion 0.1.23 primitives and capturing measured timings.
- Unit and integration test suite under `tests/` plus `ruff` and `mypy --strict` checks.

## Next Steps

- Record a 1-5 minute demo video running `probe` and `audit --demo-local --write-report`.
- Replace `@your-github-handle` in `PROJECTS.yml` with your GitHub username before opening a PR to `cortensor/community-projects`.
- Test live Cortensor Portal (`gemma4` / `gpt-oss-20b`) once Portal credentials are configured in `.env`.
