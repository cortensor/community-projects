# Project Status

**Current Phase**: 🟢 Active / Beta

**Roadmap**:
- [x] **Core Oracle Logic**: Proposal parsing, claim extraction, and validation.
- [x] **Consensus Engine**: Multi-miner agreement logic with generic LLM backend.
- [x] **Web Interface**: Full React dashboard with real-time WebSocket streaming.
- [x] **Versioning**: Support for v1, v2, v3 proposal updates with claim diffs.
- [x] **History**: Persistent validation history with SQLite/Postgres.
- [ ] **Mainnet Integration**: Connecting to Cortensor Mainnet for on-chain attestation.
- [ ] **Mobile App**: Dedicated mobile view for governance on the go.

**Known Issues**:
- **Cold Starts**: On free-tier hosting (Render), the first request may take ~50s to wake up the service.
- **WebSocket Timeout**: extremely long validation jobs (>2 mins) may require reconnection logic on some proxies.
