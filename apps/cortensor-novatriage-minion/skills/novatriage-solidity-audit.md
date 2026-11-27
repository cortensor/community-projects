---
name: novatriage-solidity-audit
description: Multi-step Web3 Solidity static triage, DexScreener/GoPlus preflight, and x402 payment-challenge verification workflow.
tools:
  - analyze_solidity_contract
  - fetch_token_onchain_preflight
  - probe_x402_endpoint
  - write_triage_report
applies_to:
  intents:
    - audit solidity contract
    - triage token risk
    - verify x402 challenge
  steps:
    - static_analysis
    - onchain_preflight
    - x402_probe
    - gated_report_write
teaches:
  - Always run deterministic static checks before recommending liquidity interaction.
  - Never treat unpaid HTTP 402 challenges as settled payments; inspect payTo and network fields directly.
safe_for_domains:
  - web3_security
  - smart_contract_triage
---

# Summary
Structured security triage procedure for EVM Solidity contracts and ERC-20 tokens before treasury or wallet interaction.

# Preconditions
- Contract source path or token contract address is provided.
- Write actions require explicit operator approval through `NovaTriageApprovalGate`.

# Procedure
1. Delegate on-chain and x402 discovery to `ReconMinion` (`fetch_token_onchain_preflight`, `probe_x402_endpoint`).
2. Run deterministic Solidity checks via `SolidityAuditorMinion` (`analyze_solidity_contract`) for `tx.origin`, `delegatecall`, reentrancy before state write, unchecked low-level calls, and arbitrary mint/drain/blacklist hooks.
3. Recall prior triage verdicts from `MemoryBundle` if available.
4. Persist the verified `NovaTriageReport` artifact through `write_triage_report` only after single-use write confirmation.

# Verification
- Ensure all reported line numbers exist in the audited Solidity source.
- Ensure live HTTP probes report actual status codes without fabricated payouts.
