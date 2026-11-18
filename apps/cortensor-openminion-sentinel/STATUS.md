# Project Status — `cortensor-openminion-sentinel`

- **Maintainer:** `@random-solver`
- **Current Version:** `v0.1.0`
- **Status:** `active`
- **License:** `MIT`
- **OpenMinion SDK:** `openminion==0.1.23`

## Current State

- Read-only EVM proxy, EIP-1967 slot, Gnosis Safe quorum, and Timelock analyzer (`sentinel/rpc_tools.py`) implemented and tested against live Ethereum and Base public RPCs with offline deterministic fallback.
- OpenMinion `0.1.23` multi-agent engine (`sentinel/engine.py`) implemented with `APIRuntime`, `@tool(min_scope="READ_ONLY")`, dual `subagent()` auditor/skeptic verification, fail-closed `Handoff` escalation, `MemoryBundle` state export/import, and `CortensorProviderConfig` / `OpenAIProviderConfig` support.
- Automated 8-probe SDK verification harness (`sentinel/probes.py`) implemented.
- Interactive web dashboard (`index.html`) and demo walkthrough (`demo.mp4`) hosted on GitHub Pages.

## Next Steps

- Connect live Cortensor Router session endpoints (`CORTENSOR_BASE_URL`, `CORTENSOR_API_KEY`) for mainnet/testnet PoI multi-miner quorum comparisons.
- Expand protocol adapters to ERC-4626 StrategyQueue / RoleManager timelock diff tracking.

## Known Issues

- On OpenMinion `0.1.23`, `subagent(..., memory_posture="read_only_bounded")` raises `ValueError("developer subagent memory grants are not bound in v1")` unless constructed via `DelegatedMemoryReadRequest`; `sentinel` defaults to `memory_posture="none"` and passes explicit JSON snapshots via `MemoryBundle`.
- On Windows hosts, `TemporaryDirectory` cleanup may encounter SQLite WAL/file handle locks on `brain/brain.db` immediately after teardown; closing `APIRuntime` and using `ignore_cleanup_errors=True` mitigates cleanup errors safely.
