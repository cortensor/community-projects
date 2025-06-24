from aiogram import types, Dispatcher
from aiogram.utils import markdown as md

# Assuming these modules exist and are correctly imported from your project structure
from .. import database as db
from ..utils import ETH_ADDR_REGEX, shorten_address

# --- HELP MESSAGE (SIMPLIFIED VERSION) ---
HELP_MESSAGE = """
*Cortensor Monitoring Bot* 🤖

*Node Management*
`/register <address> <name>` - Add a new node.
`/unregister <address>` - Remove a node.
`/list` - Show all your registered nodes.

*Monitoring*
`/stats [address]` - Get a detailed statistics report.
`/health [address]` - Check node health status.

*Live Reports*
`/autoupdate <seconds>` - Start auto-updating stats reports.
`/stop` - Stop all live reports.

*Automatic Alerts*
`/auto` - Turn **ON** failed transaction alerts.
`/off` - Turn **OFF** failed transaction alerts.
"""

async def cmd_start_help(message: types.Message) -> None:
    """
    Handles the /start and /help commands by displaying the simplified help message.
    """
    await message.reply(HELP_MESSAGE, parse_mode="Markdown")

async def cmd_register(message: types.Message) -> None:
    """
    Handles the /register command to add a new node address for monitoring.
    """
    args = message.get_args().split(maxsplit=1)
    if len(args) < 2:
        await message.reply("❌ Incorrect format. Use: `/register <address> <custom_name>`")
        return
        
    addr, name = args
    if not ETH_ADDR_REGEX.match(addr):
        await message.reply("❌ Invalid Ethereum address format.")
        return
        
    if db.add_address(message.from_user.id, addr, name):
        await message.reply(
            f"✅ Address for **{md.escape_md(name)}** (`{shorten_address(addr)}`) has been registered/updated.",
            parse_mode="Markdown"
        )
    else:
        await message.reply("Failed to register address due to a database error.")

async def cmd_unregister(message: types.Message) -> None:
    """
    Handles the /unregister command to remove a node address from monitoring.
    """
    addr = message.get_args().strip()
    if not ETH_ADDR_REGEX.match(addr):
        await message.reply("❌ Invalid Ethereum address format.")
        return
        
    if db.remove_address(message.from_user.id, addr):
        await message.reply(f"🗑️ Address `{addr}` has been unregistered.", parse_mode="Markdown")
    else:
        await message.reply(f"Could not unregister `{addr}`. Please ensure it is in your /list and try again.")

async def cmd_list(message: types.Message) -> None:
    """
    Handles the /list command to display all registered addresses for the user.
    """
    addresses = db.get_user_addresses(message.from_user.id)
    if not addresses:
        await message.reply("You have no registered addresses.\nUse `/register <address> <name>` to get started.")
        return
        
    text_lines = ["*Your registered addresses (Oldest to Newest):*\n"]
    for item in addresses:
        text_lines.append(f"• **{md.escape_md(item['name'])}**: `{item['address']}`")
        
    await message.reply("\n".join(text_lines), parse_mode="Markdown")

def register_common_handlers(dp: Dispatcher) -> None:
    """
    Registers all common command handlers for the bot.
    """
    dp.register_message_handler(cmd_start_help, commands=["start", "help"])
    dp.register_message_handler(cmd_register, commands=["register"])
    dp.register_message_handler(cmd_unregister, commands=["unregister"])
    dp.register_message_handler(cmd_list, commands=["list"])
