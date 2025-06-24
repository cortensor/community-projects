<div align="center">

  <img src="https://avatars.githubusercontent.com/u/174224856?s=200&v=4" alt="Project Banner" width="150">
  <h1>Cortensor Watcher Bot</h1>

  An enhanced and feature-rich automated monitoring tool for Cortensor nodes. This tool is designed to ensure the health, performance, and uptime of a fleet of nodes running in Docker. It includes features like remote control via Telegram and intelligent health checks based on network state and node reputation.

  <p>
    <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
    <a href="./STATUS.md"><img src="https://img.shields.io/badge/status-active-success.svg" alt="Status"></a>
    <a href="#"><img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python Version"></a>
    <a href="#"><img src="https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white" alt="Docker"></a>
  </p>
  
</div>

## Key Features

- **Majority Logic Monitoring**: Automatically restarts nodes that lag behind the network majority state.
- **Advanced Lag Detection**: Differentiates between minor state deviations and major session ID lags.
- **Proactive Error Detection**: Instantly restarts nodes upon detecting critical errors like Python `Traceback`s.
- **Network Stagnation Alerts**: Notifies you if the entire network appears to be stuck.
- **Remote Control via Telegram**: Manage the bot with commands like `/status`, `/restart`, and `/logs`.
- **Secure Configuration**: Uses a `.env` file for sensitive data like API tokens.
- **Automated Logging**: Saves node logs before every restart for easy diagnostics.

## Prerequisites

- [Git](https://git-scm.com/downloads)
- [Python](https://www.python.org/downloads/) (Version 3.8 or newer)
- [Docker](https://www.docker.com/products/docker-desktop/) and Docker Compose
- A Telegram account and a bot token from [@BotFather](https://t.me/BotFather).
- Your personal Chat ID from a bot like [@userinfobot](https://t.me/userinfobot).

## Installation & Setup

This project is located within the `cortensor/community-projects` monorepo. Follow these steps to set it up for development or personal use.

### 1. Clone the Repository
First clone the Repository to your local machine.

```bash
git clone https://github.com/cortensor/community-projects.git
cd community-projects
```

### 2. Navigate to the Project Directory
This monitoring tool is located in the `tools/` directory.
```bash
cd tools/cortensor-watcher-bot
````

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
```

### B. Operational Configuration (`config.json` file)

Edit the `config.json` file to list the Docker containers you want to monitor.

> **Important:** JSON files do not support comments. Please remove any lines starting with `//` from your final configuration.

**Example `config.json`:**

```json
{
  "containers": [
    "cortensor-1",
    "cortensor-2",
    "cortensor-3"
  ],
  "node_addresses": {
    "cortensor-1": "0xYOUR_NODE_ADDRESS_1",
    "cortensor-2": "0xYOUR_NODE_ADDRESS_2",
    "cortensor-3": "0xYOUR_NODE_ADDRESS_3"
  },
  "tail_lines": 500,
  "check_interval_seconds": 2.5,
  "grace_period_seconds": 30,
  "stats_api_url": "https://lb-be-5.cortensor.network/network-stats-tasks",
  "watch_tx_for_containers": [
    "cortensor-1",
    "cortensor-2",
    "cortensor-3"
  ],
  "tx_timeout_seconds": 45,
  "stagnation_alert_enabled": true,
  "stagnation_threshold_minutes": 30,
  "reputation_check_enabled": true,
  "reputation_api_base_url": "https://lb-be-5.cortensor.network/session-reputation/",
  "reputation_check_window": 20,
  "reputation_failure_threshold": 5,
  "reputation_restart_cooldown_minutes": 30
}
```

## Usage

You can run the bot either with Docker (recommended for production) or directly with Python (for development).

### Running with Docker (Recommended)

All `docker-compose` commands should be run from the `tools/cortensor-watcher-bot` directory, where its `docker-compose.yml` resides.

1.  **Build and Start:**
    ```bash
    docker-compose up --build -d
    ```
2.  **View Logs:**
    ```bash
    docker-compose logs -f
    ```
3.  **Stop:**
    ```bash
    docker-compose down
    ```

### Running Locally with Python

Ensure you are in the `tools/cortensor-watcher-bot` directory and your virtual environment is activated.

```bash
# Run from within tools/cortensor-watcher-bot/
python3 main.py
```

### Telegram Commands

  - <b>/help</b>: Displays all available commands.
  - <b>/status</b>: Shows the current operational status.
  - <b>/restart <container_name></b>: Restarts a specific node.
  - <b>/logs <container_name></b>: Fetches recent logs from a node.

## 👤 Maintainer

  * **@beranalpagion** (Discord)

## 🤝 Contributing

Contributions are welcome\! This project follows the standard Fork & Pull Request workflow of the main repository. For full details, please refer to the contribution guide in the root of the `community-projects` repository.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
