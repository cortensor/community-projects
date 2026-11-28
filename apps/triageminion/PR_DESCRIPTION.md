## Summary

Adds `apps/triageminion` (`v0.1.0`, **MIT License**, pinned `openminion==0.1.24`) for **Cortensor Hackathon #5**.

- **Standalone upstream repository:** https://github.com/afif-3/triageminion (tag `v0.1.0`)
- **Demo video (1280×720, rendered from the real captured runs):** https://github.com/afif-3/triageminion/blob/main/demo.mp4

**TriageMinion** is a GitHub issue triage agent built on the OpenMinion 0.1.24 Python SDK. Pointed at a public repo, it fetches open issues, and for each new/changed issue an OpenMinion `Agent` (real model) classifies it (bug / feature / question / docs), assigns a priority with a one-line justification, suggests labels, and drafts a maintainer response — producing `triage-report.md` + `triage-report.json`. Recorded runs use a **local model (Ollama `qwen2.5:3b`)**, no API key.

- **Tools:** `@tool(min_scope="READ_ONLY", idempotent=True)` `get_issue` (full issue body) and `@tool(dangerous=True)` `save_triage_record` — the only write path.
- **Permissions:** every write passes a per-run `approval_callback` (interactive y/N or `--auto-approve`); the callback denies any other tool. Nothing is ever posted to GitHub.
- **Sessions & memory:** one SDK session per target repo; durable state keyed by issue `updated_at` — run 2 in `examples/` skips unchanged issues and re-triages a changed one.
- **Structured output & errors:** `output_type=TriageVerdict` (Pydantic); explicit `ProviderError` / `TurnTimeoutError` / `AgentOutputValidationError` handling, a corrective retry, and verdict recovery from the approval-gated tool record.
- **Diagnostics:** `openminion doctor --check-turn`, per-issue timing and tool-persistence flags in the run logs.

## Bug report + fix PR (bonus)

Building this surfaced a reproducible OpenMinion bug: **all provider calls fail when `NO_PROXY` contains bracketed IPv6 entries** (httpx `trust_env` client construction).

- Report: https://github.com/openminion/openminion/issues/893
- Fix PR (fallback + regression tests): https://github.com/openminion/openminion/pull/894

## Submission Checklist

- Public source & setup/run instructions: `apps/triageminion/README.md`
- Working example (real recorded runs, reports + logs): `apps/triageminion/examples/run1/`, `apps/triageminion/examples/run2/`
- Demo video: `apps/triageminion/demo.mp4` (and linked above)
- Building Blocks Tested: `apps/triageminion/BUILDING-BLOCKS.md`
- What We Learned: `apps/triageminion/WHAT-WE-LEARNED.md`
- Full findings log (repro steps, expected vs actual): `apps/triageminion/FINDINGS.md`
- Automated tests: 4 offline tests passing via `python tests/test_triage_logic.py`
