# Release History

## v1.0.0 (2025-12-28)
**Initial Release of Xea - The DAO Governance Oracle**

### Features
- **Accurate Validation**: Break down proposals into atomic claims and validate them against web evidence.
- **Selective Revalidation**: Update proposals (v1 -> v2) and only re-check modified claims to save costs/time.
- **Live Transparency**: Watch miners research claims in real-time via WebSockets.
- **Claim Diffs**: Visual red/green diffs showing exactly what changed between proposal versions.
- **Verdict Scoring**: Confidence scores (0-100%) based on miner consensus.

### Deployment Supported
- **Frontend**: Vite/React (Vercel ready)
- **Backend**: FastAPI/Python (Render/Docker ready)
- **Database**: SQLite (Dev) / PostgreSQL (Prod)
