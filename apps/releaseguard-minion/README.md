# ReleaseGuard Minion

An inspectable, permission-gated **Repository & Web3/OSS Release Readiness Auditor Agent** built on **OpenMinion 0.1 (`openminion==0.1.24`)** for **Cortensor Hackathon #5**.

- **Standalone Upstream Repository:** [github.com/AndreyJackKali/release-guard-minion](https://github.com/AndreyJackKali/release-guard-minion) (`v0.2.0`, GitHub Actions CI passing)
- **Live Interactive Showcase (GitHub Pages):** [andreyjackkali.github.io/release-guard-minion/](https://andreyjackkali.github.io/release-guard-minion/)
- **78s HD Demo Video (`1280×720`, H.264, `24fps`, `2.02 MB`):** [andreyjackkali.github.io/release-guard-minion/demo.mp4](https://andreyjackkali.github.io/release-guard-minion/demo.mp4)
- **1-Page Printable Judge Brief & Rubric Scorecard:** [andreyjackkali.github.io/release-guard-minion/judge-brief.html](https://andreyjackkali.github.io/release-guard-minion/judge-brief.html)
- **SDK Feedback & Upstream Contributions:** [`BUILDING_BLOCKS_TESTED.md`](./BUILDING_BLOCKS_TESTED.md) | [`WHAT_WE_LEARNED.md`](./WHAT_WE_LEARNED.md)
  - **4 original upstream issues on `openminion/openminion`:** [#881](https://github.com/openminion/openminion/issues/881), [#882](https://github.com/openminion/openminion/issues/882), [#883](https://github.com/openminion/openminion/issues/883), [#884](https://github.com/openminion/openminion/issues/884)
  - **2 upstream bug-fix PRs on `openminion/openminion`:** [PR #885](https://github.com/openminion/openminion/pull/885) (fixes `#881`, `36/36` tests passing), [PR #886](https://github.com/openminion/openminion/pull/886) (fixes `#882`, `29/29` tests passing)

---

## Why ReleaseGuard Minion?

Shipping a Web3 or OSS release involves high-leverage checks (manifest completeness, licensing, CI/test coverage, `.env` and private-key hygiene) paired with side-effecting release actions (writing signed-off briefs, cutting annotated git tags). Running those steps through an opaque prompt wrapper gives operators zero policy guarantees.

**ReleaseGuard Minion** uses OpenMinion's local-first runtime so every inspection, policy boundary, approval decision, session record, memory snapshot, and subagent delegation is deterministic, bounded, and inspectable.

## Architecture

```text
release-guard CLI / Python API
  └── ReleaseGuardMinion (owns APIRuntime.from_config_path(..., logging_mode="interactive"))
        ├── Diagnostics: runtime_posture() · capability_report() · runtime_self_model() · tool_inventory_report()
        ├── Agent(name="release-guard", output_type=ReleaseAuditReport, forced_tools=["inspect_repo_manifest"])
        │     ├── READ_ONLY + idempotent=True (auto-allowed under default policy):
        │     │     ├── inspect_repo_manifest   (README, LICENSE, CHANGELOG, SECURITY, manifests, git state)
        │     │     ├── inspect_ci_and_tests    (.github/workflows, test suites, Makefile/pytest/pre-commit)
        │     │     └── scan_secret_hygiene     (.env exposure, OpenAI/GitHub/AWS/PEM/EVM private keys)
        │     ├── WRITE_SAFE + idempotent=True (policy-gated via approval_callback):
        │     │     └── write_release_brief     (single-use approval via ReleaseApprovalGate)
        │     └── dangerous=True (destructive, fail-closed):
        │           └── create_release_tag      (semver-validated git tag -a; denied unless explicitly enabled)
        ├── ReleaseApprovalGate (fail-closed single-use approval_callback + ApprovalDecisionRecord ledger)
        ├── Durable SQLite Session Store (.openminion/state/openminion.db, session_id="release-guard-<slug>")
        ├── Portable Memory Export (openminion.MemoryBundle -> save_bundle() / load_bundle())
        ├── Bounded Delegation (subagent(parent, name="secret-reviewer", tools=[scan_secret_hygiene], timeout_seconds=60))
        └── Streaming Turns (APIRuntime.submit_turn() -> RuntimeTurnHandle.stream() + result())
```

### Structured Output & Audit Envelope

- `ReleaseAuditReport` (Pydantic v2): `repo_name`, `verdict` (`ready` | `needs_work` | `blocked`), `score` (`0–100`), `rationale`, `checks: list[ReleaseCheck]`, `blockers`, `recommendations`.
- `AuditRunEnvelope`: pairs the validated `ReleaseAuditReport` with `session_id`, `run_id`, `run_state`, `thread_id`, `approvals: list[ApprovalDecisionRecord]`, `stats`, `memory_bundle_path`, and `brief_path`.

---

## Provider-Neutral Setup (Cortensor Portal, Cortensor Router & OpenMinion Providers)

ReleaseGuard Minion never hardcodes a provider or API key. It consumes any configured OpenMinion `agents.json` profile:

```bash
# Option 1: Cortensor Portal (OpenAI-compatible transport -> https://api.cortensor.app/v1, model oss-20b)
export CORTENSOR_API_KEY="..."
openminion setup --provider cortensor-portal --model oss-20b --no-chat

# Option 2: Cortensor Router (local router -> http://127.0.0.1:8080/api/v2/completions)
openminion setup --provider cortensor-router --no-chat

# Option 3: Other OpenMinion-supported providers (Groq, Gemini, OpenRouter, Ollama, OpenAI, etc.)
export GROQ_API_KEY="..."
openminion setup --provider groq --model llama-3.3-70b-versatile --no-chat

# Verify provider and runtime readiness
openminion status readiness --json
openminion doctor --check-turn
```

---

## Quick Start

Requires **Python 3.11+**.

```bash
cd apps/releaseguard-minion
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest
```

### CLI Usage

```bash
# 1. Audit a local repository (READ_ONLY tools auto-run; write brief requires --approve-brief; git tag denied)
release-guard audit /path/to/repo \
  --output-brief ./RELEASE_BRIEF.md \
  --approve-brief \
  --memory-out ./audit-memory.json

# 2. Emit full machine-readable AuditRunEnvelope JSON
release-guard audit /path/to/repo --json

# 3. Inspect OpenMinion runtime posture, capabilities, self-model, and tool count
release-guard diagnostics

# 4. Run a bounded read-only secret-hygiene subagent (timeout + scoped tool allowlist)
release-guard security-subagent /path/to/repo --timeout 60
```

---

## Verification & Test Suite

The test suite runs offline and deterministically against the real **`openminion==0.1.24`** runtime (`APIRuntime`, `Agent`, `@tool`, `subagent`, `MemoryBundle`, SQLite session persistence, `submit_turn` streaming, policy engine, and `httpx`/`llmctl` OpenAI-compatible transport via a local loopback HTTP server):

```bash
pytest -v
```

| Test File | Tests | What It Verifies |
|---|---|---|
| [`tests/test_tools.py`](./tests/test_tools.py) | 5 | Risk-tier `@tool` contracts (`READ_ONLY`, `WRITE_SAFE`, `dangerous=True`), manifest/CI/secret detection on clean & leaky repos, brief writing & semver git tag validation, fail-closed single-use `ReleaseApprovalGate` |
| [`tests/test_sdk_integration.py`](./tests/test_sdk_integration.py) | 2 | Full end-to-end `openminion==0.1.24` audit run (auto-allowed reads, single-use `approval_callback` on write, SQLite session, `MemoryBundle` export/reload, diagnostics snapshot) + scoped `subagent` & `APIRuntime.submit_turn()` streaming chunks |
| [`tests/test_openminion_findings.py`](./tests/test_openminion_findings.py) | 4 | Deterministic minimal reproducers proving 4 real `openminion==0.1.24` SDK bugs (Findings #1–#4) |
| **Total** | **11/11 PASS** | Verified on Python `3.12.3` + `openminion==0.1.24` |

## License

MIT — see [`LICENSE`](./LICENSE) (compatible with `cortensor/community-projects`).
