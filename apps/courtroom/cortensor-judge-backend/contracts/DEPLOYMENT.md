# Smart Contract Deployment Guide

## Prerequisites

Before deploying, ensure you have:
1. Foundry installed (for `forge` command)
2. Private key and RPC endpoint for your target chain
3. COR token deployed or available at a known address

## Installation

### Option 1: Install Foundry (Recommended)

If you don't have Foundry installed, install it from: https://getfoundry.sh/

```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

Then install forge-std in the contracts directory:

```bash
cd contracts
forge install foundry-rs/forge-std
```

### Option 2: Use Pre-installed Script

If Foundry is not available, use the DeploymentHelper.sol contract:

```bash
# Deploy DeploymentHelper.sol to your chain
# Then call deploy() with:
# - COR token address
# - Initial validator address
```

## Environment Setup

Create a `.env` file in the `contracts` directory:

```bash
# Network RPC endpoint
RPC_URL=https://mainnet.base.org
# or for Arbitrum
RPC_URL=https://arb1.arbitrum.io/rpc

# Private key (without 0x prefix)
PRIVATE_KEY=your_private_key_here

# COR Token address (deployed on your chain)
COR_TOKEN_ADDRESS=0x...

# Initial validator address (optional)
INITIAL_VALIDATOR_ADDRESS=0x...

# Etherscan API key for verification
BASE_ETHERSCAN_KEY=your_key_here
ARBITRUM_ETHERSCAN_KEY=your_key_here
```

## Deployment Methods

### Method 1: Using Forge Script (Recommended)

```bash
cd contracts

# Build contracts first
forge build

# Deploy to Base mainnet
forge script script/Deploy.s.sol:DeployJudge \
  --rpc-url https://mainnet.base.org \
  --private-key $PRIVATE_KEY \
  --broadcast \
  --verify

# Deploy to Arbitrum mainnet
forge script script/Deploy.s.sol:DeployJudge \
  --rpc-url https://arb1.arbitrum.io/rpc \
  --private-key $PRIVATE_KEY \
  --broadcast \
  --verify

# Deploy to localhost (for testing)
forge script script/Deploy.s.sol:DeployJudge \
  --rpc-url http://127.0.0.1:8545 \
  --private-key $PRIVATE_KEY \
  --broadcast
```

### Method 2: Using DeploymentHelper.sol

If Foundry is not available:

```bash
# 1. Deploy DeploymentHelper.sol to your target chain
# 2. Deploy Justice.sol separately with COR token address
# 3. Deploy ReputationRegistry.sol with COR token address
# 4. Call ReputationRegistry.setJusticeContract(justice_address)
# 5. Call Justice.registerValidator(validator_address, initial_reputation)
```

### Method 3: Manual Deployment (Remix)

1. Go to https://remix.ethereum.org/
2. Upload `Justice.sol` and `ReputationRegistry.sol`
3. Compile with Solidity 0.8.20
4. Deploy in this order:
   - Deploy `Justice` with COR token address
   - Deploy `ReputationRegistry` with COR token address
   - Call `reputationRegistry.setJusticeContract(justice_address)`
   - Call `justice.registerValidator(validator_address, 8000)`

## Verification

After deployment, verify your contracts on the block explorer:

```bash
# Verify on Base
forge verify-contract \
  --chain-id 8453 \
  --compiler-version 0.8.20 \
  <JUSTICE_ADDRESS> \
  contracts/Justice.sol:Justice

# Verify on Arbitrum
forge verify-contract \
  --chain-id 42161 \
  --compiler-version 0.8.20 \
  <JUSTICE_ADDRESS> \
  contracts/Justice.sol:Justice
```

## Key Contract Addresses

After deployment, save these addresses in your `.env.production`:

```bash
JUSTICE_CONTRACT_ADDRESS=0x...
REPUTATION_REGISTRY_ADDRESS=0x...
COR_TOKEN_ADDRESS=0x...
```

## Troubleshooting

### "forge command not found"
- Install Foundry: `curl -L https://getfoundry.sh/ | bash`
- Add to PATH: `export PATH=$PATH:~/.foundry/bin`

### "forge-std not found"
- Run: `cd contracts && forge install foundry-rs/forge-std`

### "COR_TOKEN_ADDRESS not set"
- Add `COR_TOKEN_ADDRESS=0x...` to your environment or `.env` file

### Insufficient balance
- Ensure your deployer account has enough native tokens (ETH, Base ETH, ARB, etc.)

### Transaction reverted
- Check contract requirements in Justice.sol and ReputationRegistry.sol
- Ensure all parameters are valid addresses

## Next Steps

1. Update `.env` files with deployed contract addresses
2. Configure Sentinel backend with contract addresses
3. Deploy Sentinel service
4. Run integration tests

See `../README.md` and `../DEPLOYMENT.md` for complete setup instructions.
