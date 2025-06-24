from aiogram import types

def get_stats_keyboard(address: str, name: str = None) -> types.InlineKeyboardMarkup:
    """
    Creates the inline keyboard for a stats message.
    FIX: Now accepts 'name' argument to prevent TypeError in other files.
    """
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(text="🔄 Refresh", callback_data=f"stats_refresh:{address}"),
        types.InlineKeyboardButton(text="❤️ Check Health", callback_data=f"health_shortcut:{address}")
    )
    keyboard.add(
        types.InlineKeyboardButton(text="📊 Dashboard", url=f"https://dashboard-devnet5.cortensor.network/stats/node/{address}"),
        types.InlineKeyboardButton(text="🌐 Arbiscan", url=f"https://sepolia.arbiscan.io/address/{address}")
    )
    return keyboard

def get_health_keyboard(address: str, name: str = None) -> types.InlineKeyboardMarkup:
    """
    Creates the inline keyboard for a health message.
    FIX: Now accepts 'name' argument to prevent TypeError.
    FIX: Callback for Refresh button is now 'health_refresh' for clarity.
    """
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        # PERUBAHAN: Callback diubah agar logikanya jelas untuk me-refresh pesan
        types.InlineKeyboardButton(text="🔄 Refresh", callback_data=f"health_refresh:{address}"),
        types.InlineKeyboardButton(text="📊 View Stats", callback_data=f"stats_shortcut:{address}")
    )
    keyboard.add(
        types.InlineKeyboardButton(text="📊 Dashboard", url=f"https://dashboard-devnet5.cortensor.network/stats/node/{address}"),
        types.InlineKeyboardButton(text="🌐 Arbiscan", url=f"https://sepolia.arbiscan.io/address/{address}")
    )
    return keyboard
