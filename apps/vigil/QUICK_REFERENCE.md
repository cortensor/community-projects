# Quick Reference Guide

## 🚀 Getting Started (30 seconds)

```bash
./start.sh
# Open http://localhost:5173
# Click "Simulate Incident"
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `backend/src/index.ts` | Main server entry point |
| `backend/src/managers/incident.ts` | Core orchestration logic |
| `backend/src/detectors/cortensor.ts` | PoI implementation |
| `frontend/src/components/Dashboard.tsx` | Main UI |
| `frontend/src/hooks/useMetrics.ts` | WebSocket connection |

## 🔧 Common Commands

```bash
# Start development
./start.sh

# Run tests
./examples/test-agent.sh

# Docker deployment
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 🌐 Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Health check |
| `/api/metrics/current` | GET | Current metrics |
| `/api/metrics/history` | GET | Historical metrics |
| `/api/incidents` | GET | All incidents |
| `/api/incidents/:id` | GET | Specific incident |
| `/api/simulate` | POST | Trigger demo incident |
| `/ws` | WebSocket | Real-time metrics |

## 🎬 Demo Flow (2 minutes)

1. **Show dashboard** (10s) - Healthy state
2. **Simulate incident** (5s) - Click button
3. **Watch detection** (15s) - Metrics spike
4. **Show analysis** (20s) - Cortensor PoI
5. **Show actions** (15s) - GitHub + Discord
6. **Show evidence** (20s) - Complete audit trail
7. **Explain safety** (15s) - Guardrails
8. **Show history** (10s) - Past incidents
9. **Show architecture** (15s) - System design
10. **Closing** (10s) - Open source

## 🔑 Environment Variables

```env
CORTENSOR_API_URL=https://api.cortensor.network
CORTENSOR_API_KEY=your_key
GITHUB_TOKEN=your_token
GITHUB_REPO=owner/repo
DISCORD_WEBHOOK_URL=your_webhook
PORT=3001
DRY_RUN=false
```

## 🐛 Troubleshooting

**Backend won't start:**
```bash
cd backend
rm -rf node_modules
npm install
npm run dev
```

**Frontend can't connect:**
- Check backend is running on port 3001
- Verify CORS settings
- Check browser console for errors

**WebSocket disconnects:**
- Check firewall settings
- Verify WebSocket URL in `useMetrics.ts`
- Check nginx/proxy configuration

## 📊 Metrics Thresholds

| Metric | Baseline | Warning | Critical |
|--------|----------|---------|----------|
| Latency | 100ms | 150ms | 200ms |
| Error Rate | 1% | 2% | 5% |
| Validator Score | 0.9 | 0.85 | 0.7 |

## 🎯 Incident Types

- `high_latency` - Latency > 2x baseline
- `high_error_rate` - Error rate > 5x baseline
- `validator_score_drop` - Score < 80% baseline

## 🔒 Safety Features

- ✅ Rate limiting (1 action per type per 5 min)
- ✅ Multi-model consensus (≥2 models)
- ✅ Read-only monitoring
- ✅ Complete audit trails
- ✅ Dry-run mode available

## 📚 Documentation

- `README.md` - Overview & quickstart
- `ARCHITECTURE.md` - System design
- `DEPLOYMENT.md` - Deployment guides
- `DEMO.md` - Demo script
- `TOOLS.md` - Agent capabilities
- `CONTRIBUTING.md` - How to contribute
- `PROJECT_SUMMARY.md` - Complete overview

## 🎓 Key Concepts

**PoI (Proof of Inference):**
- Runs same prompt across multiple models
- Compares outputs for consensus
- Reduces false positives

**PoUW (Proof of Useful Work):**
- Uses validator scores
- Weights model confidence
- Ensures quality outputs

**Evidence Bundle:**
- Complete audit trail
- Session IDs for verification
- Timeline of events
- JSON format (IPFS ready)

## 🔗 Links

- GitHub: [your-repo-url]
- Discord: discord.gg/cortensor
- Docs: docs.cortensor.network
- Hackathon: [hackathon-link]

## 💡 Tips

- Use demo mode for presentations
- Check evidence bundles for debugging
- Monitor WebSocket connection status
- Review logs for troubleshooting
- Test with dry-run mode first

## 🎉 Quick Wins

1. **Impressive demo:** One-click simulation
2. **Real integrations:** GitHub + Discord
3. **Complete audit:** Evidence bundles
4. **Production ready:** Docker + CI/CD
5. **Well documented:** 7 comprehensive docs

---

**Need help?** Check the full documentation or join Discord!
