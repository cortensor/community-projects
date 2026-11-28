# Release notes

## v0.1.0 — 2026-11-28

Initial Hackathon #5 release.

- GitHub issue triage workflow on the OpenMinion 0.1.24 Python SDK:
  fetch → memory plan (skip unchanged / re-triage changed) → per-issue agent
  run with READ_ONLY `get_issue` tool + approval-gated `save_triage_record`
  write tool → `triage-report.md` + `triage-report.json`.
- Typed structured output (`TriageVerdict`, Pydantic) with explicit handling
  of `ProviderError`, `TurnTimeoutError`, `AgentOutputValidationError`.
- Recorded real runs against `Textualize/rich` with a local Ollama model
  (`qwen2.5:3b`), including the second-run memory demonstration.
- Offline unit tests for memory planning and report rendering (4 tests).
- Findings docs: `BUILDING-BLOCKS.md`, `WHAT-WE-LEARNED.md`, `FINDINGS.md`.
