# OpenMinion 0.1.23 Engineering Feedback - `cortensor-release-gate`

## Overview

During development of **`cortensor-release-gate` (`v0.1.0`)** for **Cortensor Hackathon #5**, we built an isolated multi-subagent release-readiness auditor (`src/cortensor_release_gate/`) and a 10-check verification suite (`cortensor-release-gate probe`) targeting **`openminion==0.1.23`** on Python `3.12.6`.

- **Test Suite (`pytest`):** `9 passed` (`test_memory_store.py`, `test_openminion_integration.py`, `test_scanners.py`)
- **Static Checks:** `ruff check .` (`0` errors), `mypy --strict src` (`0` errors across `9` source files)
- **Live Cortensor Portal (`https://api.cortensor.app/v1`, `gemma4`):** Executed real Portal runs (`artifacts/live_cortensor_portal_run.json`, `run_id=c9eca6b0b22a458481e0d27b66fdc857`, `completed` in `161,451.52 ms`) and captured tool-loop `HTTP 502` telemetry (`artifacts/live_cortensor_tool_run.json`, `gateway_request_id=gw-7a61b5cf-e7e1-44fe-ad84-45f12883c6eb`)
- **Self-Audit Verdict (`cortensor-release-gate audit . --demo-local --write-report -y`):** **`READY`** (`0` blockers, `0` warnings)

---

## Live Cortensor Portal (`gemma4`) Evidence

| Scenario | Endpoint & Model | Outcome | Latency (ms) | Reference ID |
|---|---|---|---:|---|
| Single-turn `Agent.run()` | `https://api.cortensor.app/v1` (`gemma4`) | **COMPLETED** | `161,451.52` | `run_id=c9eca6b0b22a458481e0d27b66fdc857` |
| `@tool` + `SecurityAuditReport` | `https://api.cortensor.app/v1` (`gemma4`) | **4 steps -> 502** | `367,262.14` | `gw-7a61b5cf-e7e1-44fe-ad84-45f12883c6eb` |

---

## Measured Building-Block Probe Matrix (`10/10 PASS`)

Measured directly from `cortensor-release-gate probe . --json` (`artifacts/probe_matrix.json`, total elapsed `22,586.74 ms`):

| # | Probe ID | OpenMinion 0.1.23 Building Block | Outcome | Latency (ms) |
|---:|---|---|---|---:|
| 1 | `runtime_diagnostics` | `APIRuntime.from_config_path`, `tool_inventory_report` (`104` tools), `runtime_posture` (`9` keys), `runtime_self_model` (`11` keys) | **PASS** | `33.72` |
| 2 | `agent_tool_and_output_type` | `Agent`, `@tool(min_scope="READ_ONLY")`, Pydantic `output_type` coercion | **PASS** | `4,843.67` |
| 3 | `subagent_isolation` | `subagent()` isolated child session & scoped tool list | **PASS** | `1,508.47` |
| 4 | `handoff_delegation` | `Handoff(target=...)` compilation into `transfer_to_triage_planner` | **PASS** | `2,327.09` |
| 5 | `approval_callback_gate` | `ActionPolicyConfig(default_action="require_confirm")` + `WRITE_SAFE` gating | **PASS** | `1,763.85` |
| 6 | `memory_bundle_portability` | `MemoryBundle` export, save, load, import (`trust_mode="direct"`) | **PASS** | `8.14` |
| 7 | `cortensor_completion_mode` | `CortensorProvider` against `/api/v2/completions` (`session_id=7`) | **PASS** | `1,314.17` |
| 8 | `subagent_memory_guard` | Negative contract check on `memory_posture="read_only_bounded"` | **PASS** | `0.02` |
| 9 | `forced_tools_and_capabilities` | `forced_tools=["scan_docs_tool"]`, `capability_report`, `tool_schema_report` | **PASS** | `1,908.68` |
| 10 | `session_continuity_turns` | Multi-turn SQLite session continuity (`session_id="probe-continuity-1"`) | **PASS** | `8,878.93` |

---

## Key OpenMinion 0.1.23 & Cortensor Findings

Full root-cause notes and SDK source locations are documented in [docs/WHAT_WE_LEARNED.md](./docs/WHAT_WE_LEARNED.md). Summary of actionable engineering feedback:

1. **`Agent._build_payload()` omits `"channel"` (`invalid_channel` even in `mode="warn"`):**
   - `AgentProfileConfig.default_channel` defaults to `""`. `evaluate_inbound_authenticity()` rejects empty channels before inspecting `mode == "warn"`. Recommend defaulting programmatic SDK turns to `"console"` when `"console"` is enabled.
2. **`Handoff` tools default to `min_scope_default="WRITE_SAFE"`:**
   - Even read-only delegation targets pause with `Policy confirmation required` unless explicitly permitted in `approval_callback`. Adding `read_only=True` or `min_scope="READ_ONLY"` on `Handoff(...)` would simplify read-only triage pipelines.
3. **`OpenMinionConfig.to_dict()` vs `from_dict()` key asymmetry:**
   - `from_dict()` looks up top-level `"default_agent"`, whereas `to_dict()` writes `"system"` and `"agents"` without mirroring `default_agent` cleanly across round-trips.
4. **`CortensorProvider._complete_via_openai_chat_mode()` omits `http_client`:**
   - In `openminion/modules/llm/providers/cortensor/adapter.py`, `_complete_via_completion_mode()` passes `http_client=http_client_for_config(self._http_client, config)`, while `_complete_via_openai_chat_mode()` omits it. Aligning both ensures Portal (`/v1/chat/completions`) inherits connection-pool tuning.
5. **Multi-step `submit_output` round-trip amplification on Cortensor routers:**
   - Internal `FinalizationStatus` and `ClosureJudgment` structured-output steps add 2 extra LLM calls per tool-using turn. Adding a lightweight `verification_mode="minimal"` flag on `Agent` would reduce Cortensor router latency by ~2x–3x for deterministic tool pipelines.
6. **`subagent()` does not accept or forward `forced_tools`:**
   - `Agent` supports `forced_tools=[...]`, but `subagent(parent, ..., forced_tools=[...])` raises `TypeError`. Forwarding `forced_tools` would make deterministic audit subagents much cleaner.
7. **`APIRuntime.tool_schema_report()` omits agent-local `@tool` functions:**
   - Requires keyword-only `tool_name=...` and returns `None` for custom `@tool` functions attached to `Agent(tools=[...])` (verified in Probe #9).
8. **`subagent(..., memory_posture="read_only_bounded")` raises v1 boundary error:**
   - Direct use raises `ValueError: developer subagent memory grants are not bound in v1` (verified in Probe #8); `MemoryBundle` snapshots fill the cross-run state gap reliably (`8.14 ms` round-trip).
9. **`save_bundle(bundle, path)` argument ordering & `import_bundle()` return shape:**
   - `save_bundle` takes `(bundle, path)` and `import_bundle` returns summary metadata rather than `items`, requiring callers to read `bundle.items` after validation.
10. **Live Cortensor Portal (`gemma4`) single-attempt `502 router_error` termination & multi-call amplification:**
   - A single `Agent.run()` turn executed 2 round-trips (`161.45s`), and a `@tool` + `output_type` turn compounded into 5 round-trips before `CortensorProvider` aborted after attempt 1 on `HTTP 502` (`gw-7a61b5cf-e7e1-44fe-ad84-45f12883c6eb`). Retrying transient `502 router_error` responses with backoff and offering a 1-shot structured mode would raise Portal tool completion rates substantially.
