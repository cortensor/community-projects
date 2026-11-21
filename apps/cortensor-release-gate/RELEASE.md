# Release Notes

## v0.1.0 - 2026-11-18

- Initial release of `cortensor-release-gate` for Cortensor Hackathon #5.
- Pinned `openminion==0.1.23` with isolated per-run workspace/database bootstrap.
- Added security, documentation/manifest (`PROJECTS.yml`, `README.md`, `STATUS.md`, `RELEASE.md`, `LICENSE`), and Cortensor wiring scanners.
- Added `subagent()` workers, `Handoff` triage planner, `approval_callback`-gated report exporter, `MemoryBundle` cross-run diffing, and 7 OpenMinion SDK probes.
- Added built-in `LoopbackLLMServer` supporting both `/v1/chat/completions` and `/api/v2/completions` for offline testing.
