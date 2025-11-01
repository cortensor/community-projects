<div align="center">

  <img src="https://avatars.githubusercontent.com/u/174224856?s=200&v=4" alt="Project Logo" width="150">

  # **Eureka Buddy**

  *A Safe and Friendly Conversational AI for Children*

  <p>
    <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
    <a href="./STATUS.md"><img src="https://img.shields.io/badge/status-active-success.svg" alt="Status"></a>
    <a href="#"><img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python Version"></a>
    <a href="#"><img src="https://img.shields.io/badge/Telegram-%232CA5E0.svg?logo=telegram&logoColor=white" alt="Telegram"></a>
  </p>

   <p align="center">
     <a href="#-features">Features</a> •
     <a href="#-prerequisites">Prerequisites</a> •
     <a href="#-installation--setup">Installation</a> •
     <a href="#-usage">Usage</a>
   </p>
</div>

Eureka Buddy is a Telegram bot designed to provide a safe, engaging, and educational conversational experience for children under 12. It connects to the Cortensor AI network and includes robust safety features, customizable interaction styles, and parent-only controls to ensure a child-friendly environment.

## ✨ Features

* **Child-Safe by Design**: Includes built-in profanity filters and blocks unsafe topics to ensure all conversations are appropriate for children.
* **Customizable Agent Styles**: Choose from different conversational personas like "Friendly Buddy," "Storyteller," or "Homework Helper" to tailor the bot's personality.
* **Parent Mode**: Password-protected "parent mode" allows guardians to manage the bot's settings, including adding or removing custom filtered words.
* **Conversational Memory**: Remembers recent turns in the conversation to provide more contextually relevant responses.
* **Seamless Integration**: Directly connects to the Cortensor API for powerful and natural language processing.
* **Easy Configuration**: Quick and secure setup using a `.env` file to manage all API keys and tokens.

## 📋 Prerequisites

Before running this bot, it is crucial to understand that it acts as a client for the Cortensor network. Therefore, you must have access to a fully operational Cortensor backend infrastructure.

The core requirements for the backend are:

* A configured **Cortensor Node**
* **cortensord**: The Cortensor daemon service.
* A running **Router Node** that the bot can connect to.

For complete, step-by-step instructions on setting up this backend infrastructure, please follow the official **[Router Node Setup Guide](https://docs.cortensor.network/getting-started/installation-and-setup/router-node-setup)**.

## 🔧 Installation & Setup

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/cortensor/community-projects.git](https://github.com/cortensor/community-projects.git)
    cd community-projects/apps/Cortensor-EurekaKidsBot 
    ```
    *(Note: The directory name remains the same unless you change it locally.)*

2.  **Create and Activate a Virtual Environment**
    ```bash
    # For MacOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install Dependencies**
    The required packages are listed in `requirements.txt`.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**
    Create a file named `.env` in the project directory and populate it with your credentials.
    ```ini
    TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN_HERE"
    CORTENSOR_API_URL="YOUR_CORTENSOR_API_ENDPOINT_URL_HERE"
    CORTENSOR_API_KEY="YOUR_CORTENSOR_API_KEY_HERE"
    CORTENSOR_SESSION_ID="YOUR_SESSION_ID_HERE"
    # Optional: Set a PIN for parent mode
    # PARENT_PIN="1234"
    ```

## 🚀 Usage

Once the configuration is complete, run the bot:

```bash
python src/main.py
````

The bot is now running. Open your Telegram app, find your bot, and start a conversation. You can begin by sending the `/start` command.

## ⚙️ Commands

  * `/start`: Greets the user and provides basic information.
  * `/help`: Shows a detailed list of commands and features.
  * `/style [id]`: Lists available styles or sets the bot's personality.
  * `/reset`: Resets the style and chat memory.
  * `/parent`: Unlocks parent mode with a PIN to access admin commands.
  * `/setpin <new_pin>`: Sets or changes the parent mode PIN.
  * `/addbad <word>`: Adds a custom word to the filter (parent mode only).
  * `/removebad <word>`: Removes a custom word from the filter (parent mode only).

## 👤 Maintainer

  * **@beranalpagion** (Discord)

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
