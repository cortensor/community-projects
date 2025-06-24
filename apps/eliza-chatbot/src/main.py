import os
import logging
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CORTENSOR_API_URL = os.getenv("CORTENSOR_API_URL")
CORTENSOR_API_KEY = os.getenv("CORTENSOR_API_KEY")
CORTENSOR_SESSION_ID = os.getenv("CORTENSOR_SESSION_ID")

def submit_cortensor_task(update: Update, context: CallbackContext):
    user_prompt = update.message.text
    logger.info(f"Submitting task for prompt: '{user_prompt}'")

    context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    headers = {
        "Authorization": f"Bearer {CORTENSOR_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "session_id": int(CORTENSOR_SESSION_ID),
        "prompt": user_prompt,
        "prompt_type": 0,
        "stream": False,
        "timeout": 180
    }

    try:
        logger.info(f"Sending request to {CORTENSOR_API_URL} with payload: {payload}")
        response = requests.post(CORTENSOR_API_URL, headers=headers, json=payload, timeout=320)
        response.raise_for_status()

        response_data = response.json()
        logger.info(f"Received response from Cortensor: {response_data}")

        answer = response_data['choices'][0]['text']
        
        if answer and answer.strip():
            update.message.reply_text(answer.strip())
        else:
            logger.warning("Received an empty 'text' field from Cortensor API.")
            update.message.reply_text("I'm sorry, I did not receive any valid content from the server. Please try a different prompt.")

    except requests.exceptions.ReadTimeout:
        logger.error("Request timed out while waiting for a response from the server.")
        update.message.reply_text("I'm sorry, the server did not respond in time. It might be having issues or under maintenance. Please try again later.")

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 408:
            logger.warning("Request timed out on the Cortensor server side (408).")
            update.message.reply_text("I'm sorry, the server is busy or your request is taking too long to process. Please try again in a moment.")
        else:
            logger.error(f"HTTP Error occurred: {e.response.status_code} - {e.response.text}")
            update.message.reply_text(f"Sorry, an API error occurred (Status: {e.response.status_code}).")

    except (KeyError, IndexError):
        logger.error(f"Failed to parse the response JSON. Data: {response_data}", exc_info=True)
        update.message.reply_text("Sorry, I received a response, but could not understand its format.")

    except Exception as e:
        logger.error("An unexpected error occurred", exc_info=True)
        update.message.reply_text(f"Sorry, an unexpected error occurred.")


def start_command(update: Update, context: CallbackContext):
    update.message.reply_text("Hello! I am a Cortensor bot. Please ask me a question.")

def main():
    if not all([TELEGRAM_BOT_TOKEN, CORTENSOR_API_URL, CORTENSOR_API_KEY, CORTENSOR_SESSION_ID]):
        logger.critical("FATAL: One or more configurations in .env are missing! Bot cannot start.")
        return

    logger.info("Starting bot...")

    updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(MessageHandler(
        Filters.text & ~Filters.command, 
        submit_cortensor_task,
        run_async=True
    ))

    updater.start_polling()
    logger.info("Bot is running. Press Ctrl+C to stop.")
    updater.idle()

if __name__ == '__main__':
    main()
