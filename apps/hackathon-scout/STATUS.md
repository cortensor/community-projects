# Project Status – Hackathon Scout

**Maintainer:** @emilpz320-a11y
**Current Version:** v0.1.0
**Status:** Active (Cortensor Hackathon #5 submission)

---

## ✅ Current State

- OpenMinion 0.1.22 agent that turns a hackathon, bounty or grant page into a typed brief (deadline, prizes, eligibility, deliverables, judging criteria, blockers, effort, GO/SKIP verdict).
- Writes a markdown submission checklist only after a human approves the `save_checklist` call (approval-gated tool).
- Ranks every page scouted in one run: GO first, then least effort.
- Flags pages that require the builder's own money (deposits, stakes, funded wallets).
- Demo run and generated checklists in `examples/`; narrated demo video in the standalone repo.

## 🔧 Next Steps

- Route inference through the Cortensor network once a router endpoint is available to community apps.
- Cache page fetches per run to cut LLM calls on free-tier models.
- Add a deadline calendar export (ICS) for GO results.

## 🐞 Known Issues

- Free Gemini tiers allow about 20 requests per model per day; long runs need a paid key or a second model.
- Pages rendered only by JavaScript return little text; the brief then reports "Unknown" fields.

## 🔗 Upstream contributions

- Reported openminion#769 (runtime bootstrap fails on Windows deep paths) and openminion#770 (`Agent.run(timeout_seconds=...)` behaviour).
- Fix for #769 merged upstream: openminion#772 (merged into `dev` as `929654a3`, all 18 hosted checks passed).
