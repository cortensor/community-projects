# Findings log — TriageMinion development

Raw log behind `BUILDING-BLOCKS.md` and `WHAT-WE-LEARNED.md`. Every entry was
observed live in this workspace. Environment unless noted otherwise:
`openminion==0.1.24`, Python 3.12.3, Linux x86_64 VM (shared CPU, ~8 GB RAM),
Ollama 0.40.19 serving `qwen2.5:3b` (Q4_K_M) on `http://127.0.0.1:11434`.

## F1 — BUG: all provider calls fail when NO_PROXY contains bracketed IPv6 entries

- **Severity:** total provider outage in affected environments.
- **Status:** reported upstream —
  https://github.com/openminion/openminion/issues/893 ·
  fix PR: https://github.com/openminion/openminion/pull/894
- **Repro (minimal):**
  ```bash
  export NO_PROXY='localhost,127.0.0.1,::1,[::1]'
  python -c "import httpx; httpx.Client(follow_redirects=True, trust_env=True)"
  # httpx.InvalidURL: Invalid port: ':1]'
  ```
  End-to-end: `openminion setup --provider ollama --model qwen2.5:3b --no-chat`,
  then any `Agent.run(...)` →
  `ProviderError: … (InvalidURL: Invalid port: ':1]'). Please retry or switch models.`
- **Expected:** the run reaches the local provider; `127.0.0.1` is in NO_PROXY.
- **Actual:** `ProviderHTTPClient._get_client()`
  (`modules/llm/providers/transport/client.py`) builds
  `httpx.Client(follow_redirects=True, trust_env=True)` unguarded; httpx 0.29.0
  raises `InvalidURL` parsing bracketed IPv6 NO_PROXY entries while building
  URLPatterns, at client construction — before any request. Plain `urllib` and
  `curl` reach the same endpoint fine in the same env.
- **Why it matters:** container/CI/sandbox runtimes commonly publish exactly
  this NO_PROXY shape. The generic "retry or switch models" ProviderError
  message sends users to debug the wrong layer.
- **Fix (PR #894):** `_build_httpx_client()` falls back to `trust_env=False`
  with a warning on `httpx.InvalidURL`; regression tests added
  (`tests/llm/test_provider_http_client_env.py`, 2 passed; negative control
  against the unpatched wheel raises as expected).
- **Local workaround in TriageMinion:** `sanitize_proxy_env()` drops bracketed
  entries from NO_PROXY before the first provider call.

## F2 — `openminion setup` default provider timeout (60 s) is too low for local CPU models

- `setup --provider ollama` writes `providers.ollama.timeout_seconds = 60`.
  A single `/api/chat` call for a tool-using turn on a CPU-only 3B model can
  take minutes (measured: 512 prompt tokens ≈ 48 s of prompt processing alone
  on this VM, before generation). Turns then die as provider timeouts that
  look like model failures.
- **Expected:** the ollama preset either defaults to a local-inference-realistic
  timeout or `openminion doctor --check-turn` warns when the configured
  timeout is far below observed latency.
- **TriageMinion handling:** after setup, the project-scoped config's provider
  timeout is raised to 900 s (logged, in `ensure_config`).

## F3 — Turn latency on local models: auxiliary requests + a hidden 300 s brain budget

- A single `Agent.run()` issues multiple model requests around the user-visible
  turn (automatic memory extraction is the first request of every turn — also
  reported publicly by the Go-Live Gate author for Hackathon #5). Measured here:
  one triage turn = 3+ `/api/chat` requests, each re-processing a ~3.5k-token
  prompt at ~11 tok/s prompt / ~1.3 tok/s generation on this shared-CPU VM.
  First smoke run hit `TurnTimeoutError` at the caller's 1200 s budget with no
  verdict — the requests are simply that expensive locally.
- The generated config also carries `runtime.brain_turn_timeout_seconds = 300`
  (the subject of upstream issue #770): an internal budget a caller cannot see
  from the Python API surface, which can cut/repair long local turns.
- **TriageMinion handling:** project config patches — provider timeout 900 s,
  brain/chat turn timeouts 2400 s, and `runtime.memory_enabled=false`
  (extraction off; durable memory is the explicit state file + SDK session
  store). All patches are logged at startup.
- **Ask:** a documented "local model" profile (or `doctor` warnings) covering
  these three knobs; per-turn request counts in diagnostics.

## F4 — Known 0.1.22 issues worth re-checking on 0.1.24

- #853 `Agent(output_type=Model)` does not tell the model the schema — the
  official `structured_output.py` example still spells the JSON fields out in
  `instructions`, and TriageMinion does the same; whether the schema is now
  injected could not be confirmed from the docs. (Behaviour observed in our
  runs is recorded in BUILDING-BLOCKS.md.)
- #724 `forced_tools` silently not enforced on Ollama — TriageMinion avoids
  relying on `forced_tools` for correctness; tool use is verified from
  effects (staging file writes) instead of assumed.
- #725 no way to set Ollama `num_ctx` — relevant: long issue bodies + the
  SDK's system prompt can exceed the default context on small models.

## F5 — Campaign/docs findings (not SDK code)

- The DoraHacks page for Hackathon #5 (crawled 2026-10-15) and the Cortensor
  docs page **still** say the submission repository URL "will be added before
  kickoff" — after kickoff (16 Oct 2026) it never was. The actual submission
  route is PRs to `cortensor/community-projects` under `apps/<project>/`,
  discoverable only by inspecting other entrants' PRs (e.g. #99, #105, #112,
  #114 there).
- "Follow OpenMinion and Cortensor on GitHub" cannot be done literally: both
  are GitHub **organizations** and the API has no follow for orgs
  (`PUT /user/following/openminion` → 404). Starring the repo is the closest
  available action.
- `openminion setup` and the project-scoped config resolution
  (`$OPENMINION_HOME/.openminion/agents.json`) worked exactly as documented —
  one of the smoothest parts of the SDK.

## F7 — Ollama preset's `fallback` tool strategy: small models ignore the tools and drop schema fields

- With the stock ollama preset (`tool_call_strategy: fallback`), the first
  live turn (qwen2.5:3b) never called either tool: it answered directly with a
  JSON object that was **missing two of the six required fields**
  (`justification`, `draft_response`) → `AgentOutputValidationError`
  (raw: `openminion: {"issue_number":4274,"classification":"bug","priority":"high","suggested_labels":["bug","ipv6","emoji"]}`).
  The classification itself was correct — the failure is purely interface
  discipline.
- The adapter only sends native tool definitions when the strategy supports
  it (`native`/`hybrid`); `fallback` relies on text conventions a 3B model
  follows poorly. Setting `providers.ollama.tool_call_strategy: hybrid` in
  the project config (TriageMinion does this automatically) lets tool-capable
  local models (Qwen2.5 family) use native calls while keeping the fallback
  parser.
- **Ask:** make the ollama preset's strategy model-aware (or document the
  one-line config change next to the preset); the current default silently
  downgrades every tool-capable local model.
- TriageMinion also adds one corrective retry per issue (failure reason +
  full issue text inline) — see `triage.py`. Whether the retry was needed is
  visible in the run logs.

## F8 — Post-save prose replies and identical-tool-call loops with a 3B model

- After a successful approval-gated `save_triage_record`, the model's final
  reply was prose ("The issue #4274 has been triaged as a bug… The following
  response will be sent to t…") instead of the required JSON →
  `AgentOutputValidationError` (the `openminion: ` envelope again, cf. F4/#720).
  The verdict existed only in the tool record — hence TriageMinion's recovery
  path, which treats the approval-gated tool record as the verdict of record.
- On the corrective retry, the model called `save_triage_record` **three more
  times** with near-identical arguments; the SDK executed each one (each was
  approval-gated and logged). No identical-call dedup or loop brake was
  observable at the SDK layer within `agent_loop_max_steps` (default 100).
- **Ask:** (a) a "submit_output"-style terminal tool for structured turns so
  the final answer travels the tool channel instead of free text; (b) optional
  identical-tool-call dedup / repeat-call circuit breaker in the agent loop.

## F6 — Ollama in this sandbox (environment, not OpenMinion)

- `ollama pull` hung indefinitely at "pulling manifest" while `curl` to the
  same registry returned the manifest in ~1 s. The model was installed by
  fetching the OCI manifest + blobs with curl into Ollama's store layout and
  verifying the blob's sha256 against the manifest digest (exact match);
  `ollama list`/`generate` then worked normally. Recorded here because other
  builders in restricted sandboxes will hit the same wall; the OpenMinion
  ollama path itself was fine once a model existed.
