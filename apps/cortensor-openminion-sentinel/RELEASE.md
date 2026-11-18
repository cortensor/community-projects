# Release Notes — `cortensor-openminion-sentinel`

## v0.1.0 (2026-11-19)

Initial Hackathon #5 release built for **Cortensor + OpenMinion 0.1**:

- Added `sentinel/rpc_tools.py`: read-only EVM inspector decoding deployed bytecode size, EIP-1967 implementation/admin storage slots, Gnosis Safe `getThreshold()` / `getOwners()`, and Timelock `getMinDelay()` / `delay()`.
- Added `sentinel/engine.py`: OpenMinion `0.1.23` multi-agent consensus pipeline pairing primary `sentinel` auditor `Agent` (`@tool(min_scope="READ_ONLY")`) with bounded `skeptic` `subagent()`, fail-closed `Handoff` escalation (`transfer_to_incident_desk`), `MemoryBundle` (`memory_bundle.v1`) round-trip persistence, and native `CortensorProviderConfig` support (`/api/v2/completions`).
- Added `sentinel/probes.py`: automated 8-probe SDK verification suite exercising OpenMinion runtime bootstrap, tool envelopes, channel authenticity, subagent isolation, v1 memory posture guards, handoff delegation, memory bundles, and Cortensor session transport.
- Added `sentinel/cli.py`, unit/integration tests (`tests/test_sentinel.py`), web dashboard (`index.html`), and `demo.mp4` walkthrough.
