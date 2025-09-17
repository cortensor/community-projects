<div align="center">

  <img src="https://avatars.githubusercontent.com/u/174224856?s=200&v=4" alt="Project Banner" width="150">
  <h1>Cortensor Watcher Bot</h1>

  An enhanced and feature-rich automated monitoring tool for Cortensor nodes. This tool ensures health, performance, and uptime of a fleet of nodes; it works without Docker by tailing node log files and provides insights via Telegram. The bot sends warnings when issues are detected and does not perform automatic restarts or manual start/stop.

  <p>
    <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
    <a href="./STATUS.md"><img src="https://img.shields.io/badge/status-active-success.svg" alt="Status"></a>
    <a href="#"><img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python Version"></a>
    <a href="#"><img src="https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white" alt="Docker"></a>
  </p>
  
</div>

## Key Features

- **Majority Logic Monitoring**: Warns when nodes lag behind the network majority state.
- **Advanced Lag Detection**: Differentiates between minor state deviations and major session ID lags.
- **Proactive Error Detection**: Alerts on critical errors like Python `Traceback`s.
- **Network Stagnation Alerts**: Notifies you if the entire network appears to be stuck.
- **Remote Insights via Telegram**: Use commands like `/start`, `/status`, `/logs`, `/models`, `/resources`, and `/history`.
- **Secure Configuration**: Uses a `.env` file for sensitive data like API tokens.
- **Log Access**: Fetch node logs on demand for diagnostics.

## Prerequisites

- [Git](https://git-scm.com/downloads)
- [Python](https://www.python.org/downloads/) (Version 3.8 or newer)
- A Telegram account and a bot token from [@BotFather](https://t.me/BotFather).
- Your personal Chat ID from a bot like [@userinfobot](https://t.me/userinfobot).

## Installation & Setup

This project is located within the `cortensor/community-projects` monorepo. Follow these steps to set it up for development or personal use.

### 1. Clone the Repository
First clone the Repository to your local machine.

```bash
git clone https://github.com/cortensor/community-projects.git
cd community-projects
````

### 2\. Navigate to the Project Directory

This monitoring tool is located in the `tools/` directory.

```bash
cd tools/cortensor-watcher-bot
```

### 3\. Set Up Environment and Dependencies

Create a Python virtual environment and install the required libraries.

```bash
# Create the virtual environment
python3 -m venv venv

# Activate it (on Linux/macOS)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

*Note: For Windows, activate with `.\venv\Scripts\activate`.*

## Configuration

All configuration should be done within the `tools/cortensor-watcher-bot` directory.

### A. Secret Configuration (`.env` file)

Create a `.env` file in this directory and fill it with your credentials.

```env
# Environment variables for the Cortensor Watcher Bot
TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID_HERE"
RPC_URL="YOUR_RPC_PROVIDER_URL_HERE"
# Optional: Etherscan v2 unified API key
ETHERSCAN_API_KEY="QHSQFXGHEMZ8RVI5PAX6SDSVWAQEA5T7PH"

# Optional: Unified API base and chain id (pick the chain id matching your address network)
# Unified base: https://api.etherscan.io/v2/api
# Common chain ids:
# - Ethereum Mainnet: 1
# - Ethereum Sepolia: 11155111
# - Arbitrum One: 42161
# - Arbitrum Nova: 42170
# - Arbitrum Sepolia: 421614
ETHERSCAN_API_BASE="https://api.etherscan.io/v2/api"
ETHERSCAN_CHAIN_ID="421614"

# Optional: password used for privileged operations via sudo -S (not used for start/stop)
SUDO_PASSWORD=""
```

### B. Operational Configuration (`config.json` file)

Edit the `config.json` file to list the nodes you want to monitor and the absolute paths to their log files (e.g., `/var/log/cortensord-1.log`).

> **Important:** JSON files do not support comments. Please remove any lines starting with `//` from your final configuration.

**Example `config.json`:**

```json
{
  "nodes": ["cortensor-1", "cortensor-2", "cortensor-3"],
  "log_files": {
    "cortensor-1": "/var/log/cortensord-1.log",
    "cortensor-2": "/var/log/cortensord-2.log",
    "cortensor-3": "/var/log/cortensord-3.log"
  },
  "node_configs": {
    "cortensor-1": { "user": "deploy", "folder": ".cortensor", "env_file": ".env-1", "index": 1 },
    "cortensor-2": { "user": "deploy", "folder": ".cortensor", "env_file": ".env-2", "index": 2 },
    "cortensor-3": { "user": "deploy", "folder": ".cortensor", "env_file": ".env-3", "index": 3 }
  },
  "node_addresses": {
    "cortensor-1": "0xYOUR_NODE_ADDRESS_1",
    "cortensor-2": "0xYOUR_NODE_ADDRESS_2",
    "cortensor-3": "0xYOUR_NODE_ADDRESS_3"
  },
  "tail_lines": 500,
  "check_interval_seconds": 900,
  "grace_period_seconds": 930,
  "stats_api_url": "https://db-be-7.cortensor.network/network-stats-tasks",
  "watch_tx_for_containers": ["cortensor-1", "cortensor-2", "cortensor-3"],
  "tx_timeout_seconds": 45,
  "stagnation_alert_enabled": true,
  "stagnation_threshold_minutes": 30,
  
}
```

Notes:
- Each node's log file path should be accessible to the bot for reading, typically `/var/log/cortensord-<index>.log`.

## Usage

### Running Locally with Python

Ensure you are in the `tools/cortensor-watcher-bot` directory and your virtual environment is activated.

```bash
# Run from within project root
python3 src/main.py
```

### Telegram Commands

  - <b>/help</b>: Displays all available commands.
  - <b>/status</b>: Shows the current operational status for each node and the majority state.
  - <b>/logs [node_name]</b>: Fetch recent logs from node log files; without argument, shows a summary for all nodes.
  - <b>/models [node_name]</b>: Shows Docker containers grouped per node using strict display-name prefixes.
  - <b>/resources [node_name]</b>: Shows resource usage for the node's cortensord process and related containers.
  - <b>/history [node_name]</b>: Shows the latest 25 transactions (including PING) for the node's address via Etherscan/Arbiscan.
  

## 👤 Maintainer

  * **@beranalpagion** (Discord)

## 🤝 Contributing

Contributions are welcome\! This project follows the standard Fork & Pull Request workflow of the main repository. For full details, please refer to the contribution guide in the root of the `community-projects` repository.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
