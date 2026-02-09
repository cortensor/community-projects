# Roadmap

## Completed (January 2026)
- ✅ Improved Cortensor timeout handling with exponential backoff (env-configurable timeout, 3 retries)
- ✅ Added in-memory caching layer for market data, news, and AI analysis
- ✅ Enhanced error handling with retriable error codes detection
- ✅ Added elapsed time indicator during analysis
- ✅ Added "Cached" badge to indicate fast responses from cache
- ✅ Better user feedback during long AI synthesis operations

## Short-Term
- Reduce latency on multi-provider fetches (optimize TwelveData output size)
- Reinstate summarize API with updated Cortensor workflow
- Ship quick tour/onboarding copy for first-time users

## Long-Term
- Add portfolio watchlists with scheduled refreshes and email digests
- Support options analytics and implied volatility overlays
- Provide exportable PDF/CSV market briefings for teams

## Known Issues
- Cortensor AI occasionally returns timeouts; improved retry logic now handles most cases
- Commodities relying on TwelveData can respond slowly when Stooq coverage is thin
- Summarize endpoint currently disabled pending service redesign
