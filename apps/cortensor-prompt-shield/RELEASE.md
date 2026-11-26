# Release History — Cortensor Prompt Shield

## v0.1.0 (2026-11-26) — Cortensor Hackathon #5 Initial Release
- **Added**: 5-stage OpenMinion `0.1.24` red-team & least-privilege auditing workflow (`prompt-shield audit`, `prompt-shield scan`, `prompt-shield demo`).
- **Added**: Static AST `@tool` decorator analyzer + `agents.json` policy auditor.
- **Added**: Bounded `subagent()` live adversarial harness (`VEC-01` Indirect Prompt Injection, `VEC-02` Canary Exfiltration, `VEC-03` Dangerous Tool Escalation) with honeypot approval gating.
- **Added**: Cross-session `session_id` memory-isolation verifier.
- **Added**: `WRITE_SAFE` + `dangerous=True` dual-path (`DENY -> ALLOW`) verification with SHA-256 receipt attestation and dark-mode HTML dashboard generator.
- **Added**: `CompactGuardProxy` middleware compressing OpenMinion's 43 KB default prompt envelope for edge/Cortensor/local models.
- **Documented**: 9 OpenMinion building blocks (`BUILDING_BLOCKS_TESTED.md`) and 5 reproducible `openminion==0.1.24` findings (`WHAT_WE_LEARNED.md`) backed by automated `pytest` tests and upstream GitHub issues.
