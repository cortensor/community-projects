# Minion Radar

A small OpenMinion agent that tells a builder what changed in a GitHub repo since they last looked: new releases, risky changes, and bugs worth watching. It writes a short **Builder Brief** and remembers what you have already seen, so the next run only shows newer items.

Default target: `openminion/openminion`, so Cortensor and OpenMinion builders can see what changed before they upgrade.

Built for **Cortensor Hackathon #5** with the **OpenMinion 0.1 Python SDK** (`openminion==0.1.23`).

- Standalone public repository: https://github.com/ajahelube/minion-radar
- Demo video (voiced): https://github.com/ajahelube/minion-radar/blob/main/demo/minion-radar-demo-vo.mp4

## What the OpenMinion workflow does

1. `Agent(...)` is created with three Python tools, `output_type=BuilderBrief` (Pydantic) and a stable `session_id` per repo (slashes in the repo name are replaced so OpenMinion memory does not reject the session scope).
2. `radar_new_releases` and `radar_new_issues` are `@tool(min_scope="READ_ONLY", idempotent=True)`, so they run without prompts. They read the GitHub REST API and diff it against the local checkpoint. In `--film` mode they are combined into one compact `radar_snapshot`.
3. The model writes a structured `BuilderBrief` (headline, releases with risk level, issues to watch, actions). If the reply is Markdown, fenced JSON, or JSON with nearby field names, Minion Radar extracts or repairs it and retries once with a stricter prompt.
4. `radar_save_checkpoint` is a bare `@tool` (a local write), so OpenMinion's action policy asks for **human approval** before it runs. The CLI answers through `approval_callback`: it asks you y/N, or auto-approves with `--yes` or `--film`.
5. The brief is saved as Markdown with the OpenMinion `run_id` and `session_id`.

## Example

```bash
python -m minion_radar --repo openminion/openminion --film --out samples
```

`--film` takes a compact live GitHub snapshot, calls the real model once, and auto-approves the checkpoint the same way `--yes` does.

A real Cortensor Portal `oss-20b` run on 22 Nov 2026, 9:35:24 AM to 9:39:34 AM WAT (Africa/Lagos), finished in 4 minutes 10 seconds, exit 0, origin `model_generated`. The snapshot found 1 new release and 8 new issues. The model wrote a brief about OpenMinion 0.1.24 (multimodal input and stronger provider retry), flagged issues [#446](https://github.com/openminion/openminion/issues/446) and [#717](https://github.com/openminion/openminion/issues/717), and the checkpoint was auto approved. Full notes: [`samples/portal-oss-20b-film-2026-11-22.md`](samples/portal-oss-20b-film-2026-11-22.md). Printed brief: [`samples/openminion__openminion_20261122_093933.md`](samples/openminion__openminion_20261122_093933.md).

The primary demo is the voiced recording at https://github.com/ajahelube/minion-radar/blob/main/demo/minion-radar-demo-vo.mp4 (2 minutes 38 seconds; the 4 minute model wait is cut and labelled). Voice-over script: [`demo/VOICEOVER.md`](demo/VOICEOVER.md).

Headline from that run:

> OpenMinion 0.1.24 adds multimodal input (image/screenshot) and strengthens provider retry behavior while addressing storage migration issues

## Setup

Python 3.11+.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in your provider key; never commit .env
```

Configure a model provider for OpenMinion (pick one):

```bash
# Cortensor Portal (hosted Cortensor inference, if you have access)
export CORTENSOR_API_KEY=...
openminion setup --provider cortensor-portal --model oss-20b --agent radar --no-chat
# or any other supported provider, for example
openminion setup --provider openai --model gpt-4.1-mini --agent radar --no-chat
openminion doctor --check-turn
```

Then put `RADAR_AGENT_ID=radar` in `.env`.

## Run

```bash
python -m minion_radar                          # real OpenMinion run on openminion/openminion
python -m minion_radar --repo cortensor/installer
python -m minion_radar --film --out samples     # compact live snapshot, real model, auto approve
python -m minion_radar --demo-data              # real model, simulated repo fixtures
python -m minion_radar --no-model               # live GitHub data, rule based brief, no model
python -m minion_radar --demo                   # offline demo: SIMULATED data, no model, clearly labelled
```

Run it twice: the second run only shows items that are new or updated since the checkpoint you approved.

## Tests

```bash
python -m pytest -q
```

`scripts/mock_openai_server.py` is a scripted OpenAI-compatible stub used only to test the SDK wiring locally (tool calls, approval, structured output). It is not a model and its output is never a real run.

## Building Blocks Tested

Full table and reproduction notes: [docs/BUILDING_BLOCKS_TESTED.md](docs/BUILDING_BLOCKS_TESTED.md).

Status below is from two real Cortensor Portal `oss-20b` runs on 21 and 22 Nov 2026, OpenMinion 0.1.23.

| Building block | How Minion Radar uses it | Worked? | Notes |
| --- | --- | --- | --- |
| Agent execution (`Agent.run`) | One bounded turn per brief, plus a JSON retry unless `--film` | Yes | A full turn on 21 Nov took 27 min 13 s. The 22 Nov film run finished in 4 min 10 s. |
| Python tools (`@tool`) | Three tools, or one compact `radar_snapshot` in film mode | Yes | Live GitHub reads returned new releases and issues on every real run. |
| Permissions / action policy | READ_ONLY tools run freely; checkpoint write needs approval | Yes, on the film runs | 22 Nov printout: `[approval] auto approved radar_save_checkpoint (--yes)`. The first full Portal run on 21 Nov did not call the save tool. |
| Structured output (`output_type`) | `BuilderBrief` Pydantic model | Yes | 21 Nov needed alias repair and a retry. 22 Nov returned a complete brief (headline, risk labels, why-it-matters, actions) labelled `model_generated`. |
| Sessions (`session_id`) | One session per repo | Yes | Slashes are replaced (`minion-radar:openminion__openminion-film2`). The slash form raised `invalid scope`. |
| Memory | App-level checkpoint file | Yes, on film runs | Saved after approval so the next run only shows newer items. |
| Models / Portal | `cortensor-portal` preset, `oss-20b` | Yes | Usable, but slow. Film waits of 4 to 10 minutes. `PROVIDER_ERROR` happened on 21 Nov; the 22 Nov film run printed none. |
| Diagnostics | `openminion setup --check-provider` | Yes | Used on 21 Nov (24.9 s). |

## What We Learned

Full write-up: [docs/WHAT_WE_LEARNED.md](docs/WHAT_WE_LEARNED.md).

- `openminion setup --provider cortensor-portal --model oss-20b --agent radar --no-chat --check-provider` works with `CORTENSOR_API_KEY`.
- Cortensor Portal `oss-20b` can produce a real tool-using Builder Brief, but latency is high (4 to 27 minutes depending on retries). That wait has to be cut for a 1 to 5 minute demo.
- Session ids must not contain `/`, or OpenMinion memory raises `invalid scope`.
- Structured output is fragile. `oss-20b` may return aliased field names or incomplete objects; repair plus a stricter retry recovered a valid `BuilderBrief` on 21 Nov. The 22 Nov film brief needed no visible retry and matched GitHub on release `v0.1.24` and issues 446 and 717.
- Portal may raise `PROVIDER_ERROR` mid-turn and does not always retry on its own. Official docs already warn about this.
- A first-pass model run may skip `radar_save_checkpoint`. Film mode still shows the approval path by auto-approving when the tool is offered.
- Actionable product feedback: honor `Retry-After` on HTTP 429 (issue 717), and stop sharing one `alembic_version` across Postgres migrate modules (issue 446). Both are still open on 22 Nov 2026.

## Data and secrets

Reads public GitHub data only. Keys live in `.env` or your OpenMinion config, which are git-ignored. The checkpoint (`.radar/`) and default briefs directory stay on your machine. Checked-in `samples/` and `demo/` contain no API keys.

## License

MIT. Depends on OpenMinion (Apache-2.0) and Pydantic (MIT).
