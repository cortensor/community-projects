# Cortex.OS: Verifiable Intelligence Engine

Cortex.OS transforms opaque AI workflows into cryptographically proven, deterministic execution graphs, culminating in immutable on-chain evidentiary artifacts. Built for the Cortensor network, it leverages Decentralized AI to parse, validate, and score complex on-chain interactions (e.g., Smart Contract Auditing) with Proof of Useful Work (PoUW).

## The "DeGen Risk Auditor" Swarm
This repository contains the flagship Cortex.OS template: **The DeGen Risk Auditor**.
It delegates a smart contract vulnerability scan to Gemini Miners, validates their output using Groq-Llama-3 for PoUW scoring, and mints an ERC-8004 cryptographic proof to Base Sepolia.

---

## 🚀 Quickstart & Runbook

### Prerequisites
- Node.js >= 18.x
- `pnpm` (recommended) or `npm`
- Git

### Installation
1. Clone the repository and navigate to the project directory:
   ```bash
   cd apps/cortex-os
   ```
2. Install dependencies (Turborepo workspace):
   ```bash
   npm install
   ```
3. Copy the environment variables template:
   ```bash
   cp .env.example .env
   ```
   *Note: You must provide your own API keys for Supabase, Gemini, Groq, Pinata, and Cortensor to run the full pipeline.*

### Running the Application
Start the Next.js development server:
```bash
npm run dev
```
Navigate to `http://localhost:3000` to access the Mission Control Canvas.

---

## 🏗️ Architecture & Integration

For a deep dive into the system's topological sort, ERC-8004 integration, and the $0.00 Serverless architecture, please view the complete [ARCHITECTURE.md](./ARCHITECTURE.md) document within this directory.

### Tool List (What the Agent Can Do)
1.  **Smart Contract Ingestion:** Extracts bytecode/functions directly from Base/Etherscan verified addresses or raw JSON.
2.  **Fractal Reasoning (Cortensor Miner):** Analyzes bytecode for Reentrancy, Overflow, and Control Flaws.
3.  **Cross-Model Verification (PoUW):** A dedicated Llama-3 Validator evaluates the Miner's report against the original bytecode to generate a Rubric Score.
4.  **Immutable Provenance:** Bundles the prompt, the output, and the Validator score into an IPFS Evidence Bundle.
5.  **Blockchain Settlement:** Mints the execution state as an ERC-8004 NFT on Base Sepolia.

### Safety & Constraints (What it Refuses to Do)
-   **Prompt Bleed Mitigation:** The system isolates the target contract bytecode within strict cryptographic `<DATA_BLOCK>` delimiters. It refuses to execute arbitrary system commands (`ignore previous instructions...`) embedded within the target contract.
-   **No Private Key Delegation:** The agent only reads on-chain state and emits IPFS proofs. It does NOT possess trading wallet keys or execution signatures to move live funds.

---

## 🛡️ Trust & Verification (Hackathon #4 Focus)

Cortex.OS heavily relies on **Rubric-based Scoring (PoUW)** to guarantee AI safety.

Instead of implicitly trusting a single LLM output, the pipeline executes a secondary **Validator Node**. The Validator evaluates the primary Miner's performance on three axises: **Accuracy (40%)**, **Formatting (30%)**, and **Depth (30%)**. This transparent "Proof of Useful Work" score is permanently embedded in the final, on-chain IPFS payload, proving the Cortensor network executed verified consensus.

---

## 🎥 Demo & Artifacts

-   **Demo Video:** [Insert YouTube/Loom Link Here] *(Recorded for Hackathon Submission)*
-   **Target Contract (Base Sepolia):** `0xABeEDDDbB67Ec02B1c426C6EaE8d1618a6278e2f` (CortexAgenticProof.sol)

---
> **TRACK:** Agent Apps (Delegation + Execution Loops) | Cortensor Hackathon #4 
