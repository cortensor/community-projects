# Cortensor Hackathon #5: OpenMinion 0.1 SDK Developer Report
## What worked, what broke, and what I would change

**Hackathon**: [Cortensor Hackathon #5 on DoraHacks (ID: 2418)](https://dorahacks.io/hackathon/2418/detail)  
**Project**: Cortensor Task Sentinel  
**SDK evaluated**: `openminion` v0.1.20 (original 20-run batch) and verified against `openminion` v0.1.24 on PyPI (Python 3.13, Ubuntu Linux)  
**Models used for live runs**: Live Cortensor Portal (`https://api.cortensor.app/v1`) models `oss-20b` (end-to-end completion) and `gemma4` (tool-call probe + SQLite phase telemetry), plus `oss-120b` and `qwen` probes, alongside local `gpt-oss:20b-cloud` (Ollama, OpenAI-compatible endpoint) and `gemma4-it-e4b` (Lemonade) for earlier batches  
**Author**: Mike Anderson (`github.com/manderson240`), solo builder  

Every number below comes from a run I recorded. Raw data is in the repo:
`docs/live_run_capture.jsonl` (the run shown in the video), `docs/live_reliability.json`
(repeated runs after the verdict fix) and `docs/live_reliability_before_verdict_fix.json`
(the runs that exposed the rewrite problem in section 3A).

---

## 1. Summary

Cortensor Task Sentinel checks code that miners submit to a Cortensor subnet. An `openminion.Agent`
backed by a real model receives the task and decides which tools to call: an AST safety audit, a
time-limited test run, and an HMAC-signed receipt. The verdict is computed from the tool results on
the submitted code, not from the model's reply.

`uv run sentinel --live` runs one honest and one malicious submission through the agent.

---

## 2. Building Blocks Tested

| Building block | How I used it | Result |
|---|---|---|
| `Agent(...)` + `agent.run()` | One agent turn per verification task, `timeout_seconds=400` | Works once configured; see 3B and 3C for the configuration traps |
| `@tool` with type hints and docstrings | Four tools, schemas generated from signatures | Works; bare `@tool` defaults block non-interactive use (3D) |
| `@tool(min_scope="READ_ONLY", idempotent=True)` | Declares the tools side-effect free | Fixed the approval block |
| `forced_tools` | Forces `audit_code_safety` as the first call | No measurable reliability change in 20 runs (section 5); does not stop the model choosing bad arguments (3A) |
| Config file (`agents.json`) with the OpenAI-compatible provider | Pointed at Ollama, Lemonade, and live Cortensor Portal (`https://api.cortensor.app/v1`) | Works for local servers; on Portal, default OpenMinion pre-turn overhead hits `600s` timeouts, while disabling `memory_enabled`, `auto_fact_extraction`, and `reflection` with a `900s` turn timeout completed both tasks end-to-end on `oss-20b` (see 3L) |
| Sessions | A fresh `session_id` per task | A session is pinned to the channel it was created on (3C) |
| `AgentRunResult.stats` / `metadata` | Printed LLM calls by purpose and tokens per task | Very useful; one miscount found (3E) |
| `OPENMINION_LLM_DEBUG` | Logged every provider request and response | Essential for diagnosing 3B and 3F |

---

## 3. What broke

### A. The model chooses tool arguments, so "the tools decide" is not automatically true
- In my first reliability batch (5 runs per setting), one malicious run was **certified**. In the
  next batch, 5 of 10 exploit runs passed a rewritten program to a tool (section 5). The model
  called `audit_code_safety` on the submission (blocked: `import os`), then called it again on a
  rewritten version without the import, ran `execute_test_case` on the rewrite, and reported
  "Verdict: passed". That run used 20 LLM calls.
- My verdict logic read the *last* audit, so it trusted the rewrite. Fixed in this repo: the verdict
  only counts tool calls made on the submitted program (compared by AST, so reformatting is allowed),
  and a blocked audit is final
  (`live_agent._verdict_from_tools`, regression test `test_live_verdict_rejects_model_rewritten_code`).
- This is not an SDK bug, but the SDK makes it easy to miss. **Suggestion**: a way to bind a tool
  argument to a value fixed by the caller for the turn (for example `Agent(..., bound_args={"code": submission})`),
  so the model can call the tool but cannot change what it inspects.

### B. Minimal config: empty `default_channel` makes every turn fail, even in `warn` mode
- With an agent profile that sets only `provider`, `agent.run()` raised
  `RuntimeError: inbound authenticity denied (reason=invalid_channel, mode=warn)`.
- Cause: the request channel falls back to `agent_profile.default_channel`, which defaults to `""`.
  `evaluate_inbound_authenticity` returns `allowed=False` for an empty channel before it looks at the
  mode, so `mode=warn` still raises.
- Fix on my side: `"default_channel": "console"` in the agent profile.
- **Suggestion**: default `default_channel` to `console` for SDK use, or treat an empty channel as a
  warning in `warn` mode. I checked this against the source (`modules/controlplane/channels/authenticity.py`
  and `base/config/core.py`); I could not search open issues from my environment.

### C. A session id stays bound to its first channel
- After the failed run in 3B, rerunning with the fixed config and the same `session_id` raised
  `ValueError: Session 'try1' belongs to channel '', not 'console'`. The failed turn had already
  persisted the session. I now use a new session id per task.

### D. Bare `@tool` blocks non-interactive runs on an approval prompt
- With plain `@tool`, a pure function was classified `Risk: write`, `Reversibility: unknown`.
  `agent.run()` did not raise; it returned the policy prompt ("Policy confirmation required ... Reply
  exactly yes or allow_once ...") as the agent's final text, and no tool ran.
- Fix: `@tool(min_scope="READ_ONLY", idempotent=True)`.
- **Suggestion**: when there is no approval callback, raise a typed error (or put a flag in
  `AgentRunResult`) instead of returning the prompt as the answer.

### E. A tool returning a dataclass fails the turn, and the stats miss it
- A tool returning a `@dataclass(slots=True)` ran (I logged it), but the agent's reply was
  `State machine error: RUNTIME_ERROR: Object of type Res is not JSON serializable`, and
  `result.stats` reported `tool_calls: 0, tool_errors: 0`.
- **Suggestion**: convert dataclasses and Pydantic models with `asdict()` / `model_dump()`, and count
  the call and the error in stats.

### F. One verification costs many model calls
- Recorded per-task metadata (`llm_call_counts_by_purpose`) for a single forced tool sequence on
  `gpt-oss:20b-cloud`: typically `entry 1, freshness_classify 2, act 3, judge 1, reflect 1`, about 8 to
  10 calls and roughly 20,000 input tokens. Across 20 recorded tasks the range was 4 to 18 calls
  (section 5).
- The two `freshness_classify` calls ran on every task, though nothing in these tasks depends on
  fresh information. On a slow local model this matters: on `gemma4-it-e4b` one forced tool call took
  7 LLM calls and 90 s wall time.
- **Suggestion**: a documented switch to skip freshness classification, judge and reflect for simple
  tool turns.

### G. Default turn timeout is short for local models
- The default turn timeout is 90 s. My first local run timed out at exactly 90.00 s while still
  working. Passing `timeout_seconds` to `run()` fixed it.

### G2. `forced_tools` does not guarantee the forced call
- With `forced_tools=["audit_code_safety"]`, 2 of 20 recorded turns ended with no tool call at all.
  One replied "I could not safely update the task conditions"; in a demo capture another replied
  "The function `solution(10)` correctly returns `55`" without running anything. Without forcing, 2 of
  20 turns also skipped tools.
- **Suggestion**: if a forced tool was not called, raise or mark the result, so callers do not have
  to detect it themselves.

### H. Runtime state written into the current directory
- Running with `config_path` created a 6.6 MB `.openminion/` directory in the working directory
  (task, memory, browser-playwright, policy, identity, storage and more), even though the config file
  lived elsewhere. Easy to commit by accident; I added it to `.gitignore`.

### I. Desktop dependencies on headless nodes
- `openminion==0.1.20` pulls in terminal and desktop packages (`prompt-toolkit`, `send2trash`,
  `wcwidth`, `sophiagraph`) on a headless validator node.

### J. Circular import between `modules.tool.executor` and `modules.tool.registry` (fixed upstream PR)
- `from openminion.modules.tool.executor import ToolExecutionBatch` failed with a circular-import
  `ImportError`: `executor.py` imports `ToolSpec` from `registry.catalog` at module level, and
  `registry/__init__.py` imports names back from `executor.py`. Confirmed still present on PyPI `openminion==0.1.24`.
- Bug report: [openminion/openminion#733](https://github.com/openminion/openminion/issues/733)
- Fix PR: [openminion/openminion#734](https://github.com/openminion/openminion/pull/734). It defers the
  `ToolSpec` import and adds an isolated-import regression test (rebased onto `dev` `0c99b454`
  at `d8162d73`, addressing maintainer readability and `CHANGELOG.md` `Unreleased` review
  feedback; 561 critical-path tests, ruff, and mypy type checks pass with it).
- The maintainer accepted the source fix on 2026-11-26 after independent review. The PR now waits on
  their hosted macOS checks, and #733 stays open until a published release carries the fix.
- Follow-up issues filed upstream from these findings, each with a minimal repro on current `dev` `0c99b454`: [#887](https://github.com/openminion/openminion/issues/887) (a `@tool` returning a dataclass or Pydantic model fails the turn while stats report 0 tool calls, finding 3E), [#888](https://github.com/openminion/openminion/issues/888) (opt-in HTTP retry for Cortensor Portal, since `runtime.provider_retry_max_attempts` is ignored there, finding 3L) and [#889](https://github.com/openminion/openminion/issues/889) (transcript recovery after a turn timeout hits a closed SQLite connection, finding 3L).

### K. OpenMinion 0.1.24 Re-Verification (2026-11-24 UTC)
- Upgraded `pyproject.toml` and `uv.lock` to PyPI `openminion==0.1.24`. All 21 offline tests in `tests/test_validator.py` pass unchanged.
- Earlier `0.1.24` smoke runs with `gpt-oss:20b-cloud` still reproduced finding 3G2 (4-call skipped workflow with 0 tool calls) and finding 3A (model rewriting an `os.system` exploit before auditing it), both rejected fail-closed by `_verdict_from_tools`.
- Clean paired `0.1.24` receipt saved at `outputs/live_model_run_receipt.json`: honest Fibonacci certified in 10 LLM calls (24.7 s), `os.system` exploit blocked in 9 LLM calls (34.9 s).

### L. Cortensor Portal Live Evaluation (2026-11-24 UTC)
- Tested `https://api.cortensor.app/v1` with a live `CORTENSOR_API_KEY` on `openminion==0.1.24` and saved the telemetry receipt at `outputs/cortensor_portal_run_receipt.json`. `GET /v1/models` returned HTTP 200 with 4 models: `gemma4`, `oss-120b`, `oss-20b`, and `qwen`.
- Direct `/v1/chat/completions` tool-call probes (45 s timeout, offering `audit_code_safety`):
  - `gemma4`: HTTP 200, returned `finish_reason: "tool_calls"` calling `audit_code_safety({"code": "def f(): pass"})`.
  - `oss-20b`: HTTP 200, returned `finish_reason: "tool_calls"` calling `audit_code_safety({"code": "def f(): pass"})` (a 16-token short chat probe completed in 22.58 s with `system_fingerprint: "fp_ollama"`).
  - `qwen`: timed out after 45.0 s with 0 bytes received.
  - `oss-120b`: returned HTTP 502 `router_error` (`"Router pool returned an error."`) in 3.26 s.
- Full OpenMinion `0.1.24` Portal sentinel runs hit per-turn timeout ceilings at both `240s` (`oss-20b` timed out at `240.4s` / `240.26s`; `oss-120b` returned HTTP 502 in `6.22s` / `6.61s`) and `600s` (`oss-20b` failed with HTTP 500 `Router V4 request failed before model completion.` at `260.0s` on `task-fibonacci-10` and `TurnTimeoutError` at `600.25s` on `task-exploit-attempt`; `gemma4` timed out at `600.09s` and `600.08s`).
- **Root Cause from SQLite Telemetry (`gemma4`, 600s run)**:
  - On `task-fibonacci-10`, OpenMinion spent `226.7s` (`+0.03s` to `+226.72s`) in `brain.auto_fact_extraction` (`purpose: "reflect"`) before entering the turn, then `91.9s` (`+226.73s` to `+318.59s`) in `entry` and `95.4s` (`+318.59s` to `+413.98s`) in `freshness_classify`. That totaled `414.0s` of internal preflight calls before the first Sentinel tool ran. Portal `gemma4` then executed `audit_code_safety` cleanly at `+414.02s` and `execute_test_case` cleanly at `+488.19s` before `CancelledError` stopped the turn at `600.00s` ahead of `create_attestation_receipt`, `judge`, and `reflect`.
  - On `task-exploit-attempt`, `gemma4` spent `64.6s` in `auto_fact_extraction`, `83.4s` in `entry`, and `94.0s` in `freshness_classify`, executed `audit_code_safety` at `+242.05s` into the turn and finished `act` at `+358.79s`, then timed out at `600.08s`.
  - On turn cancellation, OpenMinion `0.1.24` also logged `WARNING openminion.modules.brain.loop.tools.transcript: event=brain.tool_transcript.recovery_failed ... closed=0 error_type=ProgrammingError`.
- **Resolution with Lean Config and End-to-End Portal Completion (`oss-20b`, 2026-11-24 UTC)**:
  - OpenMinion `0.1.24` accepts `runtime.memory_enabled: false`, `runtime.brain_turn_timeout_seconds: 900`, `runtime.chat_turn_timeout_seconds: 900`, `brain.auto_fact_extraction.enabled: false`, `brain.reflection.enabled: false`, and `brain.adaptive_budget.idle_timeout_s: 900` inside `agents.json`. That dropped pre-turn `auto_fact_extraction` to a `0.39s` skip (`disabled`).
  - Keeping `agents.sentinel.thinking` at default proved necessary: setting `thinking: "off"` caused `gemma4` to drop OpenMinion's hidden `task_update` argument in `entry` (`invalid_task_context_update`, `165.6s` and `204.7s`).
  - OpenMinion intentionally disables HTTP retries when the resolved vendor is Cortensor (`cortensor_portal_no_idempotency`), so two earlier `oss-20b` attempts stopped in `decide` when the decentralized miner pool emitted an HTTP 502 unadvertised function or malformed tool arguments (`task-fibonacci-10` succeeded on attempt 1 in `5` LLM calls / `655.7s`, and another `task-fibonacci-10` call failed on `decide`). `sentinel.py` now wraps `run_live_task` in up to 3 bounded retries for Portal runs because Sentinel's tools are read-only and idempotent.
  - With that config (`write_agent_config("portal", ...)` and `900s` turn timeout), live Cortensor Portal (`oss-20b`) completed both verification tasks on the first attempt with zero retries (`docs/live_run_capture.jsonl`, `outputs/cortensor_portal_run_receipt.json`):
    - `task-fibonacci-10`: `CERTIFIED (test passed (output 55))` via `audit_code_safety` (`+214.0s`), `execute_test_case` (`+281.4s`), and `create_attestation_receipt` (`+368.7s`), `6` LLM calls (`{'act': 5, 'entry': 1}`), `19,253` in / `1,760` out tokens, `722.6s` wall time.
    - `task-exploit-attempt`: `REJECTED (audit blocked: Forbidden import: 'os')` via `audit_code_safety` (`+226.7s`, blocked), `execute_test_case` (`+276.8s`, blocked), and `create_attestation_receipt` (`+337.7s`), `5` LLM calls (`{'act': 4, 'entry': 1}`), `15,998` in / `1,711` out tokens, `651.6s` wall time.
- **Suggestions for OpenMinion**:
  1. Expose a first-class low-overhead mode for high-latency decentralized routers like Cortensor Portal (~20 to 90 s per completion call) and document the working `brain` / `runtime` flags.
  2. Guard or close the SQLite handle ordering in `brain.tool_transcript` recovery so timed-out turns do not raise `ProgrammingError` on closed connections.

---

## 4. What I Learned

1. **Bind what the model inspects.** Letting the model orchestrate tools is useful, but security
   checks need their inputs fixed by the caller. A `bound_args`-style option would make this the
   default (3A).
2. **Make the minimal config work.** `{"provider": ...}` alone should produce a working agent;
   today it needs `default_channel` (3B) and `READ_ONLY` scopes (3D), and failures surface as an
   exception in one case and as a normal-looking answer in the other.
3. **Fail loudly in non-interactive runs.** An approval prompt or a serialization error returned as
   `result.text` looks like a successful answer to calling code (3D, 3E).
4. **Let simple turns be cheap.** Classifier, judge and reflect calls on every turn roughly triple
   the model calls for a three-tool workflow (3F).
5. **Keep a headless core.** Split `openminion-core` (Agent, tool, runtime) from the CLI dependencies (3I).
6. **Stats and the debug log are the best part.** Per-purpose call counts and `OPENMINION_LLM_DEBUG`
   made every problem above diagnosable within minutes.

---

## 5. Reliability

Model `gpt-oss:20b-cloud`, 5 runs of each task with and without `forced_tools`, recorded
2026-11-20. Every row, including the code the model passed to each tool, is in
`docs/live_reliability.json`.

**Current code** (AST-based guard, 20 agent turns):

| Setting | Honest task certified | Exploit rejected |
|---|---|---|
| audit forced | 4 / 5 | 5 / 5 |
| model chooses freely | 5 / 5 | 5 / 5 |

- **Rewrites.** In 5 of the 10 exploit runs the model passed a rewritten program to a tool:
  `def solution(n: int) -> int: return n`, with the `os` import and the `os.system` call removed. The
  guard from 3A rejected all 5. In one of them the model's reply was "The solution passed both the
  safety audit and the test".
- **Reformatting.** In 6 runs the model passed the submission with only formatting changes (an added
  blank line, no trailing newline). The guard compares ASTs, so these count as the submission. My
  first version compared text and wrongly flagged them as rewrites; the AST comparison fixed that.
- **Skipped workflow.** The one honest miss: no tool call, and the reply "I could not safely update the
  task conditions. Please restate the current task and its required conditions." This comes from the
  SDK's internal task-condition step (4 LLM calls, no `act` call). The run failed closed.
- **Cost.** 4 to 18 LLM calls per task (median 9.5) and 13 s to 82 s wall time per task.

**Before the guard** (`docs/live_reliability_before_verdict_fix.json`, same design): 1 of 10 exploit
runs was **certified** (section 3A) and 1 of 10 honest runs hit the same task-condition reply.

Across both batches `forced_tools` made no measurable difference to the honest task (9 / 10 with,
9 / 10 without). Five runs per cell is small; treat these as rough rates.

---

## 6. Code

- Live run: `SENTINEL_MODEL=<model> uv run sentinel --live` (see README)
- Agent and tools: [`src/cortensor_validator/openminion_agent.py`](../src/cortensor_validator/openminion_agent.py)
- Live agent run and verdict: [`src/cortensor_validator/live_agent.py`](../src/cortensor_validator/live_agent.py)
- CLI: [`src/cortensor_validator/sentinel.py`](../src/cortensor_validator/sentinel.py)
- Tests: [`tests/test_validator.py`](../tests/test_validator.py)
- Demo recorder: [`scripts/record_live_demo.py`](../scripts/record_live_demo.py)
