# Project Status

- **Current Version:** `v0.1.0`
- **Status:** Active (Cortensor Hackathon #5 Submission)
- **Pinned SDK:** `openminion==0.1.24` (`a52088443c67a47c8fbf660f47ec6f748b3247f3`)

## Verified Checks

- Offline unit and SDK integration tests (`pytest -q`): `11 passed in 1.06s`
- Live OpenAI-compatible inference runs (`openai/gpt-oss-120b`): fixture `#42` and live `openminion/openminion#236` both returned populated `model_notes` alongside deterministic severity and reproduction metrics
- Release checklist gate (`samples/release.json` `v1.4.0`): verified `hold` verdict on unchecked `Migration notes reviewed` item
- SQLite persistence (`.triage_demo/demo.db` across all 3 runs): `3` sessions, `12` session_events, `3` saved assistant turns

## Open Items

- Keep read-only GitHub surface; optional webhook listener deferred outside v0.1.0 scope.
- Track upstream OpenMinion releases for top-level exports of `TaskState` and `PhaseStatus`.
