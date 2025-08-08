import logging
import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

from src.utils.database import (
    get_user_dca_schedules, 
    update_dca_execution, 
    add_portfolio_asset,
    get_user_settings,
    get_active_dca_schedules
)
from src.services.market_data_api import get_market_data

logger = logging.getLogger(__name__)

class DCAWorker:
    """Worker for processing Dollar Cost Averaging schedules."""
    
    def __init__(self, bot=None):
        self.bot = bot
        self.scheduler = BackgroundScheduler(timezone=timezone('Asia/Jakarta'))
        
    def start(self):
        """Start the DCA scheduler."""
        # Schedule DCA checks every minute
        self.scheduler.add_job(
            func=self._check_and_execute_dca_schedules,
            trigger='interval',
            minutes=1,
            id='dca_checker',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Scheduled DCA checks every minute")
        logger.info("DCA Worker started successfully")
        
    def stop(self):
        """Stop the DCA scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("DCA Worker stopped")
    
    def _check_and_execute_dca_schedules(self):
        """Check for DCA schedules that need to be executed."""
        try:
            # Get all active DCA schedules
            schedules = get_active_dca_schedules()
            
            if schedules:
                # Group schedules by user to get their timezone settings
                user_schedules = {}
                for schedule in schedules:
                    user_id = schedule['user_id']
                    if user_id not in user_schedules:
                        user_schedules[user_id] = {
                            'settings': get_user_settings(user_id),
                            'schedules': []
                        }
                    user_schedules[user_id]['schedules'].append(schedule)
                
                # Process schedules by user timezone
                for user_id, user_data in user_schedules.items():
                    user_settings = user_data['settings']
                    user_timezone = user_settings.get('timezone', 'Asia/Jakarta')
                    
                    # Get current time in user's timezone
                    from pytz import timezone
                    user_tz = timezone(user_timezone)
                    current_time_user = datetime.now(user_tz)
                    current_minute_user = current_time_user.strftime('%H:%M')
                    
                    logger.info(f"DCA Check for User {user_id} at {current_minute_user} ({user_timezone}): Found {len(user_data['schedules'])} schedules")
                    
                    for schedule in user_data['schedules']:
                        if not schedule.get('is_active', True):
                            continue
                            
                        # Check if this schedule should execute now in user's timezone
                        if self._should_execute_now(schedule, current_time_user):
                            logger.info(f"Executing DCA for user {schedule['user_id']}: {schedule['symbol']} at {current_minute_user} {user_timezone}")
                            self._execute_dca_purchase(schedule)
                    
        except Exception as e:
            logger.error(f"Error checking DCA schedules: {e}")
    
    def _should_execute_now(self, schedule, current_time):
        """Check if a DCA schedule should execute at the current time."""
        try:
            schedule_time = schedule['time']  # Format: "HH:MM"
            current_minute = current_time.strftime('%H:%M')
            
            if schedule_time != current_minute:
                return False
            
            frequency = schedule['frequency']
            last_executed = schedule.get('last_executed')
            
            if not last_executed:
                return True  # First execution
            
            last_exec_date = datetime.fromisoformat(last_executed)
            
            if frequency == 'daily':
                return current_time.date() > last_exec_date.date()
            elif frequency == 'weekly':
                days_diff = (current_time - last_exec_date).days
                return days_diff >= 7
            elif frequency == 'monthly':
                # Check if it's been at least 30 days or if we're in a new month
                days_diff = (current_time - last_exec_date).days
                return days_diff >= 30 or current_time.month != last_exec_date.month
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking schedule execution time: {e}")
            return False
    
    def _execute_dca_purchase(self, schedule):
        """Execute a DCA purchase for the given schedule."""
        try:
            logger.info(f"Fetching market data for {schedule['symbol']}")
            
            # Get current market price
            market_data = get_market_data(schedule['symbol'])
            if not market_data:
                logger.warning(f"No market data for {schedule['symbol']} - skipping DCA execution")
                return
            
            current_price_usd = market_data.get('current_price', 0)
            if current_price_usd <= 0:
                logger.warning(f"Invalid price for {schedule['symbol']} - skipping DCA execution")
                return
            
            # Convert amount to USD if needed (main currency system)
            conversion_rates = {'USD': 1.0, 'IDR': 15000.0, 'EUR': 0.85, 'JPY': 110.0}
            schedule_currency = schedule['currency']
            amount_in_schedule_currency = schedule['amount']
            
            # Convert to USD as base currency
            if schedule_currency != 'USD':
                conversion_rate = conversion_rates.get(schedule_currency, 1.0)
                amount_usd = amount_in_schedule_currency / conversion_rate
            else:
                amount_usd = amount_in_schedule_currency
            
            # Calculate quantity to purchase (using USD amounts)
            quantity_to_buy = amount_usd / current_price_usd
            
            # Add to portfolio (simulated purchase) - store in USD as base
            add_portfolio_asset(schedule['user_id'], schedule['symbol'], quantity_to_buy)
            
            # Update DCA execution record - store execution price in USD
            update_dca_execution(
                schedule['dca_id'],
                quantity_to_buy,
                amount_usd,  # Store invested amount in USD
                current_price_usd  # Store price in USD
            )
            
            # Send notification to user if bot is available
            if self.bot:
                try:
                    # Try to get the running event loop
                    loop = asyncio.get_running_loop()
                    asyncio.run_coroutine_threadsafe(
                        self._send_dca_notification(schedule, quantity_to_buy, current_price_usd, amount_in_schedule_currency),
                        loop
                    )
                except RuntimeError:
                    # No running event loop, create a new one in a thread
                    import threading
                    thread = threading.Thread(
                        target=lambda: asyncio.run(
                            self._send_dca_notification(schedule, quantity_to_buy, current_price_usd, amount_in_schedule_currency)
                        )
                    )
                    thread.start()
            
            logger.info(f"DCA executed: {schedule['user_id']} bought {quantity_to_buy:.6f} {schedule['symbol']} at ${current_price_usd:.2f} (Amount: ${amount_usd:.2f} USD / {amount_in_schedule_currency} {schedule_currency})")
            
        except Exception as e:
            logger.error(f"Error executing DCA purchase: {e}")
    
    async def _send_dca_notification(self, schedule, quantity, price, amount):
        """Send DCA execution notification to user."""
        try:
            user_settings = get_user_settings(schedule['user_id'])
            if not user_settings.get('notifications', True):
                return  # User has notifications disabled
            
            # Get user's timezone for proper time display
            user_timezone = user_settings.get('timezone', 'Asia/Jakarta')
            from pytz import timezone
            user_tz = timezone(user_timezone)
            current_time_user = datetime.now(user_tz)
            
            currency_symbols = {
                'USD': '$', 'EUR': '€', 'JPY': '¥', 'IDR': 'Rp',
                'GBP': '£', 'SGD': 'S$', 'AUD': 'A$', 'CAD': 'C$'
            }
            currency_symbol = currency_symbols.get(schedule['currency'], schedule['currency'])
            
            # Convert price to schedule currency if needed
            conversion_rates = {'USD': 1.0, 'IDR': 15000.0, 'EUR': 0.85, 'JPY': 110.0}
            conversion_rate = conversion_rates.get(schedule['currency'], 1.0)
            price_converted = price * conversion_rate
            
            message = (
                f"🎯 <b>DCA Executed!</b>\n\n"
                f"💰 <b>Asset:</b> {schedule['symbol'].upper()}\n"
                f"💵 <b>Amount:</b> {currency_symbol}{amount:,.2f} {schedule['currency']}\n"
                f"📦 <b>Quantity:</b> {quantity:.6f}\n"
                f"💎 <b>Price:</b> {currency_symbol}{price_converted:,.2f}\n"
                f"⏰ <b>Time:</b> {current_time_user.strftime('%Y-%m-%d %H:%M:%S')} {user_timezone}\n"
                f"🔄 <b>Frequency:</b> {schedule['frequency'].title()}\n\n"
                f"✅ Your portfolio has been updated!"
            )
            
            await self.bot.send_message(
                chat_id=schedule['user_id'],
                text=message,
                parse_mode='HTML'
            )
            
            logger.info(f"DCA notification sent to user {schedule['user_id']}")
            
        except Exception as e:
            logger.error(f"Error sending DCA notification: {e}")

# Global DCA worker instance
_dca_worker = None

def start_dca_worker(bot=None):
    """Start the global DCA worker."""
    global _dca_worker
    try:
        if _dca_worker is None:
            _dca_worker = DCAWorker(bot)
            _dca_worker.start()
            logger.info("Global DCA worker started")
        else:
            logger.info("DCA worker already running")
    except Exception as e:
        logger.error(f"Error starting DCA worker: {e}")

def stop_dca_worker():
    """Stop the global DCA worker."""
    global _dca_worker
    try:
        if _dca_worker:
            _dca_worker.stop()
            _dca_worker = None
            logger.info("Global DCA worker stopped")
    except Exception as e:
        logger.error(f"Error stopping DCA worker: {e}")

def get_dca_worker():
    """Get the current DCA worker instance."""
    return _dca_worker