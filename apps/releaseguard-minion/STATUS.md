# Status — ReleaseGuard Minion

- **Current Version:** `v0.2.0`
- **Status:** Active / Submission-Ready (Cortensor Hackathon #5)
- **OpenMinion Baseline:** `openminion==0.1.24` (Python `3.11+`, verified on Python `3.12.3`)
- **Standalone Repo:** https://github.com/AndreyJackKali/release-guard-minion
- **Live Interactive Showcase:** https://andreyjackkali.github.io/release-guard-minion/
- **HD Demo Video (78s, 1280×720 H.264):** https://andreyjackkali.github.io/release-guard-minion/demo.mp4
- **1-Page Judge Brief:** https://andreyjackkali.github.io/release-guard-minion/judge-brief.html

## Verification Summary

| Check | Status | Details |
|---|---|---|
| Unit & Policy Gate Tests (`tests/test_tools.py`) | PASS (5/5) | Risk-tier `@tool` metadata, manifest/CI/secret scanners, brief write & git tag validation, single-use fail-closed `ReleaseApprovalGate` |
| End-to-End OpenMinion SDK Integration (`tests/test_sdk_integration.py`) | PASS (2/2) | Full `APIRuntime` + `Agent` + `approval_callback` + SQLite session + `MemoryBundle` round-trip + `subagent` + `submit_turn` streaming + diagnostics |
| OpenMinion `0.1.24` Reproducer Suite (`tests/test_openminion_findings.py`) | PASS (4/4) | Deterministic reproducers for Findings #1–#4 |
| Upstream `openminion/openminion` Issues | OPEN (4) | `#881`, `#882`, `#883`, `#884` |
| Upstream `openminion/openminion` Fix PRs | OPEN (2) | `#885` (`36/36` tests PASS), `#886` (`29/29` tests PASS) |

## Known Upstream Constraints (`openminion==0.1.24`)

1. `ReleaseAuditReport` uses `verdict` + `rationale` (instead of `status` + `summary`) to work around `openminion#884`.
2. `ReleaseGuardMinion.run_security_subagent()` re-attaches `reviewer.agent_id = parent.agent_id` to work around `openminion#732`.
3. Hand-authored `agents.json` configs must explicitly set `"default_channel": "console"` until `openminion#864` is merged.

## Roadmap

- Add SARIF export format for direct GitHub Code Scanning / PR annotation uploads.
- Support multi-turn `thread_id` confirmation-resume once `openminion#883` is resolved upstream.
- Add optional Solidity/Foundry & Rust/Cargo release-check adapters (`slither`/`forge test`/`cargo audit` read-only detectors).
