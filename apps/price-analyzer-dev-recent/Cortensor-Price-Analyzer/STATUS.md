# Roadmap

## Short-Term
- Reduce latency on multi-provider fetches (optimize TwelveData output size, add caching)
- Reinstate summarize API with updated Cortensor workflow
- Ship quick tour/onboarding copy for first-time users

## Long-Term
- Add portfolio watchlists with scheduled refreshes and email digests
- Support options analytics and implied volatility overlays
- Provide exportable PDF/CSV market briefings for teams

## Known Issues
- Cortensor AI occasionally returns 408 timeouts; fallback narrative engages but response takes ~60s
- Commodities relying on TwelveData can respond slowly when Stooq coverage is thin
- Summarize endpoint currently disabled pending service redesign
