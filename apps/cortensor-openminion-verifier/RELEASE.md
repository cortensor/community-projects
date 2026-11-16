# Release Notes

## [v0.1.2] - 2026-11-15

### Changed
- Re-licensed the repository from `Apache-2.0` to `MIT` (`LICENSE`, `pyproject.toml`) to align with `cortensor/community-projects/apps/*` requirements.
- Bumped package version to `0.1.2` and strictly pinned `"openminion==0.1.21"` in `pyproject.toml`.

### Added
- Added `cortensor/community-projects` metadata files: `PROJECTS.yml`, `STATUS.md`, and `RELEASE.md`.
- Added `Scoped Evidence Toolset` (`build_scoped_verifier_tools`) supporting CLI `--fixtures` catalogs, inline `dossier.metadata["evidence_sources"]` evidence records, and SSRF-guarded `fetch_public_url_excerpt`.
- Recorded `calibration_status`, `calibrated_model`, and `endpoint_host` inside `AuditRunBundle.metadata` across `audit_claim()` and `resume_publication()`.

## [v0.1.1] - 2026-11-14

### Fixed
- Fixed `build_empirical_dx_findings()` telemetry key lookups so exported `docs/WHAT_WE_LEARNED.md` and `fixtures/calibrated_sample_run.json` reflect measured probe metadata without fallback sentinel leakage.
- Injected concise prior-turn `MemoryBundle` and session message snippets into cross-turn `session_id` prompts while keeping `corroborator` and `skeptic` blind within the same turn, and cleared stale `pass_session_ids` on `import_session_memory()`.

### Changed
- Upgraded `demo_renderer.py` with wrapped captions and intra-scene `Live Terminal Storyboard` progression, and regenerated calibrated submission artifacts.

## [v0.1.0] - 2026-11-14

### Added
- Initial release of `cortensor-openminion-verifier` featuring isolated `APIRuntime` factory (`openai-compatible`, `cortensor-portal`, `cortensor-router`), single-pass and dual-pass `ConsensusAuditor`, portable `MemoryBundle` sessions, approval-gated `Handoff` publication, 10-probe `BuildingBlockProbeRunner`, and 1080p MP4 demo renderer.
