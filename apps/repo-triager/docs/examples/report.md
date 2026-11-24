# Repo Triager report — openminion/openminion

- Run: `demo-20261124T123130Z-openminion_openminion`
- Started: 2026-11-24T12:31:30+00:00  ·  Finished: 2026-11-24T12:32:17+00:00
- Provider: scripted (http://127.0.0.1:45919/v1)  ·  Source: offline
- Session: `repo-triager-demo:openminion_openminion`
- Issues triaged: 2  ·  staged plans: 1
- Severity mix: S2 2

| Issue | Severity | Component | Type | Labels | Duplicates | Conf. | Staged |
| --- | --- | --- | --- | --- | --- | --- | --- |
| #859 Reject malformed explicit plugin contract versions before lo | S2 | area:tools | bug | `bug`, `area:tools` | — | 0.78 | yes |
| #853 `Agent(output_type=Model)` does not tell the model the schem | S2 | area:sdk | bug | `bug`, `area:sdk` | — | 0.85 | no |

## #859 — Reject malformed explicit plugin contract versions before loading

- Severity **S2** — A malformed plugin contract version is accepted instead of rejected, so a broken plugin loads and fails later.
- Component `area:tools` · type `bug` · confidence 0.78 · source `model`
- Labels: `bug`, `area:tools`
- Duplicates: —
- Next action: `ready-to-label`
- Policy: stage_triage → allow (operator-flag: auto (non-interactive))
- Staged files: `/workspace/hackathons/cortensor-triager/var/outbox/openminion_openminion/0859.md`, `/workspace/hackathons/cortensor-triager/var/outbox/openminion_openminion/0859.json`

### Reply draft

Thanks for the precise report — the contract-version check should reject an explicit but malformed version before any plugin module is imported, and right now it falls through to the lenient path.

We are tracking this as an S2: a bad plugin can load successfully and then fail during the first tool call, which is much harder to diagnose. I have added `area:tools` and put it in front of the plugin loader work; no timeline yet, but I will comment here when a branch is up.

## #853 — `Agent(output_type=Model)` does not tell the model the schema, so replies fail validation

- Severity **S2** — Structured output is unusable with any real provider because the schema never reaches the model.
- Component `area:sdk` · type `bug` · confidence 0.85 · source `model`
- Labels: `bug`, `area:sdk`
- Duplicates: —
- Next action: `ready-to-label`
- Policy: stage_triage → deny (operator-flag: deny)

### Reply draft

Confirmed on 0.1.24: `Agent(output_type=Model)` validates the reply but the turn never tells the model which schema to answer with, so a hosted model replies in prose and the client raises a validation error.

Workaround for anyone hitting this today: put the JSON schema in the task message and keep `instructions` short. We are treating it as an S2 SDK defect and will link the fix here.
