# Real model run: Cortensor Portal oss-20b, film mode

Date: 21 Nov 2026, 8:56:52 AM to 9:00:39 AM WAT (Africa/Lagos)
Elapsed: 226.9 seconds (3 minutes 47 seconds)
Command: `python -m minion_radar --repo openminion/openminion --film --out samples`
Provider: OpenMinion 0.1.23 preset `cortensor-portal` at `https://api.cortensor.app/v1`
Model: `oss-20b`
Mode: `--film` (compact live snapshot, real model, checkpoint auto approved with `--yes`)
Agent id: `radar`
Session id: `minion-radar:openminion__openminion-film`
Conversation id suffix: `553b63a7f9dc4adbafe63436e4a13372`
Run state: `snapshot_fallback`
Checkpoint: approved after the brief (`[approval] auto approved radar_save_checkpoint (--yes)`)

This is the filmed path. It is faster than the morning full agent run (27 minutes 13 seconds), but it did not land under the 3 minute target. Almost all of the time is hosted model latency, not GitHub fetches.

## Timing (WAT)

| When | What |
| --- | --- |
| 8:56:52 AM | CLI start |
| 8:56:52 AM | Compact `radar_snapshot` against live GitHub (3 releases, 8 issues). Printed immediately. |
| 8:56:57 AM | OpenMinion `entry` call to `oss-20b` started (no user tools attached) |
| 8:59:28 AM | `entry` completion returned (2 minutes 31 seconds, 4096 input / 1141 output tokens) |
| 8:59:28 AM to 9:00:39 AM | OpenMinion tried a `freshness_classify` call; it failed with `PROVIDER_ERROR` after 1 minute 11 seconds |
| 9:00:39 AM | Snapshot fallback brief printed, checkpoint auto approved, CLI exit 0 |

OpenMinion 0.1.23 has no public switch to skip the judge or freshness phase. Film config turns memory off and keeps the loop short, which cut startup to a few seconds. The remaining wait is Portal latency.

## Request count and usage

This film run:

- 1 successful `oss-20b` chat completion (`entry`)
- 1 failed `oss-20b` `freshness_classify` attempt (still counts toward Portal usage)
- Total for this run: 2 Portal requests

Token usage for the successful completion: 4096 input, 1141 output.

Stay-under-limit note (Portal V1 Preview: 100 requests / 2 hours, 1,000 / 7 days): this run stayed well under the cap. Earlier the same morning used a provider check and other `oss-20b` attempts while the film path was being shaped.

## What happened

`--film` prefetched `radar_snapshot` in Python, then started `Agent` with `tools=[]` so Cortensor Portal would not 502 on entry tool routing. The model replied, but not as `BuilderBrief` JSON. It returned a fenced object shaped like `{repo, summary: {releases, issues}}`, mostly echoing the snapshot. OpenMinion treated that as an invalid contract (`missing_or_invalid_contract`). Minion Radar then built the brief from the live snapshot (`brief_from_snapshot` / `offline_brief`), restored official GitHub release URLs, and auto approved the checkpoint write.

Release tag URLs now keep the leading `v` (`/releases/tag/v0.1.23`, `/releases/tag/v0.1.22`, `/releases/tag/v0.1.21`). That was the bug in the morning sample, which used `/releases/tag/0.1.23`.

## Quality (checked against GitHub on 21 Nov 2026)

Usable as a filmed demo: live data, correct versions, official tag links, a visible approval step, and a complete brief. Because the printed brief is the snapshot fallback, the wording is rule based rather than a model written summary.

- Releases `v0.1.23`, `v0.1.22`, and `v0.1.21` match the public repo. `v0.1.21` is marked HIGH because the notes mention security (private daemon permissions). The other two are LOW with the generic "New release; read notes before upgrading." line.
- Issues `#642` (security audit / PII store permissions) and `#612` (async `@tool` handlers never awaited) are real open bugs. PR `#815` was in the snapshot but is omitted here because the fallback only lists bugs or risk flagged items.
- Actions are generic (read high risk notes, upgrade in a branch, subscribe to the open bugs). They are still accurate next steps.

If you want richer prose on camera, the morning sample `portal-oss-20b-2026-11-21.md` has a model written brief (after a JSON retry), but that run took 27 minutes and had the old tag URL bug, and it did not show the approval step.

## Builder brief (CLI output)

# Builder Brief: openminion/openminion

> FILM MODE: compact live snapshot, real model, checkpoint auto approved.

**3 new release(s), 2 issue(s) worth watching in openminion/openminion.**

## Releases
- [LOW] [v0.1.23: 0.1.23](https://github.com/openminion/openminion/releases/tag/v0.1.23): New release; read notes before upgrading.
- [LOW] [v0.1.22: 0.1.22](https://github.com/openminion/openminion/releases/tag/v0.1.22): New release; read notes before upgrading.
- [HIGH] [v0.1.21: 0.1.21](https://github.com/openminion/openminion/releases/tag/v0.1.21): Mentions security

## Issues to watch
- [MEDIUM] [#642 security audit: approval binding holds and guards fail closed, but PII sits in 0644 stores and approval/rollback events are missing (issue, open)](https://github.com/openminion/openminion/issues/642): Bug or risky change that could affect your agent.
- [MEDIUM] [#612 tools: async @tool handlers are never awaited; the tool result is a coroutine object (issue, open)](https://github.com/openminion/openminion/issues/612): Bug or risky change that could affect your agent.

## Actions
- Read the high risk release notes and pin your current version before upgrading.
- Upgrade in a branch and rerun `openminion doctor --check-turn`.
- Subscribe to the open bug issues listed above.

<sub>run_id=None session=minion-radar:openminion__openminion-film state=snapshot_fallback</sub>
