# Hackathon Watch

A Hackathon Watch agent for **Cortensor Hackathon #5** (DoraHacks, build
period Oct 16 – Dec 18, 2026; $1,150 prize pool in $COR).

It watches public hackathon list pages, spots newly listed events, and
gives a **preliminary** suitability call against one person's profile —
free-only, online-first, non-student adult, LLM / Agent / AI-app /
legal-AI direction, resident in Singapore / US. Every verdict is
labelled preliminary and needs human confirmation on the official page
before anyone registers. Nothing here registers, logs in, or pays for
anything.

## Quickstart

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/hackathon-watch check                 # fetch 3 sources, diff vs memory
.venv/bin/hackathon-watch list --limit 10       # baseline entries
.venv/bin/hackathon-watch probe                 # building-block probes
bash scripts/demo.sh                            # full $0 demo (pytest + list + check + probe + 1 live call)
```

Requirements: Python 3.11+, `openminion==0.1.21`, `pydantic`, `httpx`,
`typer`, `pytest`. No API key is needed for the default preset
(Pollinations free text endpoint, no key). No key is ever written to
disk by this package; keys come from the environment only, at call time.

## Commands

| Command | What it does |
|---|---|
| `hackathon-watch check [--sources dorahacks,devfolio,kaggle] [--live-classify] [--max-model-calls 5]` | Fetch the public list pages, diff against memory, print new entries and the preliminary-suitable alerts. Rules only by default; `--live-classify` spends at most N short model calls on entries the rule screen left `unsure`. First run with empty memory seeds memory from the bundled 2026-11-16 baseline (170 entries) so known events are not all reported as new. |
| `hackathon-watch list [--limit N]` | List the baseline's currently-open entries (reads `data/*.md`). |
| `hackathon-watch memory export [--dest PATH] [--bundle]` / `memory import SRC [--bundle]` | Export/import memory as JSON, or as an OpenMinion `MemoryBundle`. |
| `hackathon-watch probe [--offline]` | Run the building-block probes and regenerate `docs/BUILDING_BLOCKS_TESTED.md`. |

## Architecture

```
list page (public HTML)            memory (local JSON)
        |                                  |
        v                                  v
sources.py  -- parse (regex/HTML, no model) --> check.py -- diff by normalised URL
        |                                  |
        +--> suitability.py -- rule screen (deterministic, free)
        |         |
        |         +-- unsure only --> llm_client.py -- DirectClient
        |         |                   (1 call/entry, paced >=45 s,
        |         |                    tool_calls first, text JSON second,
        |         |                    both validated by Pydantic)
        |         v
        +--> alerts: new AND preliminary-suitable, with source link
                  + discovery time + "preliminary, confirm on official page"
```

- **Deterministic first.** Fetching, parsing, normalising, deduping and
  the rule screen never touch the model. The model only classifies
  entries the rules left `unsure`, one short call each, capped per run
  (default 5). A normal check costs 0–5 calls and a few thousand tokens.
- **Main road vs SDK road.** `DirectClient` (one HTTP call per step,
  paced) is the main road, because one native SDK turn fires several
  consecutive model calls and the Pollinations free tier allows 1 reply
  / 45 s / IP (HTTP 402) — the native turn fails 3/3 in that window
  (see `docs/WHAT_WE_LEARNED.md`). The SDK `Agent` road
  (`agent.py`: isolated runtime, read-only lookup tool, classifier
  agent, subagent, handoff) is built, constructed, and exercised by the
  probe suite; it is the road to use once a Portal/Router preset with a
  surviving turn is available. Switching presets never changes
  application code: `openai-compatible` (default, Pollinations) /
  `cortensor-portal` / `cortensor-router`.
- **Memory.** `state/memory.json`: known hackathons keyed by normalised
  URL (fallback: normalised name), first-seen time, reminded flag.
  `check` only alerts on keys absent from memory — nothing is reported
  twice. Export/import as plain JSON or as an OpenMinion `MemoryBundle`
  (the SDK's `import_bundle` only validates and returns a summary; this
  package does the actual load into the store).

## Suitability profile (Allen's screen)

Free-only (any entry fee → not-suitable); online-first; non-student
adults (student-only → not-suitable); direction LLM / Agent / AI
applications / legal AI; resident Singapore / US. Verdicts are three
levels only — `preliminary` / `unsure` / `not-suitable` — plus one short
reason. `preliminary` means "worth a look on the official page", never
"officially eligible".

## Sources (verified 2026-11-17)

| Source | List page | What the fetch actually returns |
|---|---|---|
| DoraHacks | `https://dorahacks.io/` | HTTP 200, ~522 KB. Listing is a JS-rendered Vue SPA: static HTML exposes only 5 `/hackathon/<slug>` links (featured/testimonial cards). Names are derived from the slug and marked `name_source="slug"` — placeholders, verify the real title on the official page. |
| Devfolio | `https://devfolio.co/hackathons` | HTTP 200, ~191 KB, server-rendered cards: real names + subdomain links (28 on the page). Deadline/prize are NOT on the list page, so they stay empty — never guessed. |
| Kaggle | `https://www.kaggle.com/competitions` | HTTP 200 but the body is a Google reCAPTCHA challenge page (~20 KB), not a competition list. Recorded as `unavailable` with evidence; never faked. Matches the 2026-11-16 baseline note (JS-rendered / 429). |

Only public list pages are fetched, at low frequency, no login.
Devfolio's `robots.txt` allows all. DoraHacks' `robots.txt` is itself
behind a human-verification page from this network, so only the two
public pages above are fetched.

## Baseline

`data/` ships a snapshot of Allen's tracker baseline (2026-11-16):
`open-list-20261116.md` (100 open + K/D supplementary entries),
`full-recheck-20261116.md` (19 new suitable), and
`full-recheck-20261116-verified.md` (19 officially verified). The
parser reads 177 lines and dedupes to **170** entries (the tracker
states 171; the 1-entry gap is a same-name `to_verify` duplicate that
survives under different keys). Use `--baseline-dir` to point `list` /
`check` at the live tracker directory instead.

## Verified run (2026-11-17, this machine)

- `pytest`: **46 passed** (loopback stubs + fixture HTML, zero LLM cost).
- Real `check` (rules only): seeded 170 baseline entries; DoraHacks 5 +
  Devfolio 28 = **33 new**; Kaggle unavailable (reCAPTCHA); 0 model
  calls, 0 tokens.
- Real `check --live-classify --max-model-calls 3`: **3 calls, 1,691
  tokens, $0** (Pollinations `gpt-oss-20b`, no key). Alerts: **AgentVerse**
  (Devfolio, rule-preliminary). Model verdicts on the unsure three:
  "Build And Brew" → not-suitable; the other two stayed unsure.
  Second run reports 0 new — no duplicate alerts.
- `probe`: **5 pass / 5 partial / 0 fail** out of 10 probes, 35.0 s,
  1 live model call (646 tokens, $0). Partials are the five blocks that
  need a live native turn, all blocked by the same Pollinations 402
  wall — see `docs/BUILDING_BLOCKS_TESTED.md` (auto-generated).

## Limitations (honest)

- DoraHacks names are slug-derived placeholders; the full card list is
  JS-rendered and not readable by plain fetch.
- Devfolio list pages carry no deadline/prize; the agent cannot tell
  you when an event closes without opening its page.
- Kaggle is currently unreadable by plain HTTP fetch (reCAPTCHA wall);
  Kaggle entries only enter via the baseline, not via live watch.
- A `preliminary` verdict is a list-page-text judgement, not an
  official eligibility check. Fee, student-only status and format are
  only as visible as the list page makes them — the official page is
  always the authority.
- The native SDK turn (`Agent.run`) does not survive the Pollinations
  free tier (1 reply / 45 s / IP vs several calls per turn). The probe
  records this instead of hiding it; the main road is the paced direct
  client. A Cortensor Portal/Router preset is wired in for when access
  is available.

## Submission checklist (Cortensor Hackathon #5)

- Public repo + README: this repo.
- SDK flow: README Architecture + `src/hackathon_watch/agent.py`
  (isolated runtime, read-only tool, classifier agent, subagent,
  handoff, MemoryBundle) + `docs/BUILDING_BLOCKS_TESTED.md`.
- Runnable example + 1–5 min demo video: `scripts/demo.sh` (video
  recorded separately from this script).
- Building Blocks Tested: `docs/BUILDING_BLOCKS_TESTED.md`
  (auto-generated by `hackathon-watch probe`).
- What We Learned: `docs/WHAT_WE_LEARNED.md` (findings from real runs
  in this repo, not copied from other entries).

## License

MIT. See `LICENSE`.
