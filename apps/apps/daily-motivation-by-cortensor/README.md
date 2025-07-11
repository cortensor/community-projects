<div align="center">

  <img src="https://avatars.githubusercontent.com/u/174224856?s=200&v=4" alt="Project Logo" width="150">

  # **Daily Motivation by Cortensor Network**

  *AI-powered Telegram bot that delivers motivational quotes tailored to your mood and timezone.*

<p>
<a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
<a href="./STATUS.md"><img src="https://img.shields.io/badge/status-active-success.svg" alt="Status"></a>
<a href="https://t.me/cortensor"><img src="https://img.shields.io/badge/Telegram-%232CA5E0.svg?logo=telegram&logoColor=white" alt="Telegram"></a>
</p>

<p align="center">
<a href="#-features">Features</a> •
<a href="#-prerequisites">Prerequisites</a> •
<a href="#-installation--setup">Installation</a> •
<a href="#-usage">Usage</a>
</p>
</div>

---

## ✨ Features

- 🌤️ **Mood-based motivation** — Personalized motivational quotes based on how users feel: happy, sad, anxious.
- ⏰ **Timezone-based scheduling** — Delivers motivation daily at 08:00 AM local time (user-selected timezone).
- 🤖 **AI-generated** — Uses the Cortensor API to produce dynamic, supportive motivational responses.
- 🔁 **Randomized prompts** — Prevents repetitive output with varied supportive prompts.
- 📦 **Simple deployment** — Easily deployed using Python, Telegram Bot API, and Cortensor endpoints.

---

## 📋 Prerequisites

This bot depends on the Cortensor API infrastructure to function. You will need:

- A valid **Cortensor API key**
- A valid **Session ID** from Cortensor network
- A registered **Telegram bot token**

---

## 🔧 Installation & Setup

1. **Clone the Repository**
```bash
git clone https://github.com/cortensor/community-projects.git
cd community-projects/apps/daily-motivation-by-cortensor

2. Install Requirements
pip install -r requirements.txt

3. Create and Activate a Virtual Environment
# For MacOS/Linux
python3 -m venv venv
source venv/bin/activate

# For Windows
python -m venv venv
.\venv\Scripts\activate

4. Install Dependencies The required packages are listed in requirements.txt.
pip install -r requirements.txt

5. Configure Environment Variables Create a file named .env inside the apps/eliza-chatbot directory and populate it with your credentials.
TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN_HERE"
CORTENSOR_API_URL="YOUR_CORTENSOR_API_ENDPOINT_URL_HERE"
CORTENSOR_API_KEY="YOUR_CORTENSOR_API_KEY_HERE"
CORTENSOR_SESSION_ID="YOUR_SESSION_ID_HERE"

🚀 Usage
Start the bot by running:
Once the configuration is complete, run the bot from within the apps/daily-motivation-by-cortensor directory:
python bot.py
The bot is now running. Open your Telegram app, find your bot, and start a conversation. You can begin by sending the /start command.

⚙️ Configuration
The following variables must be set in your .env file for the bot to function correctly:

TELEGRAM_BOT_TOKEN: The unique token you received from BotFather on Telegram.
CORTENSOR_API_URL: The full URL to the /completions endpoint of the Cortensor API.
CORTENSOR_API_KEY: The authorization key (Bearer Token) to access the Cortensor API.
CORTENSOR_SESSION_ID: The session ID required by the API payload to maintain conversation context.

👤 Maintainer
@jo_cortensor on Discord

📄 License
This project is licensed under the MIT License. See the LICENSE file for more details.

