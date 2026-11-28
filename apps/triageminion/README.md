# TriageMinion — GitHub Issue Triage Agent

> Cortensor Hackathon #5 entry. A small, working agent built with the
> **OpenMinion 0.1 Python SDK** (`openminion==0.1.24`) that performs one
> useful, repeatable workflow end-to-end with a **real model-backed run**:
> triaging a public GitHub repository's open issues.

Maintainers of busy open-source projects drown in untriaged issues.
TriageMinion points at a repo, reads each new open issue, and produces a
review-ready triage report — classification, priority, suggested labels and a
draft maintainer response — while a **human approval gate** ensures the agent
itself never writes or posts anything without permission.

## What a run does

1. **Fetch** — pulls the newest open issues from the target repo via the
   GitHub REST API (no token needed for public repos; `GITHUB_TOKEN` is used
   if present). Pull requests are excluded.
2. **Remember** — compares each issue's `updated_at` against durable local
   state (`.triageminion-state.json`). Unchanged, already-triaged issues are
   **skipped**; changed ones are re-triaged; new ones are triaged.
3. **Triage (the agent)** — for each issue to triage, an OpenMinion `Agent`:
   - calls the READ_ONLY tool `get_issue` to load the full issue body,
   - classifies it as `bug` / `feature` / `question` / `docs`, assigns a
     `critical` / `high` / `medium` / `low` priority with a one-line
     justification, suggests labels, and drafts a maintainer response,
   - persists the verdict **only** through `save_triage_record`, a tool
     marked `dangerous=True`, so every write passes the run's **approval
     callback** (interactive `y/N`, or `--auto-approve yes|no`),
   - returns the verdict as **typed structured output** validated against a
     Pydantic schema (`TriageVerdict`).
4. **Report** — writes `triage-report.md` (human-readable) and
   `triage-report.json` (structured) locally. **Nothing is ever posted to
   GitHub** — triage is read-only by design; the drafts are for a human to
   post.

## OpenMinion SDK workflow (how the SDK is used)

| Building block | How TriageMinion uses it |
| --- | --- |
| Agent execution | `openminion.Agent` context manager; one `agent.run()` per issue with per-turn `timeout_seconds` |
| Models / providers | Provider configured via `openminion setup` (project-scoped `.openminion/agents.json`); recorded runs use **Ollama + `qwen2.5:3b`** locally — any OpenAI-compatible / hosted provider (OpenRouter, Groq, Z.ai, Cortensor Portal…) works by changing two flags |
| Tools | `@tool(min_scope="READ_ONLY", idempotent=True)` for `get_issue`; `@tool(dangerous=True)` for `save_triage_record` |
| Permissions | `approval_callback(tool_name, args, approval_id) -> bool` passed to `agent.run()`; denies any tool other than the one expected write tool |
| Sessions | One session per target repo (`triageminion-<owner>-<repo>`), continued across all issues in a run |
| Memory | SDK session continuity **plus** an explicit, inspectable state file keyed by issue `updated_at` — a second run demonstrably skips unchanged issues and re-triages changed ones |
| Structured output | `output_type=TriageVerdict` (Pydantic); the SDK validates the model's reply |
| Diagnostics / errors | Typed failures handled explicitly: `ProviderError`, `TurnTimeoutError`, `AgentOutputValidationError`; per-issue timing and tool-persistence are logged |

## Setup

Requirements: Python 3.11+ (developed on 3.12.3), and a model provider.
The recorded demo uses a **local model via Ollama** — no API key, no cost:

```bash
# 1. Install Ollama (https://ollama.com) and pull the model
ollama pull qwen2.5:3b
ollama serve            # keep running on http://127.0.0.1:11434

# 2. Project setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On first run, TriageMinion creates its project-scoped OpenMinion config by
calling the official CLI for you:

```bash
openminion setup --provider ollama --model qwen2.5:3b --no-chat
# (writes ./.openminion/agents.json via $OPENMINION_HOME)
```

### Using a hosted provider instead

Any provider `openminion setup --list-providers` supports works the same way,
e.g. OpenRouter free models or Cortensor Portal:

```bash
export OPENROUTER_API_KEY=...   # or CORTENSOR_API_KEY for Portal
python triage.py --provider openrouter --model <model-id> --repo Textualize/rich
```

## Run

```bash
# Interactive: you approve each verdict write with y/N
python triage.py --repo Textualize/rich --limit 5

# Non-interactive (CI / demo): approve or deny all writes
python triage.py --repo Textualize/rich --limit 5 --auto-approve yes

# Run it again — unchanged issues are skipped from memory:
python triage.py --repo Textualize/rich --limit 5 --auto-approve yes
```

Outputs: `triage-report.md`, `triage-report.json`, `triage-staging.jsonl`
(the approval-gated tool's writes), `.triageminion-state.json` (memory).

Recorded real runs (report, JSON, staging log, console log) are in
[`examples/`](examples/). Offline logic tests:

```bash
python tests/test_triage_logic.py   # 4 tests: memory planning + report rendering
```

## Findings

- [`BUILDING-BLOCKS.md`](BUILDING-BLOCKS.md) — every building block tested,
  what worked, what didn't.
- [`WHAT-WE-LEARNED.md`](WHAT-WE-LEARNED.md) — actionable product feedback for
  the OpenMinion team.
- [`FINDINGS.md`](FINDINGS.md) — the raw findings log (bugs, rough edges, doc
  gaps) with versions, repro steps, expected vs actual.

## Safety posture

- Read-only against GitHub: the agent has no tool that can post, label or
  close anything upstream.
- The single write tool is local-file-only and approval-gated; the approval
  callback denies any unexpected tool name.
- No secrets are required for the default local-model path, and none are
  committed (`.openminion/` holds provider config only).

## License

MIT — see [`LICENSE`](LICENSE).
