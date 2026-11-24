# Status — Repo Triager

**State:** working, tested, demo recorded, ready to publish.
**Category:** apps (maintainer tooling)
**Owner:** @dorithesky
**Collaborators:** —
**Repository:** https://github.com/dorithesky/cortensor-triager
**Demo:** `demo.mp4` (2:34, offline run, English narration) — shot list and rebuild steps in `docs/DEMO.md`

## What works today

| Capability | Evidence |
| --- | --- |
| Offline demo (no credential, no net) | `repo-triager --provider scripted demo` |
| Real provider path | `--provider configured`; `OPENAI_COMPATIBLE_BASE_URL` for any OpenAI-compatible endpoint |
| Read-only GitHub ingestion | `repo-triager fetch --source live`, `tests/test_github.py` |
| Severity/component/duplicate analysis | `tests/test_heuristics.py` (18 tests) |
| Prompt-to-decision pipeline on the real runtime | `tests/test_agent_integration.py` (7 tests) |
| Human approval gate (callback + pause) | integration tests; `policy` audit line in every report |
| Memory recall across runs | `memory.write` phase + `memory.search` in the analysis turn |
| Skill rubric (ingest + admit) | `repo-triager skills ingest` |
| Scheduling | `repo-triager schedule --cron '0 9 * * 1-5'` |
| Diagnostics | `repo-triager doctor` |
| Test suite | `python -m pytest` — 69 tests, ~30 s, offline |
| Demo video | `python demo/build_demo_video.py` → `demo.mp4`; `python demo/verify_demo.py` |

## Known issues

1. A triage turn costs 12 model calls (~75 K input tokens). Batches are capped at 3 by
   default and the issue snapshot is cached; a rate-limited provider cannot finish a turn.
2. Scheduled runs need the OpenMinion daemon; the CLI records the task but cannot host it.
3. Skill admission is a separate compare-and-swap step; `repo-triager skills ingest` hides
   it behind one command.
4. Six upstream SDK findings are documented in `BUILDING_BLOCKS_TESTED.md`; finding 5 (the
   operator-CLI `getpwuid` crash) has a two-line patch candidate in `findings/patches/`.

## Roadmap

- `repo-triager serve` behind the OpenMinion HTTP gateway for a shared team queue.
- Post the daily report to Slack through an OpenMinion control plane.
- Portal / Gemma4 model comparison once access is available.
- Optional GitHub write path (labels/comment) behind an explicit, separate approval — not
  planned for this submission.
