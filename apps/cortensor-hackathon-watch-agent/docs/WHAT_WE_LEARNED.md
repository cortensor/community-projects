# What We Learned

Findings from actually running this agent (2026-11-17). Nothing here
is copied from another entry's write-up; every item has a run behind
it in this repo (`pytest`, a live `check`, or `hackathon-watch probe`).

## 1. DoraHacks' list page is a JS-rendered SPA — plain fetch only sees 5 slugs

`GET https://dorahacks.io/` returns HTTP 200, ~522 KB, but the
hackathon listing is a Vue SPA: the static HTML contains only five
`/hackathon/<slug>` links (featured / testimonial cards), no card
titles, no dates, no prizes. The `/hackathon` listing page is the same
SPA (270 KB, 6 `/hackathon/` references, no card data). So a plain-HTTP
watcher cannot enumerate DoraHacks properly; it can only notice the
handful of featured slugs. We record that honestly: names are derived
from the slug and marked `name_source="slug"`, and the README says the
full list needs a browser. (A browser-rendered fetch would fix this;
it is out of scope for the $0 plain-HTTP MVP.)

## 2. Devfolio's list page is server-rendered and genuinely parseable

`GET https://devfolio.co/hackathons` returns HTTP 200, ~191 KB, with
real cards in the static HTML: `<a href="https://<slug>.devfolio.co/">
<h3>Real Name</h3></a>` — 28 events on the page at check time. But the
cards carry no deadline and no prize, so those fields stay empty
rather than guessed. The parser must exclude the `assets` / `guide` /
`status` subdomains, which match the same URL shape but are not events.

## 3. Kaggle's competitions page is a reCAPTCHA wall for plain fetch

`GET https://www.kaggle.com/competitions` returns HTTP 200 — but the
body (~20 KB) is a Google reCAPTCHA challenge page, not a competition
list. There are no `/competitions/<slug>` links in it at all. This
matches the 2026-11-16 baseline note (JS-rendered / 429) and means a
plain-HTTP watcher cannot cover Kaggle today; the agent records the
source as `unavailable` with the evidence instead of inventing
entries. Kaggle events still enter through the baseline snapshot.

## 4. The Pollinations free tier kills a native SDK turn, not a single call

One `Agent.run` turn fires several consecutive model calls (main decide
+ internal classification rounds). Pollinations free allows 1 reply /
45 s / IP, enforced as HTTP 402, and the SDK's built-in retry (~300 ms)
does not honour `Retry-After`. The sibling project's spike verified
this 3/3; this repo's probe re-attempts exactly one native turn and
records the outcome in `docs/BUILDING_BLOCKS_TESTED.md` rather than
hiding it. The working road is the paced direct client: one call per
classification, 45 s apart, tool_calls first, text JSON second, both
validated by the same Pydantic model. A normal `check` costs 0–5 calls.

## 5. A tiny prompt still costs ~560 tokens a call

The live `check --live-classify` run made 3 calls for 1,691 tokens
(~564/call) although each prompt is ~120 words. The provider counts
roughly 300 fixed prompt tokens on top of the visible prompt (same
pattern the sibling spike measured: 317–386 prompt tokens for a
~30-token prompt). Budget token math must use the provider's counting,
not the bare prompt size.

## 6. The free model judges sensibly on almost no signal

With only a slug-derived name and a URL, `gpt-oss-20b` called
"Build And Brew" not-suitable (a brew event, not LLM/Agent) and left
two other bare-name entries unsure instead of guessing. JSON structure
was stable across all three live calls (tool_calls channel). The
failure mode to watch is semantic, not structural: a bare name gives
the model little to work with, so `unsure` is the honest majority
answer — 31 of 33 new entries stayed unsure after the rule screen.

## 7. List pages carry almost no eligibility signal

Of the 33 genuinely new entries in the live check, the deterministic
rule screen could only decide 2 (1 preliminary by direction keyword,
1 model-decided not-suitable after the live calls); the other 31 stayed
`unsure` because the list pages show no fee, no student-only flag, no
format. The watcher's value is discovery + dedupe, not verdicts: the
verdict is a triage hint, and the official page is always the authority.

## 8. Baseline parsing: one aggregator URL hides 24 distinct events

The 2026-11-16 baseline has 24 entries sharing the single URL
`https://aicpt-memo.cn/` (an aggregator page). Deduping by URL alone
collapses them into one event. The parser falls back to the normalised
name when a URL repeats, which is why 177 parsed lines dedupe to 170
instead of ~147. The tracker's own stated total is 171; the 1-entry gap
is a same-name `to_verify` duplicate that survives under different keys.

## 9. SDK 0.1.21 small facts that cost real debugging time

- `create_isolated_runtime` does not exist in 0.1.21; the working
  equivalent is `APIRuntime.from_config(config, home_root, data_root)`.
- `OpenMinionConfig()` with no agents fails (`agents is empty`); an
  `AgentProfileConfig` needs `default_channel="console"` or the turn is
  rejected as `invalid_channel` (even in warn mode).
- `APIRuntime.from_config` creates `data_root` eagerly (SQLite stores)
  but `home_root` lazily — tests must not assert the home dir exists.
- `@tool` attributes live on `fn.tool_decl` (`name`, `min_scope`,
  `dangerous`), not on the decorated function itself.
- `subagent()` returns an `Agent`; its timeout lives on
  `child.subagent_context.timeout_seconds`, not on the child.
- `MemoryBundle` is a dataclass, not a dict: use `bundle.items`, and
  the SDK's `import_bundle()` only validates the trust mode and returns
  a summary — the actual load into a store is the caller's job.
- `NO_PROXY` containing `[::1]` makes httpx raise `InvalidURL`
  (`Invalid port: ':1]'`); narrowing it to `localhost,127.0.0.1`
  fixes every httpx client in the sandbox, including the SDK's.

## 10. Rich eats square brackets in CLI output

`typer`/`rich` printing interprets `[dorahacks]` as a style tag and
silently drops it, so the first version of the check report printed
source lines without their source names. The report formatter now
avoids leading `[...]` tokens. Small, but it is exactly the kind of
silent output loss that makes a demo look broken.

## Probe results

See `docs/BUILDING_BLOCKS_TESTED.md` (auto-generated by
`hackathon-watch probe`). Summary of the 2026-11-17 live probe run:
**5 pass / 5 partial / 0 fail** out of 10 probes, 35.0 s total, 1 live
model call (646 tokens, $0). Pass: runtime isolation, structured
Pydantic output (stub + one live Pollinations call), tool +
forced_tools, MemoryBundle portability, error/timeout contracts
(loopback HTTP 500 → `ProviderError`, slow provider → `TurnTimeoutError`
on the real SDK provider path, zero model cost). Partial (all five):
the blocks that need a live native turn — session continuity, policy
confirmation gate, subagent delegation, handoff, streaming telemetry —
each constructs correctly but the single native-turn attempt died on
the Pollinations HTTP 402 wall (`Retry after 28s`), exactly the failure
the main-road DirectClient is built to route around. No probe claims a
live turn succeeded.

## What we would do next (not done here)

- Render DoraHacks in a real browser (or find its list API) so the
  watcher sees the full card list with real titles and dates instead
  of 5 featured slugs.
- Open each new event's own page once (official page) to fill
  deadline/prize/eligibility before classifying — that turns most
  `unsure` verdicts into real ones.
- Get a Kaggle path that survives the bot wall (official API or a
  browser fetch) instead of relying on the baseline snapshot.
- Re-run the native-turn probes against the Cortensor Portal preset
  once access is available, to move the live-turn partials to pass.
