import os
import logging
import requests
import random
import re
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, Bot
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext, ConversationHandler
)
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CORTENSOR_API_URL = os.getenv("CORTENSOR_API_URL")
CORTENSOR_API_KEY = os.getenv("CORTENSOR_API_KEY")
CORTENSOR_SESSION_ID = os.getenv("CORTENSOR_SESSION_ID")

# Conversation state
ASK_FEELING, ASK_TIMEZONE = range(2)

# Global user list and timezone map
user_ids = set()
user_timezones = {}
user_prompt_cache = {}  # user_id -> mood -> set of cleaned responses

# Clean model output
def clean_motivation_output(text: str) -> str:
    text = re.sub(r'^User:.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^Eliza:.*$', '', text, flags=re.MULTILINE)
    prefixes = [
        "Here is", "Here's", "This is", "Let me", "Let me share",
        "Your quote is", "Fresh motivational quote", "Here's a motivational quote",
        "Below is", "Here’s something"
    ]
    for prefix in prefixes:
        if text.lower().startswith(prefix.lower()):
            parts = text.split(":", 1)
            if len(parts) == 2:
                text = parts[1].strip()
    text = text.replace("<s>", "").replace("</s>", "")
    text = re.sub(r'\(id:\s*\d+\)', '', text)
    text = re.sub(r'[-–—]\s*[^"\n]+$', '', text).strip()
    return text.strip(' "\n”“')

# Cortensor API call
def ask_cortensor_motivation(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {CORTENSOR_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "session_id": int(CORTENSOR_SESSION_ID),
        "prompt": prompt,
        "prompt_type": 0,
        "stream": False,
        "timeout": 180
    }
    response = requests.post(CORTENSOR_API_URL, headers=headers, json=payload, timeout=320)
    response.raise_for_status()
    data = response.json()
    return data['choices'][0]['text'].strip()

# Send daily motivation
def send_daily_motivation(bot: Bot, chat_id: int):
    prompts = [
        "Give me a fresh motivational quote. Make it kind, short, and encouraging.",
        "Generate a unique, uplifting quote that inspires positivity and resilience.",
        "Write a short motivational quote that sparks energy and hope.",
        "Give a cheerful and creative motivational message under 30 words.",
        "Create a simple but powerful line of motivation that encourages someone to move forward.",
        "Say something short and motivational for someone who feels lost or uncertain.",
        "Write an encouraging quote for someone who is struggling but keeps going.",
        "Give me a creative line to remind someone that brighter days are coming.",
        "Generate a brief quote to support someone feeling anxious or nervous.",
        "Say something kind and uplifting to someone feeling emotionally overwhelmed."
    ]
    try:
        prompt = random.choice(prompts)
        result = ask_cortensor_motivation(prompt)
        cleaned_result = clean_motivation_output(result)
        bot.send_message(chat_id=chat_id, text=f"🌅 Daily Motivation:\n\n{cleaned_result}")
        logger.info(f"Motivation sent to {chat_id}")
    except Exception as e:
        logger.error(f"Failed to send motivation to {chat_id}", exc_info=True)

# Schedule jobs
def schedule_daily_jobs(scheduler: BackgroundScheduler, bot: Bot):
    scheduler.remove_all_jobs()
    for chat_id, offset in user_timezones.items():
        utc_hour = (8 - offset) % 24
        scheduler.add_job(
            send_daily_motivation,
            trigger='cron',
            hour=utc_hour,
            minute=0,
            args=[bot, chat_id],
            id=f"motivation_{chat_id}",
            replace_existing=True
        )

# /start

def start(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    user_ids.add(user_id)
    update.message.reply_text(
        "👋 Hello! I’m *Eliza Chat Bot* from the Cortensor Network.\n\n"
        "Before we start, please set your local timezone (UTC offset) so I can send daily motivation at 08:00 your time.\n"
        "Type /settimezone to begin.",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

# /settimezone

def set_timezone(update: Update, context: CallbackContext):
    keyboard = [[str(i)] for i in range(0, 24)]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text("Please choose your timezone (UTC offset):", reply_markup=reply_markup)
    return ASK_TIMEZONE

# Handle timezone

def handle_timezone(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    try:
        offset = int(update.message.text.strip())
        if 0 <= offset <= 23:
            user_timezones[user_id] = offset
            update.message.reply_text("✅ Timezone set! Now tell me how you're feeling.")
            keyboard = [["Happy", "Sad", "Anxious"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            update.message.reply_text("How are you feeling right now? 😊😢😟", reply_markup=reply_markup)
            schedule_daily_jobs(context.bot_data['scheduler'], context.bot)
            return ASK_FEELING
        else:
            raise ValueError
    except ValueError:
        update.message.reply_text("Invalid input. Please choose a number between 0 and 23.")
        return ASK_TIMEZONE

# Handle feeling

def handle_feeling(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    mood = update.message.text.lower()

    if user_id not in user_prompt_cache:
        user_prompt_cache[user_id] = {}
    if mood not in user_prompt_cache[user_id]:
        user_prompt_cache[user_id][mood] = set()

    used_responses = user_prompt_cache[user_id][mood]
    max_tries = 20
    final_response = None

    for _ in range(max_tries):
        seed = random.randint(1000, 9999)
        prompt = {
            "happy": f"Give me a fresh and unique motivational quote to celebrate happiness and joy. Make it inspiring. Avoid cliches. (id:{seed})",
            "sad": f"Give me a motivational quote to comfort and lift someone who feels sad. Make it sound original and gentle. (id:{seed})",
            "anxious": f"Give me a calming motivational quote for someone feeling anxious. Be reassuring and creative. Avoid common quotes. (id:{seed})"
        }.get(mood, f"Give me a motivational quote that is uplifting, kind, and encouraging. Make it original. (id:{seed})")

        try:
            update.message.reply_text("Looking for inspiration... 🌛")
            result = ask_cortensor_motivation(prompt)
            cleaned_result = clean_motivation_output(result)
            if cleaned_result not in used_responses:
                used_responses.add(cleaned_result)
                final_response = cleaned_result
                break
        except Exception as e:
            logger.error("Cortensor error", exc_info=True)
            update.message.reply_text("Sorry, something went wrong while contacting the Cortensor network.")
            return ConversationHandler.END

    if final_response:
        update.message.reply_text(final_response)
    else:
        update.message.reply_text("Couldn't find a unique quote right now. Try again later.")
    return ConversationHandler.END

# Free input handler

def handle_motivation_request(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    user_ids.add(user_id)
    user_input = update.message.text.lower()
    irrelevant_keywords = ["apa kabar", "siapa kamu", "kamu bisa apa"]
    if any(keyword in user_input for keyword in irrelevant_keywords):
        update.message.reply_text("I’m here to provide motivational support. Try saying what kind of motivation you need 💡.")
        return

    prompt = (
        f"Act as a motivational coach. Based on the topic: '{user_input}', "
        f"give a unique, kind, and clear motivational quote in English, less than 30 words. Avoid common quotes."
    )

    try:
        update.message.reply_text("Looking for inspiration... 🌛")
        result = ask_cortensor_motivation(prompt)
        cleaned_result = clean_motivation_output(result)
        update.message.reply_text(cleaned_result)
    except Exception as e:
        logger.error("Motivation error", exc_info=True)
        update.message.reply_text("Sorry, I couldn't get your motivation right now. Try again later.")

# Main

def main():
    if not all([TELEGRAM_BOT_TOKEN, CORTENSOR_API_URL, CORTENSOR_API_KEY, CORTENSOR_SESSION_ID]):
        logger.critical("Missing configuration in .env. Bot cannot start.")
        return

    updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    scheduler = BackgroundScheduler(timezone=utc)
    scheduler.start()
    dispatcher.bot_data['scheduler'] = scheduler

    schedule_daily_jobs(scheduler, updater.bot)

    conversation = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("settimezone", set_timezone)
        ],
        states={
            ASK_TIMEZONE: [MessageHandler(Filters.text & ~Filters.command, handle_timezone)],
            ASK_FEELING: [MessageHandler(Filters.text & ~Filters.command, handle_feeling)]
        },
        fallbacks=[]
    )

    dispatcher.add_handler(conversation)
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_motivation_request))

    updater.start_polling()
    logger.info("Eliza Chat Bot is running...")
    updater.idle()

if __name__ == '__main__':
    main()
