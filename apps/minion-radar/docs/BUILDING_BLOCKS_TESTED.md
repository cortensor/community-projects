# Building Blocks Tested

Status: filled from a real Cortensor Portal run on 21 Nov 2026, 7:50-8:19 AM WAT (Africa/Lagos). OpenMinion 0.1.23, provider `cortensor-portal`, model `oss-20b`.

| Building block | How Minion Radar uses it | Worked? | Notes |
| --- | --- | --- | --- |
| Agent execution (`Agent.run`) | One bounded turn per brief, plus one no-tool retry if structured output fails | Yes, against Portal `oss-20b` | First pass 07:51:38-08:11:47 AM WAT; JSON retry 08:11:47-08:18:48 AM WAT. Full CLI run 27 min 13 s. Portal completions often took 1-3 minutes each. |
| Python tools (`@tool`) | 3 tools in `minion_radar/agent.py` | Partial on the real run | `radar_new_releases` and `radar_new_issues` ran and returned live GitHub data. `radar_save_checkpoint` was not called by the model, so approval and the checkpoint write were not exercised this time (they still work in the stub and `--yes` path). |
| Permissions / action policy | READ_ONLY tools run freely; checkpoint write needs approval | Not exercised on this run | See row above. Verified earlier against the local scripted stub. |
| Structured output (`output_type`) | `BuilderBrief` Pydantic model | Yes, after retry | First pass was JSON with aliased fields (`version`/`summary`, `issues_prs`). OpenMinion then fail-closed after a judge-phase `ProviderError`. The app extracts or repairs JSON, including those aliases, and retries once with a stricter prompt. The retry returned valid `BuilderBrief` JSON. |
| Sessions (`session_id`) | One session per repo | Yes | Session ids now use `__` instead of `/` (`minion-radar:openminion__openminion`). This Portal run did not raise `invalid scope`. The old slash form did, on the morning Ollama run. |
| Memory | App-level checkpoint file (not OpenMinion memory) | n/a this run | No checkpoint was written because the save tool was not called. |
| Models / Portal | `cortensor-portal` preset, `oss-20b` | Yes | `setup --check-provider` succeeded in 24.9 s. 6 Portal requests used in total (1 check + 5 completions), well under the free-plan cap. Latency is high; requests do not automatically retry, which matches the official preset note. |
| Diagnostics | `openminion setup --check-provider` | Yes | Used as the minimal completion check. `doctor --check-turn` was not run, to save quota. |

## Bugs or rough edges found

1. OpenMinion 0.1.23 memory scope: session ids that contain `/` fail with `invalid scope: 'session:minion-radar:openminion/openminion'`. Environment: this machine, 21 Nov 2026. Steps: `Agent(..., session_id="minion-radar:openminion/openminion")`. Expected: session memory works. Actual: memory context build fails. Workaround used here: replace `/` with `__`.
2. Portal + OpenMinion structured output: a judge-phase `ProviderError` caused fail-closed invalid output even when the model had already returned JSON. Environment: `cortensor-portal` / `oss-20b`, 21 Nov 2026. The first-pass JSON also used different field names than `BuilderBrief`. Workaround: extract/repair plus one stricter JSON retry in Minion Radar.
3. Portal latency: five `oss-20b` completions plus setup overhead took 27 minutes for one brief. Official docs already warn that Portal can be slow and does not automatically retry.

## Update, 22 Nov 2026

A second real Portal film run, 9:35:24 AM to 9:39:34 AM WAT (Africa/Lagos), 250 seconds, exit 0, origin `model_generated`. Command: `python -m minion_radar --repo openminion/openminion --film --out samples`. Notes: `samples/portal-oss-20b-film-2026-11-22.md`.

This run exercised the blocks that were incomplete on 21 Nov:

- `radar_snapshot` returned 1 new release and 8 new issues from live GitHub.
- The checkpoint write was offered and auto approved (`[approval] auto approved radar_save_checkpoint (--yes)`).
- The printed brief was `model_generated`, with risk labels and why-it-matters filled in, not the rule-based fallback.
- No `PROVIDER_ERROR` was printed. The hosted model wait was 4 minutes 4 seconds.
- GitHub checks the same morning confirmed release `v0.1.24` and open issues 446 and 717, which the brief named correctly.

