# Phase 3.3 — Deterministic Agreement (Finalized)

## Purpose

Phase 3.3 deterministically aggregates authenticated inference claims from Cortensor into a replay-safe, auditable decision envelope, enabling conditional release while preserving fail-closed governance.

## Explicit Non-Goals

* Phase 3.3 does **not** evaluate correctness or truth.
* Phase 3.3 does **not** weight models or miners.
* Phase 3.3 does **not** learn from outcomes.
* Phase 3.3 does **not** execute actions.

Its sole responsibility is **deterministic agreement over authenticated claims**.

## Guarantees

* Same claims → same decision (deterministic replay hash)
* No inference bypass (only authenticated claims accepted)
* Conflict escalates, never releases unless policy satisfied
* Auditable envelope produced for each decision

## Files

- `src/phases/phase3_3/state.ts` — agreement state
- `src/phases/phase3_3/replay.ts` — deterministic replay hashing
- `src/phases/phase3_3/envelope.ts` — DecisionEnvelope type
- `src/phases/phase3_3/finalize.ts` — finalizer that emits sealed envelope
- `src/phases/phase3_3/guard.ts` — safety guard
- `src/phases/phase3_3/decision.ts` — deterministic decision maker
- `src/phases/phase3_3/index.ts` — sealed entry point

