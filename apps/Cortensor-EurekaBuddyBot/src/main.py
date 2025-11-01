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

    # Lazy-import modules to avoid editor false positives on package-relative imports
    try:
        config = import_module("src.config")
        bot_module = import_module("src.bot")
        parent_module = import_module("src.parent")
        safety_module = import_module("src.safety")
    except Exception:
        # Fallback to relative imports when executed as a package
        from . import config as config  # type: ignore
        from . import bot as bot_module  # type: ignore
        from . import parent as parent_module  # type: ignore
        from . import safety as safety_module  # type: ignore

    if not all([
        getattr(config, "TELEGRAM_BOT_TOKEN", None),
        getattr(config, "CORTENSOR_API_URL", None),
        getattr(config, "CORTENSOR_API_KEY", None),
        getattr(config, "CORTENSOR_SESSION_ID", None),
    ]):
        logger.critical("FATAL: One or more configurations in .env are missing! Bot cannot start.")
        return

    logger.info("Starting bot with kid-friendly safety, RAW prompts, styles, and model selection...")

    # Load persisted parent PINs (per chat) and custom words
    try:
        parent_module.load_state()
    except Exception:
        logger.warning("Could not load parent PINs; continuing without persistence.")
    try:
        safety_module.load_state()
    except Exception:
        logger.warning("Could not load custom words; continuing without persistence.")

    updater = Updater(token=config.TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", bot_module.start_command))
    dispatcher.add_handler(CommandHandler("help", bot_module.help_command))
    dispatcher.add_handler(CommandHandler("style", bot_module.style_command))
    dispatcher.add_handler(CommandHandler("reset", bot_module.reset_command))
    # Parent mode commands
    dispatcher.add_handler(CommandHandler("parent", bot_module.parent_command))
    dispatcher.add_handler(CommandHandler("addbad", bot_module.addbad_command))
    dispatcher.add_handler(CommandHandler("removebad", bot_module.removebad_command))
    dispatcher.add_handler(CommandHandler("listbad", bot_module.listbad_command))
    dispatcher.add_handler(CommandHandler("badcount", bot_module.badcount_command))
    dispatcher.add_handler(CommandHandler("checkbad", bot_module.checkbad_command))
    dispatcher.add_handler(CommandHandler("setpin", bot_module.setpin_command))
    dispatcher.add_handler(CommandHandler("parentlock", bot_module.parentlock_command))
    dispatcher.add_handler(CommandHandler("resetpin", bot_module.resetpin_command))
    dispatcher.add_handler(CommandHandler("adminresetpin", bot_module.adminresetpin_command))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, bot_module.submit_cortensor_task))

    updater.start_polling()
    logger.info("Bot is running. Press Ctrl+C to stop.")
    updater.idle()

if __name__ == '__main__':
    main()
