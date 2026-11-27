# Project Status

- **Status:** Active (`v1.0.0` — Cortensor Hackathon #5 submission)
- **OpenMinion SDK:** `openminion==0.1.24`
- **Verified Capabilities:**
  - Deterministic Solidity static scanner (`VulnerableVault.sol`: 9 findings, 100/100 CRITICAL; `SafeTreasury.sol`: 0 findings, 0/100 MINIMAL)
  - Live DexScreener + GoPlus preflight with offline/timeout fallback
  - Live Cloud Run x402 v2 discovery + `HTTP 402` header parser
  - Full OpenMinion `APIRuntime` / `Agent` / `subagent` / `Handoff` / `NovaTriageApprovalGate` / `MemoryBundle` / `Skill` / `task.schedule` / `diagnostics` workflow
- **Known Limitations:**
  - Hosted Cortensor Portal inference is wired via `providers.cortensor` config/env vars (`CORTENSOR_API_URL`, `CORTENSOR_API_KEY`), while default runs use `NovaTriageLocalModelServer` for `$0.00` deterministic reproducibility without closed keys.
