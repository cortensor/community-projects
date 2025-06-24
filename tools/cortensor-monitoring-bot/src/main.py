# main.py
import logging
import asyncio
from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import aiohttp
from dotenv import load_dotenv

load_dotenv()

from bot import config, database, data_logger
from bot.handlers.common import register_common_handlers
from bot.handlers.monitoring import register_monitoring_handlers
from bot.handlers.automation import register_automation_handlers

# DITAMBAHKAN: Import untuk tugas alert otomatis
from bot.tasks import schedule_alerting_jobs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def on_startup(dp: Dispatcher):
    """Function executed when the bot starts."""
    logger.info("Starting bot...")
    
    # PERUBAHAN: Nama fungsi setup database disesuaikan
    database.setup_database()
    data_logger.setup_history_db()
    
    dp.bot['session'] = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
    scheduler = AsyncIOScheduler(timezone="UTC")
    
    # Jadwalkan tugas data logger yang sudah ada
    data_logger.schedule_logging_jobs(scheduler, dp.bot)
    
    # DITAMBAHKAN: Jadwalkan tugas alert otomatis yang baru
    schedule_alerting_jobs(scheduler, dp.bot)
    
    dp.bot['scheduler'] = scheduler
    dp.bot['scheduler'].start()
    logger.info("Bot started and schedulers are running.")

async def on_shutdown(dp: Dispatcher):
    """Function executed when the bot stops."""
    logger.info("Shutting down bot...")
    if 'session' in dp.bot and not dp.bot['session'].closed:
        await dp.bot['session'].close()
    if 'scheduler' in dp.bot and dp.bot['scheduler'].running:
        dp.bot['scheduler'].shutdown(wait=False)
    logger.info("Shutdown complete.")

def main():
    """Main function to run the bot."""
    if not config.TELEGRAM_TOKEN:
        logger.critical("TELEGRAM_TOKEN not found in .env file. Bot cannot start.")
        return

    bot = Bot(token=config.TELEGRAM_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(bot, storage=storage)

    register_common_handlers(dp)
    register_monitoring_handlers(dp)
    register_automation_handlers(dp)

    logger.info("All handlers registered.")

    executor.start_polling(
        dispatcher=dp,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    )

if __name__ == '__main__':
    main()
