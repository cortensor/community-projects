# Hackathon Scout

> Cortensor Hackathon #5 submission · DoraHacks BUIDL [#51207](https://dorahacks.io/build/51207) · standalone repo: [emilpz320-a11y/hackathon-scout](https://github.com/emilpz320-a11y/hackathon-scout) (includes the narrated `demo.mp4`) · upstream fix merged: [openminion#772](https://github.com/openminion/openminion/pull/772)

An OpenMinion 0.1 agent that reads a hackathon, bounty or grant page and returns:

- a **typed brief**: deadline, prizes, eligibility, required deliverables, judging criteria, blockers, an effort estimate, and a **GO/SKIP** verdict;
- a **markdown submission checklist** saved to `out/<slug>.md`, written only after a human approves it;
- a **ranking** of every page scouted in one run: GO first, then the least effort.

It is built for solo builders who scan many opportunities a week. It answers "what does this one really ask for?" and flags pages that want your own money, such as deposits, stakes or a funded wallet, before you spend hours on them.

## Demo

```
$ python scout.py --yes <superteam bounty api url> https://redditgameofday2026.devpost.com/

=== https://superteam.fun/api/listings/details/build-an-autonomous-capital-agent-...
  [approval call_139] auto-approved save_checklist(build-an-autonomous-capital-agent-...)
Build an Autonomous Capital Agent on Solana and Compete for $500 in Rewards | deadline: Unknown
  blocker: Fund your agent wallet with at least 20 USDC or equivalent value in SOL
effort: ~10h | SKIP - requires the builder's own capital: Fund your agent wallet with at least 20 USDC ...
run=2a7ddd73... session=scout-c5114888... stats={'llm_calls': 9, 'tool_calls': 4, 'tool_errors': 1, ...}

=== https://redditgameofday2026.devpost.com/
Reddit Game of the Day 2026 | deadline: December 8, 2026
prizes: $35,000 in prizes
  deliverable: Project repository link
  deliverable: Demo video showcasing gameplay and daily loop
effort: ~40h | GO - Recommended for solo builders ...

=== ranking (GO first, then least effort)
1. Reddit Game of the Day 2026: GO ...
2. Build an Autonomous Capital Agent on Solana ...: SKIP - requires the builder's own capital ...
```

The full log and both generated checklists are in [`examples/`](examples/). The demo video is [`demo.mp4`](https://github.com/emilpz320-a11y/hackathon-scout/blob/main/demo.mp4) in the standalone repository.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add a model key. The demo uses Google Gemini's free tier, through OpenMinion's built-in `gemini` preset:

```
GEMINI_API_KEY=AIza...
```

Point OpenMinion at that provider once:

```bash
openminion setup --provider gemini --model gemini-3.5-flash-lite --no-chat
```

On Windows, run from a short path, for example `C:\scout`. See finding 1 in [FEEDBACK.md](FEEDBACK.md).

## Run

```bash
python scout.py https://redditgameofday2026.devpost.com/          # asks before writing the checklist
python scout.py --yes <url-a> <url-b> <url-c>                     # auto-approve and rank several pages
```

## How it works

1. **`fetch_page`** (`@tool`, `min_scope="READ_ONLY"`, so it runs without confirmation)
   - Downloads the page and keeps only the main content.
   - Flattens JSON listing APIs.
   - Runs a deterministic pre-scan that puts gating lines (deposits, "at least 20 USDC", KYC, region, deadlines) at the top, so small models don't miss them.
2. **`save_checklist`** (`@tool`, default write scope) is **gated by OpenMinion's action policy**. The `approval_callback` on `Agent.run` asks the operator `[approval] allow save_checklist(slug)? [y/N]`.
3. **`submit_brief`** (`@tool`, typed parameters) records the structured `HackathonBrief`.
   - A fixed policy then normalises the verdict: any blocker that needs the builder's own capital forces **SKIP**.
4. Each page runs in its own **session**. `run_id`, `session_id` and `stats` (LLM calls, tool calls, tokens, duration) are printed per brief.
5. Rate-limit backoff and one retry per page keep the agent working on free model tiers. FEEDBACK.md explains why each is needed.

| OpenMinion building block | Where |
|---|---|
| `Agent(instructions, tools, model)` | `main()` |
| `@tool` with `READ_ONLY` and default scopes | `fetch_page`, `submit_brief`, `save_checklist` |
| Action policy plus `approval_callback` | `save_checklist` gating |
| Sessions and run metadata (`AgentRunResult`) | one session per page, stats printed |
| Provider presets (`openminion setup --provider gemini/groq`) | setup |
| Runtime config via env (`OPENMINION_TURN_TIMEOUT_SECONDS`) | `main()` |

## Building Blocks Tested / What We Learned

See **[FEEDBACK.md](FEEDBACK.md)**: 10 concrete findings from building this on Windows with free Groq and Gemini tiers, each with a reproduction and a suggested fix.
