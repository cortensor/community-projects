# Recorded runs (real, unedited)

Model path for all runs: OpenMinion 0.1.24 + Ollama `qwen2.5:3b` on a
shared-CPU VM (~1.5 vCPU). One issue turn takes ~15–28 minutes wall-clock at
that speed; the logs are complete, not trimmed.

## run1/ — first run, `--limit 3` against Textualize/rich

- `run1.log` — full console log: 3 issues fetched, all triaged, exit 0.
- `triage-report.md` / `triage-report.json` — the deliverables.
- `triage-staging.jsonl` — records written by the approval-gated
  `save_triage_record` tool (cumulative across runs; run 1 wrote the first 3).
- `state-after-run1.json` — durable memory snapshot after run 1.
- Pattern to notice: for every issue the model persisted its verdict through
  the approval-gated tool, but its final free-text reply was prose instead of
  the required JSON, so `AgentOutputValidationError` fired and the verdict
  was recovered from the tool record (`[recover]` lines). See FINDINGS F8.

## run2/ — second run, same command (memory demonstration)

Before run 2, the stored `updated_at` for issue #4272 in the state file was
set to a stale sentinel (`2000-01-01T00:00:00Z`) to simulate an upstream edit
of that issue. Run 2 therefore reports `changed=1` (#4272, re-triaged) and
`skipped=2` (#4274, #4271 — no model calls made for them). With no state
edit, a repeat run reports `skipped=3` and finishes in seconds.

## Earlier evidence (in `../runs/` locally, summarized in FINDINGS.md)

- smoke-run1: the NO_PROXY bug (F1) killing the provider call.
- smoke-run3: `fallback` tool strategy — model ignored tools, JSON missing
  two fields (F7).
- run1-aborted-f8-loop: a corrective retry looping on repeated
  `save_triage_record` calls (F8) — the reason recovery now precedes retry.
