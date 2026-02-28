# 🚀 Cortex.OS: Release Notes

## Version 1.0.0 (Hackathon #4 Release)
**Date:** 2026-03-01

### Features
- **DeGen Risk Auditor Template:** Real-time vulnerability scanning of smart contracts utilizing Fractal Memory DAG execution.
- **Cortensor Routing:** Dynamic delegation to heterogeneous models (Gemini-3-Flash for mining, Groq-Llama-3 for Consensus Validation).
- **PoUW Validation Engine:** Implemented strict rubric-based scoring to evaluate miner outputs for accuracy, formatting, and depth.
- **ERC-8004 Web3 Settlement:** Deployed `CortexAgenticProof.sol` to Base Sepolia to mint immutable execution proofs.
- **IPFS Evidence Bundler:** Automatic generation and pinning of the entire execution state (Prompt + Output + Validation Rubric) to the Pinata Network.
- **Mission Control GUI:** Fully functional React Flow canvas with live WebSocket state polling and optimistic UI rendering.

### Known Issues
- The L2 Semantic Cache (Deja-Vu Engine) may disconnect if Vercel KV rate limits trigger frequently under heavy concurrent auditing. It fails open to standard inference.
- Time-Travel Replay Debugger currently only outputs to browser console; native canvas replay is slated for v1.1.0.
