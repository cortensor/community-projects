# What We Learned

Only findings we actually reproduced while building this agent, each with
reproduction steps and evidence. Nothing here repeats upstream issues
`openminion/openminion#773` / `#774` / `#704`, the Verifier's findings, or
WV629's F1–F13 — those belong to their authors.

## 1. `create_isolated_runtime` does not exist in openminion 0.1.21

- **Reproduce:** `getattr(openminion, "create_isolated_runtime")` raises
  `AttributeError`; a full-package grep finds zero definitions.
- **Impact:** the reference work's helper of that name is its own wrapper,
  not SDK API. The working equivalent is
  `APIRuntime.from_config(config, home_root, data_root)` (verified: runtime
  builds in ~1.7 s).
- **Source:** SPIKE.md §2.2; re-confirmed by `probe_runtime_isolation`
  (builds a real isolated runtime in temp dirs).

## 2. The default config cannot start a runtime

- **Reproduce:** `OpenMinionConfig()` then `APIRuntime.from_config(...)`
  raises `ConfigValidationError: OpenMinionConfig.agents is empty`.
- **Impact:** the minimal runnable config must hand-fill one
  `AgentProfileConfig`; the docs don't make that obvious.
- **Source:** SPIKE.md §2.2.

## 3. An empty channel is rejected even in `warn` mode

- **Reproduce:** build the runtime without `default_channel` on the agent
  profile, run a turn: `RuntimeError: inbound authenticity denied
  (reason=invalid_channel, mode=warn)`.
- **Impact:** the error names the symptom, not the fix (`default_channel`
  must be `"console"`). The `warn` label is misleading — the turn is
  refused unconditionally for an empty channel.
- **Source:** SPIKE.md §2.2, first end-to-end attempt.

## 4. A native SDK turn cannot survive the Pollinations free tier (HTTP 402) — for structured work; the draft step works

- **Reproduce:** `Agent.run` against `https://text.pollinations.ai/openai/v1`
  with `model="openai"`, three attempts on 2026-11-17, all fail in the
  decide phase with `ProviderError: ... HTTP 402: Free limit reached:
  1 reply every 45 seconds per IP. Retry after 19s ...`. A single direct
  HTTP call in the same window returns 200 in ~2.3 s.
- **Why:** one SDK turn fires several consecutive model calls; the first
  consumes the quota and the rest hit 402 immediately.
- **And when it doesn't 402:** probe runs 4 and 5 (2026-11-16 18:07 and
  18:15 UTC) — the native turn survived the rate limit (144–162 s turns)
  and still failed both times: the model replied in prose starting with a
  `triage: ` prefix (`"triage: Sure, I want to ...ue #12 belongs to?"`,
  then `"triage: Issue #12 is a b...ing, JavaScript error)."`) instead of
  the requested `TriageVerdict` JSON, and `Agent.run` raised
  `AgentOutputValidationError`. So the native path is unreliable in two
  different ways on the free tier, not one. (Recorded as a run observation
  from our own probe runs; not claimed as a new SDK bug.)
- **Round 2–3 (2026-11-17, counting proxy on 127.0.0.1:8471):** with
  `output_type=TriageVerdict` the turn's provider calls DO go through
  (4 calls, all 200, ~77 s) but the model returns partial JSON and the
  SDK's strict coercion rejects it; with `output_type=None` the raw reply
  is `triage: {"issue_id":778,"status":"open","classification":"bug",
  "suggested_labels":[...],"assignee":null}` — the model invents its own
  field names despite an explicit full-schema contract, and a same-session
  follow-up asking for the missing fields returns **all nulls**. The SDK
  has no `response_format` / `json_object` support anywhere in its
  provider layer, so structured classify through `Agent.run` is not
  reliable on this tier. **The draft step works through the SDK:**
  `Agent.run` with `output_type=None` returned
  `triage: {"answer": "Thanks for reporting issue #778. I've triaged it
  as a high-severity bug in the brain module ...", "freshness": {...}}`
  in 65.6 s — the draft text is correct, inside the SDK's internal
  `{"answer": ...}` envelope. `sdk_triage.parse_sdk_draft` understands
  the `answer` envelope, a `{"draft": ...}` object, and plain prose.
- **Impact:** classify stays on the direct HTTP client (one call per step,
  paced ≥45 s, tool_calls + `response_format=json_object`); the draft
  step runs through a real `Agent.run` turn behind `triage --via-sdk`
  (falling back to the direct draft if the SDK turn yields no usable
  draft). The probe suite re-attempts native turns per full run and
  records the outcome honestly instead of claiming a pass; the new
  `sdk_native_draft` probe covers the working path.
- **Source:** SPIKE.md §4; `probe_tool_calls` (SDK half);
  `/tmp/sdk_round2.log`, `/tmp/sdk_round2_attempt{1,2,3}.json`,
  `/tmp/sdk_round3_classify.json`, `/tmp/sdk_round3_draft.json`;
  `src/issue_triage/sdk_triage.py`; probe `sdk_native_draft`.

## 5. Retry backoff is hardcoded to 300 ms and ignores `Retry-After` (new)

- **Reproduce (runtime, no grep):** call
  `openminion.modules.llm.providers.factory._runtime_llmctl_config(...)`
  with any provider payload — the returned config always contains
  `"retries": {"max_retries": 2, "backoff_ms": 300}`. The same literal
  `300` is hardcoded in `modules/llm/providers/bridge.py`. `AgentProfileConfig`
  (the public config surface) has no `retries` field, so no user-facing knob
  reaches this value. Inspecting `modules/llm/runtime/flow.py::_call_with_retries`
  at runtime shows the sleep is `(backoff_ms / 1000) * 2**attempt` and the
  function never reads a `Retry-After` header.
- **Numbers:** default `max_retries=2` gives waits of 0.3 s + 0.6 s = 0.9 s
  total — against a 45 s free-tier window. Even raising `max_retries` cannot
  help, because the base is 300 ms and the provider's own `Retry after 19s`
  is discarded.
- **Impact:** this is the structural reason finding 4 cannot be fixed by
  configuration: the SDK's retry machinery is unusable against any
  rate limit longer than ~1 s unless the code is patched.
- **Source:** probe `error_and_timeout_contracts` (runs the config builder
  and the source check live; also asserts our own client honours
  `Retry-After` on a stubbed 402).

## 6. The public `import_bundle()` persists nothing (new)

- **Reproduce:** `export_bundle([...])` → `save_bundle` → `load_bundle` →
  `import_bundle(bundle, trust_mode="direct")` returns
  `{"trust_mode": "direct", "item_count": 1, ...}`. The function takes no
  store or runtime argument and writes nowhere — reading its source shows
  it only validates `trust_mode` and builds the summary dict. No item is
  loaded into any memory.
- **Impact:** a caller following the documented round-trip gets a summary
  and zero items actually in memory. "Portability" at this layer is
  file-level only; the real load path is the internal
  `MemoryService.import_bundle_snapshot`. Our `RepoMemory.import_bundle_file`
  implements the missing half (validated by a round-trip pytest).
- **Note:** this differs from the Verifier's finding 6 (the file round-trip
  does work); the gap is specifically that the public import does not load
  anything into memory.
- **Source:** probe `memory_bundle_portability`; `tests/test_memory.py`.

## 7. Sandbox `NO_PROXY` breaks httpx worse than SPIKE recorded

- **Reproduce:** the sandbox `NO_PROXY` contains bare IPv6
  `fd8b:4f84:7d32:99::1` and bracketed `[fd8b:4f84:7d32:99::1]` in addition
  to the `[::1]` SPIKE.md §3 recorded. Constructing any `httpx.Client`
  raises `InvalidURL: Invalid port: '4f84:7d32:99::1]'` before any request.
- **Fix:** `config.fix_proxy_env()` now keeps only plain hostname / IPv4
  entries (optionally with a port) and drops everything containing `::` or
  brackets. Reproduced as 2 pytest failures before the fix, 0 after.
- **Source:** `tests/test_cli_config.py::test_fix_proxy_env_strips_ipv6_loopback`;
  `src/issue_triage/config.py`.

## 8. With tools offered, the free model may still answer in plain-text JSON

- **Reproduce:** live triage of `openminion/openminion#778` (2026-11-17,
  Pollinations `gpt-oss-20b`): the classify call was sent with a
  `submit_triage_verdict` tool *and* `response_format=json_object`, and the
  model answered with text JSON (`channel=text`, 23,464 ms). The draft call
  in the same run used `tool_calls` (18,115 ms).
- **Impact:** tool_calls cannot be the only parse path; text-JSON parsing
  is a production path, not a fallback. Both channels go through the same
  Pydantic model in `DirectClient.chat_typed`.
- **Source:** live run log, `eval`/`triage` run 2026-11-17 01:19 UTC;
  snapshot `.issue-triage/pending/openminion-openminion-778-fbb60bfb.json`.

## 9. Free-model label invention is real; enforce the vocabulary in code

- **Reproduce:** SPIKE.md §3.3 — with `json_object` requested, the model
  returned `"label": "failure"`, a value never in the candidate list.
  Structure was valid JSON; the semantics drifted.
- **Fix in this agent:** label-like fields are Pydantic `Literal` enums
  (an invented value fails validation and triggers one correction retry),
  and `suggested_labels` are filtered against the repo's real label list
  in code (`validate_labels` drops invented labels and reports them).
  Live evidence: on #778 the model suggested exactly the repo's real
  labels (`area:brain`, `bug`, `status:maintainer-investigation`).
- **Known gap:** `component` is a free string, not an enum — the same run
  returned `component="brain"` where the repo's label is `area:brain`.
  Component normalisation against `area:*` labels is future work.
- **Source:** SPIKE.md §3.3; `src/issue_triage/models.py`,
  `src/issue_triage/triage.py::validate_labels`; pytest `test_models.py`.

## 12. The free tier can 400 with an upstream constrained-decoding glitch — and cache the 400

- **Reproduce:** probe run 1, 2026-11-17 17:44 UTC, draft call (tools +
  `response_format=json_object`): HTTP 400 `{"code": "BAD_REQUEST",
  "message": "400 Bad Request: unexpected tokens remaining in message
  header: Some(\"<|constrain|>commentary\")"}` (upstream host
  `portkey.myceli.ai`). Probe run 2, five minutes later, hit the same
  draft call twice (17:49:13 and 17:49:58, 45 s apart — the client's
  pacing): **both 400s carried a byte-identical body with the original
  timestamp `17:44:28.306Z`**. The upstream replays the cached error for
  the same request for at least 5 minutes, so re-sending the identical
  constrained request cannot recover.
- **Not the trigger:** an A/B test of the same draft prompt with and
  without `reasoning_effort="low"` (2026-11-17 ~17:53 UTC) passed both
  ways — the 400 is a transient upstream state, not caused by the
  reasoning-effort flag. By then the cached error had expired.
- **Fix in this agent:** `draft()` retries once with a *different request
  shape* (plain text, no tools, no `json_object`) — a fresh cache key that
  bypasses the constrained-decoding path. The probe runner records a
  per-probe failure instead of aborting the whole suite (and still writes
  `BUILDING_BLOCKS_TESTED.md`).
- **Update 2026-11-17:** the same 400 hit two *classify* calls in the
  label-blind eval (#777, #773) despite the slim-prompt retry — so it is
  not draft-specific, and a shape-changing retry does not always escape
  it. The eval records those issues as errors and continues.
- **Update 2026-11-19:** `classify()` now uses the same shape-changing
  retry as `draft()` (slim prompt, plain text, no tools, no
  `json_object`) instead of the slim-prompt retry with the same shape,
  which failed on #777/#773. The 400 did **not** reproduce on demand
  the same day (a direct call with #777's exact production prompt
  returned 200 in ~9 s) — the glitch is transient upstream state, and
  the fallback is justified by the two recorded eval hits, not by a
  live reproduction. In the 2026-11-19 re-run eval over the same 13
  issues, #777 and #773 both scored (feature/bug, both correct) with
  zero provider errors (file `eval/results-20261119-1525.json`); the
  re-run used 13 calls with no retries, so the fallback never fired
  there — the live proof that the fallback itself recovers a 400 is
  still only the stub test in `tests/test_triage.py`, not a live hit.
  The enum half of the fix *is* live-proven: #767 scored via the new
  synonym map (see §13).
- **Source:** `/tmp/probe_full.log` (run 1), `/tmp/probe_full2.log` (run 2,
  two 400s at 17:49:13/17:49:58, same body timestamp), `scripts/ab_reasoning_effort.py`;
  `src/issue_triage/triage.py::draft`, `src/issue_triage/probe.py::run_probes`.

## 11. The free model can die with 400 `output_token_limit_exceeded` mid-run

- **Reproduce:** first eval run (2026-11-17 17:25 UTC), issue #778 classify
  call: HTTP 400 `{"code": "output_token_limit_exceeded", "message": "The
  model exhausted its output token limit before producing an answer.
  Increase the token limit or reduce reasoning effort."}` (upstream host
  `portkey.myce...`). The same prompt had succeeded 6 minutes earlier in
  the triage run — the failure is nondeterministic: the reasoning model
  sometimes spends its whole output budget on chain-of-thought and emits
  nothing.
- **Fix in this agent:** (a) every call now sends `reasoning_effort="low"`
  by default (overridable via `ISSUE_TRIAGE_REASONING_EFFORT`, empty =
  omit); (b) `classify` retries once on a slimmed prompt (short body, no
  comments/history/CODEOWNERS) after a provider error; (c) `run_eval`
  records a per-issue error and continues instead of aborting the run.
  All three are covered by `tests/test_eval_resilience.py`.
- **Source:** `/tmp/eval10.log` (first attempt); `src/issue_triage/llm_client.py`,
  `src/issue_triage/triage.py::classify`, `src/issue_triage/eval.py::run_eval`.

## 10. One model call per step is what makes the free tier usable at all

- **Reproduce:** the direct client paces calls ≥45 s apart and makes
  exactly one call per step (classify, then draft). The #778 end-to-end run
  took 86.6 s total for 2 calls (23.5 s + 18.1 s model time + 45 s pacing)
  with zero 402s. The 10-issue eval (10 calls) ran clean at the same pacing.
- **Corollary:** token accounting on Pollinations carries ~300 prompt tokens
  of fixed overhead even for tiny prompts (SPIKE.md §3.1: 333 prompt tokens
  for a ~30-token prompt) — budget by the metered number, not the prompt.
- **Source:** live triage + eval runs, 2026-11-17; `eval/results-*.json`.

## 13. The 0.9 eval accuracy was label-aware, not independent classification

- **The leak:** the classifier prompt included the issue's existing
  maintainer labels (`"Existing labels: bug"` — while asking whether the
  issue is a bug), and the eval used those same labels as ground truth.
  The reported accuracy 0.9 (10 real openminion issues, 2026-11-16) is a
  real measured agreement, but it measures label-copying as much as
  classification. The #778 claim ("verdict exactly matches the
  maintainer's actual labels") has the same limitation: the prompt showed
  the model those labels.
- **Fix:** `eval` is now label-blind by default (`--label-aware` restores
  the old leaky mode for comparison). In blind mode the prompt renders
  `"Existing labels: (hidden — evaluation mode; classify from the issue
  text only)"`; the repo label list stays (closed-vocabulary validation
  is legitimate — it constrains the answer space, it is not the answer).
  The result file records `"mode": "label-blind" | "label-aware"`.
  Production triage still shows existing labels (a human reviews them;
  only eval hides them).
- **Numbers:** label-aware baseline 0.9 (n=10; bug P 0.857 / R 1.0,
  feature P 1.0 / R 0.75; file `eval/results-20261116-1739.json`).
  Label-blind rerun 2026-11-17: **accuracy 1.0 (10/10)** — bug P 1.0 /
  R 1.0 (support 8), feature P 1.0 / R 1.0 (support 2); confidence
  ≥0.8 6/6, 0.5–0.8 4/4 (file `eval/results-20261116-2141.json`, 18.4 min
  wall clock). Hiding the labels did not hurt accuracy. Caveats: n=10
  each; the two runs scored partly different issue sets (blind set:
  780, 779, 778, 774, 770, 769, 766, 759, 757, 754); 3 further issues
  errored and were excluded (#777, #773: the `<|constrain|>commentary`
  HTTP 400 — this time on the classify call, despite the slim-prompt
  retry; #767: the model answered `enhancement` as the issue type, an
  invalid enum value). #778 blind: bug at confidence 0.90 (label-aware:
  0.80) — the *type* classification holds without the labels; the full
  "labels exactly match the maintainer's" claim stays label-aware-only.
- **Re-run 2026-11-19 (same 13 issues, fixed code):** accuracy **0.923
  (12/13)**, 0 errors, 0 skipped (file
  `eval/results-20261119-1525.json`, 13 model calls, no retries). All
  three previously errored issues now score and are correct (#777
  feature, #773 bug, #767 feature — the last via the new synonym map in
  `models.py`, which normalises maintainer-label synonyms such as
  `enhancement` → `feature` before Pydantic validation; unknown values
  still fail loudly). The single miss is #774 (predicted bug, truth
  feature, confidence 0.85) — it was correct in the 2026-11-17 blind
  run (feature, 0.60), so this is a nondeterministic flip, not a
  regression from the fixes. Per-class: bug P 0.9 / R 1.0 (support 9),
  feature P 1.0 / R 0.75 (support 4). Calibration: mean confidence
  0.821 correct vs 0.85 wrong — the one miss was high-confidence, so
  confidence does not separate it here; ≥0.8 bucket 8/9, 0.5–0.8 4/4.
  Read the headline honestly: 1.0 (n=10) became 0.923 (n=13) because
  the hard cases that were excluded now score — the set got harder,
  not the classifier worse.
- **Expansion 2026-11-19 (10 more issues, same mechanical rule):**
  newest-first scan below 754 took 7 from page 1 (752, 751, 745, 720,
  719, 718, 717; 7 skipped unlabelled/ambiguous) and 3 from page 2
  (663, 661, 660; 13 skipped) — files
  `eval/results-20261119-1541.json` and
  `eval/results-20261119-1551.json`, 0 errors in either. First batch
  0.571 (4/7), top-up 1.0 (3/3). **Combined with the re-run: n=23,
  accuracy 0.826 (19/23), 0 errors, 20 skipped.** Per-class: bug P
  0.8 / R 1.0 (support 16), feature P 1.0 / R 0.75 (support 4),
  question 0/0 (support 2), docs 0/0 (support 1). Failure mode is
  uniform: all 4 misses are false-positive bugs (#774 feature, #745
  docs, #719/#718 question) — on the older issues, non-bug reports
  read as bug reports. Confidence does not separate: mean 0.839
  correct vs 0.837 wrong; ≥0.8 bucket 15/18, 0.5–0.8 4/5. Two of the
  misses are ground-truth judgement calls, not pure classifier
  errors: #719/#718 describe failure behaviour in title and body but
  the maintainer labelled them questions (the discussion intent is
  not in the text), while #745's body says "documentation" outright
  and was still called bug — that one is a genuine miss on a clear
  signal. Open finding, not yet addressed: the prompt has no
  docs-vs-bug / question-vs-bug disambiguation.
- **Source:** `src/issue_triage/triage.py::_classifier_messages`
  (`hide_existing_labels`), `src/issue_triage/eval.py::run_eval`
  (`blind=True` default); `tests/test_triage.py`, `tests/test_eval.py`.

## 14. A tokenless `approve --yes` bricked the snapshot it was meant to run

- **Reproduce:** `approve --yes` without `GITHUB_TOKEN` called
  `store.approve_once()` (pending → approved, refuses non-pending)
  *before* checking the token. It printed "re-run with a token to
  execute" — but that re-run failed at `approve_once` with
  `NotPendingError`, because the snapshot was already "approved". One
  tokenless approve made the snapshot unexecutable.
- **Fix:** the token is now checked *before* any state change. A tokenless
  `--yes` prints the exact `gh api` commands and leaves the snapshot
  pending, so a later token-bearing run works. A token-bearing run on a
  snapshot stranded in "approved" by the old bug resumes straight to
  execution instead of refusing it. Write failures mid-execution leave
  the snapshot "approved" for retry, and a comment-dedup guard
  (`GitHubClient.find_comment`, exact-body match over the last 100
  comments) prevents double-posting if the process dies between the post
  and the consume.
- **Source:** `src/issue_triage/cli.py` (approve command),
  `src/issue_triage/approval.py`, `src/issue_triage/github_client.py::find_comment`;
  regression tests in `tests/test_approve_cli.py` (tokenless leaves
  pending; tokenless → token consumes; stranded approved resumes;
  partial-write stays approved then retries with exactly one comment).

## 15. The SDK turn's reply is prefixed and enveloped — and its 400s are non-fatal

- **The prefix:** every raw `Agent.run` reply in rounds 1–3 arrived as
  `triage: {...}` — including the draft turn, where the agent was
  constructed with `name="draft"`. The prefix is therefore not the
  `Agent` name; it matches the runtime's agent-profile name
  (`build_isolated_runtime` registers a profile called `"triage"`).
  The raw provider response (counting proxy) carries no prefix, so the
  prefix is introduced by the SDK turn loop. Consequence: the SDK's own
  typed coercion (`output_type=TriageVerdict`) rejects its own prefixed
  reply — a genuine SDK rough edge worth reporting upstream, recorded
  here as an observation, not a claim.
- **The envelope:** the draft turn's reply is the SDK's internal shape,
  `{"answer": "<draft text>", "freshness": {...}}`, not the requested
  `{"draft": ..., "tone": ...}`. The internal freshness/intent
  classification rounds leak into the final answer. `parse_sdk_draft`
  extracts the `answer` field (and also accepts a `{"draft": ...}`
  object and plain prose).
- **The 400s are non-fatal:** in every round-2/3 turn, one internal round
  sent `<|constrain|>commentary` tokens and got HTTP 400 (the cached
  upstream error from §12, byte-identical body, same timestamp). The SDK
  retried it 3× within ~2 s (useless — same cached 400), yet the turn
  still completed and produced its final answer. The 400 kills one
  internal round, not the turn.
- **CLI runs are 0/2 native (2026-11-17 21:42, 21:44 UTC):** two live
  `triage --via-sdk` runs on #778 both failed the SDK draft turn the same
  way (first call 200, then 9× 402; the fallback to the direct draft
  worked both times, verdict bug / needs-maintainer / confidence 0.95,
  snapshot saved pending). The pattern across all evidence: the turn
  completes only when its early internal rounds fail with the
  non-quota-consuming 400 glitch instead of returning 200s — i.e. a free-tier SDK turn currently succeeds only while the upstream glitch is
  active. No pacing wait in the CLI can fix this: the turn fires its
  calls ~1 s apart and needs more than one 200 inside a 45 s window.
  That is why `--via-sdk` is best-effort with a fallback, not the
  default path.
- **Update 2026-11-19 — one mitigation attempted, still 402:** `run()`
  now waits out the DirectClient pacing interval before starting the
  SDK turn, so the turn's first internal call lands in a fresh 45 s
  window instead of on top of the classify call. Live test the same
  day (`triage --via-sdk` on the #778 fixture): the turn still failed
  with HTTP 402 (`Retry after 31s`) and fell back to the direct draft
  (verdict bug / needs-maintainer / 0.70, snapshot saved pending). The
  fresh gap does not fix it — the turn needs more than one 200 inside
  the window, and the free tier allows one. Native SDK turns cannot
  survive the free tier; `--via-sdk` stays best-effort with fallback,
  not the default. The wait stays in the code as a best-effort (it can
  only help the first internal call) with a unit test; it is not
  claimed as a fix.
- **Source:** `/tmp/sdk_round2.log`, `/tmp/sdk_round3_classify.json`,
  `/tmp/sdk_round3_draft.json`, `/tmp/sdk_proxy_log.jsonl`;
  `src/issue_triage/sdk_triage.py::strip_sdk_prefix`,
  `::parse_sdk_draft`.

## 16. Linked PRs were numbers only; now their titles and bodies are fetched

- **The gap:** `github_client.py` extracted linked PR numbers from the
  timeline (`linked_pr_numbers`) but never fetched PR contents, while
  the README implied the triage read them.
- **Fix:** `GitHubClient.get_pull_summary` (pulls endpoint; 404/403 →
  `None`) and `IssueContext.linked_pr_details`; `fetch_context(...,
  fetch_linked_prs=True)` fetches up to 2 PR summaries, each body
  truncated to 400 chars in the prompt. The eval path passes
  `fetch_linked_prs=False` so the blind rerun's prompt matches the
  baseline run except for the hidden labels (and stays inside the
  unauthenticated GitHub 60 req/hour cap).
- **Source:** `src/issue_triage/github_client.py::get_pull_summary`,
  `src/issue_triage/triage.py::fetch_context`; tests in
  `tests/test_triage.py` (PR details in prompt, no-PR-fetch, stub serves
  `/pulls/770`).

## 17. The browser preview is now in the repo, hardened

- **The gap:** the try-out page lived only as a hosted artifact; the repo
  had no HTML/JS and the README documented no browser entry point.
- **Fix:** the built page source is committed as
  `docs/browser-preview/index.html` (exported from the artifact, then
  hardened), with launch instructions in `docs/browser-preview/README.md`
  and a smoke test in `scripts/smoke_browser_preview.py`.
- **Hardening (per the ChatGPT audit, verified live 2026-11-17):**
  `response_format: {type: "json_object"}` on the triage call only (the
  brief call stays prose; Pollinations accepts the field — verified by
  curl, 9.2 s, clean `{"a": 1}`); 105 s per-attempt timeout (was 90 s);
  the `tool_calls` + `content` envelope is parsed (some free-tier replies
  come back as a tool call); one bounded auto-retry on 402 after
  `max(47 s, Retry-After)` with a visible countdown, then a manual retry;
  the 45 s cooldown is remembered in `localStorage` across refreshes and
  tabs; the Start button stays disabled while a call is in flight;
  suggested labels are validated against the repo's real 31-label list
  (from `fixtures/openminion-issue-778.json`) exactly like the CLI does,
  and drops are shown; enum values and the 0–1 confidence range are
  validated the same way. The page is labelled a simplified one-call
  preview (classify only — no comments / linked PRs / CODEOWNERS /
  memory / approval gate / draft), not the full two-step CLI pipeline.
- **Source:** `docs/browser-preview/index.html`,
  `scripts/smoke_browser_preview.py` (static checks + a `--live`
  1-call check).
