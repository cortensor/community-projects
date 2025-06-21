# Hello World Tool

A template CLI tool for interacting with Cortensor networks, managing nodes, and analyzing network data.

## Features
- Node status checking and management
- Network statistics and visualization
- Wallet management utilities
- Batch operations for node operators

## Installation

```bash
pip install cortensor-hello-tool
```

Or install from source:

```bash
git clone https://github.com/cortensor/hello-world-tool.git
cd hello-world-tool
pip install -e .
```

## Usage

```bash
# Check node status
cortensor-tool status --node-id <your-node-id>

# View network statistics
cortensor-tool stats --network mainnet

# Manage wallet
cortensor-tool wallet --create
```

## Configuration

Create a `config.yaml` file in your home directory:

```yaml
api_key: your_api_key_here
network: mainnet
log_level: info
```

## Maintainer
@cortensor-tools-admin (Discord)

## License
MIT
