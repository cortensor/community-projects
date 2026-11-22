# Minion Radar — Cortensor Hackathon #5 submission pack

Nothing in this file has been submitted. Public repo, PR, DoraHacks BUIDL, and demo upload all need Ajah's yes.

Official sources checked on 22 Nov 2026 (Africa/Lagos, WAT):

- https://docs.cortensor.network/community-and-ecosystem/hackathon/hackathon-5
- https://dorahacks.io/hackathon/2418
- https://dorahacks.io/hackathon/2418/detail
- https://github.com/orgs/cortensor/repos (4 public repos: community-projects, salt, installer, desktop-app)
- https://github.com/cortensor/community-projects (open PRs titled [Hackathon #5] exist, for example #91 to #99)
- https://discord.com/api/v10/invites/cortensor (HTTP 404, code 10006, "Unknown Invite")
- https://www.cortensor.network/ and other Cortensor docs still list https://discord.gg/cortensor

Deadline: **19 Dec 2026, 07:59 UTC** (19 Dec 2026, 8:59 AM WAT). DoraHacks is the cutoff to use. The docs page also says 18 Dec 2026 in Pacific Time; the DoraHacks timestamp is later and more precise.

## Official PR repo and Discord

**Dedicated Hackathon #5 PR repository: not found.** Official docs and the DoraHacks detail page still say "The repository URL will be added before kickoff" and "Access instructions and the submission repository will be announced before kickoff." Kickoff was 16 Oct 2026. As of 22 Nov 2026 there is no repo under the Cortensor or OpenMinion GitHub orgs whose name or description marks it as that dedicated repository.

**Related, but UNVERIFIED as the official target:** several other builders have opened pull requests titled `[Hackathon #5]` against https://github.com/cortensor/community-projects. Official docs have not named this repo as the Hackathon #5 submission repository. Do not open a PR there until Ajah says yes, and even then it should be marked UNVERIFIED unless Cortensor confirms.

**Discord invite: not working.** Official docs and GitHub READMEs still publish https://discord.gg/cortensor. At 9:32 AM WAT on 22 Nov 2026 the Discord API returned 404 Unknown Invite (code 10006) for `cortensor`. No replacement official invite was found on the docs, the website, or the public GitHub org. Ajah may still want to ask on DoraHacks (Ask Question) or try the same link from a phone later.

**Payout and wallet details:** still unpublished on the official pages. Docs say Cortensor will publish the pool, $COR conversion method, payout timing, and wallet instructions, and that KYC "may" be required. Those items remain UNVERIFIED.

## DoraHacks BUIDL drafts

**Name:** Minion Radar

**Tagline:** An OpenMinion agent that tells a builder what changed in a GitHub repo since they last looked.

**Demo video:** PLACEHOLDER (local file: `demo/minion-radar-demo.mp4`;  the 4 minute hosted model wait is cut and labelled)

**Repository:** https://github.com/ajahelube/minion-radar

**Website / live demo:** none. The CLI, the 22 Nov 2026 Portal brief, and the terminal video are the working demo.

**Tech stack:** Python 3, OpenMinion 0.1.23 Python SDK, Cortensor Portal (`oss-20b`), GitHub REST API, Pydantic.

**Description:**

Minion Radar is a small OpenMinion agent for Cortensor Hackathon 5. Point it at a GitHub repo and it writes a Builder Brief: new releases, issues worth watching, a risk level, and concrete actions. It stores a local checkpoint, so the next run only shows what is new.

It uses the OpenMinion 0.1 Python SDK in a meaningful way: an in-process Agent, three Python tools (two read-only GitHub tools and an approval-gated checkpoint write), structured output as a Pydantic BuilderBrief, a stable session id, and a real Cortensor Portal model.

A real Portal oss-20b film run on 22 Nov 2026, from 9:35:24 AM to 9:39:34 AM WAT, finished in 4 minutes 10 seconds with origin model_generated and an auto approved checkpoint. The brief named OpenMinion 0.1.24 and two real open issues, 446 and 717, which were checked against GitHub the same morning. Notes and the printed brief are in the repo under samples/.

Portal access is not required to reproduce the workflow. `--no-model` uses live GitHub data and a rule based brief, and `--demo` is clearly labelled simulated.

## PR description draft

Use this when the official Hackathon #5 repository URL is published, or only after Ajah confirms a fallback target.

**Title:** [Hackathon #5] Minion Radar — OpenMinion builder brief agent

**Body:**

```
Minion Radar is a small OpenMinion 0.1 agent that writes a Builder Brief for a GitHub repo: new releases, issues worth watching, and a local checkpoint so the next run only shows newer items.

Default target is openminion/openminion.

## Public source and setup
Public repo: https://github.com/ajahelube/minion-radar
Setup and run: see README.md (venv, openminion setup, CORTENSOR_API_KEY or another provider).

## OpenMinion SDK workflow
See the README section "What the OpenMinion workflow does": Agent with three tools, BuilderBrief structured output, session id, and an approval-gated checkpoint write.

## Example and demo
Command:
python -m minion_radar --repo openminion/openminion --film --out samples

Real Cortensor Portal oss-20b run, 22 Nov 2026, 9:35:24 AM to 9:39:34 AM WAT (Africa/Lagos), 4 minutes 10 seconds, origin model_generated, checkpoint auto approved.
Notes: samples/portal-oss-20b-film-2026-11-22.md
Brief: samples/openminion__openminion_20261122_093933.md
Demo video (wait cut): demo/minion-radar-demo.mp4

## Building Blocks Tested
See README.md and docs/BUILDING_BLOCKS_TESTED.md.

## What We Learned
See README.md and docs/WHAT_WE_LEARNED.md.

Actionable feedback already visible in the 22 Nov brief: OpenMinion issue 446 (shared alembic_version on Postgres migrate) and issue 717 (retry ignores Retry-After on 429).
```

## Local checklist (done vs still needs a yes)

- [x] Working agent, tests passing (18 passed on 22 Nov 2026)
- [x] Real model-generated Portal sample from 22 Nov 2026
- [x] README includes workflow, example, Building Blocks Tested, and What We Learned
- [x] Demo recording and voice-over script (1 to 5 minute target; wait cut)
- [x] BUIDL text and PR description drafted
- [ ] Official Hackathon #5 PR repo URL (not published as of 22 Nov 2026)
- [ ] Working Discord invite (official link invalid as of 22 Nov 2026)
- [ ] Public GitHub repository (needs Ajah's yes to push)
- [ ] Demo video uploaded to a public host
- [ ] Pull request to the official (or confirmed) submission repo (needs Ajah's yes, and the repo URL)
- [ ] DoraHacks BUIDL submitted (needs Ajah's yes)
