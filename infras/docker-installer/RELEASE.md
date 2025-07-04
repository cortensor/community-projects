# Release Notes – Docker Installer Infrastructure

## v1.0.0 – 2025-07-03

### 🚀 Features
- **Multi-node Cortensor deployment** with Docker Compose
- **Automated LLM engine setup** for each node (LLaVA-based)
- **Dynamic configuration generation** via build.sh script
- **Environment-based configuration management** with .env files
- **Easy scaling and upgrade capabilities**

### 🔧 Technical Details
- Docker-based deployment with Ubuntu 24.04 base image
- Support for Arbitrum Sepolia and Ethereum Mainnet RPC endpoints
- Automatic port allocation starting from 8091
- Docker socket mounting for container management
- Restart policies for reliable operation

### 📋 Scripts
- `build.sh` - Dynamic docker-compose.yml generation with node scaling
- `run.sh` - Node registration, verification, and mining setup
- `upgrade.sh` - Complete deployment upgrade process

### 📚 Documentation
- Comprehensive README.md with setup instructions
- Environment variable documentation and examples
- Troubleshooting guide and common issues
- Architecture overview and management commands

### 🎯 System Requirements
- Docker Engine 20.10+
- Docker Compose 2.0+
- Memory: ~1-2GB per node (including LLM engine)
- Network: Access to RPC endpoints
