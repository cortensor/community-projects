# Ready-to-file OpenMinion issue reports

Prepared from the reproductions in `findings/` while building Repo Triager. **Not filed** —
opening issues on `openminion/openminion` is a public write under the submitter's account
and needs explicit approval.

Order by severity. Each report follows the shape of the repository's existing reports
(version, environment, reproduction, expected vs actual, impact, evidence). For the
hackathon's bug bonus, file the issue → wait for acknowledgement and "in scope" → then open
a fix PR.

---

## 1. `Agent(instructions=…)` is truncated at ~860 characters with no warning

**Version:** openminion 0.1.24 (PyPI), Python 3.12.16, Linux x86_64
**Surface:** `openminion.Agent`, `openminion/api/agent.py`

**Steps**

```python
from openminion import Agent, tool
instructions = "".join(
    f"Rule {n:02d}: always explain the reasoning for this triage decision in one clear sentence. "
    for n in range(1, 31)
) + "SENTINEL_END_ABCXYZ"        # 2_599 characters
with Agent(tools=[ping], instructions=instructions, session_id="repro") as agent:
    agent.run("hello")
```

**Expected:** all 30 rules reach the model.
**Actual:** rules 01–08 reach the model; rule 09 onward is dropped, sentinel absent,
`run_state == "completed"`. No warning and no metadata flag.

**Impact:** silent behaviour loss for every agent with a real system prompt; "the model
ignores my last two rules" is unexplainable from the outside. Workaround used by our
project: keep instructions < 1,000 characters and put the rubric in the user message.

**Evidence:** `findings/repro_instructions_truncation.py`, `findings/RESULTS.md`.
Related: #811.

**Suggested fix:** stop truncating, or fail loudly (`ValueError` naming the limit) and set
`metadata["instructions_truncated"]`.

---

## 2. `Agent(output_type=Model)` never tells the model the schema

**Version:** openminion 0.1.24
**Surface:** `Agent(output_type=…)`, `openminion/api/agent.py::_coerce_output`

**Steps**

```python
class Triage(BaseModel):
    issue_number: int
    severity: str
    reason: str

with Agent(output_type=Triage, instructions="Classify the issue.", session_id="repro") as agent:
    agent.run("classify issue 859")
```

**Expected:** the request asks the model for a reply matching `Triage`.
**Actual:** no schema and no JSON instruction appear in the request; a hosted model answers
in prose, the runtime reports the turn as completed, and `_coerce_output` raises
`AgentOutputValidationError` ("Invalid JSON: expected value at line 1 column 1") after the
model call was paid for. `submit_output` exists but is used for the runtime's internal
schemas (AFE, `FreshnessContract`, `ClosureJudgment`), not for `output_type`.

**Impact:** the typed-output feature is unusable with a real provider without a client-side
workaround.

**Evidence:** `findings/repro_structured_output_schema.py`. Related: #853, #803.

**Suggested fix:** append the schema (and "answer with one JSON object") to the effective
system prompt when `output_type` is set, or route `output_type` through `submit_output`.

---

## 3. A denied or paused policy confirmation breaks a structured-output turn

**Version:** openminion 0.1.24
**Surface:** `Agent(output_type=…, approval_callback=…)`

**Steps**

1. Declare a bare `@tool` write and `Agent(output_type=Applied, tools=[write_tool])`.
2. Run with `approval_callback=lambda *a: False` (or no callback, then answer "no" on the
   paused thread).

**Expected:** a policy result the caller can act on.
**Actual:** the write is correctly blocked, the turn ends with
`"Confirmation denied. The action was not run."`, and `_coerce_output` then validates that
text against `Applied` and raises `AgentOutputValidationError`. A policy denial is
indistinguishable from a malformed model reply except by string matching `exc.raw_text`.

**Impact:** an approval gate and a typed result cannot live in the same turn; applications
must split the workflow (we run the gate in its own turn with `output_type=None`).

**Evidence:** `findings/repro_policy_gate_vs_output_type.py`. Related: #852, #803.

**Suggested fix:** skip `_coerce_output` when the turn ended on a policy stop and expose
`metadata["policy_decision"]`.

---

## 4. A session id containing `/` silently disables memory for the session

**Version:** openminion 0.1.24 / sophiagraph
**Surface:** `Agent(session_id=…)`, memory context build

**Steps**

```python
with Agent(session_id="repo-triager:openminion/openminion", …) as agent:
    agent.run("hello")
```

**Expected:** memory context is built for the session.
**Actual:** the memory layer builds `session:<id>` and validates it against
`^(session|agent|project|global):[A-Za-z0-9._:-]+$`; the `/` fails, a WARNING is logged
(`memory.build_context_with_metadata failed … invalid scope`), the turn completes, and the
agent runs without its memory capsule.

**Impact:** a repository slug is the most natural session id in a repo-oriented agent, so
this is easy to hit; silent memory loss is the worst failure mode for a memory feature.

**Evidence:** `findings/repro_session_scope.py`.

**Suggested fix:** validate/normalise the session id at the `Agent` boundary, or slugify the
scope and expose `metadata["memory_scope"]`.

---

## 5. Operator CLIs fail with `getpwuid(): uid not found` when the uid has no passwd entry

**Version:** openminion 0.1.24
**Surface:** `openminion skill ingest|admit`, `tasks`, anything using `local_operator_id()`
(`openminion/cli/identity/operator.py:9`)

**Environment:** container with `uid 1000` and no `/etc/passwd` (distroless, rootless, many
CI runners).

**Steps**

```bash
openminion skill ingest --name repro --file SKILL.md --scope global
```

**Expected:** the skill is ingested.
**Actual:**

```json
{ "ok": false, "error": { "code": "UNKNOWN", "message": "'getpwuid(): uid not found: 1000'" } }
```

Traceback: `getpass.getuser()` → `pwd.getpwuid(os.getuid())` → `KeyError`.

**Impact:** every operator CLI path that needs an operator id is unusable in such
containers, and the error names neither the surface nor the cause. Workaround: export
`USER`.

**Evidence:** `findings/repro_operator_id_getpwuid.py`.
**Patch:** `findings/patches/operator_id_fallback.patch` — fall back to
`USER`/`LOGNAME`/`uid-<n>`. Happy to open it as a PR once this report is acknowledged.

---

## 6. `memory.search` returns `[TRUNCATED]` instead of the stored content

**Version:** openminion 0.1.24
**Surface:** `memory.search` model tool

**Steps**

1. `memory.write` with `content={"severity": "S2", "component": "area:tools"}`.
2. `memory.search` with a matching query.

**Expected:** the record content is returned.
**Actual:**

```json
{"records": [{"content": {"component": "[TRUNCATED]", "severity": "[TRUNCATED]"}, …}]}
```

**Impact:** recall tells the model that a decision exists but not what it decided — worse
than no recall for consistency; we store a duplicate summary string as a workaround.

**Evidence:** `findings/repro_memory_search_truncation.py`.

**Suggested fix:** return a `content_preview`, or accept `max_chars` on the search call.

---

## Notes for whoever files these

* Attach `findings/RESULTS.md` (literal outputs) and the two artifacts in
  `docs/examples/` rather than screenshots — they are reproducible text.
* #1 and #2 are the ones worth the fix PR; #5 already has a patch.
* Security-relevant? None of the six is a vulnerability; all are behaviour/portability.
