<div align="center">

  <img src="https://avatars.githubusercontent.com/u/174224856?s=200&v=4" alt="Project Banner" width="150">
  <h1>Cortensor Monitoring Bot</h1>

  An advanced, feature-rich monitoring bot designed to provide Cortensor node operators with real-time health checks, historical performance data, and proactive transaction alerts, all managed through an interactive Telegram interface.

  <p>
    <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
    <a href="./STATUS.md"><img src="https://img.shields.io/badge/status-active-success.svg" alt="Status"></a>
    <a href="#"><img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python Version"></a>
    <a href="#"><img src="https://img.shields.io/badge/Telegram-aiogram-blue.svg" alt="Telegram Framework"></a>
  </p>
  
</div>

## ✨ Key Features

- **Comprehensive Stats Reporting**: Get on-demand `/stats` with historical trend analysis over 15m, 1h, and 24h periods.
- **Real-Time Health Checks**: A visual health bar based on recent transaction success and detailed failure reasons via `/health`.
- **Proactive Transaction Alerts**: A background task runs every minute to check for and alert on newly failed transactions via the `/auto` command.
- **Live-Updating Reports**: An `/autoupdate` command that creates persistent "report cards" in Telegram that refresh automatically.
- **Multi-Node Management**: Users can register, unregister, and list multiple node addresses to monitor from a single Telegram account. All data is stored in a local SQLite database.
- **Historical Data Logging**: A background job logs leaderboard snapshots to the database every 15 minutes to power trend analysis.

## 📋 Prerequisites

- [Git](https://git-scm.com/downloads)
- [Python](https://www.python.org/downloads/) (Version 3.8 or newer)
- A Telegram account and a bot created via [@BotFather](https://t.me/BotFather) to get your **Bot Token**.
- Your personal **Admin User ID** from a bot like [@userinfobot](https://t.me/userinfobot).
- An **Arbiscan API Key** for checking transactions.

## 🔧 Installation & Setup

This project is located within the `cortensor/community-projects` monorepo.

### 1. Clone the Repository
Clone the central community repository directly to your local machine.
```bash
git clone https://github.com/cortensor/community-projects.git
cd community-projects
````

### 2\. Navigate to the Project Directory

This monitoring tool is located in the `tools/` directory.

```bash
cd tools/cortensor-monitoring-bot
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

## ⚙️ Configuration

The bot's configuration is managed via an environment file. Node addresses are managed interactively within the bot itself.

### Environment Variables (`.env` file)

Create a `.env` file inside the `tools/cortensor-monitoring-bot` directory and fill it with your credentials.

```env
# Secret credentials for the bot
TELEGRAM_TOKEN="YOUR_TELEGRAM_BOT_TOKEN_HERE"
API_KEY="YOUR_ARBISCAN_API_KEY_HERE"
ADMIN_USER_ID="YOUR_TELEGRAM_USER_ID_HERE"
```

## 🚀 Usage

Once configured, you can run the bot. Ensure you are in the project's directory (`tools/cortensor-monitoring-bot`) and your virtual environment is activated.

```bash
python3 src/main.py
```

The bot will start, and you can begin interacting with it on Telegram using the commands below.

### Key Telegram Commands

  - `/start`: Initializes the bot and shows the main menu.
  - `/register <address> <label>`: Registers a new node address to monitor with a custom label.
  - `/unregister <address>`: Deletes a node from the monitoring list.
  - `/list`: Shows all nodes you are currently monitoring.
  - `/stats`: Provides historical performance statistics for your nodes.
  - `/health`: Displays a detailed health report for your nodes.
  - `/autoupdate`: Toggles a live-updating status message for all nodes.
  - `/stop`: Stops the live-updating message.
  - `/auto`: Toggles automatic, proactive alerts for failed transactions.
  - `/off`: Turns off automatic alerts.

## 👤 Maintainer

  - **@beranalpagion** (Discord)

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.
