# ⚖️ Cortensor Judge

<div align="center">

![Cortensor Judge](https://img.shields.io/badge/Cortensor-Judge-blue?style=for-the-badge)
![Blockchain](https://img.shields.io/badge/Blockchain-Ethereum-627EEA?style=for-the-badge&logo=ethereum)
![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)

**Decentralized Dispute Resolution Layer for AI Inference Networks**

[Features](#-features) • [Architecture](#-architecture) • [Quick Start](#-quick-start) • [Documentation](#-documentation)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Use Cases](#-use-cases)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Quick Start](#-quick-start)
- [Documentation](#-documentation)
- [Technology Stack](#-technology-stack)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

**Cortensor Judge** is a comprehensive decentralized dispute resolution system designed for AI inference networks. It provides a transparent, on-chain mechanism for challenging AI outputs, validating them through consensus, and settling disputes with token-based rewards and slashing.

### What is Cortensor Judge?

Cortensor Judge acts as a **decentralized court system** for AI inference networks, where:

- **Users** can challenge AI outputs they believe are incorrect or malicious
- **Validators** review challenges and reach consensus on outcomes
- **Smart Contracts** enforce verdicts, distribute rewards, and slash bad actors
- **Everything** is transparent, verifiable, and trustless

---

## ✨ Features

### 🔐 **Decentralized & Trustless**
- Fully on-chain dispute resolution
- No central authority or single point of failure
- Transparent and verifiable process

### ⚡ **Real-Time Processing**
- Live dispute feed and monitoring
- Real-time validator consensus
- Instant on-chain settlement

### 🛡️ **Security & Integrity**
- Cryptographic evidence verification
- Reputation-based validator system
- Automated slashing for malicious actors

### 📊 **Comprehensive Dashboard**
- Real-time dispute tracking
- Validator performance metrics
- Network statistics and analytics

### 🔗 **Blockchain Integration**
- Ethereum-compatible smart contracts
- MetaMask wallet integration
- COR token-based incentives

---

## 🎯 Use Cases

### 1. **AI Output Verification**
Challenge suspicious or incorrect AI responses in decentralized AI networks, ensuring quality and accuracy.

### 2. **Content Moderation**
Verify AI-generated content for compliance, safety, and accuracy before publication.

### 3. **Model Validation**
Test and validate AI models in production, identifying weaknesses and improving performance.

### 4. **Reputation Management**
Build and maintain reputation scores for AI providers and validators through transparent dispute resolution.

### 5. **Quality Assurance**
Ensure AI outputs meet specified standards through community-driven validation.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Dashboard  │  │   Courtroom  │  │   Validators │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ↕ HTTP/REST
┌─────────────────────────────────────────────────────────────┐
│              Backend API (Express + TypeScript)             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Sentinel   │  │  Challenge   │  │   Verdict    │     │
│  │     Bot      │  │   Service    │  │   Service    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ↕ Web3
┌─────────────────────────────────────────────────────────────┐
│         Smart Contracts (Solidity + Hardhat)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │    Justice   │  │  Reputation  │  │  COR Token  │     │
│  │   Contract   │  │  Registry   │  │   (Mock)    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ↕ RPC
┌─────────────────────────────────────────────────────────────┐
│          Local Blockchain (Hardhat Network)                  │
│              Chain ID: 31337 | Port: 8545                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
coutroom/
├── cortex-court-case/          # Frontend React Application
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── pages/              # Page components
│   │   ├── hooks/              # Custom React hooks
│   │   ├── services/           # API services
│   │   ├── config/             # Configuration files
│   │   └── utils/              # Utility functions
│   └── package.json
│
├── cortensor-judge-backend/     # Backend Services
│   ├── sentinel/               # Sentinel Bot Service
│   │   ├── src/
│   │   │   ├── server.ts       # Express server
│   │   │   ├── services/       # Business logic
│   │   │   ├── web3/           # Blockchain integration
│   │   │   └── evidence/       # Evidence handling
│   │   └── package.json
│   │
│   ├── judge-sdk/              # Judge SDK
│   │   └── src/                # SDK source code
│   │
│   ├── contracts/              # Smart Contracts
│   │   ├── contracts/         # Solidity contracts
│   │   ├── hardhat-scripts/   # Deployment scripts
│   │   └── package.json
│   │
│   └── docker/                 # Docker configuration
│
└── README.md                   # This file
```

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js** (v18.0.0 or higher)
- **npm** or **yarn**
- **MetaMask** browser extension
- **Git**

Optional but recommended:
- **Docker** and **Docker Compose** (for containerized deployment)
- **Hardhat** (for local blockchain development)

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd coutroom
```

### 2. Start Backend Services

```bash
cd cortensor-judge-backend

# Install dependencies
npm install

# Start local blockchain (Hardhat)
cd contracts
npx hardhat node

# In a new terminal, start the backend API
cd ../sentinel
npm run dev
```

The backend will be available at `http://localhost:3001`

### 3. Start Frontend Application

```bash
# Open a new terminal
cd cortex-court-case

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:8080`

### 4. Connect MetaMask

1. Open MetaMask extension
2. Add network:
   - **Network Name**: Localhost 8545
   - **RPC URL**: `http://127.0.0.1:8545`
   - **Chain ID**: `31337`
   - **Currency Symbol**: ETH
3. Import a test account (optional):
   
   > ⚠️ **SECURITY WARNING**: 
   > - **NEVER use real private keys in documentation or public repositories**
   > - For local development, use Hardhat's default test accounts (see Hardhat docs)
   > - Generate your own test accounts using MetaMask or `npx hardhat accounts`
   > - For production, always use secure key management and environment variables
   
   - **Test Account Private Key** (example format - replace with your own):
     ```
     test123456abcd7890efghijklmnopqrstuvwxyz1234567890abcdef123456
     ```
   - This is just a placeholder - use your own test account private key
   - Test accounts typically have 10,000 ETH on local Hardhat networks

### 5. Access the Application

- **Frontend**: http://localhost:8080
- **Backend API**: http://localhost:3001
- **Blockchain RPC**: http://localhost:8545

---

## 📚 Documentation

### Frontend Documentation
See [Frontend README](./cortex-court-case/README.md) for detailed frontend documentation.

### Backend Documentation
See [Backend README](./cortensor-judge-backend/README.md) for detailed backend documentation.

### API Endpoints

#### Health Check
```bash
GET /health
```

#### Challenges
```bash
POST /api/challenges
GET /api/challenges/:id
```

#### Verdicts
```bash
POST /api/verdicts
GET /api/verdicts/:id
```

---

## 🛠️ Technology Stack

### Frontend
- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Wagmi** - Ethereum interactions
- **RainbowKit** - Wallet connection
- **Framer Motion** - Animations
- **React Router** - Routing

### Backend
- **Node.js** - Runtime
- **Express** - Web framework
- **TypeScript** - Type safety
- **Ethers.js** - Blockchain interactions
- **BullMQ** - Job queue
- **Redis** - Caching and queues

### Blockchain
- **Solidity** - Smart contract language
- **Hardhat** - Development environment
- **Foundry** - Testing framework
- **Ethereum** - Blockchain network

---

## 🧪 Testing

### Frontend Tests
```bash
cd cortex-court-case
npm run test
```

### Backend Tests
```bash
cd cortensor-judge-backend
npm test
```

### Smart Contract Tests
```bash
cd cortensor-judge-backend/contracts
npx hardhat test
```

---

## 🐳 Docker Deployment

### Build and Run with Docker

```bash
cd cortensor-judge-backend
docker-compose -f docker/docker-compose.yml up -d
```

This will start:
- Backend API service
- Redis server
- Hardhat node

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- Built with modern web3 technologies
- Inspired by decentralized governance systems
- Designed for transparency and trustlessness

---

<div align="center">

**Built with ❤️ by the Cortensor Judge Team**

[Report Bug](https://github.com/your-repo/issues) • [Request Feature](https://github.com/your-repo/issues) • [Documentation](./docs)

</div>

