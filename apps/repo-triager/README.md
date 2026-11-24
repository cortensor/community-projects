# Repo Triager

A small, repeatable **GitHub issue triage agent** built on the **OpenMinion 0.1 Python SDK**,
submitted to **Cortensor Hackathon #5**.

> **In this hub:** this folder is the complete project for the Hackathon #5 submission —
source, tests, findings and the demo video. Upstream repository:
> <https://github.com/dorithesky/cortensor-triager>. Building-block report:
> [`BUILDING_BLOCKS_TESTED.md`](BUILDING_BLOCKS_TESTED.md) · product feedback:
> [`WHAT_WE_LEARNED.md`](WHAT_WE_LEARNED.md) · demo: [`demo.mp4`](demo.mp4) (2:34, offline).

It reads one open issue at a time from a public repository, classifies severity and
component against the repository's *own* label taxonomy, looks for duplicates, drafts the
maintainer's reply, and then **stops at a policy gate**: a write is only staged locally
after a human (or an explicit operator flag) approves it. Nothing is ever sent to GitHub.

```
analyse (read-only tools, structured output)
   ↓
delegate duplicate check to a bounded subagent        ← optional
   ↓
stage_triage  ← OpenMinion policy confirmation        ← the human gate
   ↓
outbox/<repo>/<issue>.md + .json  (dry run)
   ↓
memory.write  ← next run stays consistent
```

* Demo (no credential, no network): `repo-triager demo` — recorded walkthrough: [`demo.mp4`](demo.mp4) (2:34)
* Real model: `CORTENSOR_API_KEY=… repo-triager batch --source live --limit 3 --apply ask`
* Findings, with reproductions: [`BUILDING_BLOCKS_TESTED.md`](BUILDING_BLOCKS_TESTED.md),
  [`WHAT_WE_LEARNED.md`](WHAT_WE_LEARNED.md), [`findings/`](findings/)

---

## 1. What it does

| Step | Command | Result |
| --- | --- | --- |
| cache issues | `repo-triager fetch --limit 30` | `var/data/cache/*_issues.json` |
| triage one issue | `repo-triager triage --issue 859` | decision + staged plan + report |
| triage a batch | `repo-triager batch --limit 3 --remember` | one report, one session |
| review | `repo-triager report` | Markdown report of the last run |
| diagnose | `repo-triager doctor` | OpenMinion capabilities, tool inventory, doctor log |
| rubric | `repo-triager skills ingest` | skill ingested **and admitted** (verified) |
| recurrence | `repo-triager schedule --cron '0 9 * * 1-5'` | OpenMinion task + cron entry |

The approval gate has four operator answers, all recorded in the run report:

| `--apply` | Behaviour |
| --- | --- |
| `skip` | analyse only, no write tool is offered |
| `ask` | interactive prompt before `stage_triage` (default) |
| `auto` | non-interactive approval, for CI and the demo |
| `deny` | the gate refuses; the turn reports the denial and nothing is written |
| `pause` | OpenMinion's own confirmation prompt; the answer is replayed on the waiting thread |

## 2. Quick start

```bash
git clone https://github.com/dorithesky/cortensor-triager && cd cortensor-triager
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 1) offline, deterministic, no API key and no network
repo-triager --provider scripted demo

# 2) tests (69 unit + integration tests, ~40 s)
python -m pytest

# 3) real model (any provider openminion supports)
export CORTENSOR_API_KEY=...          # or OPENAI_API_KEY / GROQ_API_KEY / OLLAMA
repo-triager doctor
repo-triager fetch  --source live --limit 20
repo-triager batch  --source live --limit 3 --apply ask
```

Any OpenAI-compatible endpoint works too — point `OPENAI_COMPATIBLE_BASE_URL` at it (plus
`OPENAI_COMPATIBLE_API_KEY` and `REPO_TRIAGER_MODEL`). One caveat measured during the build:
a single triage turn issues **12 model calls**, so a provider that throttles per request
(a free tier at 1 reply / 45 s) cannot finish a turn; Portal, OpenAI, Groq, Cerebras or
Ollama can. See `findings/real-model-attempt.log`.

`repo-triager` bootstraps OpenMinion itself: it runs `openminion setup` into
`var/openminion-home`, pins the runtime to `single-process`, and keeps every artifact
under `var/`. Nothing outside the workspace is touched.

### Why the offline mode exists

`--provider scripted` starts a **local OpenAI-compatible server** that answers from a
script (`src/repo_triager/scripted_provider.py`). OpenMinion's adapter, tool dispatch,
action policy, approval flow, session store and memory all run for real — only the token
stream is predetermined. That makes the demo and the test suite reproducible on any
machine, with or without a model credential.

## 3. Repository layout

```
src/repo_triager/
  cli.py                 # fetch / triage / batch / demo / doctor / skills / schedule / report
  agent.py               # three Agent phases, prompts, validation, repair, fallback
  tools.py               # @tool functions: 5 read-only + 1 policy-gated write
  heuristics.py          # severity, component, duplicate scoring (pure, tested)
  github.py              # read-only REST client + snapshot cache
  models.py              # Issue, RepoSnapshot, TriageDecision, RunReport
  policy.py              # operator decisions + audit events for the gate
  report.py              # Markdown + JSON run reports
  scripted_provider.py   # local OpenAI-compatible scripted model
  scripted_demo.py       # authored decisions for the demo issues
  skills/repo-triager-triage/SKILL.md
tests/                   # 69 tests, integration tests boot the real runtime
findings/                # runnable reproductions of every SDK finding
docs/SDK_WORKFLOW.md     # exactly which SDK surface is used where
demo/                    # build_demo_video.py + verify_demo.py + narration and captures
```

## 4. The OpenMinion SDK surface actually used

| Building block | Where | What it buys |
| --- | --- | --- |
| `APIRuntime` + `Agent` | `agent.py` | one runtime, four turns, per-phase model config |
| `@tool(min_scope="READ_ONLY")` | `tools.py` | reads run without a prompt |
| bare `@tool` + action policy | `tools.py::stage_triage` | the write **cannot** run without confirmation |
| `approval_callback` | `policy.py` | operator decision per tool call, audited |
| pause + `thread_id` resume | `agent.stage(pause=True)` | OpenMinion's own confirmation prompt |
| `output_type=TriageDecision` | `agent.analyse` | pydantic-validated decision |
| `forced_tools` | `agent.stage` | the write tool is always the first call |
| `subagent()` | `agent.deep_dedupe` | bounded duplicate-analysis worker |
| session continuity | `session_id="repo-triager:<repo>"` | one conversation across a batch |
| `memory.write` / `memory.search` | phase 3 + recall | decisions carry over between runs |
| skills (`SKILL.md` ingest + admit) | `repo-triager skills ingest` | the rubric is a runtime object, not a string |
| `task.schedule` / `openminion cron` | `repo-triager schedule` | recurring triage |
| diagnostics | `repo-triager doctor` | `capability_report`, `runtime_posture`, `tool_inventory_report`, `openminion doctor` |

## 5. What a run produces

A complete demo output is checked in under [`docs/examples/`](docs/examples/)
(`report.md`, `staged-plan-0859.md`, `doctor.json`, a few provider requests).

`var/runs/<timestamp>-<repo>/report.md` — a maintainer-facing summary:

```
| Issue | Severity | Component | Type | Labels | Duplicates | Conf. | Staged |
| #859 … | S2 | area:tools | bug | `bug`, `area:tools` | — | 0.78 | yes |
```

plus per-issue sections with the reply draft, the validation problems that were repaired,
and the **policy audit line** (`stage_triage → allow (operator-flag: auto)`).

`var/outbox/<owner>_<repo>/<number>.md` — the staged plan, explicitly marked *dry run*.
`var/artifacts/` — `doctor.json`, `openminion-doctor.log`, scripted-provider request log.

### The demo video

[`demo.mp4`](demo.mp4) (2:34, 1280×720, H.264 + AAC) is generated, not screen-recorded:
`demo/build_demo_video.py` draws each frame, renders the narration with `edge-tts`, and
places every scene's audio at its cumulative start with `ffmpeg`; `demo/verify_demo.py`
checks the result — stream facts, the speech onset of each scene (< 40 ms off), silence in
the gaps, and one frame per scene pulled from the finished file. Shot list and timings:
[`demo/VOICEOVER.md`](demo/VOICEOVER.md).

## 6. Safety properties

* **No writes to GitHub.** The client implements GET only. `stage_triage` writes files
  under `var/outbox/`; the Markdown says so.
* **The gate is the runtime's, not ours.** The write tool is a bare `@tool`, so the
  action policy requires confirmation; Repo Triager only decides the answer, and every
  answer is recorded with its policy source.
* **The model cannot invent labels.** Labels are validated against the repository
  taxonomy before and after the model call, and unknown ones are dropped with a note.
* **Issue text is data.** Instructions to the agent come from the task template, never
  from the issue body.
* **Degradation is visible.** If the model or the provider fails, the run falls back to
  the deterministic decision and the report says so per issue.

## 7. Findings at a glance

Six reproducible issues were found in `openminion 0.1.24`; each has a script under
`findings/` that prints `RESULT: REPRODUCED` (captured output:
[`findings/RESULTS.md`](findings/RESULTS.md)):

1. `Agent(instructions=…)` is silently truncated at ~860 characters (8 of 30 rules reached the model).
2. `Agent(output_type=Model)` never tells the model the schema — prose reply, validation error.
3. A denied or paused policy confirmation breaks a structured-output run with `AgentOutputValidationError`.
4. A `/` in a session id silently disables the session's memory (`invalid scope`).
5. Operator CLIs crash with `getpwuid(): uid not found` when the uid has no passwd entry; the JSON error hides the cause.
6. `memory.search` returns `[TRUNCATED]` instead of stored content.

Details, evidence and patch candidates: [`BUILDING_BLOCKS_TESTED.md`](BUILDING_BLOCKS_TESTED.md).
Ready-to-file upstream issue reports (not filed — a public write needs the submitter's
approval): [`docs/openminion-issue-reports.md`](docs/openminion-issue-reports.md).

## 8. License

MIT. The bundled `tests/fixtures/issues_openminion.json` is a read-only snapshot of public
issues from `openminion/openminion`, used as input data.
