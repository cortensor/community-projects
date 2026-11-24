# Release — Repo Triager

## v0.1.0 — 2026-11-24

First public version, submitted to Cortensor Hackathon #5.

### Added

- Three-phase triage workflow on one `APIRuntime`: read-only analysis with
  `output_type=TriageDecision`, policy-gated staging, memory record.
- Five read-only tools (`triage_precheck`, `get_issue`, `search_duplicate_issues`,
  `label_taxonomy`, `list_open_issues`) and one bare-`@tool` write (`stage_triage`) that the
  OpenMinion action policy gates.
- Operator gate with four answers (`skip`, `ask`, `auto`, `deny`) plus the runtime's own
  pause/`thread_id` flow; every decision is recorded with its policy source.
- Bounded `subagent()` duplicate scout with graceful degradation.
- Deterministic heuristics for severity, component and duplicate candidates, plus a
  fallback decision when the model fails.
- Offline scripted provider (`repo_triager.scripted_provider`) and authored decisions, so
  the demo and the whole test suite run without a credential or network.
- Skills: `SKILL.md` rubric with one-command ingest + verified admission.
- Reports: Markdown + JSON with the decision, validation repairs, policy audit line and
  model call counts.
- `doctor`, `fetch`, `labels`, `triage`, `batch`, `demo`, `skills`, `schedule`, `report`.
- 69 tests (unit + integration against the real runtime).

### Findings reported

- `Agent(instructions=…)` truncation at ~860 characters (upstream #811).
- `Agent(output_type=Model)` never sends the schema (upstream #853).
- Policy denial breaks a structured-output turn.
- Session ids containing `/` silently disable memory.
- Operator CLIs crash without a passwd entry (`getpwuid`), patch candidate included.
- `memory.search` returns `[TRUNCATED]` for stored content.

### Not done

- No GitHub write path (labels/comments) — the submission is dry-run only by design.
- Portal / Gemma4 testing (no access).

### Submission package (2026-11-24)

- `docs/community-projects/` now matches the other Hackathon #5 PRs: `STATUS.md`,
  `RELEASE.md`, `PROJECTS.yml` (owner `@dorithesky`) and `LICENSE` — the previous note said
  the hub had no `PROJECTS.yml`; it has one per app, just not at the repository root.
- `demo.mp4` (2:34, 1280×720, H.264 + AAC, 5.3 MB) built by `demo/build_demo_video.py` and
  checked by `demo/verify_demo.py`: per-scene audio onsets within 40 ms, silent gaps,
  one frame per scene sampled from the finished file.
- Claims corrected against the artefacts: one patch (not two), four turns (not three),
  12 model calls per turn everywhere (one shot list still said 10), and the author field
  no longer carries an internal tool name.
