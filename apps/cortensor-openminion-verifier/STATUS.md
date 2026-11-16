# PROJECT STATUS

**Project:** `cortensor-openminion-verifier` (`v0.1.2`)
**Date:** 2026-11-15
**Maintainer:** `@huadeng408`

## Current Status

- **Active & Ready for Upstream Submission**: Re-licensed under the standard `MIT License` with `openminion==0.1.21` pinned deterministically in `pyproject.toml`.
- **Multi-Pass Consensus Auditor**: Dual-perspective `subagent()` passes (`corroborator` and `skeptic`) run in isolated `APIRuntime` workspaces using `READ_ONLY` `Scoped Evidence Toolset` bindings (`load_delphi_market_fixture`, `search_public_evidence`, `fetch_source_excerpt`, and SSRF-guarded `fetch_public_url_excerpt`), synthesizing typed `ConsensusVerdict` bundles with portable `MemoryBundle` persistence and fail-closed `Handoff` publication gating.
- **10-Module SDK Probe Suite**: `BuildingBlockProbeRunner` exercises all 10 core `openminion==0.1.21` primitives and exports sanitized empirical reports (`docs/BUILDING_BLOCKS_TESTED.md`, `docs/WHAT_WE_LEARNED.md`) with zero plaintext credential persistence.
- **Verification Coverage**: All loopback integration suites execute against real `openminion==0.1.21` runtime primitives over deterministic local HTTP stubs.

## Known Issues

- **Upstream `openminion==0.1.21` Rough Edges**:
  - `Handoff` `build_delegate_tool()` (`openminion/api/handoff.py:169`) invokes `handoff.target.run(message)` without forwarding caller `timeout_seconds` or `approval_callback`, requiring target-runtime `PolicyGrantInput(max_uses=1)` for autonomous single-use publication.
  - `APIRuntime.submit_turn()` reports zeroed token counts on `TurnTelemetry` while `TurnResponse.stats` records full prompt and completion tokens.
  - `resolve_entry_task_update()` (`openminion/modules/brain/loop/context/task_context.py:179`) raises `Missing/Duplicate task_update` if subagent passes share a session transcript, so each pass runs in an isolated subagent session ID.
- **Fake-IP DNS proxies**: behind a local proxy that answers DNS with fake-IP ranges (e.g. `198.18.0.0/15`), `fetch_public_url_excerpt` refuses public hostnames by design (observed live on 2026-11-16 for `www.sec.gov`); passes then fall back to curated catalog sources. Disable fake-IP DNS to fetch live URLs.
- **Default SSRF Policy**: `fetch_public_url_excerpt` blocks loopback, private, link-local, CGNAT, and reserved IP targets/redirects by default (`allow_private_network=False`).
