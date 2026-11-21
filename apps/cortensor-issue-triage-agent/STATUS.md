# PROJECT STATUS

**Project:** `cortensor-issue-triage-agent` (`v0.1.2`)
**Date:** 2026-11-21
**Maintainer:** `@ValeriaWong`

## Current Status

- **Active & Submitted (cortensor/community-projects#TBD + DoraHacks #51293)**:
  Single-issue deep triage + routing with a fail-closed approval gate,
  `openminion==0.1.21` pinned in `pyproject.toml`, MIT License.
- **Real-repo evaluation**: label-blind accuracy 0.826 (19/23) with the
  maintainer labels hidden from the model; label-aware baseline 0.9.
  0 errors across all 23 issues (the 3 errors from the 2026-11-17 run
  were fixed and re-ran correctly, 12/13 on that set); 20 issues
  skipped for ambiguous ground truth.
- **SDK-backed draft**: `--via-sdk` runs the draft step through a real
  OpenMinion `Agent.run` turn (demonstrated once in isolation); classify
  stays on the paced direct client because the SDK has no `response_format`
  support and native turns cannot survive the Pollinations free-tier
  1 reply / 45 s limit (HTTP 402). CLI runs 0/3 native, fallback works.
- **Tests & probes**: 113 pytest tests pass (loopback stubs, $0);
  building-block probes 8 pass / 3 partial / 0 fail (11 probes).

## Known Issues

- SDK native `Agent.run` turns usually fail with HTTP 402 on the
  Pollinations free tier (see `docs/WHAT_WE_LEARNED.md` §15); `--via-sdk`
  is best-effort with fallback, not the default.
- Free-model structured output is unreliable (prose instead of JSON,
  invented enum values); the direct client parses both tool_calls and
  text-JSON channels and validates against the Pydantic schema.
- The browser preview (`docs/browser-preview/index.html`) is a simplified
  one-call preview, not the full two-step CLI pipeline.
