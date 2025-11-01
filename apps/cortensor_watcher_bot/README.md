<div align="center">

  <img src="https://avatars.githubusercontent.com/u/174224856?s=200&v=4" alt="Project Logo" width="150">

  # **CORTENSOR WATCHER BOT POWERED BY CORTENSOR NETWORK **

  *Your Conversational Gateway to the Cortensor API*

  <p>
    <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
    <a href="./STATUS.md"><img src="https://img.shields.io/badge/status-active-success.svg" alt="Status"></a>
    <a href="#"><img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python Version"></a>
    <a href="#"><img src="https://img.shields.io/badge/Telegram-%232CA5E0.svg?logo=telegram&logoColor=white" alt="Telegram"></a>
  </p>

   <p align="center">
     <a href="#-features">Features</a> •
     <a href="#-prerequisites">Prerequisites</a> •
     <a href="#-installation--setup">Installation</a> •
     <a href="#-usage">Usage</a>
   </p>
</div>


> **Cortensor Watcher** is an automated system that monitors Discord developer logs, processes messages using the Cortensor API for summarization, and instantly delivers concise insights to Telegram subscribers, with clear TLDR, High level summary and key Insights.

---

## 🧠 Overview

Cortensor Watcher consists of **three main components** that run in parallel on a VPS:

| Component | Function |
|------------|-----------|
| 🛰️ `discord_watcher.py` | Monitors Discord developer channels and stores the latest messages as JSON files |
| ⚙️ `cortensor_processor.py` | Fetches new messages, summarizes them using the Cortensor API, and prepares insights |
| 📡 `telegram_bot.py` | Sends processed insights to all Telegram subscribers in real time |

---

## 🔧 Installation & Setup

This project is located within the `Cortensor Community Projects` monorepo. Follow these steps to set it up.

1.  **Clone the Main Repository**
    Clone the central hub where all community projects reside.
    ```bash
    git clone https://github.com/cortensor/community-projects.git
    cd community-projects
    ```

2.  **Navigate to the Project Directory**
    This bot is located in the `apps/` directory.
    ```bash
    cd apps/cortensor_watcher_bot
    ```

3.  **Create and Activate a Virtual Environment**
    ```bash
    # For MacOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

4.  **Install Dependencies**
    The required packages are listed in `requirements.txt`.
    ```bash
    pip install -r requirements.txt
    ```

5.  **Configure Environment Variables**
    Create a file named `config.py` inside the `apps/cortensor_watcher_bot` directory and populate it with your credentials.
    
```bash
import os

* Discord Configuration
DISCORD_TOKEN = "Your Discord Bot Token"
DISCORD_CHANNEL_ID = 123456789112345# Change it with your own discord private channel ID

* Telegram Configuration
TELEGRAM_BOT_TOKEN = "123456789:xxxxXXXxxxXXXXxxxXXXX"

* Cortensor API Configuration
CORTENSOR_API_URL = "http://Your-Router-IP:5010/api/v1//completions"
CORTENSOR_API_KEY = "Your Own API KEY"
CORTENSOR_SESSION_ID = "Input Your Session ID here"

* File paths
DATA_DIR = "data"
LATEST_DEVLOG_FILE = f"{DATA_DIR}/latest_devlog.json"
INSIGHTS_QUEUE_FILE = f"{DATA_DIR}/insights_queue.json"
PROCESSED_MESSAGES_FILE = f"{DATA_DIR}/processed_messages.json"
SUBSCRIBERS_FILE = f"{DATA_DIR}/subscribers.json"

* Create data directory if not exists
os.makedirs(DATA_DIR, exist_ok=True)

```
    ⚠️ Note: The data/ directory will be created automatically when the bot runs for the first time.

## 🪄 Running the Bot (via screen)

Use screen to run all three components independently in the background.
This is the recommended method for running on a VPS.

## 1. Start the Discord Watcher
```bash
screen -S watcher
python discord_watcher.py
```
Press Ctrl + A + D to detach from the screen while keeping it running.

## 2. Start the Cortensor Processor
```bash
screen -S processor
python cortensor_processor.py
```
## 3. Start the Telegram Bot
```bash
screen -S telegram
python telegram_bot.py
```
## 4. Manage Screens
list all running screens
```bash
screen -ls
```
Reattach to a specific screen:
```bash
screen -r watcher
```
If you want to stop:
```bash
ctrl + C
```

The bot is now running. Open your Telegram app, find your bot, and start a conversation. You just to click /start and the development insights will auto sending to the bot.

# Example Telegram Output

## Layout
```
🚀 Cortensor Watcher — Development Insight

🗒 Original Preview:
_Runtime Engine v2 deployed successfully 🚀_

🧠 TL;DR: Runtime engine v2 successfully deployed.

🔍 High-level summary:
This release improves inference speed and adds better containerization.

🔑 Key Insights:
• Reduced cold start latency
• Enhanced runtime stability
• Improved monitoring diagnostics
```
       
# CORTENSOR WATCHER BOT

## Layout
```
cortensor_watcher_bot/
├── config.py                # global configuration (token, API key, path data)
├── discord_watcher.py       # Listener for discord chanel
├── cortensor_processor.py   # Summarizer via Cortensor API
├── telegram_bot.py          # Sender insight to the Telegram
└── requirements.txt         # Dependency Python
```

## 🛠️ Dependencies
* discord.py>=2.3.0
* python-telegram-bot>=20.0
* requests>=2.31.0
* aiohttp>=3.8.0

## 👤 Maintainer

  * **@jo_cortensor** (Discord)

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for more details.

