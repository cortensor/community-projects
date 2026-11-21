# What We Learned

Findings from actually building and running Paper Deadline Watch
(`openminion==0.1.21`, free Pollinations endpoint, 2026-11-17). Every item
below was observed in a run, not inferred from docs. Nothing here repeats
another entry's upstream issues — these are this project's own findings.

## 1. The sandbox's `no_proxy` breaks the SDK's HTTP client

**Observed:** every `Agent.run()` failed before any request with
`ProviderError: ... InvalidURL: Invalid port: ':1]'`.

**Root cause (reproduced with plain httpx):** `ProviderHTTPClient` builds
`httpx.Client(follow_redirects=True, trust_env=True)`. This sandbox's
`no_proxy` contains bracketed IPv6 entries (`[::1]`,
`[fd8b:4f84:7d32:99::1]`); httpx mangles one into a URL with port `:1]`.
`trust_env=False` avoids the parse error but then there is no direct
egress (connection timeout) — the egress proxy is mandatory.

**Fix in this repo:** `config.sanitize_no_proxy()` strips bracketed
entries from `no_proxy`/`NO_PROXY` in-process before any runtime is built
(the proxy itself stays). Verified: the same request then returns HTTP 200.

**Reproduction (zero model cost):**

```python
import httpx
httpx.Client(follow_redirects=True, trust_env=True).post(
    "https://text.pollinations.ai/openai/v1/chat/completions",
    json={"model": "openai", "messages": [{"role": "user", "content": "Hi"}]},
)  # raises InvalidURL: Invalid port: ':1]'
```

Upstream note: the SDK could construct its client with an explicit
`proxy=` and a cleaned `no_proxy`, instead of trusting the environment
verbatim.

## 2. Pollinations free tier is 1 reply / 45 s per IP — and the SDK's retry cannot beat it

**Observed:** `HTTP 402: Free limit reached: 1 reply every 45 seconds per
IP. Retry after Ns`. The SDK retries internally at ~300 ms, so an
in-window retry is guaranteed to 402 again.

**Fix in this repo:** `agent.run_agent_with_retry()` catches the 402,
sleeps `Retry-after + 5 s`, and retries up to 3 times; plus
`config.pace_model_call()` keeps 50 s between model calls in-process.
The limit is per egress IP, so other agents sharing the IP still consume
the slot — a retry can legitimately fail, and then the brief falls back
to the labelled template instead of failing the command.

## 3. Free-model replies need defensive JSON parsing

**Observed:** with `output_type=BriefSynthesis`, the SDK raised
`AgentOutputValidationError` on the reply `'paper-watch: 2+2 equals 4.'`
— the model answered in prose, and the SDK prefixes replies with
`agent_id: `.

**Fix in this repo:** run with `output_type=None`, read `result.text`,
strip the `name: ` prefix, extract the first balanced `{...}` object,
then Pydantic-validate. Any failure → template brief, with the raw reply
kept in the run record. The citation table is never model-written, so a
prose reply costs nothing but the synthesis paragraphs.

## 4. The deadline cells need three parsers, not one

**Observed in the verified tables:** `full_deadline` mixes ISO dates,
English month names (`Dec 8, 2026`), `TBD`, `rolling - no fixed
deadline`, and multi-track `;`-separated cells (`2026-10-25 (Long);
2026-11-16 (Short)`). One journal `fixed_deadline` holds two dates
(`2026-11-30; 2026-12-30`). Invalid calendar dates (`2026-02-30`)
appear and must be skipped, never "corrected".

**Fix in this repo:** `dates.py` splits on `;`, parses ISO + both
English month orders per segment, keeps the segment's parenthetical
track label, and returns the earliest date >= today. Covered by
`tests/test_dates.py`.

## 5. The tables have traps a naive loader drops or doubles

**Observed:**
- 18 journal rows have an empty `abbreviation` (full name present, e.g.
  `Neural Networks` with a real 2026-12-01 fixed deadline). Skipping
  empty-abbreviation rows silently loses a deadline that is inside the
  120-day window.
- `CLSR` appears in both the journals and the law table with the
  identical name and date — one venue, listed twice.
- `FSE` / `SEC` are each *two different venues* sharing an abbreviation
  (Foundations of Software Engineering vs Fast Software Encryption;
  Edge Computing vs IFIP Information Security). Dedup by abbreviation
  alone would delete a real venue.

**Fix in this repo:** identifier falls back to `full_name` when the
abbreviation is empty; dedup key is
`(abbreviation, full_name, date, deadline_kind)`.

## 6. Model calls are the slow part; everything else is instant

**Observed:** the deterministic path (`deadlines`, template brief,
`--skip-model` probe) runs in ~1 s; a model brief needs 4 paced calls
(2 subagents + synthesis + reminder) and is dominated by the 45 s free
window and model latency, not by our code. Design consequence: the
default `deadlines` command never touches the model, and the brief
always has a template to fall back to.

## 7. Live-run outcomes (2026-11-17, Pollinations free, $0)

- **Model brief (topic 人工智能): SUCCEEDED on the second attempt**
  (`fixtures/live_run_2026-11-17_brief-ai.json`, `path: "model"`).
  The model returned valid `BriefSynthesis` JSON: nearest CVPR
  (2026-11-16, verified), A-level `[CVPR]`, all four paragraphs copied
  real venues/dates/statuses from the tool output — no hallucinated
  venue. Total 900.2 s for the whole brief; the synthesis run alone
  321.6 s. Stats for that run: `input_tokens` 19860,
  `output_tokens` 3168, `llm_calls` **8**, `tool_calls` 1,
  `tool_errors` 0.
- **One `Agent.run()` = 8 LLM calls.** The stats above show the SDK
  issues 8 model calls per run (decision + tool loop + internal
  classification turns). On a 1-reply-per-45-s free tier, a single brief
  (4 runs) therefore needs ~32 replies from the shared IP pool — that
  is why the free-tier flow is slow and why the subagents below failed.
- **Subagents are the fragile part on the free tier.** Both brief
  subagents failed in the live run: conferences with
  `EMPTY_PROVIDER_RESPONSE` ("Provider returned no usable entry
  response after configured retries" — a failure mode distinct from
  the 402), journals/law with a 402 that survived 3 retries. The
  brief still succeeded because the main synthesis re-queries the
  tools itself; subagent notes are advisory only, never load-bearing.
- **Reminder formatting also 402'd** after retries, and the handoff
  was not taken (`handoff_taken: false`) — the free model did not
  transfer to the formatter agent. The reminder is therefore
  best-effort on this tier; the brief itself is unaffected.
- **First attempt (before the 402 retry was added): all 3 model calls
  402'd and the command fell back to the labelled template brief.**
  The fallback path is exercised, not theoretical.
- **Full probe suite:** 5/10 pass on the first full run
  (`docs/BUILDING_BLOCKS_TESTED.md`, 940.7 s total):
  runtime_isolation, subagent_delegation, submit_turn_streaming_telemetry,
  memory_bundle_portability, error_and_timeout_contracts passed;
  structured_output and tool_and_forced_tools partial (the free model
  answered in prose instead of JSON, and its tool reply carried
  SDK-internal freshness language — see §8); session_continuity failed
  on a 402 that survived retries; agent_handoff partial (see §9);
  verification_honesty failed on a checker bug, not on the agent (the
  checker matched abbreviations by substring, so ICWSM's full name
  tripped "AAAI"; fixed to (abbreviation, full_name) identity matching
  and re-verified 0 violations — see §5).
- **Telemetry tokens are present here.** The streaming probe's
  `stats` carried `input_tokens` 8826 / `output_tokens` 829 /
  `llm_calls` 2 — not zero. (Another entry reported zero token counts
  in `TurnTelemetry`; in this SDK version the `AgentRunResult.stats`
  path reports them. Not claimed as a bug either way.)

## 8. SDK-internal language leaks into free-model replies

**Observed in the probe:** the tool probe's reply was not the requested
JSON but: *"I couldn't provide a grounded current general answer
because Missing exact-date evidence for an exact-date freshness
answer."* "Freshness answer" is the SDK's internal classification
vocabulary (its `FreshnessContract` turn), surfacing verbatim in the
agent's reply. The streaming probe similarly answered *"I could not
safely update the task conditions."* These are not model hallucinations
about our data — they are the runtime's own guardrail phrasing bleeding
through on a weak free model.

## 9. Handoff is policy-gated, not free

**Observed in the probe:** transferring to the formatter agent did not
run the target; instead the reply was a policy confirmation prompt:
*"Policy confirmation required. format_reminder / Risk: write / Side
effects: local / Reversibility: unknown / Choices: allow_once,
allow_session, deny / Reply exactly y …"*. A handoff therefore needs
an approval path (or a pre-issued grant) to complete; without one the
turn stalls. This explains the brief run's `handoff_taken: false` —
the formatter was then called directly instead.
