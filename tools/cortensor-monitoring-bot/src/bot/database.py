# bot/database.py

import sqlite3
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)
DB_FILE = "bot_main.db"

def setup_database() -> None:
    """
    Initializes the database and creates all necessary tables if they do not exist.
    This function is intended to be called once at bot startup.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            # Table for registered user addresses (miners)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS miners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    address TEXT NOT NULL,
                    name TEXT,
                    UNIQUE(user_id, address)
                )
            """)
            # Table to store hashes of transactions for which alerts have been sent
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notified_transactions (
                    tx_hash TEXT PRIMARY KEY
                )
            """)
            # Table to store user-specific settings, like alert preferences
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    alerts_enabled INTEGER NOT NULL DEFAULT 1
                )
            """)
            logger.info("Main database and tables have been verified.")
    except sqlite3.Error as e:
        logger.error(f"Database setup error: {e}", exc_info=True)
        raise

def add_address(user_id: int, address: str, name: str) -> bool:
    """
    Adds a new address or updates the name of an existing one for a user.
    This performs an 'upsert' operation.

    :param user_id: The user's Telegram ID.
    :param address: The Ethereum address to register.
    :param name: The custom name for the address.
    :return: True if successful, False otherwise.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            # Using INSERT OR REPLACE on a UNIQUE constraint simplifies the upsert logic.
            # First, we need to handle the case where the address is registered but the name changes.
            # Since the unique key is (user_id, address), a direct upsert is complex if we keep the ID.
            # A simpler, clear logic is to delete and re-insert or update based on existence.
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO miners (user_id, address, name) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id, address) DO UPDATE SET name=excluded.name",
                (user_id, address.lower(), name)
            )
            return True
    except sqlite3.Error as e:
        logger.error(f"Failed to add or update address {address} for user {user_id}: {e}", exc_info=True)
        return False

def remove_address(user_id: int, address: str) -> bool:
    """
    Removes a registered address for a user.

    :param user_id: The user's Telegram ID.
    :param address: The Ethereum address to unregister.
    :return: True if an address was removed, False otherwise.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM miners WHERE user_id=? AND address=?", (user_id, address.lower()))
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Failed to remove address {address} for user {user_id}: {e}", exc_info=True)
        return False

def get_user_addresses(user_id: int) -> List[Dict]:
    """
    Retrieves all registered addresses for a specific user.

    :param user_id: The user's Telegram ID.
    :return: A list of dictionaries, each containing an 'address' and 'name'.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT address, name FROM miners WHERE user_id=? ORDER BY id ASC", (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Failed to get addresses for user {user_id}: {e}", exc_info=True)
        return []

def add_notified_tx(tx_hash: str) -> None:
    """
    Adds a transaction hash to the database to prevent duplicate alerts.

    :param tx_hash: The transaction hash to record.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("INSERT OR IGNORE INTO notified_transactions (tx_hash) VALUES (?)", (tx_hash,))
    except sqlite3.Error as e:
        logger.error(f"Failed to add notified tx {tx_hash}: {e}", exc_info=True)

def is_tx_notified(tx_hash: str) -> bool:
    """
    Checks if an alert for a given transaction hash has already been sent.

    :param tx_hash: The transaction hash to check.
    :return: True if already notified, False otherwise.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM notified_transactions WHERE tx_hash = ?", (tx_hash,))
            return cursor.fetchone() is not None
    except sqlite3.Error as e:
        logger.error(f"Failed to check notified tx {tx_hash}: {e}", exc_info=True)
        return False

def get_all_registered_addresses() -> Dict[int, List[Dict]]:
    """
    Retrieves all addresses for all users, grouped by user_id for scheduled tasks.

    :return: A dictionary mapping user_ids to lists of their registered addresses.
    """
    users_data: Dict[int, List[Dict]] = {}
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, address, name FROM miners ORDER BY user_id")
            for row in cursor.fetchall():
                user_id = row['user_id']
                if user_id not in users_data:
                    users_data[user_id] = []
                users_data[user_id].append({'address': row['address'], 'name': row['name']})
    except sqlite3.Error as e:
        logger.error(f"Failed to get all registered addresses: {e}", exc_info=True)
    return users_data

def set_alert_status(user_id: int, status: bool) -> None:
    """
    Sets the automatic alert preference for a user (True for ON, False for OFF).

    :param user_id: The user's Telegram ID.
    :param status: The desired boolean status for alerts.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            # Use INSERT OR REPLACE to simplify the upsert logic
            conn.execute(
                "INSERT OR REPLACE INTO user_settings (user_id, alerts_enabled) VALUES (?, ?)",
                (user_id, int(status))
            )
    except sqlite3.Error as e:
        logger.error(f"Failed to set alert status for user {user_id}: {e}", exc_info=True)

def get_alert_status(user_id: int) -> bool:
    """
    Gets the automatic alert preference for a user. Defaults to ON (True).

    :param user_id: The user's Telegram ID.
    :return: True if alerts are enabled, False otherwise.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT alerts_enabled FROM user_settings WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            # If user has no setting, default to enabled (True)
            if result is None:
                return True
            return bool(result[0])
    except sqlite3.Error as e:
        logger.error(f"Failed to get alert status for user {user_id}: {e}", exc_info=True)
        # Default to True in case of a database error to be safe
        return True
