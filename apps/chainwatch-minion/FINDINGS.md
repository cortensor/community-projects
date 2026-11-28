# FINDINGS — chainwatch-minion (Cortensor Hackathon #5)

Building blocks tested with OpenMinion SDK 0.1.24 + a real model
(`fp/deepseek-v4.1-flash` via an OpenAI-compatible gateway), and what we
learned building a multi-chain wallet analyst around them.

## Building Blocks Tested

### 1. `@tool` decorator + scope enforcement — WORKS, with sharp edges

- `@tool(min_scope="READ_ONLY", idempotent=True)` on plain Python functions
  works exactly as advertised: the runtime exposes them to the model with
  schema-derived signatures, enforces scopes, and routes calls through the
  policy layer.
- **Sharp edge (finding #2 below):** the policy layer hardcodes
  `reversibility=UNKNOWN` for every non-read tool, which makes any WRITE-scope
  tool trigger a confirmation round-trip that the Python API cannot answer
  inline. We ended up designing the agent as read-only and moving the single
  durable write into the host CLI — a better architecture anyway, but we only
  discovered the constraint by reading SDK internals.
- **Sharp edge (finding #4):** a tool that returns a `str` gets wrapped as
  `outputs={"data": "<the string>"}`. A tool that returns a `dict` gets its
  keys hoisted to the top level of `outputs`. This distinction is invisible
  until it silently changes verification behaviour (see finding #4).

### 2. Agent + session loop — WORKS

- `Agent(instructions=..., tools=[...], session_id=..., config_path=...)`
  with `agent.run(prompt)` drives a stable multi-step tool loop: the model
  issued overview → transactions → transfers in the intended order and
  summarized only data the tools returned.
- Config lookup is CWD-relative by default; passing `config_path` explicitly
  is required when the CLI runs from a project directory.
- Sessions are address+chain-derived (`chainwatch-<addr8>-<chain>`), which
  keeps run artifacts reproducible.

### 3. Real-model brain loop with hybrid tool strategy — WORKS

- With a spec-compliant OpenAI-compatible endpoint, `tool_call_strategy:
  hybrid` produced correct multi-call plans, including a graceful
  **degraded-data run**: when every endpoint for a chain failed, the agent
  retried, fell back to another chain's data as clearly-labelled context, and
  issued a digest with explicit data gaps instead of hallucinating a balance.
  That run (`examples/run2-base-degraded.md`) is in our view the strongest
  evidence that the SDK's brain loop produces honest agents.

### 4. Freshness verification — WORKS but is non-obvious to satisfy

- The runtime classifies every request for freshness sensitivity and, for
  "exact-date" answers, demands **dated evidence in the tool outputs** before
  allowing the final answer.
- Our first three full runs were refused with "Missing exact-date evidence"
  even though every tool response contained timestamps — they were nested
  inside a JSON *string*, and the verifier only scans dict keys
  (`retrieved_at`, `observed_at`, `date`, ...).
- **Fix:** return structured dicts with a top-level `retrieved_at` key from
  every tool. After that, verification passed deterministically.
- **Lesson for other builders:** if your agent answers "state of the world
  right now" questions, put a machine-readable timestamp key in your tool
  outputs — not just in the payload text.

### 5. Action policy / confirmation flow — WORKS, Python API gap

- `action_policy.rules` accepts `block | ask | auto` modes; `default_action:
  allow` is accepted in config but ignored for `UNKNOWN_REVERSIBILITY` writes.
- Replying `allow_session` in-session grants the session — but the grant did
  not persist across separate `agent.run()` calls in our testing.
- The interactive CLI presumably answers confirmations inline; the Python API
  offers no obvious hook to do the same. Workaround: keep the agent read-only.

## Rough Edges We Hit (improvement feedback)

1. **OpenAI-compatible endpoints that always stream.** Our gateway replies
   with SSE even for `stream:false`, and labels SSE chunks
   `"object": "chat.completion"` instead of `chat.completion.chunk`. The
   SDK's strict parser rejects this. We run a 100-line local proxy that
   aggregates SSE into a single valid JSON response. Suggestion: a
   `provider.stream_mode: "auto-aggregate"` option would make OpenMinion
   work out-of-the-box with many self-hosted gateways.
2. **Global flags before subcommands.** `openminion config init
   --no-interactive` fails; `openminion --no-interactive config init` works.
   Consistent argparse-style placement would remove a common stumble.
3. **Freshness classifier is LLM-driven and per-run.** The same prompt can
   classify as `needs_exact_date=true` on one run and `false` on the next
   (we observed both within minutes). Dated evidence keys make verification
   robust either way, but a config knob to pin freshness behaviour for
   deterministic batch runs would help CI-style testing.
4. **String vs dict tool returns change verification semantics silently.**
   Documenting (or normalizing) the `outputs` wrapping for string returns
   would prevent hard-to-debug refusals.
5. **No Python-API hook for in-run confirmations.** A `run(prompt,
   on_confirm=callable)` would let headless integrations approve scoped
   writes without shell round-trips.

## What We Learned

- **Read-only agents are the sweet spot.** Designing every tool as
  READ_ONLY/idempotent eliminated the entire confirmation surface, made runs
  deterministic, and pushed the one durable write into the host CLI where it
  belongs. The policy friction pushed us into a better architecture.
- **Honest failure is a feature.** The degraded base-chain run produced a
  digest that says "unknown, re-run when endpoints recover" instead of
  inventing numbers. For a monitoring tool, that is exactly the behaviour an
  operator wants, and the SDK's verification/closure loop encouraged it.
- **Structured tool outputs beat pretty strings.** Machine-readable keys
  (timestamps especially) are load-bearing: the runtime's verification reads
  them, not your prose.
- **Data-source reachability is part of the product.** Three of five
  Blockscout instances 403 non-browser clients from datacenter IPs. Encoding
  that knowledge in the tool (and in the digest's data-quality section) turns
  an infrastructure annoyance into visible, honest output.
- **The SDK is inspectable.** Every blocker above was resolved by reading the
  installed package — the policy, freshness, and tool-result pipelines are
  small enough to understand, which is rare and valuable in agent frameworks.

## Run log summary

| Run | Chain | Outcome | Artifact |
|-----|-------|---------|----------|
| 1 | eth | ✅ full digest, risk flags | `sandbox/runs/digest-d8da6bf2-eth.md` |
| 2 | base | ⚠️ degraded (all endpoints 403) — honest data-gap digest | `examples/run2-base-degraded.md` |
| 3 | optimism | ✅ full digest, burst + dust-drop flags | `sandbox/runs/digest-d8da6bf2-optimism.md` |
