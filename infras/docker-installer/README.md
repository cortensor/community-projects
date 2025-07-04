# Docker Installer Infrastructure

A template infrastructure project for deploying Cortensor nodes and services with easy management.

## Features
- Multi-node Cortensor deployment with Docker Compose
- Automated LLM engine setup for each node
- Environment-based configuration management
- Easy scaling and upgrade capabilities

## Prerequisites

- Docker and Docker Compose installed
- Git
- Access to RPC endpoints (Arbitrum Sepolia and Ethereum Mainnet)
- Cortensor node credentials (public/private keys and contract addresses)

## Setup

1. **Clone the repository to your local machine:**
   ```bash
   git clone https://github.com/cortensor/community-projects.git
   cd community-projects/infras/docker-installer/src
   ```

2. **Configure environment variables:**
   
   Copy the example environment file:
   ```bash
   cp .env-example .env
   ```
   
   Edit the `.env` file with your configuration:
   ```bash
   # RPC URLs (required for all nodes)
   RPC_URL="YOUR_ARB_SEPOLIA_RPC_URL"
   ETH_RPC_URL="YOUR_ETHEREUM_MAINNET_RPC_URL"
   
   # Node-specific configurations
   NODE_PUBLIC_KEY_1="0x_YOUR_PUBLIC_KEY_NODE_1"
   NODE_PRIVATE_KEY_1="YOUR_PRIVATE_KEY_NODE_1"
   CONTRACT_ADDRESS_RUNTIME_1="YOUR_CONTRACT_ADDRESS_NODE_1"
   
   # Add more nodes as needed
   NODE_PUBLIC_KEY_2="0x_YOUR_PUBLIC_KEY_NODE_2"
   NODE_PRIVATE_KEY_2="YOUR_PRIVATE_KEY_NODE_2"
   CONTRACT_ADDRESS_RUNTIME_2="YOUR_CONTRACT_ADDRESS_NODE_2"
   ```

3. **Build and deploy the infrastructure:**
   
   **Option A: Generate new configuration (recommended for first-time setup):**
   ```bash
   ./build.sh
   ```
   This will prompt you for the number of nodes and generate the appropriate docker-compose.yml and .env files.
   
   **Option B: Use existing configuration:**
   ```bash
   ./build.sh --keep-config
   ```
   This will build the Docker image without regenerating the configuration files.

4. **Start the services:**
   ```bash
   docker compose up -d
   ```

5. **Monitor the deployment:**
   ```bash
   docker compose logs -f
   ```

## Architecture

The docker-installer creates a multi-node Cortensor deployment with the following components:

- **Cortensor Nodes**: Individual Cortensor instances running in separate containers
- **LLM Engines**: LLaVA-based language models for each node (port 8091+)
- **IPFS Integration**: Decentralized storage support
- **Environment Management**: Centralized configuration through .env files

Each node runs on a unique port starting from 8091, with corresponding LLM engines.

## Management

### Upgrading
To upgrade the entire deployment:
```bash
./upgrade.sh
```

### Stopping Services
```bash
docker compose down
```

### Viewing Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f cortensor-1
docker compose logs -f cts-llm-1
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `RPC_URL` | Arbitrum Sepolia RPC endpoint | Yes |
| `ETH_RPC_URL` | Ethereum Mainnet RPC endpoint | Yes |
| `NODE_PUBLIC_KEY_X` | Public key for node X | Yes |
| `NODE_PRIVATE_KEY_X` | Private key for node X | Yes |
| `CONTRACT_ADDRESS_RUNTIME_X` | Contract address for node X | Yes |

### Port Configuration
- Node 1: Port 8091
- Node 2: Port 8092
- Node N: Port 8091 + (N-1)

## Troubleshooting

1. **Container fails to start**: Check the .env file configuration and ensure all required variables are set
2. **LLM engine issues**: Verify the cortensor/llm-engine-default-0 image is available
3. **Network connectivity**: Ensure RPC URLs are accessible from the container network
4. **Permission issues**: Make sure the build.sh and run.sh scripts are executable (`chmod +x *.sh`)

## Maintainer
@mrsyhd (Discord)

## License
MIT
