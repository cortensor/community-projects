# Issue Triage Agent — single-issue deep triage + routing

> **One issue, fully routed.** Give it `owner/repo#N` and it reads the
> issue, its comments and linked PRs, then tells you **what it is, how bad
> it is, which component it belongs to, who should own it, and which queue
> it goes to** — with a confidence score and reasons. A draft first reply
> is included. Nothing is ever posted without a human saying yes.

Built for **Cortensor Hackathon #5** with `openminion==0.1.21`. Free tier
only: the default model is Pollinations (no key, $0).

## Why this, not another batch triager

Every other triage entry in this hackathon is a **batch** shallow
classifier: read 20 issues, suggest labels, rank the top 5. None of them
does a single issue in depth, none routes to a person or a queue, and none
reports confidence. This agent's main mode is the opposite:

| | Batch triagers (5 known competitors) | This agent |
|---|---|---|
| Main mode | whole-repo batch | **single-issue deep dive** (`--issue N`) |
| Component / owner | none | **component + suggested assignee** (CODEOWNERS / contributors / history) |
| Confidence + reasons | none | **confidence 0–1 + rationale + evidence quotes** |
| Routing decision | "suggested labels + next step text" | **route enum** (`ready-to-fix`, `needs-info`, `good-first-issue`, `needs-maintainer`, …) |
| Approval gate | 2 of 5 have one | fail-closed snapshot gate, single-use |
| Quantified eval | fixture-only (5/5, 4/6) | **real repo, maintainer labels as ground truth** (see below) |

Batch mode exists (`--limit N`) but is a side feature, not the pitch.

## Install

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
cp .env.example .env   # optional; defaults already point at Pollinations (free)
```

Requirements: Python ≥3.11, `openminion==0.1.21` (pinned), pydantic,
httpx, typer, pytest.

## Quickstart

```bash
# Deep-triage one real issue (2 model calls, ~2 min: paced ≥45 s apart)
issue-triage triage --repo openminion/openminion --issue 778

# Same, from a URL
issue-triage triage --issue-url https://github.com/openminion/openminion/issues/778

# Batch as a side feature (N open issues)
issue-triage triage --repo openminion/openminion --limit 5

# Zero-LLM-cost demo from the bundled fixture
bash scripts/demo.sh

# Draft via a real OpenMinion Agent.run turn (classify stays direct — see below)
issue-triage triage --repo openminion/openminion --issue 778 --via-sdk
```

`triage` prints the verdict + draft reply and saves a **pending snapshot**
under `.issue-triage/pending/`. It never touches GitHub.

## Browser preview

The same triage, clickable in a browser — no install, no key:

```bash
python3 -m http.server 8000 --directory docs/browser-preview
# open http://localhost:8000/index.html
```

`docs/browser-preview/index.html` is a single self-contained page (issue
triage + paper deadlines + hackathon watch + the three Build texts). The
triage tab is a **simplified one-call preview** — classify only, with the
same model and prompt shape as the CLI; it does not fetch comments /
linked PRs / CODEOWNERS, has no memory, and never posts anything. Full
details and the smoke test (`scripts/smoke_browser_preview.py`) are in
`docs/browser-preview/README.md`.

### Approve (the only write path)

```bash
# Execute once: apply labels + post the draft comment (needs GITHUB_TOKEN)
issue-triage approve --snapshot openminion-openminion-778-fbb60bfb --yes

# Or reject: nothing is sent, the snapshot is blocked
issue-triage approve --snapshot openminion-openminion-778-fbb60bfb --no
```

Without `GITHUB_TOKEN`, `--yes` prints the exact `gh api` commands for a
human to run instead of pretending it succeeded — and the snapshot stays
**pending**, so a later token-bearing run still works (the token is
checked *before* any state change). An approved snapshot is **consumed
once** — a second approve is refused (anti-replay). A snapshot stranded
in "approved" by the old tokenless bug resumes straight to execution
instead of being refused.

## Architecture

```
issue-triage triage --repo o/r --issue N
  │
  ├─ GitHub (public reads, no auth needed)
  │   issue + comments + timeline (linked PRs: titles + bodies, up to 2)
  │   + repo labels + CODEOWNERS + top contributors + past decisions
  │
  ├─ Classifier subagent ── 1 model call ──▶ TriageVerdict (Pydantic)
  │   type / severity / component / labels / assignee / route /
  │   confidence + rationale + evidence. Labels are filtered in code
  │   against the repo's real label list; invented labels are dropped.
  │
  ├─ Drafter subagent ──── 1 model call ──▶ TriageDraft (isolated context:
  │   only the verdict + issue summary, no shared transcript)
  │
  └─ Snapshot (.issue-triage/pending/<repo>-<n>-<hash>.json, pending)
        └─ human approve ─▶ labels + comment posted once (or gh commands)
```

**Why a direct HTTP client for classify, and SDK `Agent.run` for draft:**
one native SDK turn fires several consecutive model calls; on the
Pollinations free tier (1 reply / 45 s / IP, HTTP 402) the first call
consumes the quota and the rest fail, and the SDK's retry backoff is
hardcoded to 300 ms and ignores `Retry-After` (see
`docs/WHAT_WE_LEARNED.md` §5). Worse, the SDK has no `response_format` /
`json_object` support, so the free model free-forms its classify JSON —
it invents its own field names and a same-session follow-up returns all
nulls (measured 2026-11-17, §4). Classify therefore stays on the direct
client: exactly one call per step, paced ≥45 s apart, honouring
`Retry-After`, parsing answers through two channels — `tool_calls` first,
plain-text JSON second — both validated by the same Pydantic model. The
**draft** step does run through a real `Agent.run` turn
(`triage --via-sdk`, `output_type=None`, raw reply parsed at the app
level — the reply arrives as `triage: {"answer": ...}`); if that turn
yields no usable draft it falls back to the direct draft, and the CLI
prints which engine produced each part. The probe suite covers both
sides (`tool_and_forced_tools`, `sdk_native_draft`).

**Memory:** past decisions per repo live in `state/<owner>__<repo>.json`
and are handed to the classifier as reference, so labels and routes stay
consistent inside one repo. Export/import uses the SDK `MemoryBundle`
round-trip; note the SDK's public `import_bundle()` persists nothing —
our `RepoMemory.import_bundle_file` does the actual load
(see `docs/WHAT_WE_LEARNED.md` §6).

## Provider presets

| Preset | Endpoint | Key | Status |
|---|---|---|---|
| `openai-compatible` (default) | `https://text.pollinations.ai/openai/v1`, model `openai` (runs `gpt-oss-20b`) | none | works, $0 |
| `cortensor-portal` | `CORTENSOR_PORTAL_BASE_URL` | `CORTENSOR_PORTAL_API_KEY` | preset only — needs official access coordination |
| `cortensor-router` | `CORTENSOR_ROUTER_BASE_URL` | `CORTENSOR_ROUTER_API_KEY` | preset only — needs official access coordination |

Switch with `--preset` or `ISSUE_TRIAGE_PRESET`. Portal/router never
block the default flow. OpenRouter `:free` models are **not** wired in:
they need a key from Allen, and no key is ever invented or stored here.

## Evaluation (real repo, maintainer labels as ground truth)

```bash
issue-triage eval --repo openminion/openminion --limit 10   # ~10 min, 1 call/issue
issue-triage eval --repo openminion/openminion --limit 30   # ~25 min
```

<!-- EVAL-RESULTS: filled from eval/results-*.json after the run -->

Real run, 2026-11-17, `openminion/openminion`, 10 most recent labelled
issues, Pollinations `gpt-oss-20b`, $0 — evidence in
`eval/results-20261116-1739.json` (11.7 min wall clock, 12 model calls:
10 + 2 slim-prompt retries after `output_token_limit_exceeded`):

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| bug | 0.857 | 1.000 | 0.923 | 6 |
| feature | 1.000 | 0.750 | 0.857 | 4 |

Overall **accuracy 0.9 (9/10)**, 0 errors, 0 skipped. The single miss
(#777, `enhancement` predicted as `bug`) came with confidence 0.70 —
the model was correctly unsure.

**Read that 0.9 as the label-aware baseline, not independent accuracy:**
the prompt showed the model each issue's existing maintainer labels
while asking it to classify, and the eval scored against those same
labels. `eval` is now **label-blind by default** — the prompt hides the
existing labels (`eval --label-aware` restores the old mode for
comparison) — and every result file records its `"mode"`. Both numbers
are reported wherever the accuracy appears; see
`docs/WHAT_WE_LEARNED.md` §13.

Confidence calibration (label-aware run): mean confidence 0.839 on
correct vs 0.70 on wrong; predictions with confidence ≥0.8 were 6/6
correct; 0.5–0.8 were 3/4. High confidence means something here; low
confidence is the signal to route to a human.

Label-blind rerun, 2026-11-17, same repo, Pollinations `gpt-oss-20b`,
$0 — evidence in `eval/results-20261116-2141.json` (18.4 min wall
clock): **accuracy 1.0 (10/10)** — bug P 1.0 / R 1.0 (support 8),
feature P 1.0 / R 1.0 (support 2); confidence ≥0.8 was 6/6, 0.5–0.8 was
4/4. Hiding the labels did not hurt: the classifier reads the issue
text, it was not copying labels. Caveats: small n (10 each), and the two
runs scored partly different issue sets — the blind set is 780, 779, 778,
774, 770, 769, 766, 759, 757, 754 (two issues are new since the baseline
run); three further issues errored and were excluded from the 10 (#777,
#773: the `<|constrain|>commentary` HTTP 400, despite the slim-prompt
retry; #767: the model answered `enhancement` as the issue type, which
is not a valid enum value). #778 blind: bug, confidence 0.90
(label-aware: 0.80).

Re-run with the fixes, 2026-11-19, the same 13 issues (10 scored + 3
previously errored), Pollinations `gpt-oss-20b`, $0 — evidence in
`eval/results-20261119-1525.json` (13 model calls, no retries):
**accuracy 0.923 (12/13), 0 errors.** All three previously errored
issues now score and are correct (#777 feature, #773 bug, #767 feature
— the last via the new enum-synonym map). The single miss is #774
(predicted bug, truth feature, confidence 0.85), which was correct in
the 2026-11-17 blind run — a nondeterministic flip, not a regression.
Per-class: bug P 0.9 / R 1.0 (support 9), feature P 1.0 / R 0.75
(support 4). The headline moved from 1.0 (n=10) to 0.923 (n=13)
because the excluded hard cases now score; the set got harder, not
the classifier worse. Note: the submitted DoraHacks Build 1 description now reports the combined 19/23 (updated 2026-11-21); it previously said label-blind 10/10, the 2026-11-17 number on the 10-issue scored set.

Expansion, 2026-11-19, continuing the newest-first scan below 754
(selection rule: the first issues with unambiguous ground truth; 20
skipped as unlabelled/ambiguous across the two runs, counted not
hand-picked), Pollinations `gpt-oss-20b`, $0 — evidence in
`eval/results-20261119-1541.json` (7 issues: 752, 751, 745, 720, 719,
718, 717) and `eval/results-20261119-1551.json` (3 issues: 663, 661,
660; page 2 of the issues list, below 717): **expansion accuracy
0.571 (4/7)** on the first batch and **1.0 (3/3)** on the top-up,
**0 errors in either**. Combined with the re-run: **n=23, accuracy
0.826 (19/23), 0 errors**. Per-class combined: bug P 0.8 / R 1.0
(support 16), feature P 1.0 / R 0.75 (support 4), question P 0 / R 0
(support 2), docs P 0 / R 0 (support 1). The failure mode is uniform:
all 4 misses are false-positive bugs — a feature request (#774), a
docs issue (#745), and two questions (#719, #718) all read as bug
reports to the classifier. Confidence does not separate right from
wrong here: mean confidence 0.839 correct vs 0.837 wrong; the ≥0.8
bucket is 15/18 and 0.5–0.8 is 4/5. The headline to quote is the
combined one, 19/23, not the 10/10 of the 2026-11-17 blind run (which
excluded the 3 hard cases) — and the submitted DoraHacks Build 1 description now reports 19/23 as well (updated 2026-11-21).

Run a bigger batch with the same command and a larger `--limit`
(30 issues ≈ 25 min, 50 ≈ 40 min, paced ≥45 s apart).

## Probes

```bash
issue-triage probe                 # full suite, regenerates docs/BUILDING_BLOCKS_TESTED.md
issue-triage probe --probe tool_and_forced_tools
issue-triage probe --offline       # only the no-model probes
```

11 probes, each run for real against the block it names. Statuses are
`pass` / `partial` / `fail` — the SDK-native `Agent.run` probes are
honestly marked `fail`/`partial` with the 402 evidence, not claimed as
passes; the new `sdk_native_draft` probe covers the one SDK-native step
that demonstrably works on the free tier (the draft turn). See
`docs/BUILDING_BLOCKS_TESTED.md` (auto-generated) and
`docs/WHAT_WE_LEARNED.md` (only findings we actually reproduced, with
steps — including two new SDK rough edges: the hardcoded 300 ms retry
backoff and the no-op public `import_bundle()`).

## Tests

```bash
.venv/bin/python -m pytest -q   # 113 tests, loopback HTTP stubs, zero LLM cost
```

Covers CLI parsing, verdict validation (illegal enum values rejected),
the approval state machine (allow / deny / pause-resume / single-use
anti-replay), memory storage + bundle round-trip, GitHub parsing,
the LLM client's dual-channel parsing, pacing and 402 handling, and eval
metrics.

## Files

| Path | What it is |
|---|---|
| `src/issue_triage/` | the package (`cli`, `triage`, `sdk_triage`, `llm_client`, `github_client`, `memory`, `approval`, `eval`, `probe`, `config`, `models`) |
| `tests/` | 113 pytest tests (stubbed, $0) |
| `docs/browser-preview/` | the try-out page source (`index.html` + `README.md`) |
| `scripts/smoke_browser_preview.py` | smoke test for the browser preview (static + optional 1 live call) |
| `fixtures/openminion-issue-778.json` | real public issue snapshot (openminion/openminion#778) + repo labels |
| `scripts/demo.sh` | one-command demo on the fixture (2 real model calls, ~2 min) |
| `scripts/run_eval_set.py` | label-blind eval over an explicit set (`--numbers`) or a mechanical continuation scan (`--next-below` / `--page`) |
| `demo-video/issue-triage-demo.mp4` | demo video (1:05, real run output, re-rendered after the audit fixes) |
| `docs/BUILDING_BLOCKS_TESTED.md` | probe results (auto-generated) |
| `docs/WHAT_WE_LEARNED.md` | reproduced findings only |
| `SPIKE.md`, `probe_*.py` | pre-implementation spike: SDK + Pollinations verification |
| `eval/results-*.json` | eval evidence (kept in the repo) |

## Limitations (honest)

- The free model is `gpt-oss-20b` via Pollinations: JSON structure is
  stable, label semantics drift — hence `Literal` enums + code-enforced
  label filtering. `component` is still a free string (on #778 it returned
  `brain` where the repo label is `area:brain`); normalising it against
  `area:*` labels is future work.
- One issue costs ~2 min (45 s pacing × 2 calls); a 30-issue eval costs
  ~25 min. That is the price of the free tier, not a bug.
- No `GITHUB_TOKEN` in the environment means `approve --yes` cannot
  execute — it prints commands instead. This is by design (fail-closed).
- `eval` ground truth is maintainer labels, which are noisy: an issue can
  carry `bug` + `enhancement` at once (counted as ambiguous and skipped).
- SDK `Agent.run` cannot do the classify step on the free tier (no
  `response_format` support; the model invents JSON field names and a
  follow-up returns all nulls). `--via-sdk` runs only the draft through
  the SDK and falls back to the direct draft when the turn fails — the
  failure is printed, never hidden.
