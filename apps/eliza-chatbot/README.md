<div align="center">

  <img src="https://avatars.githubusercontent.com/u/174224856?s=200&v=4" alt="Project Logo" width="150">

  # **Cortensor Eliza ChatBot**

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

Cortensor Eliza ChatBot provides a seamless bridge between your Telegram messenger and the powerful Cortensor AI. Ask questions, get instant responses, and interact with the AI backend through a simple and familiar chat interface. This project is designed for easy deployment and robust performance.

## ✨ Features

* **Seamless Integration**: Directly connects to the Cortensor API for natural language processing.
* **Conversational Interface**: Leverages Telegram as a user-friendly platform to interact with the AI backend.
* **Asynchronous Handling**: Provides a "typing..." indicator to the user while requests are being processed for a better user experience.
* **Easy Configuration**: Quick and secure setup using a `.env` file to manage all API keys and tokens.
* **Lightweight**: Built with efficient Python libraries like `python-telegram-bot` and `requests`.

## 📋 Prerequisites

Before running this bot, it is crucial to understand that it acts as a client for the Cortensor network. Therefore, you must have access to a fully operational Cortensor backend infrastructure.

The core requirements for the backend are:

* A configured **Cortensor Node**
* **cortensord**: The Cortensor daemon service.
* A running **Router Node** that the bot can connect to.

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
    cd apps/eliza-chatbot
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
    Create a file named `.env` inside the `apps/eliza-chatbot` directory and populate it with your credentials.
    ```ini
    TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN_HERE"
    CORTENSOR_API_URL="YOUR_CORTENSOR_API_ENDPOINT_URL_HERE"
    CORTENSOR_API_KEY="YOUR_CORTENSOR_API_KEY_HERE"
    CORTENSOR_SESSION_ID="YOUR_SESSION_ID_HERE"
    ```

## 🚀 Usage

Once the configuration is complete, run the bot from within the `apps/eliza-chatbot` directory:

```bash
python src/main.py
````

The bot is now running. Open your Telegram app, find your bot, and start a conversation. You can begin by sending the `/start` command.

## ⚙️ Configuration

The following variables must be set in your `.env` file for the bot to function correctly:

  * `TELEGRAM_BOT_TOKEN`: The unique token you received from BotFather on Telegram.
  * `CORTENSOR_API_URL`: The full URL to the `/completions` endpoint of the Cortensor API.
  * `CORTENSOR_API_KEY`: The authorization key (Bearer Token) to access the Cortensor API.
  * `CORTENSOR_SESSION_ID`: The session ID required by the API payload to maintain conversation context.

## 👤 Maintainer

  * **@beranalpa** (Discord)

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
