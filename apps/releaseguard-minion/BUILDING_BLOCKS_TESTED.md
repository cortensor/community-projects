# Building Blocks Tested — OpenMinion `0.1.24` & Cortensor Integration

All tests, telemetry captures, and bug reproducers below were executed first-hand against **`openminion==0.1.24`** (upstream `main` commit `9204d66`, `dev` commit `105b0bf`) on Python `3.12.3`.

---

## 1. Cortensor & OpenMinion Provider / Transport Surface Tested

We inspected and verified OpenMinion's provider factory (`src/openminion/modules/llm/providers/factory.py:28-40`) and setup preset catalog (`openminion setup --list-providers --json`, `setup_catalog.py:55-301`):

| Integration Surface | Exact Endpoint / Adapter | How Tested | Observed Behavior |
|---|---|---|---|
| **Cortensor Portal preset (`cortensor-portal`)** | `https://api.cortensor.app/v1` (`adapter="openai"`, default model `oss-20b`, env `CORTENSOR_API_KEY`) | `openminion setup --list-providers --json` + OpenAI-compatible HTTP transport exercised via `providers.openai.base_url` | Uses OpenMinion's real `openai` adapter (`httpx` + `llmctl` chat completions + function tool-calling loop). Cleanest path for structured JSON + tool calling. |
| **Cortensor Router preset (`cortensor-router`)** | `http://127.0.0.1:8080/api/v2/completions` (`adapter="cortensor"`) | Preset catalog verification + provider factory inspection (`cortensor` registered alongside `openai`, `anthropic`, `groq`, `openrouter`, `cerebras`, `ollama`, `echo`) | Dedicated `cortensor` runtime adapter registered in `factory.py`; expects local Cortensor Router v2 completions endpoint. |
| **Loopback OpenAI-compatible transport** | `http://127.0.0.1:<ephemeral>/v1/chat/completions` (`providers.openai`) | `tests/conftest.py` (`LocalOpenAIServer`) driving real `openminion==0.1.24` `APIRuntime` + `Agent` + `httpx` | Exercises 100% of OpenMinion's brain loop, tool-call parser, action policy engine, SQLite session store, streaming turns, and telemetry with deterministic CI repeatability. |
| **Built-in `echo` provider** | `provider="echo"` | `openminion config init --provider echo` + `openminion run` + `openminion status readiness --json` | Confirms config/SQLite/CLI plumbing (`overall="demo"`, 8 checks, 0 blocked), but does not execute tool calls. |

---

## 2. OpenMinion `0.1.24` Python SDK Building Blocks Matrix

| # | Building Block | Exact SDK Symbols / Schemas Exercised | Verified Result |
|---|---|---|---|
| 1 | **Runtime Lifecycle & Config** | `APIRuntime.from_config_path(config_path, logging_mode="interactive")`, `close()`, `OpenMinionConfig` | Boots isolated `.openminion/agents.json` + SQLite DB cleanly once `default_channel: "console"` is explicitly set (see Bug #4). |
| 2 | **Agent Execution & Typed Output** | `Agent(name=..., runtime=..., agent_id=..., instructions=..., tools=..., forced_tools=["inspect_repo_manifest"], output_type=ReleaseAuditReport, session_id=...)` | End-to-end tool loop + Pydantic v2 validation succeeded (`score=94/100` on self-audit, `96/100` on fixture repo, `tool_calls=4`, `tool_errors=0`, `duration_ms=588ms`). Collides with raw-tool-markup heuristics if output model contains `status`+`summary` (Bug #1) and crashes on policy pause/denial (Bug #2). |
| 3 | **Risk-Tiered `@tool` Contracts** | `@tool(name=..., min_scope="READ_ONLY", idempotent=True)` (`inspect_repo_manifest`, `inspect_ci_and_tests`, `scan_secret_hygiene`); `@tool(idempotent=True)` (`write_release_brief`, `WRITE_SAFE`); `@tool(dangerous=True)` (`create_release_tag`) | Clear, enforceable risk taxonomy. Verified via `tool.tool_decl` metadata tests and live policy dispatch: all 3 `READ_ONLY` tools auto-allowed without prompting; write and dangerous tools always routed to policy confirmation. |
| 4 | **Policy Confirmation & Fail-Closed Gate** | `approval_callback(tool_name, args, approval_id) -> bool` implemented by `ReleaseApprovalGate` logging `ApprovalDecisionRecord` | Reliably intercepted `write_release_brief` (allowed once, denied on 2nd attempt: `denied:single_use_brief_write_already_consumed`), denied `create_release_tag` (`denied:dangerous_tag_not_enabled`), and denied unknown tools (`denied_by_default:<tool>`). |
| 5 | **Durable SQLite Sessions** | `session_id="release-guard-<repo-slug>"`, `.openminion/state/openminion.db` | Verified `openminion.db` persisted cleanly (`339,968` bytes, `20` tables, `9` session/turn rows across captured runs). |
| 6 | **Portable Memory** | `openminion.MemoryBundle`, `openminion.modules.memory.portability.save_bundle()`, `load_bundle()` | Clean `memory_bundle.v1` JSON export and reload round-trip preserving audit verdict, score, blockers, `session_id`, and `run_id`. |
| 7 | **Bounded Subagent Delegation** | `openminion.subagent(parent, name="secret-reviewer", instructions=..., tools=[scan_secret_hygiene], timeout_seconds=60)` | Tool allowlist and timeout enforcement work once `reviewer.agent_id = parent.agent_id` is manually re-attached; without workaround, silently drops `parent.agent_id` (Bug #3). |
| 8 | **Typed Streaming Turns** | `APIRuntime.submit_turn(payload={...})` -> `RuntimeTurnHandle.stream()` (`TurnChunk`) + `handle.result(timeout_s=30.0)` (`TurnResponse`) | Delivered `12` typed `TurnChunk` events (`11 status`, `1 final_text`) with structured `result.stats` telemetry. |
| 9 | **Runtime Diagnostics & CLI** | `runtime_posture()`, `capability_report()`, `runtime_self_model()`, `tool_inventory_report()` (`106` tools); CLI `openminion doctor --check-turn --json`, `status readiness --json`, `tools list` | Rich runtime introspection; CLI piping hit `BrokenPipeError` (Bug #5a / `#881`) and `doctor --json` emitted `9,703` bytes of `INFO` logs to stderr (Bug #5b / `#882`). |

---

## 3. Verified Upstream Bugs Found in `openminion/openminion` (`0.1.24`)

Before filing, we audited existing `openminion/openminion` issues and PRs to ensure zero duplicates:
- Bugs **#1, #2, #5a, #5b** were completely original, verified on both `main` (`9204d66`) and `dev` (`105b0bf`), and filed as **4 upstream issues (`#881–#884`)** plus **2 surgical upstream bug-fix PRs (`#885`, `#886`)**.
- Bugs **#3** (`subagent` drops `agent_id`) and **#4** (`default_channel` omitted) were independently reproduced in our test suite and matched existing open community PRs (`#732` and `#874`/`#864`), so we did not file duplicate issues.

### Summary Table

| ID | Severity | Root Cause (`openminion` source) | Upstream Issue | Upstream Fix PR | Local Reproducer |
|---|---|---|---|---|---|
| **#5a** | Medium | `src/openminion/cli/main.py:319-320, 382-420` | [#881](https://github.com/openminion/openminion/issues/881) | **[#885](https://github.com/openminion/openminion/pull/885)** (`36/36` tests PASS) | `openminion tools list \| head -n 5` |
| **#5b** | Medium | `src/openminion/cli/commands/doctor.py:194-199`, `src/openminion/base/logging.py:23-30, 129-132` | [#882](https://github.com/openminion/openminion/issues/882) | **[#886](https://github.com/openminion/openminion/pull/886)** (`29/29` tests PASS) | `openminion doctor --check-turn --json` |
| **#2** | High | `src/openminion/api/agent.py:362-382` (line `370`) | [#883](https://github.com/openminion/openminion/issues/883) | Design proposed in issue | `pytest -v tests/test_openminion_findings.py -k test_finding_2` |
| **#1** | High | `src/openminion/modules/brain/loop/tools/postprocess/rules.py:110-135`, `no_tool.py:487-522` | [#884](https://github.com/openminion/openminion/issues/884) | Design proposed in issue | `pytest -v tests/test_openminion_findings.py -k test_finding_1` |
| **#3** | High | `src/openminion/api/handoff.py:299-307` | *(existing upstream PR)* | [#732](https://github.com/openminion/openminion/pull/732) *(community PR)* | `pytest -v tests/test_openminion_findings.py -k test_finding_3` |
| **#4** | Medium | `src/openminion/base/config/core.py:124`, `parser/profiles.py:77` | [#874](https://github.com/openminion/openminion/issues/874) | [#864](https://github.com/openminion/openminion/pull/864) *(community PR)* | `pytest -v tests/test_openminion_findings.py -k test_finding_4` |

### Detailed Technical Breakdown of Issues `#881–#884`

#### Issue `#881` (Fixed in PR `#885`) — CLI `BrokenPipeError` Treated as Internal Error
- **Exact mechanism:** `BrokenPipeError` subclasses `OSError`, which is inside `_TERMINAL_CLI_ERRORS` in `src/openminion/cli/main.py`. Piping CLI output (`openminion tools list | head -n 5` or `openminion doctor --json | head -n 5`) triggers `_unexpected_error_exit()`, prints `openminion: internal error: BrokenPipeError: [Errno 32] Broken pipe`, and exits `1` (or raises an uncaught teardown flush error on stderr).
- **Fix landed in PR `#885`:** Catch `BrokenPipeError` before `_TERMINAL_CLI_ERRORS`, redirect stdout fd to `os.devnull` when `owns_process=True`, and exit `0` with zero stderr noise (`36/36` CLI tests + all repo validators passing).

#### Issue `#882` (Fixed in PR `#886`) — `openminion doctor --json` Emits `INFO` Bootstrap & Alembic Logs to `stderr`
- **Exact mechanism:** `_run_runtime_bootstrap_probe()` in `src/openminion/cli/commands/doctor.py:194-199` invokes `APIRuntime.from_config_path(...)` with default `logging_mode="default"`, causing ~`9.7 KB` of unfiltered `INFO` startup and Alembic migration logs to leak onto `stderr` even when `--json` is passed for machine consumption.
- **Fix landed in PR `#886`:** Pass `logging_mode="interactive" if getattr(args, "json", False) else "default"` to reuse OpenMinion's existing `apply_logging_mode("interactive")` clamping (`29/29` doctor tests + subprocess stdout-JSON / empty-stderr test passing).

#### Issue `#883` — `Agent(output_type=BaseModel)` Crashes on Policy Confirmation Pause & Denial
- **Exact mechanism:** In `src/openminion/api/agent.py:370`, `Agent._run_once()` unconditionally executes `output = self._coerce_output(reply_text)`. When a policy-gated tool triggers either:
  1. Pause-and-resume confirmation (`metadata["respond_kind"] == "policy_confirmation_prompt"`, body `"Policy confirmation required..."`), or
  2. Callback denial (`"Confirmation denied. The action was not run."`),
  OpenMinion raises `AgentOutputValidationError`, discarding `AgentRunResult` and making `result.thread_id` unreachable so callers cannot resume the confirmation workflow documented in `docs/runtime-surfaces.md:107-120`.

#### Issue `#884` — Raw Tool-Payload Heuristic Misclassifies Valid Structured JSON (`status` + `summary`)
- **Exact mechanism:** `_looks_like_unexecutable_tool_payload_text()` in `src/openminion/modules/brain/loop/tools/postprocess/rules.py:110-135` classifies **any** JSON object containing `"status"` + `"summary"` (or `"ok"` + `"summary"`) as raw tool-result markup. After any successful tool call, `_repair_raw_tool_payload_final_text()` in `no_tool.py:487-522` discards the model's valid Pydantic JSON response, prompts for plain text, exhausts retries, and overwrites the reply with `"result: the model emitted raw tool markup after successful tool results..."`.
- **Workaround in ReleaseGuard Minion:** `ReleaseAuditReport` intentionally names its fields `verdict` and `rationale` instead of `status` and `summary` (documented in `src/release_guard_minion/models.py:21-24`).

### Additional Low-Severity Friction Observed

- **`<agent_id>: ` prefix on programmatic SDK replies (`src/openminion/api/agent.py:259-274`):** `Agent.run()` prefixes `<agent_id>: ` onto `result.text` (e.g., `auditor: {"verdict": "ready", ...}`). Strict `model_validate_json(text)` fails on the first pass and succeeds only because of OpenMinion `0.1.x`'s temporary `_extract_json_object()` fallback (`API_COMPATIBILITY.md:65-67`). Suppressing the prefix for `deliver=False` programmatic turns would prevent a future breaking regression.
