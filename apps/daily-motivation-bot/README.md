<div align="center">

  <img src="https://avatars.githubusercontent.com/u/174224856?s=200&v=4" alt="Project Logo" width="150">

  # **Cortensor Daily Motivation Bot**

  *Personalized Daily Motivation, powered by Cortensor API*

  <p>
    <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
    <a href="./STATUS.md"><img src="https://img.shields.io/badge/status-active-success.svg" alt="Status"></a>
    <a href="#"><img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python Version"></a>
    <a href="https://t.me/cortensor"><img src="https://img.shields.io/badge/Telegram-%232CA5E0.svg?logo=telegram&logoColor=white" alt="Telegram"></a>
  </p>

  <p align="center">
    <a href="#-features">Features</a> •
    <a href="#-prerequisites">Prerequisites</a> •
    <a href="#-installation--setup">Installation</a> •
    <a href="#-usage">Usage</a>
  </p>
</div>

**Cortensor Daily Motivation Bot** is a Telegram bot that delivers personalized, AI-generated motivational messages to users daily at 08:00 AM (local time). Users can choose the tone of their message (cheerful, serious, or sarcastic), and the bot uses the Cortensor AI network to generate unique responses.

---

## ✨ Features

* **Daily Motivation Delivery**: Sends a motivational message every day at the user's local 08:00 AM.
* **Customizable Mood**: Users can select the tone of motivation they want (cheerful, serious, sarcastic).
* **Timezone Awareness**: Bot adjusts delivery time based on user’s actual timezone (via `/settimezone`).
* **Cortensor Integration**: Powered by Cortensor API for generating intelligent and adaptive motivational quotes.
* **Automatic Broadcast**: Sends to all users who interacted in the last 24 hours.

---

## 📋 Prerequisites

This bot connects to the Cortensor AI network. You must have:

- A **running Cortensor Router Node**
- **CORTENSOR_API_KEY** (obtainable via Cortensor dashboard or testnet)
- Python environment (>= 3.9)
- Telegram bot token (from BotFather)

---

## 🔧 Installation & Setup

1. Clone the Community Repo
```bash
git clone https://github.com/cortensor/community-projects.git
cd community-projects

2. Navigate to the Project Directory This bot is located in the apps/ directory.

cd apps/daily-motivation-bot

3. Create and Activate a Virtual Environment

# For MacOS/Linux
python3 -m venv venv
source venv/bin/activate

# For Windows
python -m venv venv
.\venv\Scripts\activate

4. Install Dependencies The required packages are listed in requirements.txt.

pip install -r requirements.txt

5. Configure Environment Variables Create a file named .env inside the apps/daily-motivation-bot directory and populate it with your credentials.

TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN_HERE"
CORTENSOR_API_URL="YOUR_CORTENSOR_API_ENDPOINT_URL_HERE"
CORTENSOR_API_KEY="YOUR_CORTENSOR_API_KEY_HERE"
CORTENSOR_SESSION_ID="YOUR_SESSION_ID_HERE"

🚀 Usage
Once the configuration is complete, run the bot from within the apps/eliza-chatbot directory:

python src/main.py
The bot is now running. Open your Telegram app, find your bot, and start a conversation. You can begin by sending the /start command.

⚙️ Configuration
The following variables must be set in your .env file for the bot to function correctly:

TELEGRAM_BOT_TOKEN: The unique token you received from BotFather on Telegram.
CORTENSOR_API_URL: The full URL to the /completions endpoint of the Cortensor API.
CORTENSOR_API_KEY: The authorization key (Bearer Token) to access the Cortensor API.
CORTENSOR_SESSION_ID: The session ID required by the API payload to maintain conversation context.

👤 Maintainer
@jo_cortensor (Discord)
📄 License
This project is licensed under the MIT License. See the LICENSE file for more details.
