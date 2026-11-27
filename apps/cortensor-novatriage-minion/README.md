# NovaTriage Minion (`cortensor-novatriage-minion`)

Autonomous multi-step **Web3 Solidity, On-Chain Token Preflight & x402 v2 Risk Triage Agent** built on **OpenMinion 0.1 (`openminion==0.1.24`)** for **Cortensor Hackathon #5**.

## What It Does

`NovaTriage Minion` coordinates specialized bounded OpenMinion agents to evaluate smart contracts, token liquidity/honeypot risk, and HTTP 402 payment-gated endpoints before wallet or treasury interaction:

1. **Deterministic Solidity Static Analyzer (`analyze_solidity_contract`, `READ_ONLY`)**:
   - Line-accurate scanner detecting `TX_ORIGIN_AUTH`, `UNTRUSTED_DELEGATECALL`, `REENTRANCY_BEFORE_WRITE`, `UNCHECKED_LOW_LEVEL_CALL`, `ARBITRARY_MINT`, `BLACKLIST_HOOK`, `OWNER_DRAIN_HOOK`, `SELFDESTRUCT_PRESENT`, and `FLOATING_OR_LEGACY_PRAGMA`.
2. **Live Public On-Chain Token Preflight (`fetch_token_onchain_preflight`, `READ_ONLY`)**:
   - Queries **DexScreener** and **GoPlus Token Security** APIs for DEX liquidity, 24h volume, honeypot flags, buy/sell taxes, and ownership controls, with clean offline/timeout degradation.
3. **Live x402 v2 Discovery & Challenge Verifier (`probe_x402_endpoint`, `READ_ONLY`)**:
   - Probes `/.well-known/x402.json` and parses unpaid `HTTP 402 PAYMENT-REQUIRED` base64 JSON headers (verifying `x402Version`, `payTo`, `network`, `asset`, and `amount` with zero fake payments).
4. **Fail-Closed Policy & Approval Gate (`NovaTriageApprovalGate`)**:
   - `READ_ONLY` tools execute automatically; `write_triage_report` (`WRITE_SAFE`) requires single-use approval; `publish_emergency_freeze_notice` (`dangerous=True`) is denied fail-closed by default.
5. **Full OpenMinion 0.1 Runtime Stack**:
   - **Delegation:** `openminion.subagent` (`SubagentRunContext`) + peer `openminion.Handoff` (`solidity_auditor_minion`, `recon_minion`) + `NovaTriageCoordinator` (`output_type=NovaTriageReport`).
   - **Streaming & Sessions:** `Agent.run_stream(on_delta=...)` + SQLite multi-turn session/thread persistence (`session_id` + `thread_id`).
   - **Memory, Skills, Tasks & Diagnostics:** Portable `MemoryBundle` export/recall, verified `Skill` catalog (`skills/novatriage-solidity-audit.md`), recurring `task.schedule` watchlist tracking, and `APIRuntime` posture/self-model/tool-inventory diagnostics.
   - **Zero-Cost Local Model + Cortensor Support:** Includes `NovaTriageLocalModelServer` (in-process OpenAI-compatible `/v1/chat/completions` server exercising OpenMinion's real `OpenAIProvider` at `$0.00` cost) and switches via env vars to `cortensor`, `openai`, `openrouter`, or `groq`.

## Quickstart

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 1. Deterministic Solidity scan
novatriage-minion scan-sol samples/VulnerableVault.sol

# 2. Live x402 v2 challenge verification
novatriage-minion x402-probe

# 3. Full OpenMinion multi-agent triage workflow (local $0 model)
novatriage-minion audit --contract samples/VulnerableVault.sol

# 4. Run full test suite
pytest -v
```

## Optional Cortensor Portal / Hosted Model Configuration

Copy `.env.example` and set:

```bash
export NOVATRIAGE_PROVIDER=cortensor
export CORTENSOR_API_URL=http://127.0.0.1:8080/api/v2/completions
export CORTENSOR_API_KEY=...
export NOVATRIAGE_MODEL=gpt-oss-20b
novatriage-minion audit --contract samples/VulnerableVault.sol --provider cortensor
```

## SDK Feedback & Hackathon Artifacts

- [OPENMINION_FEEDBACK.md](./OPENMINION_FEEDBACK.md) — Verified OpenMinion `0.1.24` issues, exact file paths/lines, and minimal reproducers
- [BUILDING_BLOCKS_TESTED.md](./BUILDING_BLOCKS_TESTED.md) — Matrix of all 10 OpenMinion building blocks exercised
- [WHAT_WE_LEARNED.md](./WHAT_WE_LEARNED.md) — Key engineering lessons from building on OpenMinion `0.1.24`
- Demo video (`1280x720` H.264 MP4): attached to GitHub Release `v1.0.0` (`demo/novatriage_minion_demo.mp4` locally)

## License

MIT — see [LICENSE](./LICENSE).
