import asyncio
import logging
from typing import Dict, List
from aiogram import types, Dispatcher
from aiogram.utils.exceptions import MessageNotModified, BotBlocked, MessageCantBeDeleted
from aiogram.utils import markdown as md
from datetime import datetime, timezone

# Adjust imports to match your project structure
from .. import utils, health_checker, database as db, report_generator, keyboards, config, arbiscan_checker

logger = logging.getLogger(__name__)

# --- State Dictionaries for Cleanup Logic ---
# These will store the message IDs of the last reports sent for each command
last_stats_messages: Dict[int, List[int]] = {}
last_health_messages: Dict[int, List[int]] = {}


async def get_name_for_address(user_id: int, address: str) -> str:
    """Helper to find a custom name for an address, falling back to a shortened version."""
    user_addresses = db.get_user_addresses(user_id)
    return next((item['name'] for item in user_addresses if item['address'].lower() == address.lower()), utils.shorten_address(address))

# --- Callback Handlers ---

async def handle_stats_refresh(cb: types.CallbackQuery):
    """Handles the 'Refresh' button click on a stats card."""
    await cb.answer(text="Refreshing data...")
    try:
        addr = cb.data.split(':', 1)[1]
        name = await get_name_for_address(cb.from_user.id, addr)
        
        session = cb.bot.get('session')
        new_report_text = await report_generator.generate_stats_report(session, addr, name)
        new_keyboard = keyboards.get_stats_keyboard(addr, name)
        
        await cb.message.edit_text(new_report_text, reply_markup=new_keyboard, parse_mode="Markdown")
            
    except MessageNotModified:
        await cb.answer("Data is already up to date.", show_alert=False)
    except Exception as e:
        logger.error(f"Error refreshing stats: {e}", exc_info=True)
        await cb.answer("Error refreshing data.", show_alert=True)

async def handle_health_refresh(cb: types.CallbackQuery):
    """Handles the 'Refresh' button on a health card by EDITING the message."""
    await cb.answer(text="Refreshing health data...")
    addr = None
    try:
        addr = cb.data.split(':', 1)[1]
        name = await get_name_for_address(cb.from_user.id, addr)
        addr_data = {'address': addr, 'name': name}
        
        session = cb.bot.get('session')
        health_data = await health_checker.get_health_data(session, addr)
        
        response_text = report_generator.format_health_report(addr_data, health_data)
        last_updated = datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M:%S %Z')
        final_text = f"{response_text}\n\n_Last updated: {last_updated}_"

        keyboard = keyboards.get_health_keyboard(addr, name)
        
        await cb.message.edit_text(
            final_text, 
            reply_markup=keyboard, 
            parse_mode="Markdown", 
            disable_web_page_preview=True
        )

    except MessageNotModified:
        await cb.answer("Data is already up to date.", show_alert=False)
    except Exception as e:
        error_addr_text = f" for address {addr}" if addr else ""
        logger.error(f"Error in health refresh{error_addr_text}: {e}", exc_info=True)
        await cb.answer("Error refreshing health data.", show_alert=True)
        
async def handle_health_shortcut(cb: types.CallbackQuery):
    """Handles the 'Check Health' button on a stats card by SENDING a new message."""
    await cb.answer() 
    addr = None
    try:
        addr = cb.data.split(':', 1)[1]
        name = await get_name_for_address(cb.from_user.id, addr)
        addr_data = {'address': addr, 'name': name}
        
        status_msg = await cb.message.answer(f"🔍 Checking health for **{md.escape_md(name)}**...")
        session = cb.bot.get('session')
        health_data = await health_checker.get_health_data(session, addr)
        
        response_text = report_generator.format_health_report(addr_data, health_data)
        last_updated = datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M:%S %Z')
        final_text = f"{response_text}\n\n_Last updated: {last_updated}_"

        keyboard = keyboards.get_health_keyboard(addr, name)
        
        await cb.message.answer(final_text, reply_markup=keyboard, parse_mode="Markdown", disable_web_page_preview=True)
        await status_msg.delete()
        
    except Exception as e:
        error_addr_text = f" for address {addr}" if addr else ""
        logger.error(f"Error in health shortcut{error_addr_text}: {e}", exc_info=True)
        await cb.message.answer("Sorry, an error occurred while processing the health check.")

async def handle_stats_shortcut(cb: types.CallbackQuery):
    """Handles the 'View Stats' button click on a health card."""
    await cb.answer()
    addr, name = None, None
    try:
        addr = cb.data.split(':', 1)[1]
        name = await get_name_for_address(cb.from_user.id, addr)
        
        status_msg = await cb.message.answer(f"🔍 Fetching stats for **{md.escape_md(name)}**...")
        session = cb.bot.get('session')
        report_text = await report_generator.generate_stats_report(session, addr, name)
        keyboard = keyboards.get_stats_keyboard(addr, name)

        await cb.message.answer(report_text, reply_markup=keyboard, parse_mode="Markdown")
        await status_msg.delete()

    except Exception as e:
        error_addr_text = f" for address {addr}" if addr else ""
        logger.error(f"Error in stats shortcut{error_addr_text}: {e}", exc_info=True)
        await cb.message.answer("Sorry, an error occurred while processing stats.")


# --- Command Handlers ---

async def cmd_stats(msg: types.Message):
    """
    Handler for /stats. Cleans up previous /stats messages before sending new ones.
    """
    user_id = msg.from_user.id
    chat_id = msg.chat.id

    # --- NEW: Cleanup logic for previous messages ---
    if user_id in last_stats_messages:
        for message_id in last_stats_messages[user_id]:
            try:
                await msg.bot.delete_message(chat_id, message_id)
            except (MessageCantBeDeleted, MessageToEditNotFound):
                pass # Ignore if message is already gone
        del last_stats_messages[user_id]
    # --- End of cleanup logic ---

    args = msg.get_args().strip().lower()
    session = msg.bot.get('session')
    sent_message_ids = []

    async def process_and_send(addr_data: Dict, initial_message: types.Message = None):
        report_text = await report_generator.generate_stats_report(session, addr_data['address'], addr_data['name'])
        keyboard = keyboards.get_stats_keyboard(addr_data['address'], addr_data['name'])
        
        target_message = initial_message if initial_message else msg
        sent_msg = await target_message.answer(report_text, reply_markup=keyboard, parse_mode="Markdown")
        sent_message_ids.append(sent_msg.message_id) # Store message ID

    if args:
        if not utils.ETH_ADDR_REGEX.match(args): return await msg.reply("❌ Invalid Ethereum address format.")
        addr_data = {"address": args, "name": utils.shorten_address(args)}
        status_msg = await msg.reply(f"🔍 Fetching stats for `{utils.shorten_address(args)}`...")
        await process_and_send(addr_data)
        await status_msg.delete()
    else:
        registered_addrs = db.get_user_addresses(user_id)
        if not registered_addrs: return await msg.reply("You have no registered addresses.")
        
        status_msg = await msg.reply(f"Processing stats for your {len(registered_addrs)} registered address(es)...")
        for addr_data in registered_addrs:
            await process_and_send(addr_data)
            await asyncio.sleep(1.2)
        await status_msg.delete()
        
    # --- NEW: Save the new message IDs ---
    if sent_message_ids:
        last_stats_messages[user_id] = sent_message_ids


async def cmd_health(message: types.Message):
    """
    Handler for /health. Cleans up previous /health messages before sending new ones.
    """
    user_id = message.from_user.id
    chat_id = message.chat.id

    # --- NEW: Cleanup logic for previous messages ---
    if user_id in last_health_messages:
        for message_id in last_health_messages[user_id]:
            try:
                await message.bot.delete_message(chat_id, message_id)
            except (MessageCantBeDeleted, MessageToEditNotFound):
                pass
        del last_health_messages[user_id]
    # --- End of cleanup logic ---
    
    args = message.get_args().strip().lower()
    session = message.bot.get('session')
    sent_message_ids = []

    async def process_health_check(addr_data):
        health_data = await health_checker.get_health_data(session, addr_data['address'])
        response_text = report_generator.format_health_report(addr_data, health_data)
        
        last_updated = datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M:%S %Z')
        final_text = f"{response_text}\n\n_Last updated: {last_updated}_"
        
        keyboard = keyboards.get_health_keyboard(addr_data['address'], addr_data['name']) 
        
        sent_msg = await message.answer(final_text, reply_markup=keyboard, parse_mode="Markdown", disable_web_page_preview=True)
        sent_message_ids.append(sent_msg.message_id) # Store message ID

    if args:
        if not utils.ETH_ADDR_REGEX.match(args): return await message.reply("❌ Invalid Ethereum address format.")
        addr_data = {"address": args, "name": utils.shorten_address(args)}
        status_msg = await message.reply("🔍 Checking health, please wait...")
        await process_health_check(addr_data)
        await status_msg.delete()
    else:
        registered_addrs = db.get_user_addresses(user_id)
        if not registered_addrs: return await message.reply("You have no registered addresses.")

        status_msg = await message.reply(f"Checking health for your {len(registered_addrs)} registered address(es)...")
        for addr_data in registered_addrs:
            await process_health_check(addr_data)
            await asyncio.sleep(1.5)
        await status_msg.delete()

    # --- NEW: Save the new message IDs ---
    if sent_message_ids:
        last_health_messages[user_id] = sent_message_ids


def register_monitoring_handlers(dp: Dispatcher):
    """Registers all monitoring-related handlers."""
    dp.register_message_handler(cmd_stats, commands=["stats"])
    dp.register_message_handler(cmd_health, commands=["health"])

    dp.register_callback_query_handler(handle_stats_refresh, lambda c: c.data.startswith('stats_refresh:'))
    dp.register_callback_query_handler(handle_health_refresh, lambda c: c.data.startswith('health_refresh:'))
    dp.register_callback_query_handler(handle_health_shortcut, lambda c: c.data.startswith('health_shortcut:'))
    dp.register_callback_query_handler(handle_stats_shortcut, lambda c: c.data.startswith('stats_shortcut:'))
