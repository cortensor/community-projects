import asyncio
import logging
from aiogram import types, Dispatcher
from aiogram.utils.exceptions import MessageToEditNotFound, MessageNotModified, BotBlocked, MessageCantBeDeleted
from aiogram.utils import markdown as md
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .. import database as db
from .. import report_generator
from ..keyboards import get_stats_keyboard

logger = logging.getLogger(__name__)

# This in-memory dictionary tracks active live-update jobs.
active_update_jobs = {}

# --- Live Stats Report Automation (/autoupdate, /stop) ---

async def cmd_autoupdate(message: types.Message):
    """
    Initiates live-updating stats reports. It will first stop and delete
    any old report cards from a previous session.
    """
    args = message.get_args().strip()
    if not args.isdigit() or int(args) < 60:
        return await message.reply("❌ Incorrect format. Use: `/autoupdate <seconds>` (minimum 60).")

    interval = int(args)
    user_id = message.from_user.id
    chat_id = message.chat.id
    scheduler: AsyncIOScheduler = message.bot.get('scheduler')
    session = message.bot.get('session')
    job_id = f"autoupdate_{user_id}"

    # --- NEW: Delete old messages before starting a new session ---
    if user_id in active_update_jobs:
        logger.info(f"Stopping previous autoupdate job for user {user_id} and cleaning up messages.")
        # Stop the scheduled job first
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
        
        # Get the list of old messages to delete
        old_messages_to_delete = active_update_jobs.get(user_id, {}).get('messages', [])
        
        for msg_info in old_messages_to_delete:
            try:
                await message.bot.delete_message(chat_id, msg_info['message_id'])
                await asyncio.sleep(0.1) # Small delay to avoid rate limits on deletion
            except MessageCantBeDeleted:
                logger.warning(f"Could not delete message {msg_info['message_id']}. It might be too old.")
            except Exception as e:
                logger.error(f"Error deleting old message {msg_info['message_id']}: {e}")
        
        # Clean up the old job from memory
        del active_update_jobs[user_id]
    # --- End of new cleanup logic ---
        
    addresses = db.get_user_addresses(user_id)
    if not addresses:
        return await message.reply("You have no registered addresses to update. Use `/register` first.")

    await message.reply(f"✅ Starting live stats updates every {interval}s. Sending new report cards now...")

    # Send initial messages and store their IDs for future edits
    sent_messages = []
    for addr_data in addresses:
        try:
            initial_report = await report_generator.generate_stats_report(session, addr_data['address'], addr_data['name'])
            keyboard = get_stats_keyboard(addr_data['address'], addr_data['name'])
            sent_msg = await message.answer(initial_report, reply_markup=keyboard, parse_mode="Markdown")
            
            sent_messages.append({
                'message_id': sent_msg.message_id, 
                'address': addr_data['address'], 
                'name': addr_data['name']
            })
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Failed to send initial message for {addr_data['address']}: {e}", exc_info=True)
            await message.answer(f"❌ Failed to create initial report for **{md.escape_md(addr_data['name'])}**.", parse_mode="Markdown")

    if not sent_messages:
        return await message.reply("Could not create any live reports. Please check the logs.")

    active_update_jobs[user_id] = {'chat_id': chat_id, 'messages': sent_messages}

    # This inner function is the job that the scheduler will execute
    async def edit_job():
        if user_id not in active_update_jobs:
            logger.warning(f"Job {job_id} running but no active message data found. Removing job.")
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
            return

        user_job_data = active_update_jobs[user_id]
        logger.info(f"Running auto-update job for user {user_id}...")
        
        for msg_info in user_job_data['messages']:
            try:
                new_report = await report_generator.generate_stats_report(session, msg_info['address'], msg_info['name'])
                new_keyboard = get_stats_keyboard(msg_info['address'], msg_info['name'])
                
                await message.bot.edit_message_text(
                    text=new_report,
                    chat_id=user_job_data['chat_id'],
                    message_id=msg_info['message_id'],
                    reply_markup=new_keyboard,
                    parse_mode="Markdown"
                )
            except MessageNotModified:
                logger.debug(f"Skipping update for {msg_info['name']}; content not modified.")
            except (MessageToEditNotFound, BotBlocked) as e:
                logger.warning(f"Message for {msg_info['name']} could not be edited ({type(e).__name__}). It might have been deleted or the bot was blocked.")
            except Exception as e:
                logger.error(f"Failed to edit message for {msg_info['name']}: {e}", exc_info=True)
    
    scheduler.add_job(edit_job, 'interval', seconds=interval, id=job_id, name=f"AutoUpdate for {user_id}")

async def cmd_stop(message: types.Message):
    """Stops the auto-updating stats reports job and deletes the messages."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    job_id = f"autoupdate_{user_id}"
    scheduler: AsyncIOScheduler = message.bot.get('scheduler')
    
    if scheduler.get_job(job_id) or user_id in active_update_jobs:
        # Same cleanup logic as in /autoupdate
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
        
        if user_id in active_update_jobs:
            old_messages_to_delete = active_update_jobs[user_id].get('messages', [])
            for msg_info in old_messages_to_delete:
                try:
                    await message.bot.delete_message(chat_id, msg_info['message_id'])
                    await asyncio.sleep(0.1)
                except Exception:
                    pass # Ignore errors if message is already gone
            del active_update_jobs[user_id]
            
        await message.reply("✅ Auto-updating stats messages have been stopped and cleaned up.")
    else:
        await message.reply("ℹ️ No auto-update job is currently running.")


# --- Automatic Transaction Alert Control (/auto, /off) ---

async def cmd_auto(message: types.Message):
    """Enables automatic failed transaction alerts."""
    user_id = message.from_user.id
    db.set_alert_status(user_id, True)
    await message.reply("✅ Automatic transaction alerts have been **enabled**.")

async def cmd_off(message: types.Message):
    """Disables automatic failed transaction alerts."""
    user_id = message.from_user.id
    db.set_alert_status(user_id, False)
    await message.reply("❌ Automatic transaction alerts have been **disabled**.")


# --- Handler Registration ---

def register_automation_handlers(dp: Dispatcher):
    """Registers all automation-related command handlers."""
    dp.register_message_handler(cmd_autoupdate, commands=["autoupdate"])
    dp.register_message_handler(cmd_stop, commands=["stop"])
    dp.register_message_handler(cmd_auto, commands=['auto'])
    dp.register_message_handler(cmd_off, commands=['off'])
