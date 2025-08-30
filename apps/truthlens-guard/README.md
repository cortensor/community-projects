# 🔍 TruthLens: AI-Powered Fact-Checker & Credibility Oracle

### *"Trustless, Transparent, and Decentralized Fact Verification"*

[![Cortensor Integration](https://img.shields.io/badge/Cortensor-Decentralized%20AI-blue)](https://cortensor.network)
[![Tech Stack](https://img.shields.io/badge/Stack-React%20%7C%20TypeScript%20%7C%20Node.js-green)](#tech-stack)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

TruthLens combats the **misinformation crisis** using **Cortensor's decentralized inference network**. Instead of relying on centralized fact-checking authorities, TruthLens leverages multiple independent AI agents (miners) to deliver transparent, explainable credibility scores.

## 🎯 Problem Statement

Misinformation spreads **faster than verified facts**. Centralized solutions fail because:

- 🔒 **Lack transparency** (black-box decisions)
- 🏛️ **Risk censorship** (controlled by single entities)  
- 📈 **Scale poorly** with information volume
- 🎯 **Introduce bias** through centralized control

**TruthLens solves this via decentralized, trustless AI verification through Cortensor.**

---

## ✨ Key Features

### 🌐 **Decentralized AI Consensus**
- Leverages **Cortensor's distributed inference network**
- Multiple independent AI miners analyze each claim
- **No single point of failure** or control
- Transparent consensus aggregation

### 🔍 **Multi-Modal Analysis**
- **Text claims** - Headlines, statements, social media posts
- **URL analysis** - Full article and content verification
- **Real-time processing** with live status updates
- **Batch analysis** for multiple claims

### 📊 **Explainable Results**
- **Credibility scores** (0-100%) with confidence intervals
- **Detailed reasoning** from each AI miner
- **Supporting sources** with credibility ratings
- **Consensus summaries** explaining the verdict

### 🔗 **Multiple Interfaces**
- **Web Application** - Full-featured analysis dashboard
- **Browser Extension** - Real-time fact-checking overlay (coming soon)
- **REST API** - Integration for third-party applications
- **Mobile-responsive** design

---

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+ 
- **npm** or **yarn**
- **Cortensor API Key** (optional for demo mode)

### 1. Clone & Install

```bash
git clone https://github.com/cortensor/community-projects.git
cd community-projects/apps/truthlens-guard

# Install frontend dependencies
npm install

# Install backend dependencies
cd backend
npm install
```

### 2. Environment Setup

```bash
# Backend (.env)
cd backend
cp .env.example .env

# Edit with your configuration
PORT=3001
NODE_ENV=development
CORTENSOR_API_KEY=your-cortensor-api-key-here
CORTENSOR_SUBNET_UID=1

# Frontend (.env)
cd ..
echo "VITE_API_URL=http://localhost:3001/api" > .env
```

### 3. Start Development Servers

```bash
# Terminal 1: Start backend
cd backend
npm run dev

# Terminal 2: Start frontend  
cd ..
npm run dev
```

### 4. Open Application

- **Web App**: http://localhost:5173
- **API Health**: http://localhost:3001/api/health
- **Backend Status**: http://localhost:3001/api/analysis/status

---

## 🧠 Cortensor Decentralized AI Integration

### **Real Cortensor Network Usage**

When configured with real Cortensor credentials:

```typescript
// Cortensor API Configuration
const inferenceRequest = {
  prompt: factCheckPrompt,
  model: 'fact-check-v1',
  subnet_uid: 1,
  min_responses: 3,
  max_responses: 10,
  timeout_ms: 30000,
  temperature: 0.1,
  consensus_required: true,
  validate_responses: true
};

// Submit to decentralized network
const response = await cortensorClient.post('/v1/inference/submit', inferenceRequest);
```

### **Demo Mode (Development)**

For development and demos, TruthLens simulates Cortensor's decentralized network:

- **5-12 simulated AI miners** with different specializations
- **Realistic processing delays** (2-6 seconds)
- **Diverse analysis approaches**: fact-checkers, source validators, bias detectors
- **Consensus variance** to demonstrate distributed decision-making

### **Miner Specializations**

| Miner Type | Focus Area | Example Analysis |
|------------|------------|------------------|
| **Fact-Checker** | Cross-referencing databases | "Strong verification through authoritative sources" |
| **Source Validator** | Evaluating source credibility | "High-quality peer-reviewed evidence" |  
| **Bias Detector** | Identifying misinformation patterns | "Minimal bias with objective reporting" |
| **Research Specialist** | Academic literature analysis | "Supported by robust scientific studies" |

---

## 📱 Usage Examples

### **Text Claim Analysis**

```bash
curl -X POST http://localhost:3001/api/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "claim": "Climate change is primarily caused by human activities",
    "type": "text",
    "options": {
      "minMiners": 5,
      "timeout": 30000
    }
  }'
```

### **Response Format**

```json
{
  "success": true,
  "data": {
    "claim": "Climate change is primarily caused by human activities",
    "type": "text",
    "analysis": {
      "credibilityScore": 0.87,
      "confidence": 0.92,
      "isCredible": true,
      "consensus": "Based on analysis from 7 independent AI miners, this claim shows strong credibility with scientific consensus...",
      "supportingSources": [
        {
          "url": "nature.com",
          "title": "Nature Scientific Papers",
          "credibility": 0.95,
          "excerpt": "Peer-reviewed climate research confirms...",
          "domain": "nature.com"
        }
      ],
      "minerResponses": [
        {
          "minerId": "cortensor_fact-checker_001",
          "score": 0.89,
          "reasoning": "Strong verification found through cross-referencing authoritative databases...",
          "sources": ["nature.com", "ipcc.ch"]
        }
      ]
    },
    "metadata": {
      "processedAt": "2025-08-30T10:45:00.000Z",
      "minerCount": 7,
      "processingTimeMs": 3420
    }
  }
}
```

---

## 🛠️ Tech Stack

### **Frontend**
- **React 18** + **TypeScript** - Modern component architecture
- **Vite** - Fast development and building
- **Tailwind CSS** - Utility-first styling
- **Framer Motion** - Smooth animations
- **Radix UI** - Accessible component primitives
- **React Query** - Server state management

### **Backend**
- **Node.js** + **Express** - RESTful API server
- **TypeScript** - Type safety and developer experience
- **Axios** - HTTP client for Cortensor integration
- **Winston** - Structured logging
- **Helmet** - Security middleware
- **Rate limiting** - API protection

### **Cortensor Integration**
- **Decentralized AI Inference** - Distributed processing
- **Multiple miner consensus** - Robust verification
- **Task routing** - Intelligent workload distribution
- **Result validation** - Quality assurance

---

## 🧪 Development

### **Running Tests**

```bash
# Backend tests
cd backend
npm test

# Frontend tests
cd ..
npm test
```

### **Building for Production**

```bash
# Build backend
cd backend
npm run build

# Build frontend
cd ..
npm run build
```

---

## 📊 Roadmap

### **Phase 1: Core Features** ✅
- [x] Cortensor decentralized AI integration
- [x] Web application with analysis dashboard
- [x] REST API for claim verification
- [x] Multi-miner consensus aggregation
- [x] Explainable AI results

### **Phase 2: Enhanced Features** 🚧
- [ ] Browser extension for real-time fact-checking
- [ ] Batch processing for multiple claims
- [ ] Advanced bias detection algorithms
- [ ] Social media integration

### **Phase 3: Scalability** 📋
- [ ] User authentication and personalization
- [ ] API rate limiting and monetization
- [ ] Mobile application
- [ ] Caching layer optimization

---

## 🤝 Contributing

We welcome contributions to TruthLens! 

### **Development Setup**

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 🙏 Acknowledgments

- **[Cortensor](https://cortensor.network)** - Decentralized AI inference network
- **React Community** - Amazing frontend ecosystem
- **Open Source Contributors** - Making this project possible

---

**Built with ❤️ for a more transparent and trustworthy information ecosystem.**
