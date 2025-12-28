# Phase 3.2 — Trusted Claim Ingress (Summary)

This document describes Phase 3.2 behavior and guarantees for the Inception backend.

## Invariant

**Phase 3.2 ingests authenticated, provenance-verified inference claims from Cortensor.**

- Claims are treated as *claims*, not *truth*.
- Claims do not have semantic authority and cannot trigger automatic releases.
- Fail-closed guarantees are enforced (no action without agreement).

## Files of interest

- `src/core/invariants.ts` — formal project invariants (FAIL_CLOSED etc.)
- `src/adapters/cortensor/types.ts` — canonical `TrustedInferenceClaim` type
- `src/adapters/cortensor/client.ts` — web3 SDK client (ethers-based)
- `src/adapters/cortensor/events.ts` — **the only** place claims enter the system
- `src/phases/phase3_2.guard.ts` — safety guard for Phase 3.2
- `src/phases/phase3_2.ts` — Phase 3.2 starter (wires `listenForTrustedClaims` to ingestion)
- `src/core/decisionEngine.ts` — ingests claims but cannot release (ESCALATE only)

## Environment

Minimal env variables required when using on-chain SDK:

```
CORTENSOR_RPC=https://your-rpc
CORTENSOR_PRIVATE_KEY=0x...
SESSION_V2_ADDRESS=0x...
SESSION_QUEUE_V2_ADDRESS=0x...
```

Using the HTTP router is optional; router config is no longer fatal when not set.

## Tests

- `src/phases/__tests__/phase3_2.test.ts` — guard tests
- `src/core/__tests__/decisionEngine.test.ts` — ingest behavior tests

## Notes for future (Phase 3.3)

Phase 3.3 will implement an Agreement & Aggregation Engine that negotiates truth across claims and performs authoritative actions only when agreement is reached.
