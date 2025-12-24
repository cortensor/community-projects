# InsightAI 🔍

> AI Research Agent powered by Cortensor's decentralized inference network

[![Built for Hackathon #3](https://img.shields.io/badge/Cortensor-Hackathon%20%233-22c55e)](https://dorahacks.io/hackathon/1768)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🌐 Live Demo

[https://insightai.vercel.app](https://insightai.vercel.app) *(Deploy to Vercel)*

## 🎯 What is InsightAI?

InsightAI is a decentralized AI research assistant that leverages Cortensor's distributed inference network to provide trusted, verifiable research insights. Instead of relying on a single AI provider, InsightAI uses Cortensor's multi-miner consensus to ensure accurate and reliable research outputs.

## ✨ Features

- 🔍 **Research Query Interface** - Ask any research question
- 🌐 **URL Analysis** - Summarize content from any URL
- ✅ **Verifiable Results** - Each response links to Cortensor dashboard for verification
- 📊 **Structured Output** - Results formatted as summary + bullet points
- 🎨 **Premium Dark UI** - Beautiful glassmorphism design with animations
- 🔄 **Demo Mode Fallback** - Works even when TestNet miners are unavailable

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   InsightAI     │────▶│ Cortensor       │────▶│ Decentralized   │
│   Frontend      │     │ Router Node     │     │ Miners (94+)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                       │
         │                       ▼                       │
         │              ┌─────────────────┐              │
         │              │ Session #127    │              │
         │              │ Gemma 3 270M    │              │
         │              └─────────────────┘              │
         │                       │                       │
         │                       ▼                       │
         └──────────────│ Blockchain TX   │◀─────────────┘
                        │ Verification    │
                        └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/insightai.git
cd insightai

# Install dependencies
npm install

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## ⚙️ Configuration

### Environment Variables

Create a `.env.local` file:

```env
# Cortensor Router Configuration
CORTENSOR_ROUTER_URL=http://localhost:5010
CORTENSOR_API_KEY=your-api-key-from-dashboard
CORTENSOR_SESSION_ID=127

# Set to false for real API, true for demo only
USE_MOCK=false
```

### Running Your Own Router Node

1. **Install cortensord** from [Cortensor Installer](https://github.com/cortensor/installer)
2. **Create a session** on [TestNet 0 Dashboard](https://dashboard-testnet0.cortensor.network/session)
3. **Start the router**: `cortensord ~/.cortensor/.env routerv1`
4. **Update `.env.local`** with your session ID

See [ENV.md](./ENV.md) for detailed configuration instructions.

## 🔧 Tech Stack

- **Framework**: Next.js 16 (App Router + Turbopack)
- **Styling**: Tailwind CSS v4
- **Components**: shadcn/ui
- **AI Backend**: Cortensor Router API (`/api/v1/completions`)
- **Blockchain**: Arbitrum Sepolia TestNet
- **Deployment**: Vercel

## 📡 Cortensor Integration

InsightAI integrates with Cortensor's Router Node API:

### How It Works

1. **Session Creation**: Create a session with COR tokens on the dashboard
2. **Router Registration**: Your router node registers with the session
3. **Task Submission**: Research queries are sent to `/api/v1/completions/{sessionId}`
4. **Multi-Miner Processing**: Query processed by 94+ decentralized miners
5. **Blockchain Verification**: Each response includes a TX hash for verification
6. **Results Display**: Structured output with verification badge

### API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/completions/{sessionId}` | POST | Submit inference request |
| `/api/v1/sessions` | GET | List available sessions |

### Request Format

```javascript
POST /api/v1/completions/127
{
  "prompt": "Research question here...",
  "stream": false,
  "timeout": 30
}
```

### Response Handling

The app parses Cortensor responses into structured format:
- **Summary**: First paragraph of the response
- **Bullet Points**: Lines starting with `-` or `•`
- **Verification**: Session ID + Task ID for dashboard verification

## 🎮 Demo Mode

When the Cortensor TestNet is unavailable, InsightAI automatically falls back to demo mode:

- Provides pre-configured research responses
- Shows "🎮 Demo Mode" badge in the UI
- Simulates realistic processing delay
- Maintains full functionality for testing

Set `USE_MOCK=true` in `.env.local` to force demo mode.

## 🎨 Screenshots

### Research Interface
*Dark mode UI with glassmorphism design*

### Verified Results
*Results show "✓ Verified via Cortensor" badge when using real API*

### Demo Mode
*Shows "🎮 Demo Mode" badge when using fallback*

## 🏆 Hackathon Track

**Agentic Applications** - InsightAI is an autonomous research assistant that:
- Acts on user queries without requiring step-by-step guidance
- Leverages Cortensor's decentralized inference for trust
- Produces verifiable, structured research outputs
- Includes blockchain transaction verification

### Cortensor Features Used
- ✅ Router Node API (`/api/v1/completions`)
- ✅ Session Management (TestNet 0)
- ✅ Multi-miner inference (94+ nodes)
- ✅ Blockchain verification (TX hashes)
- ✅ WebSocket communication

## 🤖 Agent Specification

### Action List
| Action | Description |
|--------|-------------|
| `research_query` | Process natural language research questions |
| `url_analysis` | Fetch and summarize web content |
| `structured_output` | Format response as summary + bullet points |
| `verification_link` | Provide Cortensor dashboard link for verification |

### Tool Integrations
| Tool | Purpose |
|------|---------|
| **Cortensor Router API** | Decentralized AI inference |
| **Session Management** | TestNet 0 session handling |
| **URL Fetcher** | Web content retrieval for analysis |
| **Response Parser** | Extract structured data from LLM output |

### Safety Guardrails
- 🛡️ **Rate Limiting**: API requests throttled to prevent abuse
- 🛡️ **Input Validation**: Query length and content validation
- 🛡️ **Timeout Handling**: 15-second timeout with graceful fallback
- 🛡️ **Demo Fallback**: Automatic fallback when network unavailable
- 🛡️ **No PII Storage**: No user data stored on server

## 📝 License

MIT License - see [LICENSE](LICENSE) file.

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a PR.

## 🔗 Links

- [Cortensor Documentation](https://docs.cortensor.network)
- [Cortensor Router Setup](https://docs.cortensor.network/getting-started/router-node-setup)
- [TestNet 0 Dashboard](https://dashboard-testnet0.cortensor.network)
- [Hackathon #3 Details](https://docs.cortensor.network/community-and-ecosystem/hackathon/hackathon-3)
- [DoraHacks Submission](https://dorahacks.io/hackathon/1768)
