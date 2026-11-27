# Cortensor Task Sentinel

A subnet task verification agent built with the OpenMinion 0.1 Python SDK (`openminion==0.1.24`) for Cortensor Hackathon #5 (DoraHacks `#2418`).

- **Standalone repository**: https://github.com/manderson240/cortensor-subnet-validator
- **Live demo video (74 s, live Cortensor Portal `oss-20b`)**: https://github.com/manderson240/cortensor-subnet-validator/raw/main/docs/cortensor_live_demo.mp4
- **Upstream OpenMinion fix PR**: https://github.com/openminion/openminion/pull/734 (Issue https://github.com/openminion/openminion/issues/733)

## Overview

In a Cortensor subnet, validators check miner Python submissions before signing receipts. Sending untrusted code straight to a model risks code execution, wasted tokens, and verdict manipulation. Cortensor Task Sentinel gives an `openminion.Agent` three `READ_ONLY` tools (`audit_code_safety`, `execute_test_case`, `create_attestation_receipt`) and derives the final verdict deterministically from tool outputs inspected on the submitted AST. Even if a model rewrites an `os.system` exploit into clean code during its turn, the AST equality guard rejects the run fail-closed.

## Quickstart

```bash
cd apps/cortensor-task-sentinel
uv sync --all-extras
uv run pytest -q

# Live model run (any OpenAI-compatible server; Ollama default http://localhost:11434/v1)
SENTINEL_MODEL=gpt-oss:20b-cloud uv run sentinel --live

# Cortensor Portal preset
CORTENSOR_API_KEY=<key> uv run sentinel --live --provider portal

# Deterministic offline check
uv run sentinel
```

## Verification Receipts

- Local `openminion==0.1.24` paired receipt (`outputs/live_model_run_receipt.json`): honest Fibonacci certified in 10 LLM calls (24.7 s); `os.system` exploit blocked fail-closed in 9 LLM calls (34.9 s) using `gpt-oss:20b-cloud`.
- Live Cortensor Portal `openminion==0.1.24` receipt (`outputs/cortensor_portal_run_receipt.json`): tested `https://api.cortensor.app/v1` across `gemma4`, `oss-20b`, `oss-120b`, and `qwen`. With default settings, `gemma4` hit the 600 s timeout after `414.0 s` of pre-turn reflection/classification overhead. Disabling `memory_enabled`, `auto_fact_extraction`, and `reflection` in `write_agent_config("portal", ...)` with a `900 s` turn timeout allowed live Portal `oss-20b` to complete both tasks end-to-end on the first attempt (`task-fibonacci-10` certified in 6 LLM calls / `722.6 s`; `task-exploit-attempt` rejected in 5 LLM calls / `651.6 s`), and `sentinel.py` adds bounded task retries for transient Portal router errors.
