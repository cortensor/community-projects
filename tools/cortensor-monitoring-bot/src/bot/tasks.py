import asyncio
import logging
from datetime import datetime
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import aiohttp

# Adjust imports to match your project structure
from . import database as db
from . import arbiscan_checker
from . import config

logger = logging.getLogger(__name__)

async def check_transactions_periodically(bot: Bot) -> None:
    """
    A scheduled task that periodically checks for failed transactions for all registered users.
    It respects each user's alert preference (/auto or /off).

    :param bot: The aiogram Bot instance, used to send messages.
    """
    logger.info("Running scheduled check for failed transactions...")
    
    all_users = db.get_all_registered_addresses()
    if not all_users:
        logger.info("No registered users to check. Skipping this run.")
        return
        
    api_key = config.ARBISCAN_API_KEY
    
    async with aiohttp.ClientSession() as session:
        for user_id, addresses in all_users.items():
            # First, check if the user has alerts enabled
            if not db.get_alert_status(user_id):
                logger.debug(f"Skipping user {user_id} as their alerts are disabled.")
                continue

            # Then, loop through only the addresses registered by this specific user
            for addr_data in addresses:
                address = addr_data['address']
                name = addr_data['name']
                
                # Check for recent failed transactions for this specific address
                failed_txs = await arbiscan_checker.check_failed_transactions(session, address, api_key)
                
                for tx in failed_txs:
                    # Send an alert only if it's a new failure we haven't notified before
                    if not db.is_tx_notified(tx['hash']):
                        
                        # Be more specific about which node had the error.
                        logger.info(
                            f"Found new failed tx {tx['hash']} for node '{name}' ({address}) "
                            f"belonging to user {user_id}"
                        )
                        
                        # Format the alert message in English
                        response_text = (
                            f"🚨 **Automatic Failed Transaction Alert!**\n\n"
                            f"**Node Name:** `{name}`\n"
                            f"**Address:** `{address}`\n\n"
                            f"**Details:**\n{tx['reason']}"
                        )
                        
                        try:
                            # Send the alert message to the user
                            await bot.send_message(
                                user_id, 
                                response_text, 
                                parse_mode="Markdown", 
                                disable_web_page_preview=True
                            )
                            # Record the transaction hash to prevent duplicate alerts
                            db.add_notified_tx(tx['hash'])
                        except Exception as e:
                            logger.error(
                                f"Failed to send alert to user {user_id} for tx {tx['hash']}: {e}", 
                                exc_info=True
                            )
                
                # A short delay between checking each address to be respectful to APIs
                await asyncio.sleep(0.5)

def schedule_alerting_jobs(scheduler: AsyncIOScheduler, bot: Bot) -> None:
    """
    Adds the transaction monitoring task to the APScheduler instance.

    :param scheduler: The AsyncIOScheduler instance.
    :param bot: The aiogram Bot instance to pass to the job.
    """
    # --- CHANGE IS HERE: Interval set to 1 minute for near real-time alerts ---
    scheduler.add_job(
        check_transactions_periodically, 
        'interval', 
        minutes=1,
        kwargs={'bot': bot},
        id='failed_tx_alerter' # Assign a unique ID to the job
    )
    logger.info("Failed transaction alerting job has been scheduled to run every 1 minute.")
