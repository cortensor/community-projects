# Real model run: Cortensor Portal oss-20b, film mode (model generated)

Date: 22 Nov 2026, 9:35:24 AM to 9:39:34 AM WAT (Africa/Lagos)
Elapsed: 250 seconds (4 minutes 10 seconds)
Command: `python -m minion_radar --repo openminion/openminion --film --out samples`
Provider: OpenMinion 0.1.23 preset `cortensor-portal`
Model: `oss-20b`
Mode: `--film` (compact live snapshot, real model, checkpoint auto approved)
Session id: `minion-radar:openminion__openminion-film2`
Origin: `model_generated`
Run state: `model_generated`
Checkpoint: `[approval] auto approved radar_save_checkpoint (--yes)`
CLI artifact: `samples/openminion__openminion_20261122_093933.md`
Timestamped log: `demo/raw-film-2026-11-22.log`

This run is labelled model generated, not snapshot fallback. The headline, the chosen release, the issues, and the actions came from `oss-20b`. Exit code 0.

## Timing (WAT)

| When | What |
| --- | --- |
| 9:35:24 AM | CLI start |
| 9:35:27 AM | Film mode note printed |
| 9:35:29 AM | Compact `radar_snapshot` against live GitHub (1 new release, 8 new issues) |
| 9:35:29 AM to 9:39:33 AM | Quiet wait while Cortensor Portal `oss-20b` ran (4 minutes 4 seconds). No PROVIDER_ERROR was printed. |
| 9:39:33 AM | Checkpoint auto approved, model generated brief printed, CLI exit 0 |

## Request count

The CLI does not print a per-request Portal count. The visible work was one compact snapshot (GitHub, not Portal) and one hosted model wait of 4 minutes 4 seconds, then a valid brief. Exact Portal request count for this run is UNVERIFIED, but it was a single film-mode turn and stayed well under the V1 Preview cap (100 requests / 2 hours, 1,000 / 7 days).

## Quality (checked against GitHub on 22 Nov 2026)

- Release `v0.1.24` is real (`published_at` 2026-11-21T14:45:26Z). The model's why-it-matters line matches the official release notes: multimodal input and stronger tool, memory, provider, and remote-execution behavior. The tag URL keeps the leading `v`.
- Issue [#446](https://github.com/openminion/openminion/issues/446) is open: PostgreSQL `storage migrate` modules share one `alembic_version`, and runtime storage then fails on `sessions`.
- Issue [#717](https://github.com/openminion/openminion/issues/717) is open: provider retry ignores Retry-After on HTTP 429, so a per-minute rate limit ends the turn.
- Actions follow from those three facts. Risk labels (LOW / MEDIUM) are present. This is a cleaner schema fill than the 21 Nov film run, which left why and risk blank.

## Builder brief (CLI output)

See `samples/openminion__openminion_20261122_093933.md`. The printed headline:

> OpenMinion 0.1.24 adds multimodal input (image/screenshot) and strengthens provider retry behavior while addressing storage migration issues
