# Building blocks tested

Version: **openminion 0.1.24** (PyPI wheel, Python 3.12.16, Linux x86_64, single-process runtime)
Project: **Repo Triager** — GitHub issue triage agent with a human approval gate
Date: 2026-11-24

This is the field report the hackathon asks for: what each building block did in a real
workflow, what worked, what did not, and how to reproduce every claim. Every "REPRODUCED"
below comes from a script in `findings/` that a reviewer can run without a credential.

```
python findings/repro_instructions_truncation.py     # finding 1
python findings/repro_structured_output_schema.py    # finding 2
python findings/repro_policy_gate_vs_output_type.py  # finding 3
python findings/repro_session_scope.py               # finding 4
python findings/repro_operator_id_getpwuid.py        # finding 5
python findings/repro_memory_search_truncation.py    # finding 6
python findings/measure_turn_cost.py                 # measurement
```

---

## Summary table

| Block | Used in Repo Triager | Verdict |
| --- | --- | --- |
| Agent execution (`Agent`, `APIRuntime`) | analysis, stage, memory phases | works, with two sharp edges (#1, #3) |
| Tools (`@tool`, risk classification) | 5 read tools, 1 gated write | excellent — the best-designed part of the SDK |
| Permissions / policy (`approval_callback`, pause) | the write gate | works; the callback gets no risk facts |
| Sessions | one session across a batch, `:stage`/`:memory` sub-sessions | works; scope rule is undocumented (#4) |
| Memory (`memory.write`/`memory.search`) | precedents across runs | works; search output is unreadable (#6) |
| Skills (ingest/admit) | triage rubric | works after two steps; CLI breaks on unusual uids (#5) |
| Tasks / scheduling (`task.schedule`, `openminion cron`) | `repo-triager schedule` | contract works; runtime hosting is daemon-only |
| Delegation (`subagent`) | duplicate-scout | works, cheap, isolated session |
| Structured output (`output_type`) | `TriageDecision` | validation works, prompting does not (#2) |
| Diagnostics (`doctor`, capability/posture/self-model) | `repo-triager doctor` | works and is genuinely useful |
| Model providers (OpenAI-compatible, scripted) | scripted + any hosted provider | works; setup demands a credential even for localhost |

---

## 1. Agent execution

**What we did.** One `APIRuntime.from_config_path(...)` per CLI invocation, three `Agent`
turns on that runtime: analysis (read-only), staging (the gated write), memory (a
`memory.write` turn). `runtime.close()` in a `finally`.

**What worked.** The runtime is honest about its own state: `run_state`, `run_id`,
`session_id`, `metadata["llm_calls_count"]`, `metadata["tool_loop_termination_reason"]`
were all populated and correct. `Agent` as a context manager never leaked a runtime in
hundreds of runs. Structured results (`stats`, `metadata`) made the run report possible
without any bookkeeping of our own.

**Finding 1 — instructions are truncated at ~860 characters.**
`Agent(instructions=...)` with 2,599 characters and 30 numbered rules: the model received
rules 01–08 only, the sentinel at the end was absent, and the turn still reported
`completed`. No warning, no metadata flag.

```
$ python findings/repro_instructions_truncation.py
instructions sent : 2599 characters, 30 rules, sentinel at the end
turn state        : completed
rules that reached the model: ['01', '02', '03', '04', '05', '06', '07', '08']
RESULT: REPRODUCED — 8 of 30 rules survived; everything from rule 09 onward was dropped.
```

Impact: silent behaviour loss for any agent with a real system prompt. Upstream report
#811 matches. **Workaround used here:** a < 1,000-character system prompt (role + output
contract) and the rubric/schema in the task message, which is not truncated (we send
3–4 KB task messages).

**Finding 3 — a denied/paused confirmation breaks a structured-output turn.**
`Agent(output_type=Applied)` + a gated tool + `approval_callback → False`: the tool is
correctly blocked, then `_coerce_output` tries to parse the runtime's refusal text as
`Applied` and raises `AgentOutputValidationError`. The caller cannot tell "policy denied"
from "model produced garbage" except by string-matching `exc.raw_text`.

```
$ python findings/repro_policy_gate_vs_output_type.py
raised: AgentOutputValidationError
raw reply text: 'openminion: Confirmation denied. The action was not run.'
tool executed despite the denial: False
RESULT: REPRODUCED
```

Impact: an approval gate and a typed result cannot live in the same turn. **Design used
here:** the gate runs in its own turn with `output_type=None`, which is also the better
product shape (analyse, approve, then stage).

**Smaller observations.**
* `AgentRunResult.text` is prefixed with `openminion: ` for every reply. Harmless because
  the client recovers a balanced JSON object, but it leaks into free-form replies.
* `Agent.run()` on a 3-tool triage turn does not equal one model call (see Measurement).

## 2. Tools

**What we did.** Five read tools (`get_issue`, `list_open_issues`,
`search_duplicate_issues`, `label_taxonomy`, `triage_precheck`) and one write tool
(`stage_triage`). Arguments are plain typed Python; outputs are JSON strings.

**What worked — and worked well.** The risk classification is the clearest contract in the
SDK:

* `@tool(min_scope="READ_ONLY", idempotent=True)` → runs with no prompt, no callback.
* bare `@tool` → local write, unknown reversibility → the runtime asks for confirmation
  before execution.
* the decorator derives the JSON schema from type hints, rejects extra arguments
  (`extra="forbid"`), and validates them before the handler runs.

We never had to write a gate ourselves: declaring the write tool correctly was enough.
Tool errors (a raised exception) come back to the model as a tool result it can react to,
which is what makes the "model proposes, guard validates" loop work.

One papercut: a `@tool` name is exposed to the model with dots replaced by underscores
(`memory.write` → `memory_write`), while `Agent(tools=["memory.write"])` takes the dotted
name. Both spellings appear in one workflow; the CLI documents which is which.

## 3. Permissions and policy

**What we did.** `approval_callback` for `--apply auto|deny|ask`, and the pause flow for
`--apply pause`.

**What worked.** Allow/deny is exact: the write ran only on an explicit allow, and the
`approval_id` let the report tie a decision to a specific call. The **pause prompt is
genuinely good** — it prints risk, side effects, reversibility, reason, and the accepted
answers:

```
Policy confirmation required.
stage_triage
Risk: write
Side effects: local
Reversibility: unknown
Reason: UNKNOWN_REVERSIBILITY
Choices: allow_once, allow_session, deny
```

Resuming with `agent.run("yes", thread_id=result.thread_id)` executed the pending call on
the same thread. (`findings/` finding 3 covers the denial case; the pause test lives in
`tests/test_agent_integration.py::test_pause_flow_uses_the_runtime_confirmation`.)

**Gap.** The callback signature is `(tool_name, args, approval_id)`; the risk facts above
are computed inside the runtime and shown only on the pause path. An application that
uses `approval_callback` (the scriptable path, and the only one usable in CI) must
re-derive risk from the tool name to show the operator *why* a call is being confirmed.
Passing the same facts dict to the callback would make the two paths equivalent.

**Gap.** `approval_callback` returning `False` ends the whole turn, so a per-tool policy
("always allow `memory.write`, ask for `stage_triage`") can only deny everything else.
That forced us to split memory writes into a separate turn.

## 4. Sessions

**What we did.** `session_id="repo-triager:<owner>_<repo>"` for a batch, with `:stage` and
`:memory` sub-sessions per phase. Continuity across issues was real: the follow-up turn
("Continue the active task…") carried the earlier tool results, which is how the scripted
provider maintained its step index.

**Finding 4 — a `/` in a session id silently disables memory.**

```
$ python findings/repro_session_scope.py
scope pattern: ^(session|agent|project|global):[A-Za-z0-9._:-]+$
'session:repo-triager:openminion_openminion'     valid: True
'session:repo-triager:openminion/openminion'     valid: False
turn with session_id 'repo-triager:openminion/openminion' -> completed
```

The memory layer builds `session:<id>` and rejects it; the warning goes to the log
(`memory.build_context_with_metadata failed … invalid scope`), the turn completes, and the
agent runs without its memory capsule. A repository slug is the most natural session id
in this domain, so this is easy to hit. **Workaround:** slugify the session id (we do).
A validator on `Agent(session_id=...)` — or accepting a sanitised scope — would remove a
whole class of silent failures.

## 5. Memory

**What we did.** Phase 3 stores each applied decision with `memory.write`
(`record_type=decision`, key `triage:<repo>:<issue>`); the analysis turn offers
`memory.search` so later runs can recall it.

**What worked.** Cross-run recall is real: after the demo, a later run's
`memory.search` returned `memory search returned 1 record(s)` with the matching key. The
approval gate applies to `memory.write` too, which is why our policy helper auto-allows it
and audits the decision.

**Finding 6 — the search result hides the content.**

```
$ python findings/repro_memory_search_truncation.py
{"outputs":{"content":"memory search returned 1 record(s)","data":{"count":1, …
  "content":{"component":"[TRUNCATED]","labels":"[TRUNCATED]","severity":"[TRUNCATED]"}, …
RESULT: REPRODUCED
```

Every value of a structured `content` dict comes back as `[TRUNCATED]`, so the agent knows
a precedent exists but not what it decided. **Workaround:** store a compact one-line
summary string as the record content as well. If truncation is intentional for prompt
size, a `content_preview` field (or a `max_chars` argument on `memory.search`) would make
the tool usable.

**Observation.** `memctl` is not usable in a standard home: `memctl list` requires
`--scope`, and `memctl search` tries to load a `memory.yaml` that nothing creates
(`load_config` traceback). This matches upstream report #805. The in-runtime
`memory.search` tool was the only practical way to inspect memory from a script.

## 6. Skills

**What we did.** `SKILL.md` with `# Metadata` (`skill_id: repo-triager.triage-rubric`),
`repo-triager skills ingest` for ingest **and admission**, and `skill.get` offered to the
analysis agent.

**What worked.** Ingestion parses the document into `snippets.act` / `snippets.plan`
containing the real recipe text, and `skill.get` returns that record to the model.
Admission is a proper compare-and-swap (`--expected-active-version-hash`), which is a
good design for a shared skill store.

**Finding 5 — operator CLIs crash when the uid has no passwd entry.**
In this container (`uid 1000`, no `/etc/passwd` at all):

```
$ python findings/repro_operator_id_getpwuid.py
uid 1000 has a passwd entry: False
getpass.getuser() usable : KeyError: 'getpwuid(): uid not found: 1000'
$ openminion skill ingest --name repro --file SKILL.md --scope global
{ "ok": false, "error": { "code": "UNKNOWN", "message": "'getpwuid(): uid not found: 1000'" } }
```

Cause: `openminion/cli/identity/operator.py:9` → `getpass.getuser()`. Any distroless,
rootless or CI container hits it, and the JSON error names neither the CLI surface nor the
cause. Patch candidate in `findings/patches/operator_id_fallback.patch` (fall back to
`USER`/`LOGNAME`/`uid-<n>`). **Workaround here:** export `USER` before calling the CLI.

**Papercuts.**
* Ingest lands in `pending admission`; nothing says so except the last line of `skill list`.
  A flag-free `skill ingest` that left a skill inactive surprised us twice.
* `skill list` truncates the version hash (`4826d6de5be5...`), while `skill admit` needs the
  full hash — a second call (`skill show <id> --json`) is required.
* With no YAML front matter the stored `name` is the literal string `"SKILL"`, even though
  `skill_id` parsed correctly from `# Metadata`.
* `--verification-result passed` requires `--verification-check` **and**
  `--verification-evidence-ref`, or admission fails with `INVALID_ARGUMENT` after the
  compare-and-swap. The order of the requirements is not in `--help`.

## 7. Tasks and scheduling

**What we did.** `repo-triager schedule` calls `openminion cron create` with a cron
expression, a timezone, and the instruction that runs the daily batch.

**What worked.** `task.schedule` accepted the job and returned a task id, the schedule
object, `session_target: isolated`, and — importantly — a note that runs only execute
while the daemon is running:

```
{"task_id": "caeb74f4f069459085412ed13cbf8441", "kind": "cron", "tz": "Asia/Seoul",
 "scheduler": {"hosted_by": "daemon", "state": "unreachable", "reason": "daemon_unreachable"}}
```

**Observation.** In `single-process` mode (the mode a script or CI run uses) the scheduler
is permanently "unreachable", and `tasks list` needs a configured provider just to read the
inventory. Both are understandable design choices, but the CLI should say "this runtime
cannot run scheduled work" rather than report a healthy `ok: true` with an unreachable
scheduler inside.

## 8. Delegation

**What we did.** `subagent(parent, name="duplicate-scout", …)` for a bounded
duplicate-verdict pass; result parsed as `DUP <n> <conf> <reason>` / `NOTDUP <n> <reason>`.

**What worked.** It just worked: isolated session, own timeout, parent unaffected, no
approval friction, and it is the cheapest way to get a second opinion without polluting
the main conversation. Failure handling is ours (any exception → "delegation unavailable",
the run continues), which is why one scripted provider quirk did not break the pipeline.

**Observation.** `subagent()` inherits the parent's provider configuration but not the
parent's `tools`; a subagent that needs the same read tools must be given them again. The
signature accepted `tool`-less calls fine, and the docstring's "bounded" claim held (120 s
timeout respected).

## 9. Structured output

Covered by finding 2. Summary: validation is solid (schema check, then a balanced-JSON
recovery pass for prose-wrapped objects), but the *prompt* side is missing — the schema
never reaches the model. For a "typed declarative Agent API" this is the one thing that
must be fixed for the feature to be usable with a hosted model.

Practical consequence: Repo Triager ships `OUTPUT_SCHEMA` inside the task message and
treats `AgentOutputValidationError` as a first-class path (fallback decision + note in the
report).

## 10. Diagnostics

**What we did.** `repo-triager doctor` calls `capability_report()`, `runtime_posture()`,
`runtime_self_model()`, `tool_inventory_report()` and shells `openminion doctor`.

**What worked.** These are exactly the facts an operator wants before trusting a run:

```
tools registered  : 106
memory tools      : memory.forget, memory.search, memory.write, task.consolidate_memory
skill tools       : skill.get, skill.ingest, skill.ingest_url, skill.inspect, skill.list, skill.remove
self-model health : unavailable
doctor: OK (ok=23 warn=3 fail=0)
[WARN] identity.bundle: Identity profile is missing in IdentityCtl for agent 'openminion'.
```

`runtime_posture()["canonical_turn_path"]` is the clearest documentation of the call path we
have seen in an agent framework: `services/runtime/ingress.run_turn_payload →
services/request_orchestrator.run_turn → GatewayService.run_once →
BrainBridgeService.run_turn → BrainRunner.run`.

**Observation.** `runtime_self_model()` returns `health: "unavailable"` on a fresh home
without saying what would make it available (`degraded_reasons` is empty). One line of
guidance would save an hour.

## 11. Measurement — what one turn costs

```
$ python findings/measure_turn_cost.py
LLM calls : 12        tool calls: 3
input tokens: 75,298  output tokens: 828      elapsed: 966 ms (local scripted provider)
calls by purpose: act 5, entry 2, judge 3, freshness_classify 1, reflect 1
```

One 3-tool triage turn is **12 model calls**, not 4. The fixed per-turn calls (auto fact
extraction, freshness classification, reflection, closure judgment) dominate a small
workflow, and each call carries the full tool catalog and grounding block, which is why
input tokens are ~6 KB–6 K tokens per call. With a 3-issue batch that is ~36 calls.

**A rate-limited provider cannot run one turn.** Trying the same turn against a free hosted
OpenAI-compatible endpoint failed with
`HTTP 402: Free limit reached: 1 reply every 45 seconds per IP` — 12 calls need ~9 minutes,
and the runtime's 3-attempt retry cannot span that (`findings/real-model-attempt.log`).
A real model run therefore needs a provider without a per-request throttle (Portal, OpenAI,
Groq, Cerebras, Ollama) — a configuration change, not a code change.

This is not a bug, but it is the single most important number for anyone building a
batch or scheduled agent: batch size, caching, and a deterministic pre-pass (which keeps
the model's job small) matter more than tool-call micro-optimisation. Repo Triager
therefore (a) caches the issue snapshot, (b) pre-scores severity/component deterministically,
and (c) keeps the default batch at 3.

## 12. Providers

**What we did.** `openminion setup --provider custom-openai-compatible --base-url …` for the
scripted provider, and the documented presets for hosted models.

**What worked.** A custom OpenAI-compatible endpoint is a first-class citizen: the adapter
sent `tools`/`tool_choice`, parsed native `tool_calls`, and handled our SSE fallback.

**Friction.**
* `openminion setup` refuses a localhost custom endpoint without a credential
  (`Missing credential … Export OPENAI_COMPATIBLE_API_KEY`). Any placeholder works, but the
  requirement reads as a bug for a local model.
* The generated config has no CLI switch for `runtime.process_mode`; we patch
  `agents.json` to `single-process` so a script does not spawn a daemon. A
  `--process-mode` flag on setup would remove the need for that.
* `process_mode: single-process` still requires `OPENMINION_HOME`/`--home-root` hygiene in
  child processes: passing `--home-root` and exporting nothing else is the combination that
  worked for us.

---

## What we did not test

Honest scope limit: Portal and Gemma4 (no access), A2A/ACP surfaces, the HTTP gateway,
the graph viewer, plugin authoring, and multi-agent rooms. Everything above was exercised
through the Python SDK, the CLI, or both.

## Artifacts

| File | Content |
| --- | --- |
| `var/artifacts/doctor.json` | capability report, runtime posture, tool inventory |
| `var/artifacts/openminion-doctor.log` | full `openminion doctor` output |
| `var/artifacts/scripted-provider-requests.jsonl` | every request the runtime sent to the model |
| `var/runs/*/report.json` | decisions, validation, policy events, per-issue evidence |
| `findings/patches/operator_id_fallback.patch` | fix candidate for finding 5 |
