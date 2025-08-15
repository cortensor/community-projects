Project Logo
Cortensor Eliza ChatBot
Your Conversational Gateway to the Cortensor API

License Status Python Version Telegram

Features • Prerequisites • Installation • Usage

Cortensor Eliza ChatBot provides a seamless bridge between your Telegram messenger and the powerful Cortensor AI. Ask questions, get instant responses, and interact with the AI backend through a simple and familiar chat interface. This project is designed for easy deployment and robust performance.

✨ Features
Fast, secure health analysis with no central server.
* Personalized recommendations based on symptoms, lifestyle, and goals.
* Cross-checking from multiple nodes to reduce errors.
* Privacy protected with blockchain technology.
* Direct access via Telegram, responsive on all devices.
  
📋 Prerequisites
Before running this bot, it is crucial to understand that it acts as a client for the Cortensor network. Therefore, you must have access to a fully operational Cortensor backend infrastructure.

The core requirements for the backend are:

A configured Cortensor Node
cortensord: The Cortensor daemon service.
A running Router Node that the bot can connect to.
For complete, step-by-step instructions on setting up this backend infrastructure, please follow the official Router Node Setup Guide.

🔧 Installation & Setup
This project is located within the Cortensor Community Projects monorepo. Follow these steps to set it up.

1. Clone the Main Repository Clone the central hub where all community projects reside.

* git clone https://github.com/cortensor/community-projects.git
* cd community-projects

2. Navigate to the Project Directory This bot is located in the apps/ directory.

* cd apps/eliza-chatbot
  
3. Create and Activate a Virtual Environment

# For MacOS/Linux
python3 -m venv venv
source venv/bin/activate

# For Windows
python -m venv venv
.\venv\Scripts\activate

4. Install Dependencies The required packages are listed in requirements.txt.

* pip install -r requirements.txt

5. Configure Environment Variables Create a file named .env inside the apps/eliza-chatbot directory and populate it with your credentials.

* TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN_HERE"
* CORTENSOR_API_URL="YOUR_CORTENSOR_API_ENDPOINT_URL_HERE"
* CORTENSOR_API_KEY="YOUR_CORTENSOR_API_KEY_HERE"
* CORTENSOR_SESSION_ID="YOUR_SESSION_ID_HERE"
  
🚀 Usage
Once the configuration is complete, run the bot from within the apps/Health_Adivisor directory:

* python src/main.py

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
