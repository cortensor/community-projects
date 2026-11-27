# Release Notes: Cortensor Task Sentinel

## v0.1.0 (Cortensor Hackathon #5)

- Upgraded and verified on `openminion==0.1.24` (with `outputs/live_model_run_receipt.json`).
- OpenMinion `Agent` integration (`default_channel="console"`, `forced_tools=["audit_code_safety"]`) with three `READ_ONLY`, idempotent `@tool` callables (`audit_code_safety`, `execute_test_case`, `create_attestation_receipt`).
- Submission AST binding in `_verdict_from_tools()` so model-rewritten code cannot pass an audit or earn a certificate on behalf of an exploit submission.
- Live Cortensor Portal (`https://api.cortensor.app/v1`) evaluation across `oss-20b`, `gemma4`, `oss-120b`, and `qwen` (`outputs/cortensor_portal_run_receipt.json`): added lean Portal runtime config in `write_agent_config("portal", ...)` (disabling `memory_enabled`, `auto_fact_extraction`, and `reflection` with a 900 s turn timeout while keeping default `thinking` for `gemma4`) and bounded Portal task retries in `sentinel.py`; live Portal `oss-20b` completed both tasks end-to-end (`task-fibonacci-10` certified in 6 LLM calls / 722.6 s; `task-exploit-attempt` rejected in 5 LLM calls / 651.6 s), recorded in the 74 s live Portal demo video.
- Miner code runs in a child `python -I -S` process with a hard wall clock kill and `RLIMIT_AS` (512 MB) and `RLIMIT_CPU` limits. An in-process timer was not enough, because a `while True` inside a bare `except:` swallowed the timer exception and hung the validator. The AST audit also refuses frame, generator and `__mro__` style attribute walks, `globals`/`locals`/`vars`, and dunder text in string literals.
- 29 offline unit and regression tests in `tests/test_validator.py`, including the bare `except:` loop and a memory bomb.
- Upstream bug report (`openminion/openminion#733`) and rebased fix PR (`openminion/openminion#734`, rebased onto `dev` `0c99b454` at `d8162d73`) for circular import in `openminion.modules.tool.executor`.
