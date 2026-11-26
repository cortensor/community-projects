# CommitSeam

**Exactly-once local SQLite rerun queue across OpenMinion `0.1.24` crash seams.**

Built for **Cortensor Hackathon #5 (OpenMinion 0.1 SDK Builder Sprint)**.

## Problem

When an OpenMinion `0.1.24` agent executes a side-effecting tool (such as enqueueing failed CI tests for rerun), OpenMinion's gateway request deduplication and in-memory `RuntimeEngine` tool cache only mark completion **after** the tool returns and the turn finishes. If a `TurnTimeoutError`, `ProviderError` (such as a post-tool rate limit), or process crash strikes between a local SQLite `COMMIT` and turn return, a naive retry either **duplicates the job (`2` rows instead of `1`)** or **drops an uncommitted job (`0` rows instead of `1`)**.

## How CommitSeam Solves It

```text
JUnit XML ──▶ Deterministic Parser ──▶ expected_items (SQLite WAL, persisted before turn 1)
                                              │
               ┌──────────────────────────────┴───────────────────────────────┐
               ▼                                                              ▼
   Handoff Triage Peer (READ_ONLY)                          Coordinator Agent (WRITE_SAFE)
   - inspect_failure only                                   - Agent.run(approval_callback=decide)
   - zero write tools                                       - enqueue_rerun -> UNIQUE(request_id, item_id)
                                                            - fresh session_id per retry under same request_id
                                                                              │
                                                                              ▼
                                              ┌──────────────────────────────────────────────┐
                                              │ Seam B (pre-commit) : 0 -> 1 on retry        │
                                              │ Seam A (post-commit): 1 -> 1 same job_id     │
                                              │ Approval denied     : 0 rows + denied event  │
                                              └──────────────────────────────────────────────┘
                                                                              │
                                                                              ▼
                                       commitseam diagnose + Redacted MemoryBundle (one-way read-only)
```

- **Authoritative local SQLite WAL ledger (`queue.sqlite`)** — strictly isolated from OpenMinion's session store (`openminion.sqlite`).
- **Single-source recovery** — `pending_items = expected_items(request_id) - committed_jobs(request_id)` is computed strictly from SQLite; replays with identical `payload_digest` return `action="reused"` and the exact original `recovered_job_id`, while mutated digests return `ERR_PAYLOAD_CONFLICT` without mutating the row.
- **Explicit approval & Handoff safety** — `Handoff` triage peer has strictly `READ_ONLY` tools (since `openminion==0.1.24` `Handoff` does not forward parent `approval_callback`), while the coordinator `Agent` executes writes only through `Agent.run(approval_callback=decide)` bound to `(request_id, item_id, queue_path)`.
- **Dual-track reproducibility** — `pytest -v` runs 18 offline tests (including 500 Hypothesis property-based test cases across `P1..P5` + independent oracle calibration + real `openminion==0.1.24` over a local deterministic loopback server with `0` API calls), while `commitseam demo --yes` runs against a real LLM (`MODE: LIVE`).

## Verified `MODE: LIVE` Results (`openminion==0.1.24` + Groq `openai/gpt-oss-20b`)

Full redacted receipt: [`docs/live-sdk-receipts.json`](./docs/live-sdk-receipts.json).

| Scenario | Request ID | After Crash | Final Committed | Action / Job ID | Sessions | Exact-Once |
| --- | --- | --- | --- | --- | --- | --- |
| **1. Approval Denial** | `live-v1-deny` | `0` | `0` (`1` denied event) | `Confirmation denied` (`tool_calls=0`) | `live-v1-deny-s1` | Verified (`0` writes) |
| **2. Seam B (Pre-Commit Crash)** | `live-v1-pre` | `0` | `1` (`0 → 1`) | `created` (`job-d8f135b36452`) | `live-v1-pre-s1`, `live-v1-pre-s2` | `true` |
| **3. Seam A (Post-Commit Crash)** | `live-v1-post` | `1` | `1` (`1 → 1`) | `reused` (`job-5852d88f0621` == `recovered_job_id`) | `live-v1-post-s1`, `live-v1-post-s2` | `true` |

## 3-Minute Quickstart

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 1. Inspect CLI help (zero credentials required)
commitseam demo --help

# 2. Run the full offline test + Hypothesis PBT suite (0 external API calls)
pytest -v

# 3. Run the deterministic offline end-to-end demo & offline diagnosis
commitseam demo --yes --provider offline --run-dir .commitseam-offline --request-id demo-1
commitseam diagnose --run-dir .commitseam-offline --request-id demo-1-post --json

# 4. Run live against Groq (or any OpenAI/Cortensor-compatible endpoint via OPENAI_API_KEY + OPENAI_BASE_URL)
export GROQ_API_KEY="your-key"
commitseam demo --yes --provider groq --model openai/gpt-oss-20b --run-dir .commitseam-live --request-id live-1
commitseam diagnose --run-dir .commitseam-live --json
```

## OpenMinion `0.1.24` Engineering Findings

- [`BUILDING_BLOCKS_TESTED.md`](./BUILDING_BLOCKS_TESTED.md) — full matrix of 13 tested OpenMinion `0.1.24` components with runnable reproduction commands.
- [`WHAT_WE_LEARNED.md`](./WHAT_WE_LEARNED.md) — 7 concrete engineering lessons & actionable SDK improvement proposals (including our organic live Groq post-tool `ProviderError: RATE_LIMITED` confirmation of the commit seam).
- [`docs/live-sdk-receipts.json`](./docs/live-sdk-receipts.json) — redacted `MODE: LIVE` receipt with real approval IDs, session IDs, token/timing stats, and `context_traces` inspection.

## License

[MIT](./LICENSE)
