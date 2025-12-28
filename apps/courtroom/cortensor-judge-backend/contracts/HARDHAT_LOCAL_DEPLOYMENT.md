# Local Blockchain Deployment with Hardhat

## Overview

Deploy and test Cortensor Judge smart contracts locally using Hardhat. Perfect for development and testing before mainnet deployment.

---

## 🚀 Quick Start (5 minutes)

### 1. Install Dependencies

```bash
cd contracts
npm install
```

### 2. Start Local Blockchain Node

```bash
npm run hardhat:node
```

This starts a local Hardhat node on `http://127.0.0.1:8545` with 20 test accounts.

**Terminal Output Example:**
```
Started HTTP and WebSocket JSON-RPC server at http://127.0.0.1:8545

Accounts
========
Account #0: 0x14dC79964da2C08b23698B3D3cc7Ca32193d9955 (balance: 10000 ETH)
Account #1: 0x23618e81E3f5cdF7f54C3d65f7FBc0aBf5B21E8f (balance: 10000 ETH)
...
```

### 3. Deploy Contracts (in another terminal)

```bash
cd contracts
npm run hardhat:deploy
```

**Output:**
```
🚀 Deploying Cortensor Judge contracts to localhost...

📝 Deploying contracts with account: 0x14dC79964da2C08b23698B3D3cc7Ca32193d9955
Account balance: 10000000000000000000000

1️⃣ Deploying Mock COR Token...
✅ COR Token deployed at: 0x5FbDB2315678afccb333f8a9c6FCC1ea3EFAB49f

2️⃣ Deploying Justice contract...
✅ Justice contract deployed at: 0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512

3️⃣ Deploying ReputationRegistry contract...
✅ ReputationRegistry deployed at: 0x9fE46736679d2D9a65F0992F2272dE9f3c7FA6e0

================================
📋 Add these to your .env file:
================================
BLOCKCHAIN_RPC_URL=http://127.0.0.1:8545
JUSTICE_CONTRACT_ADDRESS=0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512
REPUTATION_REGISTRY_ADDRESS=0x9fE46736679d2D9a65F0992F2272dE9f3c7FA6e0
COR_TOKEN_ADDRESS=0x5FbDB2315678afccb333f8a9c6FCC1ea3EFAB49f
VALIDATOR_ADDRESS=0x14dC79964da2C08b23698B3D3cc7Ca32193d9955
VALIDATOR_PRIVATE_KEY=0x...
================================
```

### 4. Update Backend .env

Copy the contract addresses from deployment output:

```bash
# In cortensor-judge-backend/.env
BLOCKCHAIN_RPC_URL=http://127.0.0.1:8545
JUSTICE_CONTRACT_ADDRESS=0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512
REPUTATION_REGISTRY_ADDRESS=0x9fE46736679d2D9a65F0992F2272dE9f3c7FA6e0
COR_TOKEN_ADDRESS=0x5FbDB2315678afccb333f8a9c6FCC1ea3EFAB49f
VALIDATOR_ADDRESS=0x14dC79964da2C08b23698B3D3cc7Ca32193d9955
VALIDATOR_PRIVATE_KEY=0x...
```

### 5. Start Backend Services

```bash
# Terminal 1: Start Redis (if available)
docker run -d -p 6379:6379 redis:7-alpine

# Terminal 2: Start Sentinel backend
cd sentinel
npm run dev
```

**Backend should now be running on http://localhost:3001**

---

## 📋 Hardhat Network Configuration

### Available Networks

**Development (Default):**
```bash
npm run hardhat:deploy  # Uses hardhat (local) network
```

**Base Mainnet:**
```bash
npm run hardhat:deploy:base
```

**Arbitrum Mainnet:**
```bash
npm run hardhat:deploy:arbitrum
```

### Network Details

```json
{
  "localhost": {
    "url": "http://127.0.0.1:8545",
    "chainId": 31337
  },
  "hardhat": {
    "chainId": 31337,
    "accounts": 20,
    "balance": "10000 ETH each"
  },
  "base": {
    "chainId": 8453,
    "url": "https://mainnet.base.org"
  },
  "arbitrum": {
    "chainId": 42161,
    "url": "https://arb1.arbitrum.io/rpc"
  }
}
```

---

## 🔧 Deployment Scripts

### What Gets Deployed

1. **MockCORToken** - ERC-20 token for testing
   - Mints 1,000,000 COR to deployer
   - Approves 1,000,000 COR for bonds

2. **Justice Contract** - Core dispute resolution
   - Registered validator with 8000 initial reputation
   - Ready to accept challenges

3. **ReputationRegistry** - Agent reputation tracking
   - Linked to Justice contract
   - Ready to record verdicts

### Deployment Code

Location: `contracts/hardhat-scripts/deploy.ts`

The script:
- ✅ Deploys all 3 contracts
- ✅ Links them together
- ✅ Registers initial validator
- ✅ Approves tokens
- ✅ Saves deployment addresses to `deployments.json`
- ✅ Prints environment variables

### Running Custom Deployments

```bash
# Deploy to specific network
npx hardhat run hardhat-scripts/deploy.ts --network localhost

# Deploy and verify on testnet
npx hardhat run hardhat-scripts/deploy.ts --network base-sepolia

# View deployment info
cat deployments.json
```

---

## 🧪 Testing Workflows

### Scenario 1: Test Challenge Flow

```bash
# 1. Start node
npm run hardhat:node

# 2. Deploy (in another terminal)
npm run hardhat:deploy

# 3. Start backend with deployed addresses
cd ../sentinel
npm run dev

# 4. Test challenge endpoint
curl -X POST http://localhost:3001/challenge \
  -H "Content-Type: application/json" \
  -d '{
    "evidence": {
      "minerOutput": "incorrect",
      "expectedOutput": "correct",
      "ipfsHash": "test-hash"
    },
    "bondAmount": "1000000000000000000"
  }'
```

### Scenario 2: Full Dispute Workflow

```bash
# Generate mock evidence
curl -X POST http://localhost:3001/test/generate-evidence \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 2+2?"}'

# Initiate challenge
curl -X POST http://localhost:3001/challenge \
  -H "Content-Type: application/json" \
  -d '{
    "evidence": {...from above...},
    "bondAmount": "1000000000000000000"
  }'

# Monitor outputs
curl http://localhost:3001/queue/stats

# Submit verdict
curl -X POST http://localhost:3001/verdict/submit \
  -H "Content-Type: application/json" \
  -d '{
    "disputeId": "1",
    "verdict": "0",
    "reasoning": "Output is incorrect"
  }'
```

---

## 📊 Hardhat Features

### Console Access

```bash
# Access Hardhat console with deployed contracts
npx hardhat console --network localhost

# Then in console:
const Justice = await ethers.getContractFactory("Justice");
const justice = await Justice.attach("0x...");
const dispute = await justice.getDispute(1);
console.log(dispute);
```

### Debugging

```bash
# Run with debug output
DEBUG=hardhat:* npm run hardhat:deploy

# Trace calls
npx hardhat run hardhat-scripts/deploy.ts --network localhost --trace
```

### Gas Reports

```bash
# Enable gas reporting
REPORT_GAS=true npm run hardhat:deploy
```

---

## 🐛 Troubleshooting

### Port 8545 Already in Use

```bash
# Find process using port 8545
netstat -ano | findstr :8545

# Kill process (Windows)
taskkill /PID <PID> /F
```

### Contract Not Found

```bash
# Recompile contracts
npm run hardhat:compile

# Clean and rebuild
npm run hardhat:clean
npm run hardhat:compile
```

### Insufficient Balance

Hardhat accounts have 10,000 ETH by default. If deployment fails:

```bash
# Check account balance in hardhat console
const balance = await ethers.provider.getBalance("0x...");
console.log(ethers.formatEther(balance));
```

### RPC Connection Issues

```bash
# Verify node is running
curl http://127.0.0.1:8545 -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# Should return current block number
```

---

## 📈 Development Workflow

### Recommended Setup

```
Terminal 1: Hardhat Node
npm run hardhat:node

Terminal 2: Deploy + Watch
npm run hardhat:deploy

Terminal 3: Redis (optional)
docker run -d -p 6379:6379 redis:7-alpine

Terminal 4: Backend
cd sentinel && npm run dev

Terminal 5: Testing/Debugging
# Your test commands here
```

### Resetting Blockchain

To reset blockchain state:

```bash
# Stop node (Ctrl+C in Terminal 1)
# Start fresh node
npm run hardhat:node

# Redeploy contracts
npm run hardhat:deploy
```

---

## 🔗 Integration with Backend

### How It Works

1. **Local Node** provides blockchain at http://127.0.0.1:8545
2. **Contracts** deployed with addresses saved to `deployments.json`
3. **Backend** configured with contract addresses via .env
4. **SDK** can call contract methods through provider

### Contract Interaction Example

```typescript
import { ethers } from "ethers";

const provider = new ethers.JsonRpcProvider("http://127.0.0.1:8545");
const Justice = new ethers.Contract(
  "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512",
  JUSTICE_ABI,
  provider
);

// Get dispute
const dispute = await Justice.getDispute(1);
console.log("Dispute status:", dispute.status);
```

---

## 📚 Additional Resources

- **Hardhat Docs**: https://hardhat.org/
- **Ethers.js**: https://docs.ethers.org/
- **Solidity**: https://docs.soliditylang.org/

---

## ✅ Verification Checklist

- [ ] Hardhat installed: `npm install` in contracts
- [ ] Node running: `npm run hardhat:node`
- [ ] Contracts deployed: `npm run hardhat:deploy`
- [ ] .env updated with contract addresses
- [ ] Redis running (if needed)
- [ ] Backend started: `npm run dev -w sentinel`
- [ ] Health check: `curl http://localhost:3001/health`

---

## Summary

✅ **Complete local development environment ready!**

You now have:
- Local blockchain node (Hardhat)
- Deployed smart contracts
- Mock COR token with 1M tokens
- Backend API connected
- Full testing capability

**Start with:** `npm run hardhat:node`
