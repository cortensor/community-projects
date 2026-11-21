# OpenMinion GitHub Issue & Release Triage Agent

Built for **Cortensor Hackathon #5** using the **OpenMinion 0.1.24** Python SDK (`commit a52088443c67a47c8fbf660f47ec6f748b3247f3`).

- **Live Demo Page & Video:** https://princejain756.github.io/openminion-github-triage/
- **Direct Demo MP4:** https://princejain756.github.io/openminion-github-triage/demo.mp4
- **Standalone Repository:** https://github.com/princejain756/openminion-github-triage

## Overview

`openminion-github-triage` converts GitHub issue and release payloads (from local fixtures or live GitHub REST endpoints) into structured `openminion-triage.v1` JSON reports. Deterministic rules score issue severity and reproduction completeness or validate release semver tags, binaries, and Markdown checklists. An optional OpenAI-compatible model client adds concise maintainer `model_notes` on top of the deterministic fact pack.

## OpenMinion 0.1.24 SDK Workflow

1. Two typed read-only functions (`triage.assess_issue`, `triage.assess_release`) are registered with `@tool(min_scope="READ_ONLY", idempotent=True)`.
2. `derive_tool_specs(declaration.tool_family_spec())` builds strict schemas registered into `ToolRegistry`.
3. Every triage run creates a `SQLiteSessionStore` session, records loaded input and tool completion events (`agent.bound`, `triage.issue.loaded` / `triage.release.loaded`, `triage.tool.completed`), and executes real `ProviderToolCall` objects via `ToolRegistry.execute_calls`.
4. Each report embeds a serialized `TaskState`, two `PhaseStatus` snapshots (`analyzing` or `verifying` -> `completed`), and persists the final JSON report as an assistant turn inside `SQLiteSessionStore`.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install "git+https://github.com/openminion/openminion.git@a52088443c67a47c8fbf660f47ec6f748b3247f3"
.venv/bin/pip install -e ".[dev]"
```

## Run Tests (Offline, Mock Transports)

```bash
.venv/bin/python -m pytest -q
```

Verified result: `11 passed in 1.06s` (no network calls required).

## Verified Live Model-Backed Runs

Set `CORTENSOR_BASE_URL`, `CORTENSOR_API_KEY`, and `CORTENSOR_MODEL` (for example Cortensor Portal or any OpenAI-compatible endpoint such as Groq `openai/gpt-oss-120b`), plus an optional `GITHUB_TOKEN`:

```bash
# 1. Fixture issue with live model notes
.venv/bin/python -m triage_agent.cli --session-db .triage/demo.db \
  issue example/project --file samples/issue.json --model "$CORTENSOR_MODEL"

# 2. Live public GitHub issue (openminion/openminion#236) with live model notes
.venv/bin/python -m triage_agent.cli --session-db .triage/demo.db \
  issue openminion/openminion --number 236 --model "$CORTENSOR_MODEL"

# 3. Release gate validation (v1.4.0 unchecked checklist hold)
.venv/bin/python -m triage_agent.cli --session-db .triage/demo.db \
  release example/project --file samples/release.json
```

Checked-in live run outputs are saved under `artifacts/`:
- [artifacts/live_issue_fixture.json](artifacts/live_issue_fixture.json): `high` severity, reproduction `100/100`, `model_notes` populated by `openai/gpt-oss-120b`.
- [artifacts/live_openminion_issue_236.json](artifacts/live_openminion_issue_236.json): live GitHub issue `openminion/openminion#236`, `medium` severity, reproduction `70/100`, `model_notes` populated by `openai/gpt-oss-120b`.
- [artifacts/live_release_fixture.json](artifacts/live_release_fixture.json): `hold` verdict triggered by unchecked `Migration notes reviewed` checklist item.

## Documentation & SDK Feedback

- [docs/BUILDING_BLOCKS_TESTED.md](docs/BUILDING_BLOCKS_TESTED.md)
- [docs/WHAT_WE_LEARNED.md](docs/WHAT_WE_LEARNED.md)
- [FEEDBACK.md](FEEDBACK.md)

## Known Boundaries

- Severity and reproduction completeness use explicit rule heuristics, not learned classifiers.
- Checkbox parsing checks Markdown list items formatted as `- [ ]` or `- [x]`.
- The agent is strictly read-only on GitHub (never posts comments or alters releases).
