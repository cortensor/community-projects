# Cortensor Portal & Gemma4 Live Integration & Empirical Findings (`openminion==0.1.21`)

> **Recorded**: `2026-11-16T17:06:33Z` – `2026-11-16T17:19:31Z` (Live Cortensor Portal V1 Preview, `https://api.cortensor.app/v1`)  
> **SDK & Preset**: `openminion==0.1.21` · `--preset cortensor-portal` (`CORTENSOR_API_KEY` via isolated `.env`, zero persisted secrets)  
> **Raw Sanitized Evidence Bundle**: [`fixtures/live_cortensor_portal_gemma4.json`](../fixtures/live_cortensor_portal_gemma4.json)

---

## 1. Live Cortensor Portal Model Alias Sweep (`/v1/chat/completions`)

Tested against the hosted Cortensor Portal gateway (`https://api.cortensor.app/v1/chat/completions`) across all four documented Portal aliases (`gemma4`, `oss-20b`, `qwen`, `oss-120b`):

| Portal Alias | Hosted Model | HTTP Status | Latency (ms) | Prompt / Completion / Total Tokens | Outcome & Observed Behavior |
|---|---|---:|---:|---|---
| **`gemma4`** | Gemma 4 E4B (`e4b`) | **`200 OK`** | `21,511.61` | `28 / 44 / 72` | Exact instruction adherence (`"CORTENSOR_PORTAL_LIVE"`), `finish_reason="stop"`. Fastest successful Portal model (`21.1s`–`21.5s`). |
| **`oss-20b`** | OSS 20B (`20b`) | **`200 OK`** | `39,666.73` | `78 / 104 / 182` | Exact instruction adherence (`"CORTENSOR_PORTAL_LIVE"`), `finish_reason="stop"`. Spends ~30–70 internal tokens before emitting visible text (truncates at `max_tokens=32`, succeeds cleanly at `max_tokens>=96`). |
| **`qwen`** | Qwen 3.5 9B (`9b`) | `500` / Timeout | `42,733` – `45,769.91` | — | Intermittent `HTTP 500` (`{"code": "router_v4_internal_error", "message": "Router V4 request failed before model completion."}`) or `>45s` read timeout under current preview load. |
| **`oss-120b`** | OSS 120B (`120b`) | `502 Bad Gateway` | `2,446.01` | — | Documented on Portal as *"Supported, no capacity"*; returns `HTTP 502` (`{"code": "router_error", "message": "Router pool returned an error."}`). |

---

## 2. Live OpenMinion `0.1.21` Execution on Cortensor Portal (`gemma4` & `oss-20b`)

### 2.1 End-to-End Streaming Verification (`APIRuntime.submit_turn(stream=True)` — **PASS on Both `gemma4` & `oss-20b`**)

Using `create_isolated_runtime(preset="cortensor-portal", model=...)`, both **`gemma4`** and **`oss-20b`** completed full OpenMinion `APIRuntime.submit_turn(stream=True)` SSE streaming turns over `https://api.cortensor.app/v1`:

| Metric | `cortensor-portal` + **`gemma4`** | `cortensor-portal` + **`oss-20b`** |
|---|---|---|
| **Status** | **PASS (`ok=True`, `errors=[]`)** | **PASS (`ok=True`, `errors=[]`)** |
| **Final Text** | `"verifier: CORTENSOR_STREAM_VERIFIED"` | `"verifier: CORTENSOR_STREAM_VERIFIED"` |
| **SSE `TurnChunk`s Emitted** | `12` (`status`, `final_text`) | `12` (`status`, `final_text`) |
| **End-to-End Turn Latency** | `72,659.01 ms` (`duration_ms=72,420`) | `77,733.23 ms` (`duration_ms=77,586`) |
| **`TurnResponse.stats` Tokens** | `input_tokens=2,108` · `output_tokens=82` (`llm_calls=1`) | `input_tokens=1,870` · `output_tokens=37` (`llm_calls=1`) |
| **Portal SSE Usage Coverage** | `reported=1, missing=0` (`input`, `output`, `total`) | `reported=1, missing=0` (`input`, `output`, `total`) |
| **`TurnResponse.telemetry` Tokens** | `tokens_in=0, tokens_out=0` *(reproduces [`openminion#773`](https://github.com/openminion/openminion/issues/773))* | `tokens_in=0, tokens_out=0` *(reproduces [`openminion#773`](https://github.com/openminion/openminion/issues/773))* |

- **Positive Finding**: Setting `provider_identity={"service_vendor": "cortensor", "transport_adapter": "openai_chat", "wire_protocol_family": "openai_chat_completions"}` with `cortensor-portal` cleanly streams SSE chunks and populates `llm_usage_coverage` (`reported=1, missing=0`) into `RunStats` on both `gemma4` and `oss-20b`.
- **Live Reproduction of Upstream Bug `#773` on Cortensor Portal**: Both Portal runs recorded exact token counts in `TurnResponse.stats` (`2,108 / 82` on `gemma4`; `1,870 / 37` on `oss-20b`) while `TurnResponse.telemetry` reported `0 / 0` — fixed upstream in our accepted PR [`openminion/openminion#775`](https://github.com/openminion/openminion/pull/775).

### 2.2 Multi-Step `Agent.run()` & Tool-Schema Diagnostics (with Safe Gateway Request IDs)

When running multi-call `Agent.run()` / `ConsensusAuditor` turns (where `openminion==0.1.21`'s internal Brain executes sequential structured-schema calls for `FreshnessContract`, `TaskContext`, `@tool` dispatch, and `ClosureJudgment` / `submit_output`), we captured two reproducible Cortensor Portal V1 Preview edge cases with exact gateway request IDs:

1. **Portal Gateway Strict Tool-Argument Validator Rejects `oss-20b` Structured Tool Calls with `HTTP 502` instead of Passing Back for Repair**:
   - **Gateway Request IDs**: `gw-166b6f5a-6c9d-4458-8611-824a3d93c55e` (`62,765 ms`, `native`), `gw-70cbf7a3-5eee-4a04-820d-5a6771687f70` (`172,057 ms`, `ConsensusAuditor` single-pass with `tool_call_strategy="hybrid"`).
   - **Observed Error**: `openai request failed with HTTP 502: Model tool arguments do not match the advertised schema.`
   - **Root Cause & Actionable Fix**: Even when `tool_call_strategy="hybrid"` is set on `providers.openai`, OpenMinion's internal Brain structured-output phases (`submit_output`) send native function schemas. When `oss-20b` emits slightly non-conforming tool arguments, the Portal gateway intercepts the response and returns `HTTP 502` (which OpenMinion treats as a fatal/transport `ProviderError` after retries) rather than returning the raw assistant tool call (or an `HTTP 422` structured validation code) so OpenMinion's built-in structured-output correction loop can repair it in-turn.

2. **Router V4 Pre-Completion `HTTP 500` Compounding Across Multi-Call Brain Turns (`gemma4` & `oss-20b`)**:
   - **Gateway Request IDs**:
     - `gemma4`: `gw-8126efdb-f745-4940-9dfb-358de6eae395` (`69,366 ms`), `gw-3e2068a0-4717-40b1-aa33-847dc57e19f2` (`113,618 ms`)
     - `oss-20b`: `gw-83684e89-808d-4b58-af3f-2529ab52f732` (`178,396 ms`), `gw-cccd5a65-0601-4d8e-9cf1-999dfb73f802` (`137,635 ms`)
   - **Observed Error**: `HTTP 500: Router V4 request failed before model completion.` (`code: "router_v4_internal_error"`), plus `240.0s` `TurnTimeoutError` on `gemma4` native forced-tool dispatch (matching Portal `/stats` aggregate `75.0%` 7-day completion rate and `p95=436.8s` latency).
   - **Actionable Recommendation**: For Cortensor Portal V1 Preview workloads, single-call `APIRuntime.submit_turn()` (`allowed_tools=[]`) achieves high completion reliability (`72s`–`77s` on `gemma4` and `oss-20b`), whereas multi-step `Agent.run()` workflows benefit from adding a lightweight single-shot structured JSON mode in OpenMinion that bypasses auxiliary reflection/closure round-trips when `service_vendor == "cortensor"` and `timeout_seconds >= 480`.

3. **OpenMinion `setup_catalog.py` Model List & No-Capacity Status Codes**:
   - In `openminion==0.1.21`, `get_setup_preset("cortensor-portal")` sets `recommended_models=('oss-20b',)` (`discovery_posture='recommended_only'`), omitting **`gemma4`** and **`qwen`** even though `gemma4` is live on Portal and responded `45%` faster than `oss-20b` (`21.5s` vs `39.7s`) on direct completions and `72.7s` vs `77.7s` on `submit_turn` SSE streams.
   - Unprovisioned aliases (`oss-120b`) currently return `HTTP 502` (`code: "router_error"`), causing OpenMinion's `OpenAIProvider` to retry them as transient 5xx transport faults; returning `HTTP 503` or `HTTP 429` (`code: "model_no_capacity"`) would let SDK clients fail fast without burning router retries.

---

## 3. Reproduce Against Cortensor Portal

```powershell
# Store CORTENSOR_API_KEY in gitignored .env (never commit secrets)
$env:CORTENSOR_API_KEY = "<your_ctp_portal_key>"

# Run building-block probes or audit against Cortensor Portal + gemma4 / oss-20b
cortensor-verifier probe --preset cortensor-portal --model gemma4 --timeout-seconds 240 --probes agent_runtime_isolation memory_bundle_portability submit_turn_streaming_telemetry
cortensor-verifier audit --claim-id delphi-btc-etf-2024 --preset cortensor-portal --model oss-20b --single-pass --timeout-seconds 480
```
