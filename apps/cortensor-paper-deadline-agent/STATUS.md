# PROJECT STATUS

**Project:** `cortensor-paper-deadline-agent` (`v0.1.0`)
**Date:** 2026-11-21
**Maintainer:** `@ValeriaWong`

## Current Status

- **Active (DoraHacks BUIDL 51456 submitted, Under Review; PR in preparation for submission to cortensor/community-projects)**:
  Paper-deadline watch + research briefs over verified CCF tables,
  `openminion==0.1.21` pinned in `pyproject.toml`, MIT License.
- **Real data, verified once**: 682 CCF venues in the master list
  (387 conferences, 295 journals, CCF 2026 7th edition); 390 conference
  deadline rows with per-date verification status. 48 conference deadlines
  fall in the 120-day window, every date carrying a verification status
  (verified / cycle-not-announced / not-found).
- **Real model brief**: a full brief ran once on the Pollinations free
  endpoint ($0, 2026-11-17 02:32 run, 900.2 s, path "model"). The demo
  video instead shows the labelled template fallback: on that run the
  free tier gave 0 turns in 42 attempts (all HTTP 402), so the brief
  fell back to the template and says so (fixture
  `fixtures/live_run_2026-11-17_brief-ai.json`, total 632.6 s).
- **Tests & probes**: 41 pytest tests pass (loopback stubs, $0);
  building-block probes 5 pass / 4 partial / 1 fail (10 probes) —
  subagents are fragile on the free tier, so the main synthesis agent
  re-queries the tools itself. The one fail is `session_continuity`
  (HTTP 402 on the free tier).
- **Demo video**: 70 s (69.97 s), real demo run. GitHub Release asset
  published as v0.1.0 on the standalone repo (2026-11-21):
  https://github.com/ValeriaWong/cortensor-paper-deadline-agent/releases/download/v0.1.0/paper-deadline-demo.mp4

## Known Issues

- Subagent delegation rarely completes a live turn on the Pollinations
  free tier (HTTP 402); the synthesis agent compensates by re-querying.
- Dates marked cycle-not-announced or not-found are shown as such;
  the agent never invents a deadline.
- The brief step is slow on the free tier (45 s pacing between replies).
