# Release Notes — FixBrief Agent

## v0.1.0 — Cortensor Hackathon #5

- OpenMinion 0.1.24 agent: run-scoped READ_ONLY tools
  (`get_source_facts`, `lookup_term`), approval-gated write tool
  (`save_brief_markdown`), `forced_tools`, typed `RepairBrief` output,
  durable sessions with follow-up turns.
- Deterministic fact extraction (section-aware Markdown parsing +
  sentence signal patterns) shared by the model path and the offline
  fallback.
- Multilingual briefs (EN/ES/PT/AR) with a 30-term repair glossary.
- CLI: `setup`, `doctor`, `brief`, `followup`, `history`, `show`,
  `samples`. Exit codes mirror the SDK error taxonomy.
- SQLite brief history + JSON run receipts.
- 25 offline tests; recorded demo video from a real terminal session.
