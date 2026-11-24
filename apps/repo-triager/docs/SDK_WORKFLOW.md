# The SDK workflow, step by step

One triage run touches OpenMinion in six places. This page maps each step to the code that
does it, so a reviewer can follow the SDK usage without reading the whole tree.

```
cli.py                     agent.py                   tools.py
  │                          │                          │
  ├─ RuntimeSession ─────────┼─ openminion setup ────────┤  (agents.json, single-process)
  ├─ open_runtime ───────────┤ APIRuntime.from_config_path
  │                          │
  │                          ├─ Agent(analyse)  ────────► triage_precheck, get_issue,
  │                          │   output_type=TriageDecision  search_duplicate_issues,
  │                          │                            label_taxonomy, memory.search,
  │                          │                            skill.get
  │                          ├─ subagent(duplicate-scout)  (optional)
  │                          ├─ Agent(stage)   ────────► stage_triage  ← policy gate
  │                          └─ Agent(remember) ───────► memory.write
  └─ report.write_report     (RunReport → report.md + report.json)
```

## 0. Bootstrap

```python
settings = Settings(workspace=Path("var"))
with RuntimeSession(settings, provider_mode="scripted") as session:   # or "configured"
    runtime = APIRuntime.from_config_path(str(settings.config_path))
```

`RuntimeSession` calls `openminion setup` only when `agents.json` is missing, then patches
the three runtime keys that setup does not expose (`process_mode`, `daemon_auto_start`,
`log_level`). In `scripted` mode it starts the local provider **first** and points the
config at its ephemeral port.

Why `single-process`: a CLI must not spawn a daemon as a side effect. Consequence:
scheduled tasks are registered but cannot run (see `BUILDING_BLOCKS_TESTED.md` §7).

## 1. Analysis turn

```python
with Agent(
    runtime=runtime,                       # one runtime shared by all phases
    name="repo-triager",
    instructions=SYSTEM_PROMPT,            # < 1,000 chars: instructions are truncated
    tools=[triage_precheck, get_issue, search_duplicate_issues, label_taxonomy,
           list_open_issues, "memory.search", "skill.get"],
    output_type=TriageDecision,            # validated client-side
    session_id="repo-triager:openminion_openminion",
) as agent:
    result = agent.run(message, timeout_seconds=180)
decision: TriageDecision = result.output
```

* Decorated tools and built-in tool names may be mixed in `tools=[...]`; the list becomes
  the turn's `allowed_tools`, so the other 100 built-ins stay out of the prompt.
* `message` carries the issue, the deterministic pre-check, the rubric and the JSON schema.
  It is 3–4 KB; the system prompt is 300 characters. This split exists because of the
  instructions truncation finding.
* The runtime may continue the turn on its own ("Continue the active task…"), so a
  scripted provider must key its steps on the conversation, not on one request.

## 2. Tool execution and the deterministic guard

Read tools are `@tool(min_scope="READ_ONLY", idempotent=True)` — no confirmation, no
friction. `stage_triage` is a bare `@tool` and therefore a write with unknown
reversibility: **the runtime asks before it runs**, every time, regardless of what our code
wants. That is the gate; `policy.py` only supplies the answer.

The tool itself validates the model's proposal before writing (labels ∈ taxonomy,
`duplicate_of` ⊆ snapshot, issue number matches the pending plan) and returns a JSON error
the model can react to. Model proposes → guard validates → policy gates.

## 3. Delegation

```python
with Agent(runtime=runtime, name="repo-triager-parent", session_id=sid) as parent:
    scout = subagent(parent, name="duplicate-scout", instructions=..., timeout_seconds=120)
    verdict = scout.run(dedupe_message)
```

The subagent gets its own session and timeout. Our parser accepts
`DUP <n> <confidence> <reason>` / `NOTDUP <n> <reason>`; anything unparseable, or any
exception, leaves the analysis decision untouched ("delegation unavailable" is logged, the
run continues).

## 4. The gate — two ways to answer it

**Callback (scriptable):**

```python
def decide(tool_name: str, args: dict, approval_id: str) -> bool:
    if tool_name != "stage_triage":
        return False
    return operator_mode == "auto"

agent.run(stage_message, approval_callback=decide)
```

**Pause (interactive, uses the runtime's own prompt):**

```python
result = agent.run(stage_message)                  # no callback
if result.metadata.get("respond_kind") == "policy_confirmation_prompt":
    print(result.text)                             # Risk / Side effects / Reversibility
    result = agent.run("yes", thread_id=result.thread_id)
```

The pause path needs no `output_type` (finding 3) and no callback; it is the path to show
a human. Both paths record a `PolicyEvent` — tool, argument preview, decision, policy
source, approval id — in the report.

## 5. Memory turn

```python
Agent(runtime=runtime, tools=["memory.write"], forced_tools=["memory.write"])
```

`forced_tools` guarantees the write is attempted; the callback allows only
`memory.write`. The record key is `triage:<repo>:<issue>`, so a later run can find it with
`memory.search` (which is offered to the analysis turn). Note the record content is a
compact string *and* a dict: `memory.search` truncates dict values (finding 6).

## 6. Report

`RunReport` → `runs/<timestamp>-<repo>/report.md` + `report.json`. The JSON keeps the
decision, the validation problems, the policy events, the outbox paths, run/session ids and
the model call counts — enough to audit a run without the console.

## Where each SDK call happens

| SDK call | File:line |
| --- | --- |
| `APIRuntime.from_config_path` | `agent.py::open_runtime` |
| `Agent(...).run` (analysis) | `agent.py::TriagerAgent.analyse` |
| `Agent(...).run` (gate, callback) | `agent.py::TriagerAgent.stage` |
| `Agent(...).run` (gate, pause + resume) | `agent.py::TriagerAgent.stage` (`pause=True`) |
| `subagent(...).run` | `agent.py::TriagerAgent.deep_dedupe` |
| `Agent(...).run` (memory) | `agent.py::TriagerAgent.remember` |
| `apiruntime.capability_report()` etc. | `cli.py::cmd_doctor` |
| `openminion setup` / `doctor` / `skill` / `cron` | `config.py::RuntimeSession`, `cli.py` |
