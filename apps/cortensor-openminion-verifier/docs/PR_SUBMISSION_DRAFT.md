# Cortensor Hackathon #5 Submission Pack & Operator Checklist

> **Source Repository**: `https://github.com/huadeng408/cortensor-openminion-verifier`  
> **SDK Pin**: `openminion==0.1.21` | **License**: `MIT` | **Package Version**: `v0.1.2`  
> **Primary Channels**: DoraHacks Hackathon #5 (`#2418`) BUIDL + `cortensor/community-projects` (`apps/cortensor-openminion-verifier/`) PR (`dev-huadeng408`)  
> **Bonus Track**: Manual issue/PR drafts for `openminion/openminion` in [`docs/UPSTREAM_OPENMINION_BONUS_DRAFTS.md`](https://github.com/huadeng408/cortensor-openminion-verifier/blob/main/docs/UPSTREAM_OPENMINION_BONUS_DRAFTS.md)

---

## Operator Pre-Submission Checklist (English + 简体中文操作清单)

Complete these manual checks before posting to DoraHacks or opening the upstream PR (请按以下清单人工核对后再公开提交)：

- [ ] **Star & Fork Upstream Repositories / 点赞并 Fork 上游仓库**:
  - Star & Fork `openminion/openminion`: `https://github.com/openminion/openminion`
  - Star & Fork `cortensor/community-projects`: `https://github.com/cortensor/community-projects`
- [ ] **Verify Latest Discord Directory Layout / 核对最新 Discord 公告与目录规范**:
  - Confirm the latest Hackathon #5 Discord announcement matches target path `apps/cortensor-openminion-verifier/` and required metadata files ([`PROJECTS.yml`](https://github.com/huadeng408/cortensor-openminion-verifier/blob/main/PROJECTS.yml), [`STATUS.md`](https://github.com/huadeng408/cortensor-openminion-verifier/blob/main/STATUS.md), [`RELEASE.md`](https://github.com/huadeng408/cortensor-openminion-verifier/blob/main/RELEASE.md), [`LICENSE`](https://github.com/huadeng408/cortensor-openminion-verifier/blob/main/LICENSE) `MIT`).
- [ ] **Manual Public Flip / 手动将源仓库设为 Public**:
  - Switch `huadeng408/cortensor-openminion-verifier` visibility from `Private` to `Public` manually in GitHub Settings right before submitting (or stage the clean tracked tree on branch `dev-huadeng408` of your `cortensor/community-projects` fork under `apps/cortensor-openminion-verifier/`).
- [ ] **Run Final Test & Secret Hygiene Check / 终检测试与零明文密钥扫描**:
  - Verify `.env`, `.openminion/`, `.openminion-state/`, `artifacts/`, and API keys remain untracked.
  - Run `.\.venv\Scripts\python.exe -m pytest -q` on `main` (`0 failed`) and confirm `assert_no_plaintext_secrets` passes cleanly.
- [x] **Demo Video (`4:06`, `1920x1080`, `30fps`, narrated + captioned) / 1080p 英文演示视频（真实模型实跑）**:
  - Public MP4: https://github.com/huadeng408/cortensor-openminion-verifier/releases/download/v0.1.2/cortensor_hackathon5_demo.mp4 (release page: https://github.com/huadeng408/cortensor-openminion-verifier/releases/tag/v0.1.2). The live-run chapter is a timestamped replay of a real `grok-4.6` audit recorded on 2026-11-16 (`fixtures/live_run_2026-11-16_trace.jsonl`).
  - Paste the public MP4 URL into the DoraHacks BUIDL form and the Hackathon #5 PR body.

---

## Channel 1: DoraHacks Hackathon #5 (`#2418`) BUIDL Submission Template

Copy and paste the section below directly into the DoraHacks Hackathon #5 (`#2418`) BUIDL form (replace the demo video placeholder URL after uploading `cortensor_hackathon5_demo.mp4`):

```markdown
### Project Title
Cortensor OpenMinion Verifier — Redundant Claim Consensus Auditor & 10-Module SDK Probe Suite

### Summary
`cortensor-openminion-verifier` (`v0.1.2`, `MIT` License) is an isolated multi-agent consensus verification application and empirical SDK benchmark harness built on `openminion==0.1.21` for Cortensor Hackathon #5 (`#2418`).

Single-pass LLM verification hallucinates, skips counter-evidence, and risks unapproved external side effects. Aligned with Cortensor PoI/PoUW redundancy principles, `cortensor-openminion-verifier` turns an ambiguous prediction-market or oracle `ClaimDossier` into a structured `ConsensusVerdict` through isolated dual-perspective `subagent()` passes (`corroborator` and `skeptic`), cross-turn `MemoryBundle` portability, and fail-closed `Handoff` publication gating.

### OpenMinion 0.1.21 Integration Highlights
- **Zero-Key Runtime Isolation**: `create_isolated_runtime()` boots `APIRuntime.from_config_path()` with per-workspace `home_root` / `data_root` SQLite DBs and scrubs `api_key=''` in `.openminion/agents.json`.
- **4 `READ_ONLY` Scoped Evidence Tools (`build_scoped_verifier_tools`)**: Binds `load_delphi_market_fixture`, `search_public_evidence`, `fetch_source_excerpt`, and SSRF-guarded `fetch_public_url_excerpt` (supporting CLI `--fixtures` catalogs and inline `dossier.metadata["evidence_sources"]` while blocking loopback, private, link-local, CGNAT, and unsafe redirects by default).
- **Blind Dual-Perspective `subagent()` Passes**: `corroborator` and `skeptic` run in separate `SubagentRunContext` sessions (`parent_transcript_inherited=False`, `memory_posture="none"`) and synthesize typed Pydantic outputs via `synthesize_consensus()`.
- **Portable `MemoryBundle` & Explicit `thread_id` Continuity**: Exports/imports scoped session memory (`export_bundle` -> `save_bundle` -> `load_bundle` -> `import_bundle`) with fail-closed foreign `session_id` rejection.
- **Approval-Gated Publication via `Handoff`**: `transfer_to_publisher` routes to a dangerous `WRITE_SAFE` `@tool` that pauses fail-closed when `approval_callback=None`, supports `deny`, and enforces single-use `PolicyGrantInput(max_uses=1)` + replay protection on `allow_once`.
- **Provider-Agnostic Presets**: Supports `openai-compatible`, `cortensor-portal`, and `cortensor-router` without application code changes.

### OpenMinion 0.1 Building Blocks Tested (10/10 Live LLM Calibrated on `grok-4.7`)

| # | Probe ID | Building Block | Status | Latency (ms) | Verified Telemetry |
|---:|---|---|---|---:|---|
| 1 | `agent_runtime_isolation` | Agent & APIRuntime Isolation | PASS | 6576.08 | `db_count=14`, `secret_free_config=True` |
| 2 | `structured_pydantic_output` | Pydantic Output & Validation Error | PASS | 207213.19 | `status=OK`, `score=0.99`, `negative_validation_error=True` |
| 3 | `tool_and_forced_tools` | `@tool` & `forced_tools` | PASS | 77598.94 | `forced_tool=probe_echo_tag`, 2 tool invocations |
| 4 | `policy_confirmation_gate` | Dangerous `@tool` Allow/Deny/Pause/Resume | PASS | 76300.74 | `allow_executed=True`, `deny_blocked=True`, `pause_blocked=True`, `resume_executed=True` |
| 5 | `session_continuity` | Multi-Turn `thread_id` & Isolation | PASS | 92405.48 | `same_session_recalled=True`, `second_session_isolated=True` |
| 6 | `memory_bundle_portability` | `MemoryBundle` Roundtrip | PASS | 1.99 | `bundle_version=memory_bundle.v1`, `invalid_mode_rejected=True` |
| 7 | `subagent_delegation` | `subagent()` & `SubagentRunContext` | PASS | 30651.67 | `parent_transcript_inherited=False`, scoped `tool_allowlist` |
| 8 | `agent_handoff` | `Handoff` Peer Agent Transfer | PASS | 110097.21 | `tool_name=transfer_to_specialist`, `handoff_invocations=1` |
| 9 | `submit_turn_streaming_telemetry` | `submit_turn()` `TurnChunk` & `TurnTelemetry` | PASS | 6278.02 | `12` `TurnChunk`s, `stats=(11841/430)` vs `TurnTelemetry(0/0)` |
| 10 | `error_and_timeout_contracts` | Retries, Timeout & Wire Contracts | PASS | 4765.67 | `http_500_attempts=6`, `TurnTimeoutError`, `Anthropic`/`Cortensor`/`OpenAI` SSE checks |

- **Fresh Live Run Shown in Demo (2026-11-16, `grok-4.6`, `delphi-btc-etf-2024`)**: verdict `SUPPORTED`, `agreement_score=0.975`, `mean_confidence=0.925`, `corroborator (0.95)` & `skeptic (0.90)`, `Handoff allow_once` `published=True`, `23` requests / `146,855` tokens / `439.4 s` model latency. The SSRF guard refused a live `sec.gov` fetch whose hostname resolved to a non-public fake-IP (`198.18.0.177`, local proxy DNS) and both passes fell back to curated primary sources. Raw bundle: [`fixtures/live_run_2026-11-16_grok-4.6.json`](https://github.com/huadeng408/cortensor-openminion-verifier/blob/main/fixtures/live_run_2026-11-16_grok-4.6.json), event trace: [`fixtures/live_run_2026-11-16_trace.jsonl`](https://github.com/huadeng408/cortensor-openminion-verifier/blob/main/fixtures/live_run_2026-11-16_trace.jsonl).
- **Dual-Pass Live Audit (`grok-4.6`, `delphi-btc-etf-2024`)**: Verdict `SUPPORTED`, `agreement_score=0.98`, `mean_confidence=0.94`, `corroborator (0.96)` & `skeptic (0.92)`, `3` read-only tool calls, `Handoff allow_once` `published=True`, `20` requests / `118,193` total tokens / `394,205 ms`.

### Reproduction Commands (MIT License)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
cortensor-verifier probe --preset openai-compatible --model grok-4.7 --timeout-seconds 180 --export-docs
cortensor-verifier audit --claim-id delphi-btc-etf-2024 --preset openai-compatible --model grok-4.6 --multi-pass --session-id demo-01 --publish --approval-mode allow_once
cortensor-verifier render-demo --sample-json fixtures/calibrated_sample_run.json --duration-seconds 75 --fps 10 -o artifacts/cortensor_hackathon5_demo.mp4
```

### Links & Artifacts
- **Repository (`MIT` License)**: https://github.com/huadeng408/cortensor-openminion-verifier
- **Building Blocks Matrix (`10/10`)**: https://github.com/huadeng408/cortensor-openminion-verifier/blob/main/docs/BUILDING_BLOCKS_TESTED.md
- **Empirical DX Report (`What We Learned`)**: https://github.com/huadeng408/cortensor-openminion-verifier/blob/main/docs/WHAT_WE_LEARNED.md
- **Upstream OpenMinion Bug & Patch Drafts (Bonus Track)**: https://github.com/huadeng408/cortensor-openminion-verifier/blob/main/docs/UPSTREAM_OPENMINION_BONUS_DRAFTS.md
  - Maintainer-confirmed Issue [#773](https://github.com/openminion/openminion/issues/773) + Substantive Fix PR [#775](https://github.com/openminion/openminion/pull/775) (`TurnResponse.telemetry` token totals from `RunStats`)
  - Maintainer-confirmed Issue [#774](https://github.com/openminion/openminion/issues/774) (`Handoff` per-target `timeout_seconds` & `approval_callback` concrete proposal)
- **DoraHacks BUIDL (`#51230`)**: https://dorahacks.io/build/51230
- **Calibrated Sample Fixture**: https://github.com/huadeng408/cortensor-openminion-verifier/blob/main/fixtures/calibrated_sample_run.json
- **Demo Video (`4:06`, `1920x1080`, narrated, real live run)**: https://github.com/huadeng408/cortensor-openminion-verifier/releases/download/v0.1.2/cortensor_hackathon5_demo.mp4
```

---

## Channel 2: `cortensor/community-projects` Pull Request Template

> **Fork Branch**: `dev-huadeng408` -> `cortensor/community-projects:main`  
> **Target Path**: `apps/cortensor-openminion-verifier/`  
> **Required Metadata Included**: `PROJECTS.yml`, `STATUS.md`, `RELEASE.md`, `LICENSE` (`MIT`), `openminion==0.1.21`

Copy and paste the PR title and body below when opening the pull request against `cortensor/community-projects`:

- **Suggested PR Title**: `feat(apps): add cortensor-openminion-verifier (v0.1.2, MIT, openminion==0.1.21)`

```markdown
### Summary

Adds **`cortensor-openminion-verifier`** (`v0.1.2`, **`MIT` License**) under `apps/cortensor-openminion-verifier/` — an isolated **Redundant Claim Consensus Verifier & 10-Module Building-Block Probe Suite** built on **`openminion==0.1.21`**.

Given a prediction-market / oracle **`ClaimDossier`**, the application coordinates:
1. Two isolated **`subagent()`** verifier passes (**`corroborator`** and **`skeptic`**, `parent_transcript_inherited=False`) restricted to `min_scope="READ_ONLY"` tools (`load_delphi_market_fixture`, `search_public_evidence`, `fetch_source_excerpt`, and SSRF-guarded `fetch_public_url_excerpt` with `--fixtures` and inline `evidence_sources` scoping).
2. Consensus synthesis (**`synthesize_consensus()`**) into a typed **`ConsensusVerdict`** with portable **`MemoryBundle`** persistence scoped per `session_id`.
3. Approval-gated external publication via **`Handoff`** (`transfer_to_publisher`) enforcing fail-closed `pause` (`approval_callback=None`), explicit `deny`, or single-use **`allow_once`** (`PolicyGrantInput(max_uses=1)` + replay protection).
4. A 10-probe **`BuildingBlockProbeRunner`** suite calibrated against both deterministic loopback HTTP stubs and live LLM inference.

### Upstream Community Package Checklist
- [`PROJECTS.yml`](https://github.com/huadeng408/cortensor-openminion-verifier/blob/main/PROJECTS.yml) (`category: apps`, `owner: "@huadeng408"`, `version: v0.1.2`, `status: active`)
- [`STATUS.md`](https://github.com/huadeng408/cortensor-openminion-verifier/blob/main/STATUS.md) (active status & known upstream `openminion==0.1.21` rough edges)
- [`RELEASE.md`](https://github.com/huadeng408/cortensor-openminion-verifier/blob/main/RELEASE.md) (`v0.1.0` -> `v0.1.1` -> `v0.1.2`)
- [`LICENSE`](https://github.com/huadeng408/cortensor-openminion-verifier/blob/main/LICENSE) (`MIT` License, matching `cortensor/community-projects/apps/*` policy)
- Exact SDK Pin: `openminion==0.1.21` in [`pyproject.toml`](https://github.com/huadeng408/cortensor-openminion-verifier/blob/main/pyproject.toml)

### OpenMinion 0.1 Building Blocks Exercised (`10/10` Verified)

1. **`agent_runtime_isolation`**: Isolated `home_root` / `data_root` SQLite DBs + scrubbed secret-free `agents.json` (`14` DBs, `6576.08 ms`).
2. **`structured_pydantic_output`**: Strict `BaseModel` validation + `AgentOutputValidationError` negative contract (`207213.19 ms`).
3. **`tool_and_forced_tools`**: Custom `@tool` dispatch + deterministic `forced_tools=(...)` execution (`77598.94 ms`).
4. **`policy_confirmation_gate`**: `@tool(dangerous=True, min_scope="WRITE_SAFE")` gated via `approval_callback` (`allow` & `deny`) plus fail-closed `approval_callback=None` pause (`thread_id`) and `allow_once` resume (`76300.74 ms`).
5. **`session_continuity`**: Multi-turn `thread_id` continuity within `session_id` + zero cross-session leakage (`92405.48 ms`).
6. **`memory_bundle_portability`**: `export_bundle` -> `save_bundle` -> `load_bundle` -> `import_bundle` roundtrip (`1.99 ms`).
7. **`subagent_delegation`**: Isolated `SubagentRunContext` delegation without closing parent runtime (`30651.67 ms`).
8. **`agent_handoff`**: Coordinator-to-specialist peer transfer via `Handoff` (`transfer_to_specialist` / `transfer_to_publisher`, `110097.21 ms`).
9. **`submit_turn_streaming_telemetry`**: Real `APIRuntime.submit_turn()` streaming `TurnChunk` (`12` chunks) + `TurnResponse.stats` (`11841` in / `430` out) vs `TurnTelemetry` (`0/0`) check (`6278.02 ms`).
10. **`error_and_timeout_contracts`**: `http_connection_reuse_enabled=False` Windows policy, HTTP 500 `ProviderError` (`6` attempts), `TurnTimeoutError`, and `AnthropicProvider` / `CortensorProvider` / `OpenAIProvider.stream()` SSE usage wire contracts (`4765.67 ms`).

Full live matrix: [`docs/BUILDING_BLOCKS_TESTED.md`](https://github.com/huadeng408/cortensor-openminion-verifier/blob/main/docs/BUILDING_BLOCKS_TESTED.md)

### Key Empirical DX Findings (`10` Findings from Live `openminion==0.1.21` Calibration)

Full technical breakdown with source locations, repro snippets, expected-vs-actual diagnostics, and per-probe telemetry is documented in [`docs/WHAT_WE_LEARNED.md`](https://github.com/huadeng408/cortensor-openminion-verifier/blob/main/docs/WHAT_WE_LEARNED.md):

1. **Worktree-Isolated Containment**: Explicit `home_root` / `data_root` isolates `agents.json` and SQLite/Alembic DBs per workspace without touching developer global configuration.
2. **Internal Classifiers & Output Coercion**: `FreshnessContract` / `FinalizationStatus` / `ClosureJudgment` (`tool_choice="submit_output"`) require preserving `action_summary`, and `Agent._coerce_output()` relies on `_extract_json_object()` due to the `f"{agent_id}: "` reply prefix.
3. **Read-Only Tool Binding & Forced Dispatch**: `@tool(min_scope="READ_ONLY")` combined with `tool_choice="forced"` executes deterministically without workspace writes.
4. **Sync `approval_callback` vs Fail-Closed Pause/Resume**: `@tool(dangerous=True, min_scope="WRITE_SAFE")` honors boolean `approval_callback` (`allow` / `deny`) and pauses fail-closed on `approval_callback=None` until `Agent.run("allow_once", session_id=..., thread_id=...)`.
5. **Explicit `thread_id` Requirement**: `Agent.run(session_id=...)` forks a fresh thread on settled sessions unless `thread_id` is forwarded explicitly alongside `session_id`.
6. **Cross-Runtime `MemoryBundle` Portability**: `export_session_memory()` and `import_session_memory()` roundtrip portable bundles across separate `APIRuntime` SQLite stores and reject invalid trust modes fail-closed.
7. **Isolated Subagent Passes & `90.0s` Timeout Forwarding**: Per-pass isolated subagent sessions prevent `resolve_entry_task_update()` `Missing/Duplicate task_update` crashes (`openminion/modules/brain/loop/context/task_context.py:173-191`), while explicit `timeout_seconds` prevents falling back to `90.0s`.
8. **Peer `Handoff` Timeout/Approval Forwarding Gap**: `build_delegate_tool()` (`openminion/api/handoff.py:168-170`) calls `handoff.target.run(message)` without caller `timeout_seconds` or `approval_callback`, requiring target-runtime `PolicyGrantInput(max_uses=1)`; live coordinators also paraphrase specialist text (`verbatim_ack=False`).
9. **`submit_turn()` Telemetry vs `TurnResponse.stats`**: `APIRuntime.submit_turn()` emitted `12` `TurnChunk`s with `TurnTelemetry(duration_ms=6281, tokens_in=0, tokens_out=0)` whereas `TurnResponse.stats` recorded `input_tokens=11841`, `output_tokens=430` (`openminion/services/runtime/daemon.py:549-555`).
10. **Provider Wire Protocols, Retry Multiplication & Connection Reuse Policy**: `AnthropicProvider` (`x-api-key` + `/anthropic/v1/messages`), `CortensorProvider` (`Bearer` + `/cortensor/api/v2/completions`), and `OpenAIProvider.stream()` (`service_vendor="openai"` SSE usage gating) were verified alongside `http_connection_reuse_enabled=False`, HTTP 500 `6`-attempt retry multiplication, and `TurnTimeoutError`.

### Calibration Telemetry Summary (`[Live LLM Calibrated]`)

- **10/10 Building-Block Probes (`grok-4.7`)**: `10/10` `PASS` (`failed=0`), `611,888.99 ms` total latency (`https://<configured-openai-compatible-relay>/v1`).
- **Dual-Pass Audit (`grok-4.6`, `delphi-btc-etf-2024`)**: Verdict `SUPPORTED`, `agreement_score=0.98`, `mean_confidence=0.94`, passes `corroborator (0.96)` & `skeptic (0.92)`, `3` read-only tool calls, `Handoff allow_once` `published=True`, `20` requests / `118,193` total tokens / `394,205 ms` recorded in [`fixtures/calibrated_sample_run.json`](https://github.com/huadeng408/cortensor-openminion-verifier/blob/main/fixtures/calibrated_sample_run.json).

### Reproducibility & Demo Video

- Fresh live run shown in the demo (2026-11-16, `grok-4.6`, `delphi-btc-etf-2024`): verdict `SUPPORTED`, `agreement_score=0.975`, `mean_confidence=0.925`, `corroborator (0.95)` & `skeptic (0.90)`, `Handoff allow_once` `published=True`, `23` requests / `146,855` tokens / `439.4 s` model latency. The SSRF guard refused a live `sec.gov` fetch whose hostname resolved to a non-public fake-IP (`198.18.0.177`, local proxy DNS) and both passes fell back to curated primary sources. Raw bundle: [`fixtures/live_run_2026-11-16_grok-4.6.json`](https://github.com/huadeng408/cortensor-openminion-verifier/blob/main/fixtures/live_run_2026-11-16_grok-4.6.json), event trace: [`fixtures/live_run_2026-11-16_trace.jsonl`](https://github.com/huadeng408/cortensor-openminion-verifier/blob/main/fixtures/live_run_2026-11-16_trace.jsonl).

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
cortensor-verifier render-demo --sample-json fixtures/calibrated_sample_run.json --duration-seconds 75 --fps 10 -o artifacts/cortensor_hackathon5_demo.mp4
```

- **Demo Video (`4:06`, `1920x1080`, narrated + captioned H.264 MP4, real live `grok-4.6` run)**: https://github.com/huadeng408/cortensor-openminion-verifier/releases/download/v0.1.2/cortensor_hackathon5_demo.mp4
```

---

## Bonus Track Pointer: Upstream `openminion/openminion` Issue & Patch Drafts

For the Hackathon #5 Bonus Track, **3 minimal upstream bug reports & patch drafts** verified directly against installed `openminion==0.1.21` site-packages are staged for manual human filing in [`docs/UPSTREAM_OPENMINION_BONUS_DRAFTS.md`](https://github.com/huadeng408/cortensor-openminion-verifier/blob/main/docs/UPSTREAM_OPENMINION_BONUS_DRAFTS.md):

1. `openminion/services/runtime/daemon.py:549-555` — Populate `TurnResponse.telemetry.tokens_in` / `tokens_out` from `turn_result.stats` / `total_*_tokens_used`.
2. `openminion/api/handoff.py:168-170` — Allow `Handoff` / `build_delegate_tool()` to forward `timeout_seconds` and `approval_callback` to `handoff.target.run()`.
3. `openminion/modules/brain/loop/context/task_context.py:173-191` — Guard `resolve_entry_task_update()` against sequential `subagent()` omissions when `clarify=False` and duplicate parallel `task_update` sidecar patches.
