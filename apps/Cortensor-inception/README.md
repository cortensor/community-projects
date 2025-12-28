# Inception - Layered trust for AI inference. AI outputs are released only after decentralized validation.

Inception is a trust-conditional execution layer that prevents AI outputs from being accepted or acted upon unless decentralized validators approve them. It holds AI inference results in escrow, validates them via redundant inference and scoring, and only releases outputs that meet configurable acceptance criteria.

---

## 🚨 Problem

Modern AI systems are increasingly agentic, with the ability to act on infrastructure, sign transactions, and make high-impact decisions. Current inference is fundamentally unsafe because:

- Inference is unverified: no proof that the model actually ran, the correct model/version was used, or the output wasn’t altered.
- Single-model outputs are brittle: LLMs hallucinate, fail silently, and produce inconsistent results.
- Agents have no objective mechanism for deciding when to act: they lack confidence signals and independent validation.
- There is no concept of conditional AI execution: outputs are always released, even when unsafe.

**Core Gap:** There is no mechanism to condition the release of AI outputs on decentralized trust and validation.

---

## 💡 Proposed Solution — Inference Escrow

Inference Escrow treats AI inference like a transaction that must clear escrow before being accepted. Instead of assuming AI outputs are valid, the system:

- Holds outputs in escrow
- Runs redundant, independent inference (Proof of Inference — PoI)
- Scores outputs for usefulness (Proof of Useful Work — PoUW)
- Releases, rejects, or escalates results based on configurable rules

One-line definition: Inference Escrow is a trust-conditional execution layer where AI outputs are released only if decentralized validators approve them.

---

## 🧠 Why this is new

No existing AI system provides conditional output release based on independent validator approval and verifiable proof of execution. This primitive requires decentralized inference networks (e.g., Cortensor) to provide independence, proofs, and economic incentives.

---

## 🏗️ Conceptual Architecture

```
Client / Agent
   ↓
Inference Escrow API
   ↓
Cortensor Session (PoI)
   ↓
Redundant Inference (N nodes)
   ↓
Validator Scoring (PoUW)
   ↓
Escrow Decision Engine
   ↓
Outcome: RELEASE | REJECT | ESCALATE
```

--- 

## 🔐 Escrow Decision States

| State      | Meaning                                  |
|------------|------------------------------------------|
| RELEASE    | Output is trustworthy and safe to act on |
| REJECT     | Output failed validation and must not be used |
| ESCALATE   | Human or higher-cost validation required |

Each decision includes a confidence score, validator evidence, and disagreement metrics.

---

## 🔁 Validator Pipeline (PoUW)

Combined confidence formula (example):

```ts
confidence =
  0.5 * semanticAgreement +
  0.3 * rubricScore +
  0.2 * deterministicScore;
```

Thresholds (example):

- `>= 0.85` → RELEASE
- `< 0.5` → REJECT
- else → ESCALATE

Validators include agreement checks, LLM rubric scoring, deterministic rules (regex, JSON schema, numeric checks), and embedding similarity.

---

## 📦 Evidence Bundle

A structured proof produced for every escrow decision. Example:

```json
{
  "decision": "RELEASE",
  "confidence": 0.89,
  "validators": 4,
  "agreement": "high",
  "proofs": [
    { "node": "node-1", "proof": "..." },
    { "node": "node-2", "proof": "..." }
  ]
}
```

Evidence bundles are JSON artifacts that can optionally be anchored (IPFS, on-chain) for public verifiability.

---

## 🧪 API (MVP)

- `POST /infer-escrow`
  - Request: `{ prompt, escrowRules?, metadata? }`
  - Response (async or sync): `{ id, status, decision?, evidence? }`

- `GET /escrow/:id`
  - Returns full record, evidence bundle, and decision trace.

Example `curl`:

```bash
curl -X POST http://localhost:3000/infer-escrow \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Summarize the security findings","escrowRules":{"threshold":0.85}}'
```

---

## 🗂️ Folder Structure (MVP)

```
inference-escrow/
├── src/
│   ├── server.ts
│   ├── app.ts
│   ├── routes/escrow.routes.ts
│   ├── cortensor/
│   │   ├── client.ts
│   │   ├── session.ts
│   │   └── inference.ts
│   ├── escrow/
│   │   ├── engine.ts
│   │   ├── decision.ts
│   │   └── types.ts
│   ├── validators/
│   │   ├── agreement.ts
│   │   ├── rubric.ts
│   │   └── deterministic.ts
│   ├── evidence/bundle.ts
│   ├── storage/db.ts
│   └── index.ts
├── diagrams/
├── README.md
├── .env.example
├── package.json
└── LICENSE
```

---


## 🏆 Hackathon #3 — Short summary

We are building this project for **Hackathon #3 (Cortensor)** — focused on agentic applications, PoI/PoUW validation, tooling, and public goods. Key points:

- **Objective:** Build PoC apps, validators, or developer tooling that leverage Cortensor’s decentralized inference (PoI/PoUW).
- **Focus areas:** Agentic assistants, validation utilities, app stores, SDKs/CLIs, observability, and public/free inferencing.
- **Timeline:** Kick-off: Nov 21, 2025 · Submission deadline: Jan 4, 2026.
- **Prize pool (high-level):** Top prizes range from $800 to $50 (in $COR equivalents); ongoing grants available for standout projects.
- **How to participate:** Join Discord (discord.gg/cortensor), build in the community repo, and submit a public repo with a demo and README.

This README highlights which hackathon we're participating in and what to prioritize.

---

## 📄 License

This project is released under the MIT License. See [LICENSE](LICENSE) for details.

---

## 🙋 Contributing

Contributions are welcome. Please open issues for bugs and feature requests. For major changes, open a PR and include tests and docs.

---

## Acknowledgements

This project is inspired by cutting-edge work in decentralized inference networks and trust primitives for agentic AI.

---

## Getting Started (run locally)

Follow the order below. Backend must be running before using the frontend demo.

Quick judge/demo steps:

1. Start backend (defaults to http://localhost:4000). Ensure `ATTESTOR_KEY` or `attestor.key` exists when you want real signatures.
2. Start frontend (`npm run dev`) and open `http://localhost:3000/claim` to submit a claim and view evidence + an option to verify with the attestor public key.

---

## Local setup for AI-backed processing 🔧

To run the full system (LLM + simulator + evidence bundling) you can set these environment variables in your shell or a `.env.local` file in `backend/`:

- `LLM_API_URL` — full URL to your LLM chat API (e.g., `https://api.openai.com/v1/chat/completions` or an Ollama endpoint)
- `LLM_API_KEY` — API key for the LLM provider (if required)
- `LLM_MODEL` — provider model identifier (optional)
- `LLM_PROVIDER` — choice of LLM provider integration (auto | adk | fetch). When `adk`, the app will attempt to use the `adk-ts` package if installed.
- `LLM_TEMPERATURE` — default temperature for LLM generation (0.0 - 1.0)
- `SESSION_ID` — default session id to use for requests (default: `1`)
- `ATTESTOR_KEY` — path to the attestor private key (optional; if omitted the service will still run but auditing will be marked as unavailable)

Notes:
- The backend is defensive: it validates inputs, retries transient LLM failures, and will gracefully mark auditing/auditOk as false when signing/verifying is unavailable, so you can run locally without an attestor key.
- Start the backend with `cd backend && npm run dev` and frontend with `cd frontend && npm run dev`.



1. Backend (Node + TypeScript + Express)

```bash
cd backend
npm install
cp .env.example .env
# edit .env as needed
npm run dev
```

2. Frontend (Next.js + TypeScript + Tailwind)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 and click "Login" to call the `/infer-escrow` demo endpoint.

---
