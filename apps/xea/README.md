# Xea

**Verifiable governance intelligence powered by decentralized inference**

Xea produces verifiable governance intelligence by decomposing DAO proposals into atomic claims, validating them via redundant decentralized inference (PoI/PoUW), and producing signed, machine-verifiable evidence bundles and attestations.

## Quickstart

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.11+ (for local backend development)

### Running with Docker Compose

```bash
# Clone the repository
git clone https://github.com/your-org/xea-governance-oracle.git
cd xea-governance-oracle

# Copy environment configuration
cp .env.example .env

# Start all services
docker-compose up --build
```

Services will be available at:
- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs

### Local Development

```bash
# Backend
cd backend
pip install -e .
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev

# Workers
cd workers
python worker.py
```

## LLM Usage (Optional)

Xea optionally uses **Google Gemini** to assist with claim extraction.
If no `GEMINI_API_KEY` is configured in `.env`, Xea automatically falls back to a **deterministic rule-based extractor** to ensure reproducibility and demo stability.
All validation, PoI, and PoUW logic is independent of the LLM provider.

### Cortensor Testnet Integration

Xea runs on a self-hosted Cortensor Router (installed from the official Cortensor
installer) connected to Cortensor Testnet-0.

All validation requests are executed by Cortensor-operated miners and scored
using Proof of Inference (PoI) and Proof of Useful Work (PoUW).

Xea uses Cortensor’s documented Web2 API for session-based decentralized inference.
All inference calls in this project are real, auditable, and reproducible.

## Documentation

- [SPEC.md](./SPEC.md) — Full specification with data models, endpoints, and acceptance criteria
- [docs/demo_script.md](./docs/demo_script.md) — Demo walkthrough
- [docs/how_to_validate.md](./docs/how_to_validate.md) — Validation guide

## Project Structure

```
/
├── backend/           # FastAPI backend application
├── frontend/          # React frontend application
├── workers/           # RQ workers and mock miners
├── infra/             # Docker and deployment configs
├── contracts/         # Solidity attestation contracts (placeholder)
├── tests/             # Test suite
└── docs/              # Documentation
```

## Demo Script

See [docs/demo_script.md](./docs/demo_script.md) for a step-by-step demo walkthrough.

## License

MIT — see [LICENSE](./LICENSE)
