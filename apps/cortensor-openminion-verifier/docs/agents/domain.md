# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root: canonical domain glossary and disambiguated terminology.
- **`docs/adr/`**: read ADRs that touch the area you're about to work in.

## File structure

Single-context repo:

```
/
├── CONTEXT.md
├── docs/
│   ├── adr/
│   │   └── 0001-*.md
│   └── agents/
│       ├── domain.md
│       ├── issue-tracker.md
│       └── triage-labels.md
└── ...
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a spec, a refactor proposal, a hypothesis, or a test name), use the term as defined in `CONTEXT.md`. Avoid synonyms listed under `_Avoid_`.

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-NNNN (...), worth reopening because…_
