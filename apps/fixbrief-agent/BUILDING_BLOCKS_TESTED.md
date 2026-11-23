# Building Blocks Tested — FixBrief on OpenMinion 0.1.24

Environment: Linux x86_64, Python 3.12, `openminion==0.1.24` (PyPI),
project-local `OPENMINION_HOME`. Providers exercised: `echo` (SDK demo
provider) and `openai` pointed at a local llama.cpp server
(`llama-cpp-python` 0.3.37, Qwen2.5-1.5B-Instruct GGUF Q4_K_M,
127.0.0.1:8000, no credentials, no paid services).

## Real model-backed runs (receipts in `outputs/`)

- **Forced-tool probe** (SDK example pattern): `tool_calls=1`,
  6 LLM calls, 14,859 input tokens — forced tool executed and its
  result used in the reply. Log: `outputs/probe-llama.log`.
- **Tool-grounded followup turns** (the demo centerpiece):
  standalone run `88705059891b4ccebf89edf71a898365` (5 LLM calls,
  1 tool call, 0 errors, 11,997 in / 427 out tokens, 465.9 s;
  transcript in `outputs/model_followup_success.txt`), and the
  recorded demo runs `026e7fbb6edb4a63ad7b5af3176038a2` (7 LLM calls,
  2 tool calls — Spanish summary from tool facts) +
  `ae06deaf9a8d4b5ba96e9d16815339ac` (session-continuity answer).
  Latest receipt: `outputs/live_model_run_receipt.json`. Language
  note: the 1.5B model answered in English once and in imperfect
  Spanish once — content stayed grounded in the tool facts;
  instruction-following is the limit at this model size.
- **Typed-output brief turns** (`output_type=RepairBrief`) did not
  complete on this hardware: one turn returned prose instead of JSON
  (correctly rejected, exit 2), one picked the write tool and hit the
  approval denial (exit 2), and a full attempt hit
  `TurnTimeoutError` at 2400 s (exit 3). The code path is identical
  for hosted/stronger models; the 1.5B CPU model is the bottleneck
  (finding 11). Structured briefs in the demo come from the labeled
  deterministic path (`generated_by="deterministic-fallback"`).

## What was tested

| Building block | How FixBrief uses it | Result |
|---|---|---|
| Python SDK install | `pip install openminion==0.1.24` | ✅ Works (see rough edge 1) |
| `config init` | `openminion config init --provider echo/ollama` into project-local home | ✅ Works; `Agent(config_path=...)` picks it up |
| Decorated tools (`@tool`) | 2× `READ_ONLY` + 1 bare write tool, run-scoped | ✅ Works; functions stay plain callables (unit-testable) |
| `forced_tools` | `forced_tools=["get_source_facts"]` | ⚠️ No-op under `echo` (finding 2); ✅ verified with real model (`tool_calls=1` in receipts) |
| Typed output (`output_type`) | `output_type=RepairBrief` (pydantic) | ✅ Correctly rejects echo replies with `AgentOutputValidationError` |
| Sessions | `session_id` + follow-up turn | ✅ Session/run IDs returned in `AgentRunResult` |
| Approval callback | Write tool gated by `approval_callback(tool, args, id) -> bool` | ✅ Signature confirmed in SDK source; `READ_ONLY` tools skip prompts under default policy |
| Provider errors | `ProviderError` → CLI exit 1 | ✅ Taxonomy documented in `API_COMPATIBILITY.md`; mapped in CLI |
| Turn timeout | `TurnTimeoutError` → CLI exit 3 | ✅ Mapped in CLI |
| Run receipts | `result.stats` / `result.metadata` → JSON receipt | ✅ Rich metadata (tokens, tool counts, durations) |

## Findings (what worked, what broke, rough edges)

### 1. Install needs a disk-backed temp dir in small-tmpfs containers (environment, not SDK bug)
`pip install openminion` failed with `OSError(28, 'No space left on
device')` when `/tmp` was a 512 MB tmpfs, because pip stages large
wheels (SQLAlchemy, cryptography) there. Setting `TMPDIR` and
`PIP_CACHE_DIR` to a workspace path fixed it. Worth a one-line note in
the install docs for container/CI users.

### 2. `echo` + `forced_tools` executes zero tools
With the echo provider, `agent.run(...)` returned
`stats={'tool_calls': 0, ...}` even with `forced_tools=["lookup_order"]`
— echo just echoes the prompt. This is consistent with the docs
("demo mode does not call a model"), but it means **forced-tool
verification is impossible in demo mode**. A test double that actually
invokes forced tools with canned args would make SDK wiring testable
without a model. FixBrief's test suite asserts the honest failure
instead: echo + `output_type` raises `AgentOutputValidationError`
(exit code 2), so echo output can never be mistaken for a model brief.

### 3. Ollama default timeout (60 s) is too low for CPU inference
The generated `agents.json` sets `providers.ollama.timeout_seconds=60`.
On CPU-only hardware a 1.5B model needs longer for multi-step tool
loops. FixBrief patches it to 300 s in its project config. Consider
raising the Ollama default or documenting the knob next to the provider
setup flow.

### 4. Decorated tools remain directly callable — excellent for testing
`@tool(...)` returns the original function, so tool logic can be unit
tested without booting the runtime (`get_source_facts("sample", ...)`
in pytest). This is a genuine strength of the 0.1 SDK surface.

### 5. Structured-output compatibility helps weak models
Per `API_COMPATIBILITY.md`, one schema-valid JSON object wrapped in
provider prose is accepted during 0.1.x. That tolerance is what makes
typed output viable with small local models that add chatter around
JSON. FixBrief relies on it (and still validates with pydantic).

### 6. Sandbox proxy env breaks httpx twice (environment findings, worked around)
Two real failures hit during development in a proxied sandbox:
(a) `NO_PROXY` containing bracketed IPv6 (`[::1]`) makes httpx raise
`InvalidURL: Invalid port: ':1]'` when building proxy patterns — this
would break any httpx-based provider call. FixBrief strips bracketed
entries (`normalize_no_proxy`) before SDK runs. (b) A TLS-intercepting
egress proxy signs with a local CA present in the system bundle /
`SSL_CERT_FILE` but not in certifi, so default httpx verification
fails with `CERTIFICATE_VERIFY_FAILED`. FixBrief's fetcher prefers
`SSL_CERT_FILE`/system bundle. Builders behind corporate proxies will
hit both; the SDK could normalize these once in its HTTP layer.

### 7. `config init` silently keeps the old provider without `--force`
Re-running `openminion config init --provider openai` over an existing
echo config exits 0 but leaves `provider: echo` in place — our first
"model" run actually hit echo and failed validation (exit 2, honest
but confusing). FixBrief now passes `--force` on provider switches
(regression-tested). Also note: `config init --provider` accepts fewer
names than `setup --list-providers` (no `cortensor-portal`; use
`cortensor` then patch the agent provider field).

### 8. Turn budget: `Agent.run(timeout_seconds=...)` does not override the 300 s brain cap
With a local CPU model (~5 tok/s), a forced-tool turn needed >300 s
(6 LLM calls, 14,859 input tokens, tool executed correctly) and
returned `Stopped: turn time limit reached (300s/300s)` despite
`timeout_seconds=850`. The cap lives in
`runtime.brain_turn_timeout_seconds` (default 300). FixBrief raises
brain/chat/gateway budgets to 2400 s in its project config. Document
which timeout wins — builders on local models will hit this first.

### 9. llama.cpp servers: context size and `json_schema` gaps
(a) OpenMinion turn prompts are ~2,700–3,000 tokens before any tool
results, so `llama_cpp.server --n_ctx 2048` fails every turn with
HTTP 400 ("requested 2710 tokens"). Use `--n_ctx 8192` or larger.
(b) `llama-cpp-python` 0.3.37's server rejects
`response_format.type=json_schema` (only `text`/`json_object`).
OpenMinion's typed output still works because validation happens
client-side (`model_validate_json` on reply text, with prose-wrapped
JSON tolerance) — no server-side schema enforcement required.
(c) Memory capture (on by default) adds structured-output LLM calls
per turn; against llama.cpp these produced GBNF grammar requests
(`failed to parse grammar` in server logs) and extra minutes of CPU
time. FixBrief disables memory capture for its bounded workflow;
sessions still persist via storage.

### 10. Approval denial can end a typed-output turn with non-JSON text
With a 1.5B local model, the agent chose the approval-gated write tool
(`save_brief_markdown`) as its final action instead of returning the
brief JSON. The callback denied it, and the turn ended with
`Confirmation denied. The action was not run.` — which then failed
`output_type` validation (our exit code 2). Two lessons: (a) with weak
models, keep write tools out of the toolset unless the turn needs
them, or instruct explicitly against them; (b) a denied approval
mid-turn is a terminal outcome, not a recoverable tool error the model
can route around. FixBrief now instructs against the write tool
unless asked, and the recorded demo runs with `--yes` so the gate is
exercised on the allow path (see receipt `approval_log`).

### 11. Full brief turns on a 1.5B CPU model exceed even a 2400 s budget
Measured locally (Qwen2.5-1.5B Q4_K_M via llama.cpp, ~5–10 tok/s
generation, ~30 tok/s prompt eval): a forced-tool probe turn took
~7 min (6 LLM calls, 14,859 input tokens, tool executed correctly).
A full typed-output brief turn made 17+ LLM calls with ~3k-token
prompts and hit `TurnTimeoutError` at 2400 s (correctly mapped to our
exit code 3). The multi-phase brain loop (decide/plan/tool/closure)
multiplies prompt-eval cost on slow local hardware. Mitigations that
helped: warm prefix cache, memory capture off, schema-in-prompt.
Builders targeting local models need either a faster model, a larger
turn budget, or a leaner turn path — worth a "local model" profile in
the docs with realistic token/time expectations.

### 12. Approval callback contract is discoverable only in source
The callback signature `(tool_name, args, approval_id) -> bool` is not
in the PyPI README examples; it was confirmed in
`openminion/api/agent.py`. A 5-line example in `examples/sdk/` would
save every builder this archaeology. FixBrief denies the write tool by
default and only allows `save_brief_markdown` with `--yes`.

## Reproduce

```bash
.venv/bin/python -m pytest tests/ -q          # 25 offline tests
.venv/bin/fixbrief setup --provider echo      # credential-free config
.venv/bin/fixbrief brief --device "Samsung Galaxy A54" \
  --symptom "not charging" --sample samsung-not-charging.md \
  --provider echo                             # exits 2 (validation), by design
.venv/bin/fixbrief setup --provider ollama --model qwen2.5:1.5b
.venv/bin/fixbrief brief --device "Samsung Galaxy A54" \
  --symptom "not charging" --sample samsung-not-charging.md --lang es
cat outputs/live_model_run_receipt.json       # provider/model/session/stats
```
