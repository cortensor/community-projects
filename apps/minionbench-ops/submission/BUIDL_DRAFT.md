# Minionbench Ops — OpenMinion 0.1.24 Release Triage Guard & Runtime Diagnostic Workbench

## Problem & Overview

Cortensor Hackathon #5 (`#2418`) invites builders to ship practical, repeatable agents on the OpenMinion `0.1.x` Python SDK while stress-testing OpenMinion's core building blocks (`APIRuntime`, `Agent`, `@tool` permission scopes, durable `session_id` state, structured outputs, error handling, and Cortensor Portal/Router configuration). Early alpha builders face two recurring friction points before shipping an agent to Cortensor Mainnet Full Alpha:

1. Pre-release workspaces frequently drift on secret hygiene, `agents.json` channel/provider mappings, or retry/timeout settings when switching between hosted OpenAI-compatible endpoints (`gemini`, `cortensor-portal`) and direct router nodes (`cortensor-router`).
2. Maintainers need reproducible, line-numbered telemetry showing what worked, what broke, and which SDK defaults trip new developers.

**Minionbench Ops** solves both problems in one compact Python 3.12 tool: an OpenMinion-powered **Release & Triage Guard Agent** paired with a **6-Probe Empirical Runtime Diagnostic Workbench** and a Dark Studio (`noir`) interactive console.

## Architecture & Solution

Minionbench Ops follows a strict vertical-slice architecture (`Invariants -> Schema -> Ledger -> State Engine -> Pipe -> Paint`) with AST-verified zero sibling imports across feature bricks:

- **`src/kernel/event_bus.py`:** Append-only thread-safe `EventBus`, frozen receipt/probe dataclasses, automatic credential scrubbing (`redact_secrets`), and a `CORRUPT_GATE_CONTROL=1` negative-control tripwire against vacuous tests.
- **`src/features/triage_tools/`:** Registers three `@tool(min_scope="READ_ONLY", idempotent=True)` tools (`inspect_workspace_manifest`, `audit_python_module_risks`, `check_cortensor_config_posture`) that execute without confirmation prompts, alongside a bare write `@tool` (`stage_release_brief`) that pauses at OpenMinion's `policy_confirmation_prompt` boundary until explicitly approved via `approval_callback`.
- **`src/features/minion_runner/`:** Manages isolated `.openminion_runtime/{home,data}` SQLite roots via `APIRuntime.from_config_path(...)` and `Agent(...)`. Executes real neural-model multi-tool triage runs across durable `session_id` + `thread_id` chains, generates validated `OpenMinionConfig` profiles (`cortensor-portal`, `cortensor-router`, `gemini`, `ollama`), and includes a real TCP `http://127.0.0.1/v1` `ThreadingHTTPServer` loopback endpoint for fast deterministic tests without mocks.
- **`src/features/runtime_diagnostics/`:** Exercises six empirical OpenMinion `0.1.24` building blocks and captures five source-verified SDK findings:
  1. `OM-FINDING-01`: Omitting `"default_channel": "console"` on a custom `agents.<id>` block raises `RuntimeError: inbound authenticity denied (reason=invalid_channel, mode=warn)` (`security.py:132`).
  2. `OM-FINDING-02`: Setting a human display string in `agents.<id>.name` triggers `UnknownProfileError` during turn timeout resolution (`timeout.py:54`).
  3. `OM-FINDING-03`: Sequential `Agent.run(...)` calls on one `session_id` fork threads (`fork_thread`, `session_history_available="false"`) unless `thread_id=first.thread_id` is supplied (`examples/sdk/sessions.py`).
  4. `OM-FINDING-04`: `openminion setup --list-providers --json` lists 20 preset IDs (`gemini`, `cortensor-portal`, `cortensor-router`) whereas `SUPPORTED_PROVIDERS` in `agents.json` accepts 9 transport keys, disabling retries on Cortensor Portal (`cortensor_portal_no_idempotency`, `max_retries=0`) and flooring Cortensor Router turn timeouts at `455.0s`.
  5. `OM-FINDING-05`: A single bounded tool turn triggers 7 internal LLM calls (`entry`, `freshness_classify`, `act` x3, `reflect`, `judge`), motivating a single-pass SDK mode for metered decentralized routers.
- **`web/diagnostic_console.html`:** Dark Studio (`noir`) single-page console featuring live run telemetry, a 6-axis SVG verification radar, keyboard navigation (`1`–`6`, `R`, `E`), Cortensor config posture inspection, and high-DPI PNG receipt export.

## Demo Walkthrough & Verification

Reproduce the complete live model run, 6 diagnostic probes, and test suite locally in three commands:

```bash
python3.12 -m venv .venv && .venv/bin/pip install "openminion>=0.1.24" "pytest>=8.0.0"
.venv/bin/python -m src.cli
.venv/bin/pytest tests -q
```

- **Repository:** https://github.com/HindsightWise/minionbench-ops-openminion
- **Demo Video (H.264 MP4):** https://github.com/HindsightWise/minionbench-ops-openminion/raw/main/outputs/demo_walkthrough.mp4
- **Generated Verification Artifacts:** `outputs/live_model_run_receipt.json`, `outputs/building_blocks_tested.json`, `BUILDING_BLOCKS_TESTED.md`, and `WHAT_WE_LEARNED.md`.

## Roadmap & Milestones

- **Milestone 1 (Completed — Hackathon #5 Alpha):** Shipped OpenMinion `0.1.24` vertical-slice Release & Triage Guard, live neural multi-tool run receipt, 6/6 building-block probe suite, 5 source-verified SDK findings, and Dark Studio Diagnostic Console.
- **Milestone 2 (Next — Upstream OpenMinion PRs):** Coordinate with OpenMinion maintainers on issues and targeted fix PRs for `default_channel` fallback (`OM-FINDING-01`), `agents.<id>.name` profile resolution (`OM-FINDING-02`), and `examples/sdk/sessions.py` `thread_id` continuity (`OM-FINDING-03`).
- **Milestone 3 (Cortensor Mainnet Full Alpha):** Add live Cortensor Portal (`oss-20b`) and Gemma4 latency/determinism benchmarking across dedicated vs ephemeral router session pools once Portal cohort credentials are provisioned.
