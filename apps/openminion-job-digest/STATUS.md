# Project Status - openminion-job-digest

**Maintainer:** @abdalla-dawoud  
**Current Version:** v0.1.0  
**Status:** Active (hackathon build)

## Current State

- Runs end to end on OpenMinion 0.1.24 with Groq free tier (qwen/qwen3.8-27b).
- Three free job sources; seen-store dedupe across runs.

## Next Steps

- Move the model pick back into an `output_type` Agent turn once small free models fit the request budget.
- Add scoring by posted date.

## Known Issues

- Free job feeds are thin on engineering roles on some days; the digest can legitimately return zero picks.
- Free-tier providers can rate limit mid-run; the script retries and can fall back to a second provider config.
