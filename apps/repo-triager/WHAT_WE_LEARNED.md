# What we learned

Actionable feedback from building **Repo Triager** on `openminion 0.1.24`, ordered by how
much it would change a builder's experience. Each item names the surface, the observed
behaviour, the impact, and a concrete change. Reproductions live in `findings/`.

---

## P0 — a typed Agent API that never tells the model the schema

**Surface:** `Agent(output_type=Model)`, `openminion/api/agent.py`

**Observed:** the request to the provider contains the user message and the tool catalog,
but never the schema of `Model` and never an instruction to answer with JSON. A hosted
model answers in prose; `_coerce_output` then raises `AgentOutputValidationError` on a run
the runtime itself reports as `completed`.

**Repro:** `findings/repro_structured_output_schema.py` (schema present in any request:
`False`).

**Impact:** the advertised typed-output feature is unusable with a real provider without a
workaround, and the failure arrives *after* the tokens are paid for. Every builder will
independently reinvent the "put the schema in the prompt" trick.

**Change:** when `output_type` is set, append the JSON schema (and "answer with one JSON
object") to the effective system prompt, or expose `output_schema_mode="prompt|tool"`. If
the schema is intentionally delivered as a tool (`submit_output`), then wire it as the
final tool call for `output_type` too — today `submit_output` is used for the runtime's
internal schemas while `output_type` is validated from free text, which is the confusing
part.

---

## P0 — silent truncation of `Agent(instructions=…)`

**Surface:** `Agent(instructions=...)`

**Observed:** 2,599 characters of instructions → rules 01–08 reached the model, the sentinel
at the end did not, the turn reported `completed`.

**Repro:** `findings/repro_instructions_truncation.py`.

**Impact:** a system prompt is where behaviour lives. Dropping its tail without a warning
turns "the model ignores my last two rules" into an unexplainable bug. (Upstream #811.)

**Change:** either stop truncating, or cap explicitly and loudly: raise
`ValueError`/`InstructionsTooLong` with the limit, and set
`result.metadata["instructions_truncated"] = {"kept": 860, "dropped": 1739}`. A warning log
line is the minimum.

---

## P1 — the approval callback cannot see what the pause prompt shows

**Surface:** `Agent.run(approval_callback=...)`, pause prompt

**Observed:** the pause prompt prints `Risk`, `Side effects`, `Reversibility`, `Reason`,
`Choices`. `approval_callback(tool_name, args, approval_id)` receives none of them.

**Impact:** an application that wants a real operator decision in code (CI, a UI, a
headless runner) has to re-derive risk from the tool name and then hope it agrees with the
policy that actually gated the call. The two confirmation paths should not have different
information.

**Change:** pass the risk facts as a fourth argument (or a keyword `facts=`):
`callback(tool_name, args, approval_id, facts)` — the runtime already builds them for the
pause path.

---

## P1 — denial semantics collapse into the model result

**Surface:** `approval_callback` returning `False`; `output_type` combination

**Observed:** a denial ends the turn with the text "Confirmation denied. The action was not
run."; if the Agent has `output_type`, that text is then validated as the model's answer and
raises `AgentOutputValidationError`. A denial is indistinguishable from a malformed reply
without string matching.

**Repro:** `findings/repro_policy_gate_vs_output_type.py`.

**Change:** return a typed outcome — `AgentRunResult.policy` (or
`metadata["policy_decision"] = {"tool": …, "decision": "deny", "reason": …}`) and skip
`_coerce_output` when the turn ended on a policy stop. Also, `False` for one tool should
deny *that call* and let the model continue (it may choose another route) unless the caller
asks for turn-level denial.

---

## P1 — session ids are not validated against the memory scope they produce

**Surface:** `Agent(session_id=...)` → memory context

**Observed:** `session_id="repo-triager:openminion/openminion"` becomes
`session:repo-triager:openminion/openminion`, which fails
`^(session|agent|project|global):[A-Za-z0-9._:-]+$`. The turn completes; memory is silently
absent.

**Repro:** `findings/repro_session_scope.py`.

**Impact:** the most natural session id in a repository-oriented agent contains `/`.
Silent memory loss is the worst failure mode for a memory feature.

**Change:** validate/normalise `session_id` at the `Agent` boundary (or slugify the scope
and record the mapping), and surface a `metadata["memory_scope"]` fact so a caller can see
which scope was actually used.

---

## P1 — operator CLIs assume a passwd entry

**Surface:** `openminion skill ingest|admit`, `tasks`, anything using
`local_operator_id()`

**Observed:** `KeyError: 'getpwuid(): uid not found: 1000'` in a container without
`/etc/passwd`; the JSON surface reports `{"ok": false, "error": {"code": "UNKNOWN"}}`, so the
message is the only clue.

**Repro:** `findings/repro_operator_id_getpwuid.py`; patch candidate
`findings/patches/operator_id_fallback.patch`.

**Change:** `try: getpass.getuser() except (KeyError, OSError): USER/LOGNAME/uid-<n>`.
This is a two-line fix that unblocks every container and CI runner.

---

## P2 — memory search hides the record it found

**Surface:** `memory.search` (model tool)

**Observed:** values inside a structured `content` dict come back as the literal string
`[TRUNCATED]`.

**Repro:** `findings/repro_memory_search_truncation.py`.

**Impact:** recall tells the model "a decision exists" but not what it decided, which is
worse than no recall for consistency.

**Change:** return a `content_preview` (first N characters, N configurable), or honour a
`max_chars` argument on the search call. Keep `[TRUNCATED]` only for genuinely oversized
values, and say how large they were.

---

## P2 — the skill lifecycle needs three commands and a full hash

**Surface:** `skill ingest`, `skill admit`, `skill list`

**Observed:** ingest leaves the skill `pending admission` (inactive); admission needs
`--expected-active-version-hash` (full hash) which `skill list` truncates
(`4826d6de5be5...`); `--verification-result passed` then demands `--verification-check` and
`--verification-evidence-ref` or fails after the compare-and-swap. Ingest also defaults
`name` to `"SKILL"` when the document has no YAML front matter, even with a valid
`skill_id` in `# Metadata`.

**Impact:** three round trips and a failed attempt for the (very common) first-time flow.

**Change:** `skill ingest --admit` (with a `--verify <command>` that writes its own
evidence file), accept a hash prefix in `--expected-active-version-hash`, list the full
hash in `skill list --json`, and derive `name` from the `# Purpose` heading or the document
title.

---

## P2 — batch economics are invisible

**Surface:** turn execution

**Observed:** one 3-tool triage turn = **12 model calls** (`act` 5, `entry` 2, `judge` 3,
`freshness_classify` 1, `reflect` 1) and ~75 K input tokens with the scripted provider;
the fixed per-turn structured calls dominate.

**Impact:** builders size batches and schedules as if a turn were one call, then pay 3–12×.
`metadata["llm_calls_count"]` exists — it should be hard to miss.

**Corollary:** a 12-call turn needs a provider that does not throttle per request. Our live
attempt against a free OpenAI-compatible endpoint died on
`HTTP 402: 1 reply every 45 seconds per IP`. The runtime retried three times and gave up,
correctly — but the error ("provider failed before it could return a decision") does not say
"your turn needs 12 calls at 1/45 s, so budget ~9 minutes". A builder on a cheap plan will
read that as a bug in their code.

**Change:** log a one-line summary at the end of each turn
(`turn: 12 calls, 75k input tokens, 3 tools`) at INFO, and document a
`runtime.disable_turn_overhead=[freshness,reflect]`-style switch for deterministic,
tool-driven workflows. A "no reflection" mode would halve the cost of a batch agent that
does not need conversational judgement.

---

## P2 — diagnostics that cannot explain themselves

**Surface:** `APIRuntime.runtime_self_model()`, `openminion doctor`

**Observed:** `health: "unavailable"` with an empty `degraded_reasons` on a fresh home;
`doctor` warns `identity.bundle` is missing without saying whether anything depends on it.

**Change:** each `unavailable`/`warning` fact carries a `next_command` (it already does for
some doctor checks — extend that to the self-model facts).

---

## P3 — small frictions worth a line each

1. **`openminion: ` prefix on every `AgentRunResult.text`.** A client that asked for `str`
   output does not expect a channel prefix. Document it, or strip it for SDK callers.
2. **`setup` demands a credential for `custom-openai-compatible` even at `127.0.0.1`.**
   Allow an empty credential for loopback base URLs.
3. **No `--process-mode` flag on `setup`.** Building a scripted or CI-shaped runtime
   requires hand-editing `agents.json` (`runtime.process_mode = "single-process"`).
4. **Tool name spelling differs between APIs.** `Agent(tools=["memory.write"])` vs the
   model-facing `memory_write`. Accept both in `Agent(tools=...)`.
5. **`cron create` reports `ok: true` with `scheduler.state: "unreachable"`** in
   single-process mode. Make the task's own record say "requires the daemon" (it does, in
   `scheduler_note`) and have the CLI print that note to stderr.
6. **`memctl` needs a `memory.yaml` nothing creates** (upstream #805). Until it is fixed, the
   in-runtime `memory.search` tool is the only scriptable inspection path.

---

## What was genuinely good

Worth saying clearly, because these are the parts we built on without fighting:

* **The `@tool` risk contract.** `min_scope="READ_ONLY"` vs. a bare `@tool` vs.
  `dangerous=True` mapped exactly onto the three kinds of action in a triage workflow.
  We wrote no policy code.
* **The pause prompt.** Risk, side effects, reversibility, reason, accepted answers — the
  best operator-facing confirmation text we have seen in an agent runtime.
* **`runtime_posture()["canonical_turn_path"]`.** One field that explains the whole call
  path.
* **`subagent()`.** Bounded, isolated, cheap; a second opinion without a second runtime.
* **`openminion doctor`.** Caught our provider, storage and permission mistakes early.
* **The config surface.** One `agents.json`, absolute paths, provider presets for a dozen
  vendors — moving between the scripted provider and a hosted model was one flag.

---

## What we would build next on this base

1. A `repo-triager serve` mode behind the OpenMinion HTTP gateway, so a maintainer team can
   share one triage queue.
2. A scheduled run through the daemon (the cron contract already accepts our instruction)
   with the report posted to a Slack channel through a control plane.
3. A Portal/Gemma4 comparison once access is available — the provider abstraction makes
   this a config change, and the measurement script already records the numbers.
