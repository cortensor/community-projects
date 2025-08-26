<div align="center">

  <img src="https://avatars.githubusercontent.com/u/174224856?s=200&v=4" alt="Project Logo" width="150">

  # **DECENTRALIZED PROMPTING HELPER POWERED BY CORTENSOR NETWORK **

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

A Telegram bot that helps users improve their prompts before sending them to the Cortensor AI network.

## ✨ Features

* **Automatic Prompt Improvement**: Automatically generates enhanced prompt variations.
* **Multiple Prompt Options**: Offers 5 improved prompt options with different contexts.
* **User History**: Saves user prompt history.
* **Knowledge Base Integration**: Searches relevant documents for better context.
* **Rate Limiting**: Prevents abuse with message throttling.

## 📋 Prerequisites

Before running this bot, it is crucial to understand that it acts as a client for the Cortensor network. Therefore, you must have access to a fully operational Cortensor backend infrastructure.

The core requirements for the backend are:

* A configured **Cortensor Node**
* **cortensord**: The Cortensor daemon service.
* A running **Router Node** that the bot can connect to.
* Python 3.8+
* Telegram Bot Token
* Required libraries (see requirements.txt)

For complete, step-by-step instructions on setting up this backend infrastructure, please follow the official **[Router Node Setup Guide](https://docs.cortensor.network/getting-started/installation-and-setup/router-node-setup)**.

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
    cd apps/prompt-helper
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
    Create a file named `.env` inside the `apps/prompt-helper` directory and populate it with your credentials.
    ```ini
    TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN_HERE"
    CORTENSOR_API_URL="YOUR_CORTENSOR_API_ENDPOINT_URL_HERE"
    CORTENSOR_API_KEY="YOUR_CORTENSOR_API_KEY_HERE"
    CORTENSOR_SESSION_ID="YOUR_SESSION_ID_HERE"
    ```

## 🚀 Usage

Once the configuration is complete, run the bot from within the `apps/Health_Advisor` directory:

```bash
python bot.py
````

The bot is now running. Open your Telegram app, find your bot, and start a conversation. You can begin by sending the `/start` command.

## ⚙️ Configuration

The following variables must be set in your `.env` file for the bot to function correctly:

  * `TELEGRAM_BOT_TOKEN`: The unique token you received from BotFather on Telegram.
  * `CORTENSOR_API_URL`: The full URL to the `/completions` endpoint of the Cortensor API.
  * `CORTENSOR_API_KEY`: The authorization key (Bearer Token) to access the Cortensor API.
  * `CORTENSOR_SESSION_ID`: The session ID required by the API payload to maintain conversation context.

## 📝 How to Use
  * 1. Start a chat with the bot on Telegram
  * 2. Send your prompt or question
  * 3. The bot will display 5 improved prompt options
  * 4. Select the most appropriate option
  * 5. The bot will send the selected prompt to Cortensor API
  * 6. Receive the results directly in the chat
## 🎯 Usage Example
  * **USER**: "Write an article about coffee"
  * Bot will display 5 options:
  * 1. Write a 500-word article about the history of coffee in Indonesia, casual style.
  * 2. Write a short 300-word article about the health benefits of coffee.
  * 3. Write an article about coffee, focusing on types of Indonesian coffee.
  * 4. Write an article about modern coffee trends in Indonesia, casual style.
  * 5. Write an educational article about the process from coffee bean to cup.
       
## 🔄 Workflow
  * 1. User sends a message to the bot
  * 2. Bot generates 5 enhanced prompt variations
  * 3. User selects one option
  * 4. Bot sends the selected prompt to Cortensor API
  * 5. Results are returned to the user
  * 6. Prompt and results are saved in history
       
# Prompt Helper

## Layout
```
prompt-helper/
├── bot.py              # Main bot application
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (created manually)
├── prompt_cache.pkl   # Prompt cache (auto-generated)
├── user_history.pkl   # User history (auto-generated)
└── knowledge_base.json# Knowledge base (auto-generated)
```

## 🛠️ Dependencies
* aiogram ~= 2.25.1
* aiohttp ~= 3.8.5
* sentence-transformers ~= 2.2.2
* scikit-learn ~= 1.3.2
* python-dotenv ~= 1.0.0
* numpy ~= 1.24.3

## 👤 Maintainer

  * **@jo_cortensor** (Discord)

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
