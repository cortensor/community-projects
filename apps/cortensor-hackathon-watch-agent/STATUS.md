# PROJECT STATUS

**Project:** `cortensor-hackathon-watch-agent` (`v0.1.0`)
**Date:** 2026-11-21
**Maintainer:** `@ValeriaWong`

## Current Status

- **Active (DoraHacks BUIDL 51457 submitted, Under Review; PR in preparation for submission to cortensor/community-projects)**:
  New-competition radar with preliminary suitability screening,
  `openminion==0.1.21` pinned in `pyproject.toml`, MIT License.
- **Real-run verification (2026-11-17)**: baseline 170 open entries;
  rules-only check found 33 new (DoraHacks 5 + Devfolio 28); Kaggle was
  unavailable (reCAPTCHA wall — recorded as unavailable, never faked);
  live classify took 3 calls / 1,691 tokens / $0 and alerted on AgentVerse
  (Devfolio, preliminary-suitable).
- **Tests & probes**: 46 pytest tests pass (loopback stubs, $0);
  building-block probes 5 pass / 5 partial / 0 fail (10 probes) — the
  partials are the blocks that need a live native SDK turn, all blocked by
  the Pollinations 402 rate-limit wall, recorded instead of hidden.
- **Demo video**: 74.6 s, real demo.sh run. The single live classification
  in the video returns `unsure`. GitHub Release asset published as
  v0.1.0 on the standalone repo (2026-11-21):
  https://github.com/ValeriaWong/cortensor-hackathon-watch-agent/releases/download/v0.1.0/hackathon-watch-demo.mp4

## Known Issues

- DoraHacks list pages are JS-rendered, so static fetch sees only 5
  featured links (names are slug-derived placeholders, marked as such).
- Devfolio list pages carry no deadline or prize, so those fields stay
  empty, never guessed.
- A `preliminary` verdict is a list-page-text judgement, not an official
  eligibility check — the agent says so on every alert.
- SDK native `Agent.run` turns usually fail with HTTP 402 on the
  Pollinations free tier; see `docs/WHAT_WE_LEARNED.md`.
