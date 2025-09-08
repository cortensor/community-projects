import os
import sys
import logging
from importlib import import_module
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    # Ensure project root is on sys.path when running as a script
    if __package__ is None or __package__ == "":
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))

    try:
        config = import_module("src.config")
        bot_module = import_module("src.bot")
        db_module = import_module("src.db.storage")
    except Exception:
        from . import config as config  # type: ignore
        from . import bot as bot_module  # type: ignore
        from .db import storage as db_module  # type: ignore

    if not all([
        getattr(config, "TELEGRAM_BOT_TOKEN", None),
        getattr(config, "CORTENSOR_API_URL", None),
        getattr(config, "CORTENSOR_API_KEY", None),
        getattr(config, "CORTENSOR_SESSION_ID", None),
    ]):
        logger.critical("FATAL: One or more configurations in .env are missing! Bot cannot start.")
        return

    logger.info("Starting Tweet/Thread Generator bot…")

    # Initialize local database
    try:
        db_module.init_db()
    except Exception as e:
        logger.warning(f"DB init failed: {e}")

    updater = Updater(token=config.TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", bot_module.start_command))
    dispatcher.add_handler(CommandHandler("help", bot_module.help_command))
    try:
        dispatcher.add_handler(CommandHandler("settings", bot_module.settings_command))
    except Exception:
        logger.warning("/settings command handler could not be registered.")
    # /diag removed

    try:
        dispatcher.add_handler(CommandHandler("thread", bot_module.thread_command))
        from telegram.ext import CallbackQueryHandler
        dispatcher.add_handler(CallbackQueryHandler(bot_module._thread_callback, pattern=r"^thr\|"))
        dispatcher.add_handler(CallbackQueryHandler(bot_module._cmd_callback, pattern=r"^cmd\|"))
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, bot_module.handle_text_input))
    except Exception:
        logger.warning("Interactive handlers not available.")

    updater.start_polling()
    logger.info("Bot is running. Press Ctrl+C to stop.")
    updater.idle()

if __name__ == '__main__':
    main()
