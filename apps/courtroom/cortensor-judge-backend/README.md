# ⚙️ Cortensor Judge - Backend

<div align="center">

![Node.js](https://img.shields.io/badge/Node.js-339933?style=for-the-badge&logo=node.js&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)
![Express](https://img.shields.io/badge/Express-000000?style=for-the-badge&logo=express&logoColor=white)
![Ethereum](https://img.shields.io/badge/Ethereum-627EEA?style=for-the-badge&logo=ethereum&logoColor=white)

**Backend Services for Decentralized AI Dispute Resolution**

[Features](#-features) • [Architecture](#-architecture) • [Getting Started](#-getting-started) • [API Documentation](#-api-documentation)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Services](#-services)
- [Smart Contracts](#-smart-contracts)
- [API Documentation](#-api-documentation)
- [Configuration](#-configuration)
- [Development](#-development)
- [Deployment](#-deployment)
- [Troubleshooting](#-troubleshooting)

---

## 🎯 Overview

The Cortensor Judge backend is a comprehensive system that handles dispute resolution logic, blockchain interactions, and evidence management. It consists of three main components:

1. **Sentinel Service** - Main API server and dispute processing
2. **Judge SDK** - Client library for interacting with the system
3. **Smart Contracts** - On-chain dispute resolution logic

---

## ✨ Features

### 🔐 **Secure & Reliable**
- Type-safe TypeScript implementation
- Comprehensive error handling
- Input validation and sanitization
- Secure evidence storage

### ⚡ **High Performance**
- Asynchronous processing with BullMQ
- Redis-based job queues
- Efficient blockchain interactions
- Optimized database queries

### 🔗 **Blockchain Integration**
- Ethereum smart contract interactions
- Real-time event monitoring
- Transaction management
- Gas optimization

### 📊 **Monitoring & Metrics**
- Health check endpoints
- Performance metrics
- Error tracking
- Request logging

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Sentinel Service (Express API)             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Challenge  │  │   Verdict   │  │   Evidence   │ │
│  │   Service    │  │   Service   │  │   Service    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                    ↕                    ↕
        ┌──────────────────┐  ┌──────────────────┐
        │   Dispute Queue  │  │  Justice Client  │
        │     (BullMQ)     │  │   (Ethers.js)    │
        └──────────────────┘  └──────────────────┘
                    ↕                    ↕
        ┌──────────────────┐  ┌──────────────────┐
        │      Redis       │  │  Smart Contracts │
        │   (Job Queue)    │  │   (Hardhat)      │
        └──────────────────┘  └──────────────────┘
```

---

## 📁 Project Structure

```
cortensor-judge-backend/
├── sentinel/                    # Main API service
│   ├── src/
│   │   ├── server.ts           # Express server setup
│   │   ├── config/             # Configuration
│   │   │   ├── env.ts          # Environment variables
│   │   │   └── system.ts       # System configuration
│   │   ├── services/           # Business logic
│   │   │   ├── challenge.service.ts
│   │   │   └── verdict.service.ts
│   │   ├── web3/               # Blockchain integration
│   │   │   └── justice.client.ts
│   │   ├── evidence/          # Evidence handling
│   │   │   ├── bundle.ts      # Evidence bundling
│   │   │   └── ipfs.ts        # IPFS integration
│   │   ├── queue/             # Job queues
│   │   │   └── dispute.queue.ts
│   │   ├── similarity/         # Similarity algorithms
│   │   │   └── cosine.ts
│   │   ├── cortensor/         # Cortensor integration
│   │   │   ├── router.ts
│   │   │   └── validate.ts
│   │   ├── monitoring/        # Metrics and monitoring
│   │   │   └── metrics.ts
│   │   └── types/             # TypeScript types
│   │       └── evidence.ts
│   ├── package.json
│   └── tsconfig.json
│
├── judge-sdk/                   # Client SDK
│   ├── src/
│   │   ├── client.ts           # Main SDK client
│   │   ├── challenge.ts        # Challenge operations
│   │   ├── submitEvidence.ts   # Evidence submission
│   │   └── types/
│   │       └── evidence.ts
│   └── package.json
│
├── contracts/                   # Smart contracts
│   ├── contracts/
│   │   ├── Justice.sol         # Main dispute contract
│   │   ├── ReputationRegistry.sol
│   │   ├── MockCORToken.sol
│   │   └── interfaces/
│   │       └── ICOR.sol
│   ├── hardhat-scripts/
│   │   └── deploy.ts           # Deployment script
│   ├── script/
│   │   └── Deploy.s.sol       # Foundry deployment
│   ├── hardhat.config.ts
│   └── package.json
│
├── docker/                      # Docker configuration
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── package.json                 # Root package.json
└── README.md                    # This file
```

---

## 🚀 Getting Started

### Prerequisites

- **Node.js** 18.0.0 or higher
- **npm** or **yarn**
- **Redis** (for job queues)
- **Hardhat** (for local blockchain)

### Installation

1. **Navigate to backend directory**
   ```bash
   cd cortensor-judge-backend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Install workspace dependencies**
   ```bash
   npm install --workspaces
   ```

### Environment Setup

Create a `.env` file in the `sentinel/` directory:

```env
# Server Configuration
PORT=3001
NODE_ENV=development
CORS_ORIGIN=http://localhost:8080

# Blockchain Configuration
RPC_URL=http://127.0.0.1:8545
CHAIN_ID=31337

# ⚠️ SECURITY WARNING: Never use real private keys in production or commit them to git!
# For local development, generate your own test account or use Hardhat's default accounts
# Example format (replace with your own test key):
# PRIVATE_KEY=test123456abcd7890efghijklmnopqrstuvwxyz1234567890abcdef123456
# For production, use environment variables or secure key management services
PRIVATE_KEY=your_private_key_here

# Contract Addresses
JUSTICE_CONTRACT_ADDRESS=0x...
REPUTATION_CONTRACT_ADDRESS=0x...
COR_TOKEN_ADDRESS=0x...

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# IPFS Configuration (optional)
IPFS_API_URL=http://localhost:5001
```

### Running the Services

#### 1. Start Local Blockchain

```bash
cd contracts
npx hardhat node
```

This starts a local Hardhat node on `http://127.0.0.1:8545`

#### 2. Deploy Smart Contracts

```bash
# Using Hardhat
npx hardhat run hardhat-scripts/deploy.ts --network localhost

# Or using Foundry
forge script script/Deploy.s.sol:DeployJudge --broadcast --rpc-url http://localhost:8545
```

#### 3. Start Redis

```bash
# Using Docker
docker run -d -p 6379:6379 redis:latest

# Or using local Redis
redis-server
```

#### 4. Start Sentinel Service

```bash
cd sentinel
npm run dev
```

The API will be available at `http://localhost:3001`

---

## 🔧 Services

### Sentinel Service

The main API service that handles:
- Challenge creation and management
- Verdict processing
- Evidence handling
- Blockchain interactions

**Key Features**:
- RESTful API endpoints
- Real-time dispute processing
- Queue-based job processing
- Blockchain event monitoring

### Judge SDK

Client library for interacting with the system:

```typescript
import { JudgeClient } from '@cortensor/judge-sdk';

const client = new JudgeClient({
  apiUrl: 'http://localhost:3001',
  rpcUrl: 'http://127.0.0.1:8545'
});

// Create a challenge
const challenge = await client.createChallenge({
  taskId: 'task-123',
  evidence: {...}
});
```

### Smart Contracts

#### Justice Contract
Main dispute resolution contract handling:
- Challenge creation
- Validator voting
- Verdict execution
- Reward distribution

#### Reputation Registry
Tracks validator reputation scores.

#### Mock COR Token
ERC-20 token for testing rewards and slashing.

---

## 📡 API Documentation

### Health Check

```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "services": {
    "blockchain": "connected",
    "redis": "connected"
  }
}
```

### Create Challenge

```http
POST /api/challenges
Content-Type: application/json

{
  "taskId": "task-123",
  "challenger": "0x...",
  "evidence": {
    "originalOutput": "...",
    "challengedOutput": "...",
    "similarity": 0.85
  }
}
```

### Get Challenge

```http
GET /api/challenges/:id
```

### Submit Verdict

```http
POST /api/verdicts
Content-Type: application/json

{
  "challengeId": "challenge-123",
  "validator": "0x...",
  "verdict": "uphold",
  "reason": "..."
}
```

### Get Verdict

```http
GET /api/verdicts/:id
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | `3001` |
| `NODE_ENV` | Environment | `development` |
| `RPC_URL` | Blockchain RPC URL | `http://127.0.0.1:8545` |
| `CHAIN_ID` | Blockchain chain ID | `31337` |
| `REDIS_HOST` | Redis host | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |

### Smart Contract Configuration

Edit `contracts/hardhat.config.ts` to configure:
- Network settings
- Compiler version
- Gas settings

---

## 💻 Development

### Available Scripts

```bash
# Development
npm run dev              # Start sentinel in dev mode
npm run build            # Build all workspaces
npm run start            # Start sentinel in production mode

# Testing
npm test                 # Run all tests
npm run test:coverage    # Run tests with coverage

# Code Quality
npm run lint             # Lint all workspaces
npm run lint:fix         # Fix linting issues
npm run typecheck        # Type check all workspaces
npm run format           # Format code

# Contracts
npm run contracts:build  # Build contracts
npm run contracts:deploy # Deploy contracts
```

### Development Workflow

1. Start local blockchain
2. Deploy contracts
3. Start Redis
4. Start sentinel service
5. Make changes and test

### Testing

```bash
# Run all tests
npm test

# Run specific test
npm test -- sentinel/src/tests/integration.test.ts

# Watch mode
npm test -- --watch
```

---

## 🐳 Deployment

### Docker Deployment

```bash
# Build image
docker build -f docker/Dockerfile -t cortensor-judge:latest .

# Run with docker-compose
docker-compose -f docker/docker-compose.yml up -d
```

### Production Deployment

1. Set `NODE_ENV=production`
2. Configure production RPC URL
3. Set up Redis cluster
4. Deploy smart contracts to mainnet
5. Update contract addresses in `.env`
6. Start services with PM2 or similar

---

## 🔍 Troubleshooting

### Connection Issues

**Problem**: Cannot connect to blockchain

**Solutions**:
1. Verify Hardhat node is running
2. Check RPC URL in `.env`
3. Verify chain ID matches

**Problem**: Redis connection failed

**Solutions**:
1. Ensure Redis is running
2. Check Redis host and port
3. Verify network connectivity

### Contract Issues

**Problem**: Contract deployment fails

**Solutions**:
1. Check Hardhat node is running
2. Verify account has sufficient balance
3. Check contract compilation

### API Issues

**Problem**: API endpoints not responding

**Solutions**:
1. Check server logs
2. Verify port is not in use
3. Check CORS configuration

---

## 📚 Additional Resources

- [Express Documentation](https://expressjs.com)
- [Ethers.js Documentation](https://docs.ethers.io)
- [Hardhat Documentation](https://hardhat.org)
- [BullMQ Documentation](https://docs.bullmq.io)
- [Redis Documentation](https://redis.io/docs)

---

## 🤝 Contributing

When contributing to the backend:

1. Follow TypeScript best practices
2. Write comprehensive tests
3. Document your code
4. Follow the existing code style
5. Update API documentation

---

## 📝 License

This project is licensed under the MIT License.

---

<div align="center">

**Built with ❤️ using Node.js, TypeScript, and Ethereum**

[Back to Main README](../README.md)

</div>

