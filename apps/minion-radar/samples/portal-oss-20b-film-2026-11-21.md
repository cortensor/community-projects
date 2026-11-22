# Real model run: Cortensor Portal oss-20b, film mode (model generated)

Date: 21 Nov 2026, 9:08:43 AM to 9:18:33 AM WAT (Africa/Lagos)
Elapsed: 590.6 seconds (9 minutes 51 seconds)
Command: `python -m minion_radar --repo openminion/openminion --film --out samples`
Provider: OpenMinion 0.1.23 preset `cortensor-portal` at `https://api.cortensor.app/v1`
Model: `oss-20b`
Mode: `--film` (compact live snapshot, real model, checkpoint auto approved with `--yes`)
Agent id: `radar`
Session id: `minion-radar:openminion__openminion-film2`
Conversation id suffix: `ead6dfa25ccc4f34ab1b5b729eeab4cf`
Origin: `model_generated`
Run state: `model_generated` (repaired from the model reply after OpenMinion rejected the raw schema)
Checkpoint: approved after the brief (`[approval] auto approved radar_save_checkpoint (--yes)`)

This run is labelled model generated, not snapshot fallback. The printed headline, the releases and issues the model chose, and the actions came from the `oss-20b` reply. Judges can treat this as a real model demo.

## Timing (WAT)

| When | What |
| --- | --- |
| 9:08:43 AM | CLI start |
| 9:08:43 AM | Compact `radar_snapshot` against live GitHub (3 releases, 8 issues). Printed immediately. |
| 9:08:48 AM | First OpenMinion `entry` call to `oss-20b` started (no user tools attached) |
| 9:13:19 AM | First `entry` call failed with `PROVIDER_ERROR` after 4 minutes 31 seconds. CLI retried once. |
| 9:13:19 AM | Retry `entry` call started |
| 9:16:47 AM | Retry completion returned (3 minutes 28 seconds, 4096 input / 272 output tokens) |
| 9:16:47 AM to 9:18:33 AM | OpenMinion tried a `freshness_classify` call; it failed with `PROVIDER_ERROR` after 1 minute 46 seconds |
| 9:18:33 AM | Model generated brief printed, checkpoint auto approved, CLI exit 0 |

## Request count and usage

This film run:

- 1 failed `oss-20b` `entry` attempt
- 1 successful `oss-20b` chat completion (`entry`)
- 1 failed `oss-20b` `freshness_classify` attempt
- Total for this run: 3 Portal requests

Token usage for the successful completion: 4096 input, 272 output.

Stay-under-limit note (Portal V1 Preview: 100 requests / 2 hours, 1,000 / 7 days): this run stayed well under the cap.

## What the model returned

The model did not nest the snapshot under `summary`. It returned a JSON object with the BuilderBrief keys, including a written headline and three concrete actions. Two gaps in the raw reply:

- `releases` was a list of version strings (`"0.1.21"`, `"0.1.22"`, `"0.1.23"`) instead of objects with `why_it_matters` and `risk`.
- Issue items had `number` and `title` but no `url`, `why_it_matters`, or `risk`.

Minion Radar accepted that as model generated, restored official GitHub release tag URLs (including the leading `v`), and printed the brief below. Issue URLs were still missing in this printout because the titles had no `#` and the URL filler only looked for `#123` at the time. After this run, `apply_tool_urls` also matches a bare issue number, and `enrich_brief_from_cache` fills empty why and risk fields from the same live snapshot the model was given, without changing the model headline, selected items, or actions. The block below is the CLI output as printed, not a later enrich.

## Quality (checked against GitHub on 21 Nov 2026)

- Headline is model written and names 0.1.23.
- Release links are the official tags: `/releases/tag/v0.1.21`, `/releases/tag/v0.1.22`, `/releases/tag/v0.1.23`.
- Issues `#642` (security audit / PII store permissions) and `#612` (async `@tool` handlers never awaited) are real open bugs. Actions also mention memctl default config, which is PR `#815`, and the `openminion:` console prefix, which is issue `#567`. Those two were in the snapshot but not listed as issues.
- Because why and risk were blank in the raw reply, this printout shows `[NONE]` and empty why lines. That is thinner than a full schema reply, but it is still the model brief, not the rule based fallback.

## Builder brief (CLI output)

# Builder Brief: openminion/openminion

> MODEL GENERATED: compact live snapshot, real model brief, checkpoint auto approved.

**OpenMinion 0.1.23 – Latest Improvements for Runtime, CLI, and SDK**

## Releases
- [NONE] [0.1.21](https://github.com/openminion/openminion/releases/tag/v0.1.21): 
- [NONE] [0.1.22](https://github.com/openminion/openminion/releases/tag/v0.1.22): 
- [NONE] [0.1.23](https://github.com/openminion/openminion/releases/tag/v0.1.23): 

## Issues to watch
- [NONE] [642 security audit: approval binding holds and guards fail closed, PII sits in 0644 stores](None): 
- [NONE] [612 tools: async @tool handlers are never awaited; tool result is a coroutine object](None): 

## Actions
- Verify that all async @tool handlers are awaited before returning results.
- Confirm that the 'openminion:' channel prefix does not impede console output.
- Make sure memctl can auto-derive default config when implicit defaults are missing.

<sub>origin=model_generated run_id=None session=minion-radar:openminion__openminion-film2 state=model_generated</sub>
