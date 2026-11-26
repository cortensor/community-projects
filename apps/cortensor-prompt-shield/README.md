# Cortensor Prompt Shield (`cortensor-prompt-shield`)

> **Automated Prompt-Injection, `@tool` Scope & Session-Isolation Security Auditor built on the OpenMinion `0.1.24` Python SDK for Cortensor Hackathon #5.**

`cortensor-prompt-shield` helps Cortensor & OpenMinion builders audit their tool-using AI agents **before deployment** — combining static Python AST inspection, live sandboxed adversarial probing via bounded `subagent()` delegation, cross-session canary-leak verification, Pydantic v2 structured security reporting, fail-closed `WRITE_SAFE` approval-gate attestation, and a built-in **`CompactGuardProxy`** that trims OpenMinion's 43 KB default outbound prompt overhead by >85% for small/edge Cortensor miner models.

---

## Live Artifacts & Demo

- **Interactive Live Dashboard (GitHub Pages)**: https://loganz2.github.io/cortensor-prompt-shield/
- **Demo Video (42.5s, 1280×720 H.264, verified live `qwen2.5:3b` + `openminion==0.1.24` run)**: [`docs/cortensor_prompt_shield_demo.mp4`](./docs/cortensor_prompt_shield_demo.mp4) ([Direct Link](https://loganz2.github.io/cortensor-prompt-shield/cortensor_prompt_shield_demo.mp4))
- **Live SHA-256 Attested Audit Receipt (`45` live model calls, `0` errors, `72.6%` prompt compaction)**: [`outputs/live_audit_receipt.json`](./outputs/live_audit_receipt.json)
- **Interactive Dark-Mode HTML Audit Dashboard**: [`outputs/security_audit_report.html`](./outputs/security_audit_report.html)
- **OpenMinion 0.1.24 Building Blocks Matrix (9 blocks tested)**: [`BUILDING_BLOCKS_TESTED.md`](./BUILDING_BLOCKS_TESTED.md)
- **Actionable Upstream Findings & Bug Repros**: [`WHAT_WE_LEARNED.md`](./WHAT_WE_LEARNED.md)
  - Upstream issues filed on `OpenMinion/openminion`: [#874](https://github.com/openminion/openminion/issues/874), [#875](https://github.com/openminion/openminion/issues/875), [#876](https://github.com/openminion/openminion/issues/876)

---

## 5-Stage OpenMinion `0.1.24` Audit Architecture

```text
Target Python Workspace + agents.json
  │
  ├── Stage 1: Streaming AST & Policy Agent (Agent.run_stream + forced_tools)
  │     • @tool(min_scope="READ_ONLY", idempotent=True) scan_agent_tools
  │     • @tool(min_scope="READ_ONLY", idempotent=True) inspect_openminion_policy
  │
  ├── Stage 2: Bounded Target Sandbox (subagent() + approval_callback gate)
  │     • VEC-01 Indirect Prompt Injection via untrusted tool attachment
  │     • VEC-02 Direct System-Prompt / Canary Exfiltration
  │     • VEC-03 Dangerous Tool Scope Escalation (honeypot export_sensitive_vault)
  │
  ├── Stage 3: Session Isolation Security Invariant (shared vs. isolated session_id)
  │     • Verifies audit marker persists in session_alpha and NEVER leaks to session_beta
  │
  ├── Stage 4: Typed Synthesis (output_type=SecurityAuditReport Pydantic v2)
  │     • Produces grade (A–F), risk_score_0_100, prioritized findings & @tool patches
  │
  └── Stage 5: Dangerous Write Gate Verification (@tool(min_scope="WRITE_SAFE", dangerous=True))
        • Verifies DENY path (fail-closed, zero bytes written)
        • Verifies ALLOW path (writes SHA-256 attested JSON + standalone HTML report)
```

### Bonus Builder Utility: `CompactGuardProxy`
While testing `openminion==0.1.24`, we discovered that even a minimal 2-character prompt sends **43,301 bytes** (`16,695` chars of default `## Runtime Grounding` + 8 built-in tools), causing HTTP 400 prompt-budget failures on edge/prompt-capped endpoints. `CompactGuardProxy` (`src/cortensor_prompt_shield/guard_proxy.py`) safely compacts redundant boilerplate under configurable byte ceilings while keeping custom instructions, user prompts, and `@tool` definitions intact — enabling reliable live runs on small/edge Cortensor models and OpenAI-compatible gateways.

---

## Quick Start

### 1. Install (Python 3.11+)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Offline Static AST Scan (Zero API Key Needed)
```bash
prompt-shield scan --target examples/vulnerable_sample_agent.py
```

### 3. Full 5-Stage Live Model Audit
Point at **any** OpenAI-compatible provider (Cortensor Portal `https://api.cortensor.app/v1`, OpenAI, OpenRouter, or Cortensor Router `/api/v2/completions`):

```bash
export OPENAI_API_KEY="your-provider-key"
prompt-shield audit \
  --target examples/vulnerable_sample_agent.py \
  --out outputs \
  --provider openai \
  --base-url https://api.openai.com/v1 \
  --model gpt-4.1-mini
```

Or pass `--no-compact-proxy` for direct uncompacted calls against high-context endpoints, or `--provider cortensor` for local Cortensor Router v2 (`http://127.0.0.1:8080/api/v2/completions`).

### 4. Run Automated Test Suite (Includes OpenMinion `0.1.24` SDK Finding Repros)
```bash
pytest -v
```

---

## Repository Layout

```text
cortensor-prompt-shield/
├── README.md
├── BUILDING_BLOCKS_TESTED.md       # 9 OpenMinion 0.1.24 building blocks tested
├── WHAT_WE_LEARNED.md              # 5 reproducible bugs & DX friction reports
├── LICENSE                         # MIT
├── pyproject.toml
├── examples/
│   └── vulnerable_sample_agent.py  # Intentional @tool misconfiguration benchmark target
├── src/cortensor_prompt_shield/
│   ├── agent.py                    # 5-stage OpenMinion 0.1.24 orchestrator
│   ├── cli.py                      # `prompt-shield scan | audit` CLI
│   ├── guard_proxy.py              # CompactGuardProxy (>85% prompt overhead reduction)
│   ├── html_report.py              # Dark-mode standalone HTML audit dashboard generator
│   ├── models.py                   # Pydantic v2 models including output_type=SecurityAuditReport
│   ├── scanner.py                  # Python AST @tool scope & agents.json policy scanner
│   └── tools.py                    # READ_ONLY + WRITE_SAFE/dangerous=True @tool suite
├── tests/
│   └── test_prompt_shield.py       # 6 unit + SDK finding regression tests
├── outputs/
│   ├── live_audit_receipt.json     # SHA-256 attested live run receipt
│   └── security_audit_report.html  # Rendered interactive HTML report
└── docs/
    └── cortensor_prompt_shield_demo.mp4
```

---

## License

MIT — built from scratch for **Cortensor Hackathon #5**.
