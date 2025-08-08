import logging
from telegram import Update
from telegram.ext import Application, CommandHandler
from telegram.ext import ContextTypes

from src.config import TELEGRAM_BOT_TOKEN
from src.bot.handlers import (
    start_command,
    help_command,
    analyze_command,
    settings_command,
    list_jobs_command,
    delete_job_command,
    refresh_command,
    clearcache_command,
    schedule_command,
    list_schedules_command,
    delete_schedule_command,
    status_command,
    add_asset_command,
    remove_asset_command,
    view_portfolio_command,
    clear_portfolio_command,
    dca_command
)
from src.core.worker import start_background_worker
from src.core.scheduler_manager import SchedulerManager
from src.core.dca_worker import start_dca_worker
from src.utils.database import setup_database
from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)

# --- GLOBAL ERROR HANDLER ---
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the user."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    if isinstance(context.error, Exception):
        user_message = "Oops! It seems there was an unexpected technical error in the bot. My team has been notified."
        if update.effective_message:
            await update.effective_message.reply_text(user_message, parse_mode='HTML') # Ensure parse_mode for error messages
        elif update.effective_chat:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=user_message, parse_mode='HTML') # Ensure parse_mode for error messages

def main():
    """Starts the bot, the worker, and the scheduler."""
    setup_logging()
    logger = logging.getLogger(__name__)

    print("DEBUG: TELEGRAM_BOT_TOKEN loaded as: {}... (first 5 chars)".format(TELEGRAM_BOT_TOKEN[:5] if TELEGRAM_BOT_TOKEN else "None"))
    print(f"DEBUG: TELEGRAM_BOT_TOKEN type: {type(TELEGRAM_BOT_TOKEN)}")
    print("DEBUG: Inside main() function.")

    if not TELEGRAM_BOT_TOKEN:
        logger.critical("FATAL: TELEGRAM_BOT_TOKEN is not configured.")
        print("DEBUG: TELEGRAM_BOT_TOKEN is NOT configured, exiting.")
        return
    else:
        print("DEBUG: TELEGRAM_BOT_TOKEN is configured, proceeding.")


    setup_database()
    print("DEBUG: Database setup complete.")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    print("DEBUG: Telegram Application initialized.")

    scheduler_manager = SchedulerManager()
    scheduler_manager.start()

    print("DEBUG: Scheduler started.")

    start_background_worker(application.bot)
    print("DEBUG: Background worker started.")

    start_dca_worker(application.bot)
    print("DEBUG: DCA worker started.")

    # --- Register all command handlers ---
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("analyze", analyze_command))
    application.add_handler(CommandHandler("refresh", refresh_command))
    application.add_handler(CommandHandler("list_jobs", list_jobs_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("delete_job", delete_job_command))
    application.add_handler(CommandHandler("schedule", schedule_command))
    application.add_handler(CommandHandler("list_schedules", list_schedules_command))
    application.add_handler(CommandHandler("delete_schedule", delete_schedule_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("clearcache", clearcache_command))

    application.add_handler(CommandHandler("add_asset", add_asset_command))
    application.add_handler(CommandHandler("remove_asset", remove_asset_command))
    application.add_handler(CommandHandler("view_portfolio", view_portfolio_command))
    application.add_handler(CommandHandler("clear_portfolio", clear_portfolio_command))
    application.add_handler(CommandHandler("dca", dca_command))

    application.add_error_handler(error_handler)

    application.run_polling()
    logger.info("Bot is running with Scheduler and Worker. Press Ctrl+C to stop.")
    print("DEBUG: application.run_polling() started (this should block).")

if __name__ == '__main__':
    main()