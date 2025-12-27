# Release Notes

## [v1.0.0] - 2025-12-26
- Initial release of ClaimCheck Oracle
- Next.js UI and API for decentralized fact-checking
- Streams claims through Cortensor router and aggregates miner verdicts
- Supports context via URL or explicit text, with Tavily API integration
- Displays aggregate verdict, confidence, dispersion, reasoning, and citations
- Miner cohort size configurable (default: 3, min: 1, max: 5)
- End-to-end polling, validation, and error handling
- All configuration via .env.local (no hardcoded secrets)
- UI improvements and more granular error messages
- Enhanced validation and scoring logic for miner outputs
- Performance optimizations for polling and evidence aggregation


---

### How to use
- Update this file with each new release.
- Follow semantic versioning and keep a changelog of all user-facing changes.
