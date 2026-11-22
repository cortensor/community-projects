# What We Learned

Filled from real runs on 21 Nov 2026, OpenMinion 0.1.23.

- Setup: `openminion setup --provider cortensor-portal --model oss-20b --agent radar --no-chat --check-provider` is non-interactive and worked with `CORTENSOR_API_KEY`. The connection check completed in 24.9 seconds. `--list-providers` needs no network.
- Without an `agents.json`, `Agent.run` raises `ConfigManagerError: config file not found`. A friendlier hint pointing to `openminion setup` would help new builders.
- Cortensor Portal (`oss-20b`) is usable for a real tool-using run, but it is slow: this brief took 27 minutes 13 seconds for 5 completions plus a setup check (6 requests). Individual completions often took 1-3 minutes. That is too long to record unedited in a 1 to 5 minute demo video.
- Tool calls themselves were fast (GitHub reads finished in about a second). Almost all of the time was model latency.
- Structured output is fragile with this stack. `oss-20b` returned JSON, but with aliases (`version`, `summary`, `issues_prs`) instead of `title`, `why_it_matters`, and `issues_to_watch`. OpenMinion then fail-closed after a judge-phase `ProviderError`. Repairing aliases and retrying once with a stricter JSON-only prompt recovered a valid `BuilderBrief`.
- Session ids must not contain `/`, or OpenMinion memory raises `invalid scope`. Using `openminion__openminion` in the session id avoided that warning on the Portal run.
- The model skipped `radar_save_checkpoint` on this run, so a live demo of the approval-gated write still needs a run where that tool is actually called.
- `oss-20b` quality after retry was good enough to skip `gemma4` and `qwen` and keep quota free. Facts checked against GitHub: 0.1.23 notes, PR #815, and issue #642 were right; 0.1.22 was under-described, and tag URLs missed the leading `v`.

## Update, 22 Nov 2026

A later film run on Portal `oss-20b` finished in 4 minutes 10 seconds with a clean `model_generated` brief and an approved checkpoint. There was no printed `PROVIDER_ERROR` this time, but the wait was still too long to leave uncut in a 1 to 5 minute demo.

The brief itself is useful product feedback: it surfaced two real open OpenMinion issues, both still open when checked on 22 Nov 2026:

- [#446](https://github.com/openminion/openminion/issues/446): PostgreSQL `storage migrate` modules share one `alembic_version`, and runtime storage then fails on `sessions`.
- [#717](https://github.com/openminion/openminion/issues/717): provider retry ignores Retry-After on HTTP 429, so a per-minute rate limit ends the turn.

Release `v0.1.24` (published 21 Nov 2026, 14:45 UTC) was described accurately, including multimodal input and stronger provider retry behavior.

