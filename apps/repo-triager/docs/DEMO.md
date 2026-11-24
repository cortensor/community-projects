# Demo script (1–5 minutes)

## The recorded cut — `demo.mp4`

Built and verified on 2026-11-24: **2:34, 1280×720, H.264 + AAC, 5.3 MB**, English
narration, offline (scripted provider, no key, no network). Scene-by-scene script and
timings: [`demo/VOICEOVER.md`](../demo/VOICEOVER.md).

```bash
python demo/build_demo_video.py     # frames (Pillow) + narration (edge-tts) + ffmpeg mux
python demo/verify_demo.py          # ffprobe facts, per-scene audio onsets, sampled frames
```

The build measures each scene's narration and lays the scenes end to end, so the audio is
placed with `adelay` at the *cumulative* start of every scene rather than all at zero.
`verify_demo.py` proves it: every scene's speech onset lands within 40 ms of its planned
start, the gaps between scenes stay digitally silent (−180 dBFS measured), and one frame
per scene is pulled out of the finished MP4 for a look (`demo/build/verify-frames/`).

What it shows, in order: title and workflow → `doctor` on the real runtime → the demo run
(issue #859 → S2 `area:tools`) → the approval gate **allowed for #859 and denied for
#853** → the staged dry-run plan and the run report → the six SDK findings → the
truncation reproduction and `69 passed` on the suite.

## Recording it by hand instead (live model)

Two versions: an offline one that always works, and a live one with a real model. Record
the live one if you have a provider key; record the offline one as a fallback and label it.

```bash
repo-triager --provider scripted demo          # offline, ~40 s, no key needed
```

## Before recording

```bash
cd cortensor-triager
source .venv/bin/activate
rm -rf var                       # clean state, so the report is fresh
export CORTENSOR_API_KEY=...     # only for the live version
```

Terminal: 100×30, font 16+, dark background. Keep `BUILDING_BLOCKS_TESTED.md` open in a
second window for the findings section.

## Shot list

| # | Time | Screen | Say |
| --- | --- | --- | --- |
| 1 | 0:00–0:20 | `README.md` top | "Repo Triager is an issue triage agent for maintainers. It reads an issue, classifies it against the repository's own labels, drafts the maintainer reply, and stops at a human approval gate before anything is written." |
| 2 | 0:20–0:50 | `repo-triager doctor` | "OpenMinion is configured in-process. 106 tools registered, memory and skill tools present, doctor is green. This is the runtime the agent will use." |
| 3 | 0:50–1:40 | `repo-triager --provider scripted demo` | "The model is a local scripted provider so the run is reproducible; every other part — the runtime, the tools, the policy gate, sessions, memory — is the real thing." Point at: `#859 → S2 area:tools`, `tools used: [triage_precheck, get_issue, search_duplicate_issues]`, `12 LLM calls, 3 tool calls`. |
| 4 | 1:40–2:20 | same output, step 3 | "Now the gate. The write tool is a bare OpenMinion `@tool`, so the action policy requires confirmation. Approved → staged. Denied → refused, and nothing is written." Show `policy events` and `outbox:`. |
| 5 | 2:20–2:50 | `cat var/outbox/openminion_openminion/0859.md` | "The staged plan is a dry-run artifact: severity, component, labels, duplicates, and the reply draft. Nothing was sent to GitHub." |
| 6 | 2:50–3:20 | `repo-triager report` (or open `report.md`) | "Every run leaves an auditable report: the decision, the validation repairs, the policy decision with its source, and the model call counts." |
| 7 | 3:20–4:10 | `BUILDING_BLOCKS_TESTED.md` §1–2 | "The hackathon asks what broke. `Agent(instructions=…)` is truncated at about 860 characters — here are 30 rules, only 8 arrive. And `Agent(output_type=…)` never sends the schema to the model." |
| 8 | 4:10–4:40 | terminal: `python findings/repro_instructions_truncation.py` | Run it live: "8 of 30 rules survived, the turn still says completed." |
| 9 | 4:40–5:00 | `WHAT_WE_LEARNED.md` top | "Each finding has a reproduction, an impact, and a proposed change — two P0s, three P1s and a P2. The gate, the tool risk contract, and `subagent()` were the parts that needed no fighting." |

## Live version (real model)

The hackathon's objective asks for a demo that "shows a real model-backed run", so a live
segment is worth having even though the recorded cut is honest about being scripted. With
any unthrottled key (Cortensor Portal, Groq, Cerebras, OpenAI, or a local Ollama) the run
is 30–90 s per issue:

```bash
repo-triager fetch --source live --limit 20
repo-triager triage --source live --issue 859 --apply ask
```

If the only endpoint available is a *throttled free* one, `demo/paced_proxy.py` sits in
front of it and spaces the calls (the runtime retries twice with 300 ms backoff, which no
1-reply-per-45-s provider can satisfy):

```bash
UPSTREAM_BASE_URL=https://text.pollinations.ai/openai MIN_INTERVAL_SEC=45 \
    python demo/paced_proxy.py &          # 127.0.0.1:8787/v1
OPENAI_COMPATIBLE_BASE_URL=http://127.0.0.1:8787/v1 OPENAI_COMPATIBLE_API_KEY=local \
REPO_TRIAGER_MODEL=openai-fast repo-triager --provider configured triage --issue 859 --apply auto
```

Type `y` at the prompt on camera (that is the gate working with a real model). Then:

```bash
repo-triager report
```

Expect 30–90 s per issue on a hosted model; Portal can be slower. If the provider times
out twice, fall back to the offline demo and say so.

## Facts worth quoting on camera

* 69 tests, ~40 s: `python -m pytest`.
* One triage turn = 12 model calls (`act` 5, `entry` 2, `judge` 3, `freshness_classify` 1,
  `reflect` 1) and ~75 K input tokens — `python findings/measure_turn_cost.py`.
* The write tool cannot run without confirmation: enforced by OpenMinion's action policy,
  not by Repo Triager.
* 44 real open issues and 31 labels from `openminion/openminion` ship as the offline
  snapshot (`tests/fixtures/issues_openminion.json`).
