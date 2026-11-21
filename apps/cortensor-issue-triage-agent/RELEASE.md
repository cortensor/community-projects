# Release Notes

## [v0.1.2] - 2026-11-21

### Added
- Eval error-class fixes: enum synonym normalisation
  (e.g. `enhancement` → `feature`) and a shape-changing retry after a
  provider HTTP 400; the 3 previously errored issues now score.
- Re-run + expansion: same-13 re-run 12/13 (0.923), expansion to
  **n=23, label-blind accuracy 0.826 (19/23), 0 errors**; eval runner
  `scripts/run_eval_set.py` with evidence in `eval/results-20261119-*.json`.
- SDK pacing mitigation: `DirectClient.wait_pacing()` before `--via-sdk`
  turns (still 0/3 native on the free tier — documented, not hidden).
- Concordium Agent Card (`docs/.well-known/agent-card.json`) and x402
  gateway (`concordium/`, testnet) — outside the Hackathon #5 scope,
  included as shipped in the repo.
- Demo video re-rendered (65.3 s, 113 tests, eval label-blind 19/23).

### Fixed
- `src/issue_triage/__init__.py` `__version__` was stale at 0.1.0
  (the 0.1.1 bump missed it); now 0.1.2 everywhere.
- README notes that said the submitted DoraHacks Build 1 description
  still reported 10/10; the Build now reports 19/23 (updated 2026-11-21).

## [v0.1.1] - 2026-11-17

### Added
- ChatGPT-audit fixes: SDK-backed draft (`--via-sdk`, draft step through
  a real OpenMinion `Agent.run` turn); label-blind evaluation (10/10 on
  the scored set, 3 issues errored and excluded — see v0.1.2 for the fix);
  linked-PR fetching (`get_pull_summary`); hardened browser preview
  (`docs/browser-preview/index.html`).
- Building-block probe suite rerun: 8 pass / 3 partial / 0 fail
  (11 probes); `docs/BUILDING_BLOCKS_TESTED.md`, `docs/WHAT_WE_LEARNED.md`.
- Demo video (65 s, real CLI run); first GitHub Release (v0.1.1).

### Fixed
- Approval-gate bug: a tokenless approve marked the snapshot "approved"
  before the GitHub token check; the token is now checked before any
  state change, and tokenless `--yes` prints the `gh api` commands and
  leaves the snapshot pending.

## [v0.1.0] - 2026-11-16

### Added
- Initial release of `cortensor-issue-triage-agent`: single-issue deep
  triage (`--issue N`) reading issue, comments and linked PRs; verdict
  (type, severity, component, labels, assignee, route, confidence,
  rationale, evidence) plus a draft first reply.
- Fail-closed approval gate: pending snapshots, single-use, tokenless
  approve prints exact `gh api` commands without changing state.
- Label-blind evaluation 10/10 on the scored set (3 issues errored and
  excluded) + label-aware baseline 0.9 on real openminion issues.
- Demo video (65 s, real CLI run).
