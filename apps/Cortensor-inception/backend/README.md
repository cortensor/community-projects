# Inception — Backend

Minimal backend to start development quickly.

Prereqs: Node.js >= 18

Install dependencies:

```bash
cd backend
npm install
cp .env.example .env
# edit .env if necessary
npm run dev
```

Endpoints:
- `GET /health` — health check
- `POST /infer-escrow` — dummy escrow decision (body: `{ prompt: string }`)
- `POST /api/claims/submit` — submit a claim (body: `{ type, claim, context?, risk?, sessionId? }`) — server reads `ATTESTOR_KEY` (defaults to `attestor.key`) to sign evidence
- `POST /api/claims/llm` — generate N claims using a configured LLM and run the pipeline (body: `{ prompt, miners?, temperature?, apiUrl?, authenticated?, sessionId? }`). The server uses `LLM_API_URL` by default if `apiUrl` is not provided.
- `POST /api/claims/audit/verify` — verify a bundle with a public key (body: `{ bundle, attestation, publicKeyPem }`)
- `POST /api/risk` — run risk analysis on a `TreasurySnapshot` payload (body: `{ totalUsdValue: number, positions: [{ token: string, usdValue: number }] }`) — uses ADK AgentBuilder if available, falls back to LLM or deterministic analysis

Replace the placeholder auth and Cortensor integration with real services when ready.
