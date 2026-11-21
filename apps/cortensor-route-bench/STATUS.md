# Project Status — `cortensor-route-bench`

- **Version:** `v0.1.0`
- **Status:** `active`
- **Maintainer:** `@ixroo`
- **OpenMinion SDK Target:** `openminion==0.1.23`

## Completed
- Preflight inspector across `gemini`, `cortensor-portal`, `cortensor-router`, `openrouter`, `groq`, and `ollama`.
- 10 live OpenMinion 0.1.23 SDK building-block probes with bounded backoff and telemetry export.
- Multi-agent PoI-style route consistency verifier using `subagent()`, `DelegatedMemoryReadRequest`, `Handoff`, `@tool(min_scope="READ_ONLY")`, and Pydantic contracts.
- Interactive static viewer (`index.html`) + deterministic `pytest` suite.

## Known Limitations
- Cortensor Portal (`https://api.cortensor.app/v1`) requires a manually granted team API key (`CORTENSOR_API_KEY`); compatibility routes expose text-in/text-out only without native tool calling.
- Live runs on free-tier endpoints may experience `HTTP 429` throttling if `--pace-seconds` is set below `1.5`.
