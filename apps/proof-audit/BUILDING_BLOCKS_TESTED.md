# OpenMinion Building Blocks Tested (`openminion==0.1.24`)

This document records the exact OpenMinion SDK and CLI building blocks exercised by **ProofAudit Minion** (`proof-audit/`).

| Building Block | Where Used | Purpose in ProofAudit Minion | Verification Status |
| --- | --- | --- | --- |
| `APIRuntime.from_config_path` | `proof_audit/agent.py` | Shared runtime initialized from an isolated `agents.json` with `home_root` and `data_root` in a temp dir. | Verified (unit + e2e mock OpenAI server) |
| `runtime.close()` | `proof_audit/agent.py` | Cleanly closes SQLite storage and HTTP clients in `finally`. | Verified (Windows temp dir cleanup) |
| `Agent` | `proof_audit/agent.py` | Two-stage agent orchestration (Stage 1 Collector + Stage 2 Verdict Judge) sharing one `APIRuntime`. | Verified (e2e mock OpenAI server) |
| `@tool(min_scope="READ_ONLY", idempotent=True)` | `proof_audit/checks.py` | Non-mutating checks (`inspect_repo_manifest`, `scan_sdk_surface`, `probe_openai_compatible_endpoint`). | Verified (direct + Agent tool calls) |
| `@tool(idempotent=True)` | `proof_audit/checks.py` | Bounded `run_repo_smoke_check` (`py_compile`), classified as local write so `approval_callback` gates execution. | Verified (`approval_callback` invoked) |
| `output_type=ProofAuditReport` | `proof_audit/agent.py`, `proof_audit/models.py` | Pydantic v2 structured output validation on Stage 2 Judge turn. | Verified (e2e mock OpenAI server) |
| `session_id` | `proof_audit/agent.py` | Preserves session continuity across Stage 1 and Stage 2 turns. | Verified (`outcome.session_id` asserted) |
| `approval_callback` | `proof_audit/agent.py` | Logs tool approval decisions (`tool_name`, `args`, `approval_id`) before `run_repo_smoke_check` executes. | Verified (asserted in e2e test) |
| `ProviderError` | `proof_audit/agent.py` | Explicit exception handling on upstream HTTP 500 / transport errors, with optional deterministic offline fallback. | Verified (HTTP 500 e2e test) |
| `openminion.services.bootstrap.provider_setup` | `proof_audit/agent.py` | Programmatic `ProviderSetupRequest` + `build_provider_setup` + `atomic_save_setup_config` for `openrouter`, `cortensor-portal`, `custom-openai-compatible`. | Verified (config generation + e2e) |
| `openminion setup --list-providers --json` | CLI / Docs | Discovers supported provider presets (`openrouter`, `cortensor-portal`, `cortensor-router`, `custom-openai-compatible`). | Verified (CLI run) |
| `openminion doctor --check-turn --json` | CLI / Docs | Environment and runtime readiness check referenced in target repo audits. | Verified (CLI surface) |

## Live Model Run Evidence (`2026-11-27T11:29:12Z`)
- **Provider / Model**: `openrouter` / `nvidia/nemotron-3.5-super-vl:free`
- **Session ID**: `proof-audit-eff1f9debb`
- **Approval Callback**: `approvals_count=1` (`run_repo_smoke_check`, `approved=true`)
- **Offline Fallback**: `False` (100% live model-backed Stage 1 tool collection + Stage 2 Pydantic `ProofAuditReport`)
- **Verdict / Score**: `READY` (`100/100`)
- **Cortensor Portal Probe**: `https://api.cortensor.app/v1/models` -> `HTTP 401` in `1039.76 ms` (reachable; API key required)
- **`openminion doctor --json`**: Exit `0` (verified `config.exists`, runtime manager component health, and identity bundle diagnostic output).
