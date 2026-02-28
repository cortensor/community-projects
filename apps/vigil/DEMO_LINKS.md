# Demo Video & Live URL

**Live Demo**: [https://vigil-j1mo5b288-marvy247s-projects.vercel.app/](https://vigil-j1mo5b288-marvy247s-projects.vercel.app/)

**Demo Video**: [https://youtu.be/QDhwuFRhrcQ](https://youtu.be/QDhwuFRhrcQ)

## Demo Video

**Status:** Ready to record

### Recording Instructions

1. **Setup:**
   ```bash
   ./start.sh
   # Wait for services to start
   # Open http://localhost:5173
   ```

2. **Recording Tools:**
   - OBS Studio (recommended)
   - Loom
   - QuickTime (Mac)
   - Windows Game Bar (Windows)

3. **Recording Checklist:**
   - [ ] Record in 1080p or higher
   - [ ] Enable microphone for narration
   - [ ] Show full browser window
   - [ ] Demonstrate complete workflow (2-3 minutes)
   - [ ] Follow DEMO.md script

4. **Upload:**
   - YouTube (unlisted or public)
   - Loom
   - Vimeo

5. **Add link here:**
   ```
   🎬 Demo Video: [YOUR_VIDEO_URL_HERE]
   ```

---

## 🌐 Live Demo URL

### Option 1: Deploy to Vercel (Frontend) + Railway (Backend)

**Frontend (Vercel):**
```bash
cd frontend
vercel --prod
```

**Backend (Railway):**
```bash
cd backend
railway up
```

**Update frontend API URLs:**
- Edit `frontend/src/hooks/useMetrics.ts`
- Edit `frontend/src/hooks/useIncidents.ts`
- Replace `localhost:3001` with Railway URL

### Option 2: Deploy to Single Server (AWS EC2, DigitalOcean, etc.)

```bash
# On server
git clone [your-repo]
cd vigil
docker-compose up -d
```

**Access:**
- Frontend: http://your-server-ip:5173
- Backend: http://your-server-ip:3001

### Option 3: Local Demo

```bash
./start.sh
```

**Access:**
- Frontend: http://localhost:5173
- Backend: http://localhost:3001

**Share via:**
- Screen sharing during demo
- ngrok tunnel: `ngrok http 5173`
- Record video and share link

---

## 📝 Reproduction Steps

### Quick Start (2 minutes)

1. **Clone repository:**
   ```bash
   git clone https://github.com/yourusername/vigil.git
   cd vigil
   ```

2. **Start services:**
   ```bash
   ./start.sh
   ```

3. **Open browser:**
   ```
   http://localhost:5173
   ```

4. **Trigger demo:**
   - Click "Simulate Incident" button
   - Select incident type (High Latency, High Error Rate, or Validator Drop)
   - Watch full cycle complete

5. **View results:**
   - See metrics spike in real-time
   - Watch status change: detected → analyzing → confirmed → acting → resolved
   - Click incident card to view evidence bundle
   - Check Cortensor session IDs
   - View model outputs and consensus

### Detailed Walkthrough (5 minutes)

1. **Initial State:**
   - Dashboard shows healthy metrics
   - All values in green
   - WebSocket connected indicator

2. **Simulate High Latency:**
   - Click "⚡ High Latency" button
   - Latency metric turns red
   - Value jumps to 300-400ms
   - New incident card appears

3. **Watch Analysis:**
   - Status: "analyzing"
   - Agent sends to Cortensor PoI
   - 3 models validate in parallel
   - Takes 2-3 seconds

4. **View Consensus:**
   - Click incident card
   - See 3 session IDs
   - View model outputs:
     - gpt-4: isAnomaly=true, confidence=0.87
     - claude-3: isAnomaly=true, confidence=0.91
     - gemini-pro: isAnomaly=true, confidence=0.84
   - Consensus: YES (3/3 agree)
   - Average confidence: 0.873

5. **Check Actions:**
   - Status: "acting"
   - GitHub issue created (if configured)
   - Discord alert sent (if configured)
   - Incident logged to database

6. **View Evidence Bundle:**
   - Scroll to "Evidence Bundle" section
   - See complete JSON with:
     - Metrics snapshot
     - Cortensor session IDs
     - Model outputs with validator scores
     - Actions taken
     - Timeline of events

7. **Check History:**
   - Navigate to "Incidents" page
   - See all past incidents
   - Click any to view details

### API Testing (3 minutes)

1. **Health Check:**
   ```bash
   curl http://localhost:3001/api/health
   ```

2. **Get Current Metrics:**
   ```bash
   curl http://localhost:3001/api/metrics/current
   ```

3. **Simulate Incident:**
   ```bash
   curl -X POST http://localhost:3001/api/simulate \
     -H "Content-Type: application/json" \
     -d '{"type":"high_latency"}'
   ```

4. **Get Incidents:**
   ```bash
   curl http://localhost:3001/api/incidents
   ```

5. **Run Test Suite:**
   ```bash
   ./examples/test-agent.sh
   ```

### Docker Deployment (5 minutes)

1. **Build and run:**
   ```bash
   docker-compose up -d
   ```

2. **Check logs:**
   ```bash
   docker-compose logs -f backend
   ```

3. **Access:**
   - Frontend: http://localhost:5173
   - Backend: http://localhost:3001

4. **Stop:**
   ```bash
   docker-compose down
   ```

---

## 🎯 Key Features to Demonstrate

1. **Real-time Monitoring**
   - Live metrics updating every 2 seconds
   - WebSocket connection indicator

2. **Multi-Model Validation (PoI)**
   - 3 models analyze in parallel
   - Session IDs visible
   - Consensus calculation shown

3. **Validator Scoring (PoUW)**
   - Each model has validator score
   - Scores weight confidence
   - Average displayed

4. **Automated Actions**
   - GitHub issue creation
   - Discord webhook alerts
   - Database logging

5. **Evidence Bundles**
   - Complete audit trail
   - JSON format
   - IPFS-ready
   - Timeline visualization

6. **Safety Features**
   - Rate limiting (5 min window)
   - Multi-model consensus required
   - Read-only monitoring
   - No dangerous operations

---

## 📊 Expected Results

After running demo, you should see:

- ✅ Incident detected within 1 second
- ✅ Analysis completed in 2-3 seconds
- ✅ 3 Cortensor session IDs generated
- ✅ Consensus reached (or not)
- ✅ Actions executed (if consensus)
- ✅ Evidence bundle generated
- ✅ Incident resolved
- ✅ Total cycle: 4-5 seconds

---

## 🐛 Troubleshooting

**Services won't start:**
- Check Node.js version: `node --version` (need 18+)
- Install dependencies: `cd backend && npm install && cd ../frontend && npm install`
- Check ports 3001 and 5173 are free

**No incidents appearing:**
- Check backend logs: `docker-compose logs backend`
- Verify WebSocket connection (green indicator)
- Try manual API call: `curl -X POST http://localhost:3001/api/simulate -H "Content-Type: application/json" -d '{"type":"high_latency"}'`

**Frontend can't connect:**
- Verify backend is running: `curl http://localhost:3001/api/health`
- Check browser console for errors
- Verify API URLs in frontend hooks

---

## 📞 Support

- GitHub Issues: [your-repo]/issues
- Discord: discord.gg/cortensor
- Documentation: See README.md, ARCHITECTURE.md, DEMO.md

---

**Once you have a live URL or video, update this file with the links!**
