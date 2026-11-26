# Release History — ReleaseGuard Minion

## `v0.2.0` (2026-11-26)
- Added Cortensor Hackathon #5 community-projects package under `apps/releaseguard-minion/` (MIT-licensed for `cortensor/community-projects`).
- Added comprehensive `BUILDING_BLOCKS_TESTED.md`, `WHAT_WE_LEARNED.md`, `STATUS.md`, and `RELEASE.md` documenting 9 OpenMinion `0.1.24` SDK building blocks, Cortensor Portal/Router presets, and captured telemetry.
- Linked 4 original upstream issues on `openminion/openminion` (`#881`, `#882`, `#883`, `#884`) and 2 upstream bug-fix PRs (`#885`, `#886`).
- Published 78s `1280×720` H.264 demo walkthrough (`https://andreyjackkali.github.io/release-guard-minion/demo.mp4`), live GitHub Pages interactive showcase (`https://andreyjackkali.github.io/release-guard-minion/`), and 1-page printable judge brief (`https://andreyjackkali.github.io/release-guard-minion/judge-brief.html`).

## `v0.1.0` (2026-11-26)
- Initial release of `release-guard-minion` on `openminion==0.1.24`:
  - 5 risk-tiered `@tool`s (`inspect_repo_manifest`, `inspect_ci_and_tests`, `scan_secret_hygiene`, `write_release_brief`, `create_release_tag`).
  - Fail-closed single-use `ReleaseApprovalGate` callback with auditable `ApprovalDecisionRecord` ledger.
  - Durable SQLite session persistence, portable `MemoryBundle` export/reload, bounded `subagent` delegation, `submit_turn` typed streaming, and runtime diagnostics CLI (`release-guard audit | diagnostics | security-subagent`).
  - 11/11 automated pytest tests including 4 deterministic `openminion==0.1.24` finding reproducers and GitHub Actions CI.
