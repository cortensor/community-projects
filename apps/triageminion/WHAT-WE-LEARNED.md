# What We Learned — actionable feedback for the OpenMinion team

Built TriageMinion (GitHub issue triage) on `openminion==0.1.24` with a local
Ollama model, no paid keys. Ordered by impact; evidence in `FINDINGS.md`.

## 1. A malformed proxy env must never take down every provider call (bug, with fix)

`ProviderHTTPClient` builds `httpx.Client(trust_env=True)` unguarded. In any
environment whose `NO_PROXY` contains bracketed IPv6 literals (`[::1]` —
containers, CI, sandboxes do this), httpx raises `InvalidURL: Invalid port:
':1]'` at client construction and **all** provider calls fail, surfaced only
as a generic "retry or switch models" `ProviderError`.
→ Issue #893 with minimal repro; fix PR #894 (fallback to `trust_env=False`
with a warning + regression tests). Even with the fallback, please make the
error message name the proxy env as the suspect — the current wording sends
users to debug a healthy model.

## 2. Local-model builders need a latency-realistic starter profile

Three separate defaults each broke or nearly broke a CPU-local run, and none
is mentioned in the Ollama provider docs:

- `providers.ollama.timeout_seconds = 60` from `setup` (one tool-turn request
  can take minutes on CPU);
- `runtime.brain_turn_timeout_seconds = 300` (invisible from the Python API;
  cf. #770);
- automatic memory extraction = one extra full-price model request per turn.

→ Ship a documented "local / small model" profile (or have
`openminion doctor --check-turn` warn when observed latency ≫ configured
timeouts). We patched all three in our project config and logged each patch;
steal that list as the profile's contents.

## 3. The Ollama preset's `fallback` tool strategy undersells tool-capable models

With `tool_call_strategy: fallback`, qwen2.5:3b ignored both tools and
free-answered. Switching the provider config to `hybrid` (native tool
definitions + fallback parsing) fixed tool use. The preset can't know the
model, but the docs page for Ollama should say: *if your model supports tool
calling, set `tool_call_strategy: hybrid`*. One sentence would have saved an
hour of diagnosis.

## 4. Structured output: say whether the schema is injected, and surface raw replies cleanly

The official example spells the JSON fields out in `instructions`, implying
the `output_type` schema is *not* given to the model (cf. #853). We did the
same and validation still caught a reply missing two fields — the safety net
works — but `AgentOutputValidationError.raw_text` arrived wrapped as
`openminion: {…}`, which looks like a closure-judge envelope leaking into the
error surface (cf. #720). Document the contract; return the model's raw reply
unwrapped.

## 5. Diagnostics: expose per-turn request counts

When a turn is slow, the first question is "how many model requests did that
turn make, and how long did each take?" Today that requires reading the
*provider's* server log (we counted `/api/chat` POSTs in Ollama's log). A
`result.stats` field or a `doctor`-style run summary with request count +
per-request latency would make local-model development dramatically easier.

## 6. What genuinely worked well

- `openminion setup` + project-scoped config resolution
  (`$OPENMINION_HOME/.openminion/agents.json`) — exactly as documented,
  zero surprises.
- The approval-callback design: per-run, `(tool_name, args, approval_id)`,
  trivial to implement a real human gate and an `--auto-approve` CI mode
  against. This is the right shape for agent permissions.
- Typed errors (`ProviderError` / `TurnTimeoutError` /
  `AgentOutputValidationError`) made failure handling explicit instead of
  string-matching — our retry logic is built directly on them.
- Sessions just persist (SQLite store), and `result.session_id` makes
  continuity observable without extra code.

## 7. Campaign-level note (not SDK)

The Hackathon #5 DoraHacks/docs pages still say the submission repo URL
"will be added before kickoff". It never was; the route (PRs to
`cortensor/community-projects` under `apps/`) is only discoverable by
inspecting other entrants' PRs. And "follow on GitHub" can't be done for
organizations (no follow API for orgs) — starring is the closest action.
Both are one-line doc fixes that would remove real friction for every
entrant.
