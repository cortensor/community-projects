import logging.handlers
from typing import cast
from itertools import batched
import requests
from datetime import datetime, timezone, timedelta
import time
import sqlite3
import logging
from humanize.time import naturaltime
import re

import asyncio
from aiohttp_retry import ExponentialRetry
from asyncio_throttle import Throttler
from aioetherscan import Client
from aioetherscan.exceptions import EtherscanClientApiError

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    ConversationHandler,
    CallbackQueryHandler,
    filters,
)


from NodeData import NodeData, NODE_STATUS
from MetricScraper import MetricScraper
from Metric import Metric
from ChatConfig import ChatConfig, PERFORMANCE_STYLE
from BotConfig import BotConfig

import rank_score_calculator
from collections import Counter, defaultdict
import telegram

from session_data import SessionData
from contract_reader import ContractReader


BOT_CONFIG = BotConfig()

CONTRACT_READER = ContractReader(BOT_CONFIG.RPC_ARB_SEPOLIA, BOT_CONFIG.CONTRACT_COR_COGNETIVE)

BOT_DB_CONNECTION: sqlite3.Connection = None
BOT_DB_CURSOR = sqlite3.Cursor = None  # = DB_CONNECTION.cursor()
BOT_APP = (
    ApplicationBuilder().token(BOT_CONFIG.TELEGRAM_BOT_TOKEN).build()
)  # TELEGRAM_BOT_TOKEN

ETH_API_CLIENT = None
METRIC_SCRAPER = None

MAX_MSG_LENGTH = 10000
# holds a mapping for chat id to active (means latest) message id (for status/overview msg) or none_DEL
# must message id must be cleared if bot conversation is held or failed tx are sent. And updated if a new message was sent and no edit was done
CHAT_ID_MESSAGE_IDS: dict[str, list[int]] = dict()
CHAT_ID_SESSION_MESSAGE_ID: dict[str, int] = dict()
NODES = dict()
NODES_METRICS = dict()
NEW_ETH_BALANCES = dict()

METHOD_TO_FUCNTION = {
    "0x65c815a5": "Commit",
    "0xf21a494b": "Precommit",
    "0xca6726d9": "Prepare"
}

LAST_SESSION_DATA: SessionData = None


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        # logging.FileHandler("conomo_bot.log"),
        logging.handlers.RotatingFileHandler('./logs/conomo_bot.log', maxBytes=100000, backupCount=10),
        logging.StreamHandler()],
)
logger = logging.getLogger("CoNoMo_Bot")

# dont show telgram bot get requests
logging.getLogger("httpx").setLevel(logging.WARNING)


def boostrap_db():
    # Database for telegram bot
    with sqlite3.connect(BOT_CONFIG.BOT_DB_FILE) as con:
        cur = con.cursor()
        try:
            cur.execute(
                """CREATE TABLE IF NOT EXISTS chat_node(
                chat_id INTEGER, 
                node_address TEXT,
                node_label TEXT,
                PRIMARY KEY (chat_id, node_address)
                )"""
            )
            con.commit()
            

            cur.execute(
                """CREATE TABLE IF NOT EXISTS chat(
                chat_id INTEGER PRIMARY KEY,
                notification_node_status BOOLEAN DEFAULT 1,
                notification_failed_tx BOOLEAN DEFAULT 1,
                metrics_warning_threshold INTEGER DEFAULT -1, 
                metrics_drop_threshold INTEGER DEFAULT -1, 
                active BOOLEAN DEFAULT 1,
                bonus_roles INTEGER DEFAULT 0, 
                new_nodes INTEGER DEFAULT 0 , 
                performance_style INTEGER DEFAULT 0 
                )"""
            )
            con.commit()

        finally:
            cur.close()


def remove_message_ids(chat_id):
    global CHAT_ID_MESSAGE_IDS
    CHAT_ID_MESSAGE_IDS.pop(chat_id, None)


def truncate_address(s, max_length=15):
    if len(s) <= max_length:
        return s
    half_length = (max_length - 3) // 2  # Account for "..."
    return s[:half_length] + "..." + s[-half_length:]


# Authentication decorator
def bot_user_authorized(fn):
    """Decorator: checks if user authorized or fails"""

    def wrapper(*args, **kwargs):
        # Expects that Update object is always the first arg
        update: Update = args[0]
        chat_id = update.effective_user.id

        # Ignore requests from unauthorized users
        # if update.effective_user.name not in AUTHORIZED_USERS:
        # TODO: Fix return type if unauthed
        if (
            True
            or chat_id in BOT_CONFIG.AUTHORIZED_ADMIN_IDS
            or is_whitelisted(chat_id)
        ):
            return fn(*args, chat_id, **kwargs)
        else:
            return unauthorized(*args, chat_id)

    return wrapper


def bot_admin_authorized(fn):
    """Decorator: checks if admin authorized or fails"""

    def wrapper(*args, **kwargs):
        # Expects that Update object is always the first arg
        update: Update = args[0]
        chat_id = update.effective_user.id

        # Ignore requests from unauthorized users
        # if update.effective_user.name not in AUTHORIZED_USERS:
        # TODO: Fix return type if unauthed
        if chat_id in BOT_CONFIG.AUTHORIZED_ADMIN_IDS:
            return fn(*args, chat_id, **kwargs)
        else:
            return unauthorized(*args, chat_id)

    return wrapper


def track_node(chat_id, node_address, node_label):
    # cur = DB_CONNECTION.cursor()

    res = BOT_DB_CURSOR.execute(
        "SELECT node_address FROM chat_node WHERE chat_id = ? and node_address = ? ",
        (chat_id, node_address)
    )

    if res.fetchone():
        # User chat/combination already exists
        # print('Node already tracked!')
        logger.info(
            f'Node "{node_address}" for chat_id "{chat_id}" already registered!'
        )
        return False

    BOT_DB_CURSOR.execute(
        "INSERT OR IGNORE INTO chat_node (chat_id, node_address, node_label) VALUES (?, ?, ?)",
        (chat_id, node_address.lower(), node_label),
    )
    BOT_DB_CURSOR.connection.commit()

    # print('Node registered for tracking!')
    logger.info(
        f'Node "{node_address}" for chat_id "{chat_id}" successfully registered!'
    )

    return True


def untrack_node(chat_id, node_address):
    # cur = DB_CONNECTION.cursor()

    if not get_chat_to_node(chat_id, False, node_address):
        # chat/node combination not existing
        logger.info(f'Node "{node_address}" for chat_id "{chat_id}" not subscribed!')
        return False

    BOT_DB_CURSOR.execute(
        "DELETE FROM chat_node WHERE chat_id = ? and node_address = ?",
        (chat_id, node_address),
    )
    BOT_DB_CURSOR.connection.commit()

    logger.info(
        f'Node "{node_address}" for chat_id "{chat_id}" successfully unsubscribed!'
    )
    return True


def get_chat_to_node(chat_id=None, only_active: bool = False, adr=None):
    sql = "SELECT chat_node.chat_id, chat_node.node_address, coalesce(chat_node.node_label, chat_node.node_address) AS node_label FROM chat_node LEFT JOIN chat ON chat_node.chat_id = chat.chat_id "

    params = ()
    if chat_id:
        sql += "WHERE chat_node.chat_id = ? "
        params = (chat_id,)
    if adr:
        sql += "AND chat_node.node_address = ? "
        params = (chat_id, adr)
    if only_active:
        sql += f"{' AND' if chat_id else ' WHERE'} (chat.active = 1 OR chat.active IS NULL) "
        # params += (1,)

    sql += "ORDER BY chat_node.chat_id, coalesce(chat_node.node_label, chat_node.node_address)"

    res = BOT_DB_CURSOR.execute(sql, params)

    return res.fetchall()


def delete_chat(chat_id):
    logger.info(
        f'Deleting data for chat_id "{chat_id}"'
    )

    BOT_DB_CURSOR.execute(
        "DELETE FROM chat_node WHERE chat_id = ?",
        (chat_id,),
    )
    BOT_DB_CURSOR.connection.commit()

    logger.info(
        f'Deleted chat_node data for chat_id "{chat_id}"'
    )

    BOT_DB_CURSOR.execute(
        "DELETE FROM chat WHERE chat_id = ?",
        (chat_id,),
    )
    BOT_DB_CURSOR.connection.commit()

    logger.info(
        f'Deleted chat data for chat_id "{chat_id}"'
    )


def is_whitelisted(user_id):
    sql = "SELECT chat_id FROM whitelist WHERE chat_id = ?"

    res = BOT_DB_CURSOR.execute(sql, (user_id,))

    return res.fetchone() is not None


def get_chat_config(chat_id) -> ChatConfig:
    sql = "SELECT notification_node_status, notification_failed_tx, metrics_warning_threshold, metrics_drop_threshold, active, bonus_roles, new_nodes, performance_style FROM chat WHERE chat_id = ?"
    res = BOT_DB_CURSOR.execute(sql, (chat_id,))

    row = res.fetchone()
    if row:
        chat_config = ChatConfig(
            chat_id=chat_id,
            notification_node_status=row[0] == 1,
            notification_failed_tx=row[1] == 1,
            metrics_warning_threshold=row[2],
            metrics_drop_threshold=row[3],
            active=row[4] == 1,
            bonus_roles=row[5],
            new_nodes=row[6],
            performance_style=PERFORMANCE_STYLE(row[7]),
        )
        return chat_config
    else:
        return ChatConfig(chat_id=chat_id)


def update_chat_config(chat_config: ChatConfig):
    sql = """INSERT INTO chat (chat_id, notification_node_status, notification_failed_tx, metrics_warning_threshold, metrics_drop_threshold, active, bonus_roles, new_nodes, performance_style) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) 
        ON CONFLICT(chat_id) DO UPDATE SET 
        notification_node_status=?,
        notification_failed_tx=?,
        metrics_warning_threshold=?,
        metrics_drop_threshold=?,
        active=?,
        bonus_roles=?,
        new_nodes=?,
        performance_style=?
        WHERE chat_id = ? """

    BOT_DB_CURSOR.execute(
        sql,
        (
            # Insert
            chat_config.chat_id,
            int(chat_config.notification_node_status),
            int(chat_config.notification_failed_tx),
            int(chat_config.metrics_warning_threshold),
            int(chat_config.metrics_drop_threshold),
            int(chat_config.active),
            int(chat_config.bonus_roles),
            int(chat_config.new_nodes),
            int(chat_config.performance_style.value),
            # Update
            int(chat_config.notification_node_status),
            int(chat_config.notification_failed_tx),
            int(chat_config.metrics_warning_threshold),
            int(chat_config.metrics_drop_threshold),
            int(chat_config.active),
            int(chat_config.bonus_roles),
            int(chat_config.new_nodes),
            int(chat_config.performance_style.value),
            # Where
            chat_config.chat_id,
        ),
    )
    BOT_DB_CURSOR.connection.commit()

    return BOT_DB_CURSOR.rowcount == 1


def update_node_label(chat_id, node_address, node_label):
    sql = """UPDATE chat_node
        SET node_label = ?
        WHERE chat_id = ? and node_address = ?"""

    BOT_DB_CURSOR.execute(
        sql,
        (
            # Update
            node_label,
            # Where
            chat_id,
            node_address
        ),
    )
    BOT_DB_CURSOR.connection.commit()

    return BOT_DB_CURSOR.rowcount == 1


def get_eth_balance(node_address):
    return NEW_ETH_BALANCES.setdefault(node_address, 0)


async def update_new_eth_balances(node_addresses: list[str]):
    global NEW_ETH_BALANCES
    NEW_ETH_BALANCES.clear()

    # OLD LOGIC using Etherscan API
    # for batch in batched(node_addresses, 20):
    #     try:
    #         # TODO: etherscan v2 update not wroking for balance
    #         balances = await ETH_API_CLIENT.account.balances(batch)

    #         for balance in balances:
    #             NEW_ETH_BALANCES[balance["account"]] = int(balance["balance"]) / (
    #                 10**18
    #             )
    #     except Exception:
    #         logger.exception(f"Error retrieving eth balalances for {batch}")

    for address in node_addresses:
        NEW_ETH_BALANCES[address] = CONTRACT_READER.get_eth_balance(address)



def filter_cor_txs(txs):
    # TODO: improve cortensor tx detection
    return [tx for tx in txs if tx["methodId"] != "0x"]


async def get_latest_txs(node_address, latest_known_block=0):
    try:
        txs = await ETH_API_CLIENT.account.normal_txs(
            address=node_address,
            sort="desc",
            page=1,
            offset=25,
            start_block=str(latest_known_block),
        )
        return txs
    except EtherscanClientApiError as e:
        if e.message != "No transactions found":
            logger.exception("No transactions found")
        return []
    except Exception:
        logger.exception(f'Failed to retrieve latest txs for "{node_address}"')
    return []


async def set_new_node_status(node_data: NodeData, new_status: NODE_STATUS):
    # first compare with old state
    node_data.notify = node_data.notify or (node_data.status != new_status)
    node_data.status = new_status


async def update_consecutive_pings(node_data: NodeData, txs: list = []):
    for tx in txs:
        if tx["functionName"] != "ping()":
            node_data.consecutive_pings = 0
            break
        else:
            node_data.consecutive_pings += 1


async def update_node_status(node_data: NodeData, tx_timestamp, txs: list = []):
    if not tx_timestamp:
        # no tx == offline
        # first compare with old state
        await set_new_node_status(node_data, NODE_STATUS.OFFLINE)
        return

    # check node stall
    await update_consecutive_pings(node_data, txs)

    # tx_timestamp = int(timestamp["timeStamp"])
    # currentUTC = datetime.now(timezone.utc)
    currentUTC = node_data.updated_at

    if tx_timestamp + BOT_CONFIG.ALIVE_THRESHOLD_SEC < int(currentUTC.timestamp()):
        timestampUTC = datetime.fromtimestamp(tx_timestamp, timezone.utc)
        logger.info(
            f'Node "{node_data.address}" offline! Node has no transaction since: {timestampUTC} (current: {currentUTC})'
        )
        # await BOT_APP.bot.send_message(chat_id, msg)
        await set_new_node_status(node_data, NODE_STATUS.OFFLINE)
    else:
        # set notify for node stall -> warning on stall
        status = (
            NODE_STATUS.ONLINE
            if node_data.consecutive_pings < BOT_CONFIG.NODE_STALL_THRESHOLD
            else NODE_STATUS.STALL
        )
        await set_new_node_status(node_data, status)


def create_health_history(node_data: NodeData):
    TIME_DELTA_MIN = 30  # 10
    start_from = node_data.updated_at

    start_time = start_from.replace(
        second=0,
        microsecond=0,
        minute=(start_from.minute // TIME_DELTA_MIN) * TIME_DELTA_MIN,
    )
    end_time = start_time + timedelta(minutes=TIME_DELTA_MIN)

    new_history = ""
    oldest_ts = node_data.timestamps[-1] if node_data.timestamps else None
    latest_ts = node_data.timestamps[0] if node_data.timestamps else None
    
    alive_threshold_min = BOT_CONFIG.ALIVE_THRESHOLD_SEC // 60

    steps = 16  # 48
    for i in range(steps):
        end_time = start_time + timedelta(minutes=TIME_DELTA_MIN)

        if i == 0:
            first_end_time = end_time

        all_ts_in_timeframe = [
            ts
            for ts in node_data.timestamps
            if start_time.timestamp() <= ts < end_time.timestamp()
        ]
        found_count = len(all_ts_in_timeframe)

        if i == 0:
            effective_end_time = start_from.replace(
                second=0,
                microsecond=0,
                minute=(start_from.minute // alive_threshold_min) * alive_threshold_min,
            ) 
        else:
            effective_end_time = end_time
        all_consecutive_found = check_intervals(
            all_ts_in_timeframe, start_time.timestamp(), effective_end_time.timestamp()
        )

        last_iteration = (
            oldest_ts and end_time.timestamp() - TIME_DELTA_MIN * 60 <= oldest_ts
        ) or (
            node_data.history_end_ts
            and end_time.timestamp() - TIME_DELTA_MIN * 60 <= node_data.history_end_ts
        )

        if found_count == 0 and i == 0:
            new_history += "⬜"
        elif (
            found_count == 0
            and (oldest_ts and end_time.timestamp() <= oldest_ts)
            or (
                node_data.history_end_ts
                and end_time.timestamp() <= node_data.history_end_ts
            )
        ):
            break
        else:
            if i == 0:
                latest_found = (
                    latest_ts
                    and latest_ts
                    >= start_from.timestamp() - BOT_CONFIG.ALIVE_THRESHOLD_SEC
                )
            else:
                latest_found = (
                    latest_ts
                    and latest_ts
                    >= end_time.timestamp() - BOT_CONFIG.ALIVE_THRESHOLD_SEC
                )

            if latest_found and (
                all_consecutive_found or (not all_consecutive_found and last_iteration)
            ):
                new_history += "🟩"
            elif found_count > 0 and (not latest_found or not all_consecutive_found):
                new_history += "🟨"
            elif not latest_found or found_count == 0:
                new_history += "🟥"
        start_time -= timedelta(minutes=TIME_DELTA_MIN)  # Move backwards in time

    # TODO: Just a dirty fix to repalce warning with online if first run and there maybe only one ts for the last block
    if (
        not node_data.history
        and new_history
        and len(new_history) > 2
        and new_history[-1] == "🟨"
    ):
        new_history = new_history[:-1] + "🟩"

    history = (new_history + node_data.history)[:steps]
    node_data.history = history[1:]

    if len(new_history) > 1:
        cut_time = start_time + timedelta(minutes=TIME_DELTA_MIN * len(new_history))

        node_data.timestamps = [
            ts for ts in node_data.timestamps if ts >= cut_time.timestamp()
        ]

        node_data.history_end_ts = cut_time.timestamp()
    last_start_time = first_end_time - timedelta(minutes=TIME_DELTA_MIN) * (
        # len(new_history) # TODO: -1?
        len(history)  # TODO: -1?
    )

    return (
        first_end_time.strftime("%H:%M"),
        last_start_time.strftime("%H:%M"),
        "".join(history),
    )


def check_intervals(timestamps, start_time, end_time):
    # start_time = 1708123200  # 12:00:00 Unix timestamp
    # end_time = 1708123440    # 12:04:00 Unix timestamp

    expected_time = (
        end_time - BOT_CONFIG.ALIVE_THRESHOLD_SEC
    )  # Start checking from 12:03:30
    index = 0
    n = len(timestamps)

    while expected_time >= start_time:
        # Ensure at least one timestamp exists in the current 30-sec interval
        found = False
        while index < n and timestamps[index] >= expected_time:
            if timestamps[index] < expected_time + BOT_CONFIG.ALIVE_THRESHOLD_SEC:
                found = True  # A valid timestamp is found in this window
                break
            index += 1

        if not found:
            return False  # Missing a required 30-second interval

        expected_time -= (
            BOT_CONFIG.ALIVE_THRESHOLD_SEC
        )  # Move to the previous 30-sec interval

    return True  # All required intervals are covered


async def get_latest_node_data(node_address) -> NodeData:
    logger.info(f'Checking node="{node_address}"')

    # block_number_db, balance_warning_db = get_db_node_data(node_address)
    # nd = NodeData(address=node_address)
    node_data = cast(
        NodeData, NODES.setdefault(node_address, NodeData(address=node_address))
    )
    # node_data.last_block_ts = 0
    node_data.notify = False
    node_data.failed_txs = []

    try:
        # Warn if eth balance is below BALANCE_WARNING
        new_balance = get_eth_balance(node_address)
        # new_balance_warning = WARNING_STATUS.WARN if node_data.balance < BALANCE_WARNING_THRESHOLD else WARNING_STATUS.NO_WARNING
        node_data.notify = (
            new_balance >= BOT_CONFIG.BALANCE_WARNING_THRESHOLD
            and node_data.balance < BOT_CONFIG.BALANCE_WARNING_THRESHOLD
        ) or (
            new_balance < BOT_CONFIG.BALANCE_WARNING_THRESHOLD
            and node_data.balance >= BOT_CONFIG.BALANCE_WARNING_THRESHOLD
        )
        node_data.balance = new_balance

        node_data.updated_at = datetime.now(timezone.utc)
        # last_checked_block_number = int(node_data.block) + 1
        txs = await get_latest_txs(node_address, node_data.last_block + 1)

        # set block info
        node_data.last_block = (
            int(txs[0]["blockNumber"]) if txs else node_data.last_block
        )
        node_data.last_block_ts = (
            int(txs[0]["timeStamp"]) if txs else node_data.last_block_ts
        )
        # cor_txs = txs  # TODO: check if needed: filter_cor_txs(txs)
        await update_node_status(node_data, node_data.last_block_ts, txs)

        # collect all timestamps for later visualization
        node_data.timestamps[:0] = [int(tx["timeStamp"]) for tx in txs]
        # await collect_node_timestamps(node_address, cor_txs)

        # TODO: explicit asc order by ts
        node_data.failed_txs = [tx for tx in txs if tx["isError"] != "0"][:10]
        # failed tx should be listed asc
        node_data.failed_txs.reverse()
        if node_data.failed_txs:
            logger.info(
                f'Node "{node_address}" has {len(node_data.failed_txs)} failed transactions!'
            )
            # tx_url = ARBISCAN_TX_URL_PREFIX + tx["hash"]
    except Exception:
        logger.exception(f'Error while checking node "{node_data.address}"!')

    # await asyncio.sleep(0.1)

    return node_data


async def unauthorized(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id):
    logger.info(f"Unauthorized access from {update.effective_user}")


@bot_user_authorized
async def edit_node_label_1(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id
):
    # logger.info(f'Listing registered nodes for chat_id="{chat_id}"')
    chat_id_node_addresses_label = get_chat_to_node(chat_id)
    node_addresses_label = [(node_address, node_label) for _, node_address, node_label in chat_id_node_addresses_label]

    if not node_addresses_label:
        await update.message.reply_text("No nodes registered")
        remove_message_ids(chat_id)
        return ConversationHandler.END

    buttons = []
    for address, label in node_addresses_label:
        buttons.append(
            [InlineKeyboardButton(truncate_address(label, 32), callback_data=address)]
        )
    reply_keyboard = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(
        "Select the node to edit the label for:",
        reply_markup=reply_keyboard,
    )

    remove_message_ids(chat_id)

    return 1


@bot_user_authorized
async def edit_node_label_2(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id
):
    query = update.callback_query
    node_address = query.data.lower()
    context.user_data['node_address'] = node_address

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()

    await query.edit_message_text(
        f"Provide label for address {node_address}:"
    )

    remove_message_ids(chat_id)

    return 2


@bot_user_authorized
async def edit_node_label_3(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id
):
    
    label = update.message.text
    node_address = context.user_data['node_address']

    update_node_label(chat_id, node_address, label)

    await update.message.reply_text(
        f"Label '{label}' for address {node_address} set."
    )

    remove_message_ids(chat_id)

    return ConversationHandler.END



@bot_user_authorized
async def subscribe_node_1(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id):
    await update.message.reply_text("Provide the node address to monitor. By adding ', <label>' you can set a label for this node. The label also be modified later.")

    remove_message_ids(chat_id)

    return 1


@bot_user_authorized
async def subscribe_node_2(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id):
    parts = update.message.text.split(',', 1)

    node_address = parts[0].lower().strip()
    pattern = re.compile("^(0x[a-fA-F0-9]{40})$")
    if not pattern.match(node_address):
        logger.info(f"User {chat_id} provided a wrong node address '{node_address}'")
        await update.message.reply_text(
            "Node address does not seem to be valid. Please try again."
        )  # , reply_markup=ReplyKeyboardRemove()

        remove_message_ids(chat_id)
        return ConversationHandler.END  # 1
    
    node_label = parts[1].strip() if len(parts) > 1 else None

    # check if address is a valid node
    txs = await get_latest_txs(node_address)
    # cor_txs = filter_cor_txs(txs)
    if not txs:  # cor_txs:
        logger.info(f'No transactions found for node_address="{node_address}')
        await update.message.reply_text(
            f'No transactions found for node "{node_address}"! Make sure node is already running.'
        )
        return

    logger.info(f'Registering chat_id="{chat_id}" and node_address="{node_address}')
    # register node for tracking
    if track_node(chat_id, node_address, node_label):
        await update.message.reply_text(f'Node {"\"" + node_label + "\" " if node_label else ""}subscribed successfully. Remember that next update may take up to 5 minutes.')
    else:
        await update.message.reply_text("Node already subscribed!")

    remove_message_ids(chat_id)

    return ConversationHandler.END


@bot_user_authorized
async def unsubscribe_node_1(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id
):
    # logger.info(f'Listing registered nodes for chat_id="{chat_id}"')
    chat_id_node_addresses_label = get_chat_to_node(chat_id)
    node_addresses_label = [(node_address, node_label) for _, node_address, node_label in chat_id_node_addresses_label]

    if not node_addresses_label:
        await update.message.reply_text("No nodes registered")
        remove_message_ids(chat_id)
        return

    buttons = []
    for address, label in node_addresses_label:
        btn_label = truncate_address(label, 32) + ("" if label == address else ": " + truncate_address(address, 17))
        buttons.append(
            [InlineKeyboardButton(btn_label, callback_data=address)]
        )
    reply_keyboard = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(
        "Select the node to unsubscribe:",
        reply_markup=reply_keyboard,
    )

    remove_message_ids(chat_id)

    return 1


@bot_user_authorized
async def unsubscribe_node_2(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id
):
    query = update.callback_query
    node_address = query.data.lower()
    pattern = re.compile("^(0x[a-fA-F0-9]{40})$")
    if not pattern.match(node_address):
        logger.warning(
            f'Invalid address provided for unsubscribe_node_2 for chat_id="{chat_id}" and node_address="{node_address}'
        )

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()

    # await unregister_node(update, update.effective_user.id, update.message.text)
    logger.info(f'Unsubscribing chat_id="{chat_id}" and node_address="{node_address}')
    # unregister node for tracking
    if untrack_node(chat_id, node_address):
        # await update.message.reply_text("Node unsubscribed successfully.")
        await query.edit_message_text(
            text=f"Node {query.data} unsubscribed successfully."
        )
    else:
        # await update.message.reply_text("Failed to unsubscribed node!")
        await query.edit_message_text(text=f"Failed to unsubscribed node {query.data}")

    remove_message_ids(chat_id)


@bot_user_authorized
async def handle_bonus_role_1(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id):
    chat_config = get_chat_config(chat_id)
    await update.message.reply_text(f"Provide the the amount of bonus roles you have (e.g. Early Birds I). Current: {chat_config.bonus_roles}")

    remove_message_ids(chat_id)

    return 1


@bot_user_authorized
async def handle_bonus_role_2(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id):
    logger.info(f'Setting bonus roles for chat_id="{chat_id}"')
    
    amount = 0
    try:
        amount = int(update.message.text)
    except ValueError:
        logger.info("Wrong amount for bonus roles provided. Try again")
        return ConversationHandler.END
    
    # TODO: add bonus roles + new node property to chat config
    chat_config = get_chat_config(chat_id)
    chat_config.bonus_roles = amount

    update_chat_config(chat_config)
    await update.message.reply_text(f'{amount} bonus roles set.')
    
    remove_message_ids(chat_id)

    return ConversationHandler.END


@bot_user_authorized
async def handle_new_nodes_1(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id):
    chat_config = get_chat_config(chat_id)
    await update.message.reply_text(f"Provide the the amount of new nodes you have in this phase. Current: {chat_config.new_nodes}")

    remove_message_ids(chat_id)

    return 1


@bot_user_authorized
async def handle_new_nodes_2(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id):
    logger.info(f'Setting new nodes for chat_id="{chat_id}"')
    
    amount = 0
    try:
        amount = int(update.message.text)
    except ValueError:
        logger.info("Wrong amount for new nodes provided. Try again")
        return ConversationHandler.END

    chat_config = get_chat_config(chat_id)
    chat_config.new_nodes = amount

    update_chat_config(chat_config)
    await update.message.reply_text(f'{amount} new nodes set.')
    
    remove_message_ids(chat_id)

    return ConversationHandler.END


@bot_user_authorized
async def list_subscribed_nodes(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id
) -> None:
    # await unregister_node(update, update.effective_user.id, update.message.text)
    logger.info(f'Listing registered nodes for chat_id="{chat_id}"')
    chat_id_node_addresses_label = get_chat_to_node(chat_id)
    
    node_addresses_label = [(node_address, node_label) for _, node_address, node_label in chat_id_node_addresses_label]
    # node_addresses = [node_address for _, node_address, _ in chat_id_node_addresses_label]

    if node_addresses_label:
        # buttons = []
        msg_addresses = ""
        for address, label in node_addresses_label:
            msg_addresses += (
                "<b>" + truncate_address(label) + "</b>"
                + ("" if label == address else ": " + truncate_address(address, 17))
                + ': 📊<a href="'
                + BOT_CONFIG.COR_DASHBOARD_URL_PREFIX
                + address
                + '">Dashboard</a>'
                + '   🔍<a href="'
                + BOT_CONFIG.ARBISCAN_ADDRESS_URL_PREFIX
                + address
                + '">Arbiscan</a>\n\n'
            )

        await update.message.reply_html(
            "Following node addresses have been subscribed:\n\n" + msg_addresses,
        )

        # reply_keyboard = InlineKeyboardMarkup(buttons)
        # await update.message.reply_text(
        #     "Following node addresses have been subscribed:",
        #     reply_markup=reply_keyboard,
        # )
    else:
        await update.message.reply_text("No nodes registered")

    remove_message_ids(chat_id)



@bot_user_authorized
async def show_metrics_for_address(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id
) -> None:
    # pattern = re.compile("^(0x[a-fA-F0-9]{40})$")

    # if not context.args: #or not pattern.match(context.args[0]):
    # await update.message.reply_text(" No node address provided. Use /metrics <address>")

    logger.info(
        f'Showing nodes for registered nodes for chat_id="{chat_id}" for metrics fetching'
    )
    chat_id_node_addresses_label = get_chat_to_node(chat_id)
    
    node_addresses_label = [(node_address, node_label) for _, node_address, node_label in chat_id_node_addresses_label]
    # node_addresses = [node_address for _, node_address, _ in chat_id_node_addresses_label]

    if not node_addresses_label:
        await update.message.reply_text("No nodes registered")
        remove_message_ids(chat_id)
        return

    buttons = []
    for address, label in node_addresses_label:
        buttons.append(
            [
                InlineKeyboardButton(
                    truncate_address(label, 32), callback_data="metrics___" + address
                )
            ]
        )
    reply_keyboard = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(
        "Select the node to show metrics for:",
        reply_markup=reply_keyboard,
    )

    remove_message_ids(chat_id)


@bot_user_authorized
async def handle_show_metrics_for_address(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id
) -> None:
    pattern = re.compile("^(0x[a-fA-F0-9]{40})$")

    await BOT_APP.bot.send_chat_action(chat_id, ChatAction.TYPING)
    # if not context.args: #or not pattern.match(context.args[0]):
    # await update.message.reply_text(" No node address provided. Use /metrics <address>")

    query = update.callback_query
    node_address = query.data
    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()

    node_address = node_address[len("metrics___") :]

    if not pattern.match(node_address):
        logger.warning(
            f'Invalid address provided for show metrics for chat_id="{chat_id}" and node_address="{node_address}'
        )

    logger.info(
        f'Show metrics for chat_id="{chat_id}" and node_address="{node_address}'
    )

    chat_config = get_chat_config(chat_id)

    # msg = await fetch_metrics_for_node(node_address)
    metrics = METRIC_SCRAPER.scrape_address(node_address)

    success_rate_emoji = get_success_rate_emoji(
        metrics, chat_config.metrics_warning_threshold
    )
    msg = f"{success_rate_emoji}<b><u>Node metrics: {truncate_address(node_address, 23)}</u></b>{success_rate_emoji}\n\n"
    for metric in metrics:
        msg += create_metrics_msg(metric, chat_config.metrics_warning_threshold)

    await query.edit_message_text(text=msg, parse_mode="html")

    remove_message_ids(chat_id)


def get_success_rate_emoji(metrics, custom_warning_threshold=0):
    warning = ""
    for metric in metrics:
        if metric.success_rate is not None:
            if metric.success_rate <= 0:
                return "🚨"
            elif metric.success_rate <= custom_warning_threshold:
                warning = "⚠️"
    return warning


def create_metrics_msg(metric: Metric, custom_warning_threshold=0, rate_drop=None):
    success_rate_emoji = get_success_rate_emoji([metric], custom_warning_threshold)
    success_rate_msg = (
        f"{metric.success_rate}% {success_rate_emoji}"
        if metric.success_rate is not None
        else "N/A"
    )

    msg = f"<b>{metric.name}:</b>\n"
    if rate_drop:
        msg += f"Success rate drop: {-metric.prior_success_rate_drop}\n"
    msg += "Success rate: " + success_rate_msg + "\n"
    msg += f"Point: {metric.points}\n"
    msg += f"Counter: {metric.counter}\n"
    msg += "\n"

    return msg


def build_toggle_notifications_buttons(chat_config: ChatConfig):
    buttons = [
        [
            InlineKeyboardButton(
                f"{'✅' if chat_config.active else '❌'} Bot is {'enabled' if chat_config.active else 'disabled'}",
                callback_data=f"notification___active___{not chat_config.active}",
            )
        ],
        [
            InlineKeyboardButton(
                f"{'✅' if chat_config.notification_node_status else '❌'} Node status {'enabled' if chat_config.notification_node_status else 'disabled'}",
                callback_data=f"notification___node_status___{not chat_config.notification_node_status}",
            )
        ],
        [
            InlineKeyboardButton(
                f"{'✅' if chat_config.notification_failed_tx else '❌'} Failed transactions {'enabled' if chat_config.notification_failed_tx else 'disabled'}",
                callback_data=f"notification___failed_tx___{not chat_config.notification_failed_tx}",
            )
        ],
        [
            InlineKeyboardButton(
                f"{'✅' if chat_config.performance_style.value >= 0 else '❌'} Performance style: {chat_config.performance_style.name} ➡️",
                callback_data="notification___performance_style___options",
            )
        ],
        [
            InlineKeyboardButton(
                f"{'✅' if chat_config.metrics_warning_threshold >= 0 else '❌'} Metrics success rate warning{': ' + str(chat_config.metrics_warning_threshold) if chat_config.metrics_warning_threshold >= 0 else ''} ➡️",
                callback_data="notification___metrics_warning_threshold___options",
            )
        ],
        [
            InlineKeyboardButton(
                f"{'✅' if chat_config.metrics_drop_threshold >= 0 else '❌'} Metrics success rate drop{': ' + str(chat_config.metrics_drop_threshold) if chat_config.metrics_drop_threshold >= 0 else ''} ➡️",
                callback_data="notification___metrics_drop_threshold___options",
            )
        ],
    ]

    return InlineKeyboardMarkup(buttons)


def create_inline_keyboard_value_button(
    callback_key, current_value, selectable_value
) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        f"{'✅' if current_value == selectable_value else ''} {selectable_value}",
        callback_data=f"{callback_key}___{selectable_value}",
    )


def build_toggle_notifications_performance_style_options(
    chat_config: ChatConfig, callback_key
):
    current_value = chat_config.metrics_warning_threshold

    buttons = [
        [
            InlineKeyboardButton(
                f"{'✅' if current_value == PERFORMANCE_STYLE.OFF else ''} Off",
                callback_data=f"{callback_key}___{PERFORMANCE_STYLE.OFF.value}",
            )
        ],
        [
            InlineKeyboardButton(
                f"{'✅' if current_value == PERFORMANCE_STYLE.FULL else ''} Full",
                callback_data=f"{callback_key}___{PERFORMANCE_STYLE.FULL.value}",
            )
        ],
        [
            InlineKeyboardButton(
                f"{'✅' if current_value == PERFORMANCE_STYLE.PIN else ''} Pin",
                callback_data=f"{callback_key}___{PERFORMANCE_STYLE.PIN.value}",
            )
        ],
    ]

    return InlineKeyboardMarkup(buttons)


def build_toggle_notifications_metrics_warning_threshold_options(
    chat_config: ChatConfig, callback_key
):
    current_value = chat_config.metrics_warning_threshold

    buttons = [
        [
            create_inline_keyboard_value_button(callback_key, current_value, 10),
            create_inline_keyboard_value_button(callback_key, current_value, 25),
            create_inline_keyboard_value_button(callback_key, current_value, 50),
        ],
        [
            create_inline_keyboard_value_button(callback_key, current_value, 75),
            create_inline_keyboard_value_button(callback_key, current_value, 85),
            create_inline_keyboard_value_button(callback_key, current_value, 95),
        ],
        [
            InlineKeyboardButton(
                f"{'✅' if current_value == -1 else ''} Off",
                callback_data=f"{callback_key}___-100",
            )
        ],
    ]

    return InlineKeyboardMarkup(buttons)


def build_toggle_notifications_metrics_drop_threshold_options(
    chat_config: ChatConfig, callback_key
):
    current_value = chat_config.metrics_drop_threshold

    buttons = [
        [
            create_inline_keyboard_value_button(callback_key, current_value, 1),
            create_inline_keyboard_value_button(callback_key, current_value, 3),
            create_inline_keyboard_value_button(callback_key, current_value, 5),
        ],
        [
            create_inline_keyboard_value_button(callback_key, current_value, 10),
            create_inline_keyboard_value_button(callback_key, current_value, 20),
            create_inline_keyboard_value_button(callback_key, current_value, 30),
        ],
        [
            create_inline_keyboard_value_button(callback_key, current_value, 50),
            create_inline_keyboard_value_button(callback_key, current_value, 75),
            create_inline_keyboard_value_button(callback_key, current_value, 90),
        ],
        [
            InlineKeyboardButton(
                f"{'✅' if current_value == -1 else ''} Off",
                callback_data=f"{callback_key}___-1",
            )
        ],
    ]

    return InlineKeyboardMarkup(buttons)


@bot_user_authorized
async def toggle_notifications(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id
):
    chat_config = get_chat_config(chat_id)
    reply_keyboard = build_toggle_notifications_buttons(chat_config)

    await update.message.reply_text(
        "Toggle one of the following notification types:",
        reply_markup=reply_keyboard,
    )

    remove_message_ids(chat_id)


@bot_user_authorized
async def handle_toggle_notifications(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id
):
    query = update.callback_query
    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()

    data = query.data
    chat_config = get_chat_config(chat_id)

    if data.startswith("notification___active___"):
        chat_config.active = data[len("notification___active___") :] == "True"
        logger.info(
            f'chat_id="{chat_id}" toggled active notifications="{chat_config.active}"'
        )
    if data.startswith("notification___node_status___"):
        chat_config.notification_node_status = (
            data[len("notification___node_status___") :] == "True"
        )
        logger.info(
            f'chat_id="{chat_id}" toggled node status notifications="{chat_config.notification_node_status}"'
        )
    elif data.startswith("notification___failed_tx___"):
        chat_config.notification_failed_tx = (
            data[len("notification___failed_tx___") :] == "True"
        )
        logger.info(
            f'chat_id="{chat_id}" toggled failed tx notifications="{chat_config.notification_failed_tx}"'
        )
    elif data == "notification___performance_style___options":
        await query.edit_message_text(
            text="Select the style for performance overview. This includes ranks overview.",
            reply_markup=build_toggle_notifications_performance_style_options(
                chat_config, "notification___performance_style___options"
            ),
        )
        remove_message_ids(chat_id)
        return
    elif data.startswith("notification___performance_style___options___"):
        chat_config.performance_style = PERFORMANCE_STYLE(int(
            data[len("notification___performance_style___options___") :]
        ))
        logger.info(
            f'chat_id="{chat_id}" toggled performance_style notifications="{chat_config.performance_style.name}"'
        )
    elif data == "notification___metrics_warning_threshold___options":
        await query.edit_message_text(
            text="Select below which metric sucess rate you will receive a warning",
            reply_markup=build_toggle_notifications_metrics_warning_threshold_options(
                chat_config, "notification___metrics_warning_threshold___options"
            ),
        )
        remove_message_ids(chat_id)
        return
    elif data.startswith("notification___metrics_warning_threshold___options___"):
        chat_config.metrics_warning_threshold = int(
            data[len("notification___metrics_warning_threshold___options___") :]
        )
        logger.info(
            f'chat_id="{chat_id}" toggled metrics_warning_threshold notifications="{chat_config.metrics_warning_threshold}"'
        )
    elif data == "notification___metrics_drop_threshold___options":
        await query.edit_message_text(
            text="Select below which metric success rate drop in the last 6 hours you will receive a warning",
            reply_markup=build_toggle_notifications_metrics_drop_threshold_options(
                chat_config, "notification___metrics_drop_threshold___options"
            ),
        )
        remove_message_ids(chat_id)
        return
    elif data.startswith("notification___metrics_drop_threshold___options___"):
        chat_config.metrics_drop_threshold = int(
            data[len("notification___metrics_drop_threshold___options___") :]
        )
        logger.info(
            f'chat_id="{chat_id}" toggled metrics_drop_threshold notifications="{chat_config.metrics_drop_threshold}"'
        )

    update_chat_config(chat_config)

    await query.edit_message_text(
        text="Configure your notifications:",
        reply_markup=build_toggle_notifications_buttons(chat_config),
    )

    remove_message_ids(chat_id)


@bot_user_authorized
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id) -> None:
    await update.message.reply_html(
        "<b>CoNoMo 0.4 beta</b>\n\n"
        + "Features:\n\n"
        + "- Intelligent notifications: Only receive new messages when something happens according to your settings else the latest message gets just updated. You dont get spammed with notifications and still always have the latest data available.\n"
        + "- Node Status: Always have a overview of your nodes. This includes information like online or offline state, ETH balance, metric warnings and visualization of the health for the last 8 hours.\n"
        + "- Failed transactions: Get notified when a transaction failed including detailed information about it.\n"
        + "- Node stall: Get notified when a node is stall. The last 25 transaction are only pings.\n"
        + "- Metrics on demand: The latest metrics data is just one click away.\n"
        + "- Node management: Add, remove, edit labels or list your currently configured nodes.\n"
        + "- Estimated rewards: Shows rewards based on your nodes and bonuses.\n"
        + "- Performance: Shows how you nodes currently perform based on metrics.\n"
        + "- Rank: Shows an overview of all ranks and per node.\n"
        + "\n\n"
        + "Select a command to start:\n\n"
        + "/subscribe to subscribe a node address\n"
        + "/unsubscribe to unsubscribe a node address\n"
        + "/nodes to list subscribed node addresses\n"
        + "/edit_node_label to Edit label of a node\n"
        + "/show_metrics to show metrics for a node address\n"
        + "/bonus_roles to set amount of bonus roles\n"
        + "/new_nodes to set amount of new nodes in this phase\n"
        # + "/update_all_metrics to update metrics for all nodes\n"
        + "/notifications for notification settings\n"
    )

    remove_message_ids(chat_id)


@bot_user_authorized
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id) -> None:
    await update.message.reply_html(
        "<b>Health:</b>\n"
        + "Every square equals a 10 minute timeframe. Were new squares will be added left. If at least one transaction happend in this timeframe a 🟩 will be shown else a 🟥. If there is no data available for the current update a ⬜ will be displayed."
        + "\n\n"
        + "<b>Node stall:</b>\n"
        + "If the last 25 transactions of a node are only pings the node is marked as stall. Showing a warning and the last consecutive ping count."
        + "\n\n"
        + "<b>Estimated rewards:</b>\n"
        + "Estimated rewards are calculated based on nodes amount, new nodes in this phase, bonus roles and rank prizes. Configure your new nodes and bonus roles accordingly in settings. Rank prizes are only based on your node cluster as the bot does not have knowledge about all clusters. Due to the max spots rank prizes may be off a lot. "
        + "Base reward and ranks prizes are always shown separatly.\nFormula: (base reward + new nodes reward) * bonus roles multiplier + rank prizes = total"
        + "\n\n"
        + "<b>Notifications:</b>\n"
        + "<i>Bot:</i> If disabled the bot does not send any new messages.\n\n"
        + "<i>Node status:</i> If enabled the bot sends new messages if on-/offline status changed or eth balance is low. If disabled the bot will still ensure that the nodes status message is the latest but you will not receive any notifications on changes.\n\n"
        + "<i>Performance style:</i> Configure the style of performance overview. This includes ranks.\n\n"
        + "Off: Performance and ranks may change often which results in a lot of notifications. Turn it off to just show node details.\n"
        + "Full: Show detailed overview of node performance and ranks\n"
        + "Pin: Shows a one-liner for node performance. This is helpful if you pin the bot chat in telegram.\n\n"
        + "<i>Failed transactions:</i> If enabled sends new messages if a failed transaction happens.\n\n"
        + "<i>Metrics success rate warning:</i> If a node metric success rate drops below this value a warning will be shown. Node metrics are updated every 6 hours!\n\n"
        + "<i>Metrics success rate drop:</i> If a node metric success rate drops more than this value over the last 6 hours a notification will be send. Node metrics are updated every 6 hours!"
    )

    remove_message_ids(chat_id)


@bot_user_authorized
async def node_address_not_valid(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id
) -> int:
    logger.info(f"User {chat_id} provided a wrong node address '{update.message.text}'")
    await update.message.reply_text(
        "Node address does not seem to be valid. Please try again."
    )  # , reply_markup=ReplyKeyboardRemove()

    remove_message_ids(chat_id)

    return ConversationHandler.END


@bot_user_authorized
async def default_conv_fallback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id
) -> int:
    logger.warning(f"Convesation for chat {chat_id} could not be handled")
    await update.message.reply_text(
        "Could not handle the conversation. Please try again."
    )  # , reply_markup=ReplyKeyboardRemove()

    remove_message_ids(chat_id)

    return ConversationHandler.END


@bot_admin_authorized
async def list_users(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id
) -> None:
    user_ids = BOT_DB_CURSOR.execute(
        "SELECT DISTINCT chat_id FROM chat_node"
    ).fetchall()
    if user_ids:
        msg = f"Registered users ({len(user_ids)}):\n\n" + "\n".join(
            [str(user_id[0]) for user_id in user_ids]
        )
    else:
        msg = "No registered users!"

    logger.info(msg)
    await update.message.reply_text(msg)

    remove_message_ids(chat_id)


@bot_admin_authorized
async def list_nodes(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id
) -> None:
    addresses = BOT_DB_CURSOR.execute(
        "SELECT DISTINCT node_address FROM chat_node"
    ).fetchall()
    if addresses:
        msg = f"Registered nodes ({len(addresses)}):\n\n"

        for batch in batched(addresses, 25):
            msg += "\n".join([str(address[0]) for address in batch])
            await update.message.reply_text(msg)
            msg = ""


    else:
        msg = "No registered nodes!"
        await update.message.reply_text(msg)


    remove_message_ids(chat_id)


def get_failed_tx_reason(tx_hash):
    response = requests.get(
        "https://api.tenderly.co/api/v1/public-contract/421614/tx/" + tx_hash
    )
    if response.status_code == 200:  # and response.json()['message'] == 'OK':
        return response.json()["error_message"]

    return "UNKNOWN"


async def handle_new_metrics(metrics_per_address):
    logger.info("Handling new metrics...")

    global NODES_METRICS

    chat_id_node_addresses_label = get_chat_to_node(None, True)
    address_to_chat_ids = dict()
    address_chat_id_to_label = dict()
    for chat_id, node_address, node_label in chat_id_node_addresses_label:
        address_to_chat_ids.setdefault(node_address, []).append(chat_id)
        address_chat_id_to_label[node_address + "_" + str(chat_id)] = node_label

    chat_id_to_config = dict()

    for address, metrics_for_address in metrics_per_address.items():
        old_metrics = NODES_METRICS.get(address, None)
        # If no old metrics for this node. Just update and do nothing
        if not old_metrics:
            NODES_METRICS[address] = metrics_for_address
            continue

        for metric in metrics_for_address:
            old_metric = next((m for m in old_metrics if m.name == metric.name), None)
            if (
                old_metric
                and metric.success_rate is not None
                and old_metric.success_rate is not None
            ):
                # Check if the new value is smaller (i.e., a decrease)
                if metric.success_rate < old_metric.success_rate:
                    metric.prior_success_rate_drop = abs(
                        old_metric.success_rate - metric.success_rate
                    )
                else:
                    metric.prior_success_rate_drop = (
                        0  # No decrease or not significant decrease
                    )

        NODES_METRICS[address] = metrics_for_address

        chat_ids = address_to_chat_ids.get(address, None)
        for chat_id in chat_ids:
            chat_config = chat_id_to_config.setdefault(
                chat_id, get_chat_config(chat_id)
            )
            if chat_config.metrics_drop_threshold == -1:
                continue
            msg = ""
            for metric in metrics_for_address:
                if metric.prior_success_rate_drop >= chat_config.metrics_drop_threshold:
                    msg += create_metrics_msg(
                        metric,
                        chat_config.metrics_warning_threshold,
                        metric.prior_success_rate_drop,
                    )
            if msg:
                msg = (
                    f"🚨 <b><u>Metrics drop: {truncate_address(address_chat_id_to_label[address + "_" + str(chat_id)], 23)}</u></b> 🚨\n\n"
                    + msg
                )

                await BOT_APP.bot.send_message(
                    chat_id,
                    msg,
                    parse_mode="HTML",
                )
                remove_message_ids(chat_id)
    
    logger.info("Handling of metrics finished.")

    return


async def main():
    throttler = Throttler(rate_limit=4, period=1.0)
    retry_options = ExponentialRetry(attempts=2)

    global ETH_API_CLIENT
    ETH_API_CLIENT = Client(
        BOT_CONFIG.ETH_API_KEY,
        throttler=throttler,
        retry_options=retry_options,
        api_kind="arbitrum",
        network="sepolia",
    )

    global BOT_DB_CONNECTION
    BOT_DB_CONNECTION = sqlite3.connect(BOT_CONFIG.BOT_DB_FILE)
    global BOT_DB_CURSOR
    BOT_DB_CURSOR = BOT_DB_CONNECTION.cursor()

    global CHAT_ID_MESSAGE_IDS

    while True:
        try:
            start = time.time()

            # Session check. ADMIN only
            await check_session_data(BOT_CONFIG.AUTHORIZED_ADMIN_IDS)


            chat_id_node_addresses_label = get_chat_to_node(None, True)
            logger.info(f"Checking nodes: {chat_id_node_addresses_label}")

            all_distinct_node_addresses = list(
                set([node_address for _, node_address, _ in chat_id_node_addresses_label])
            )

            ###### Update node data
            await update_node_datas(all_distinct_node_addresses)

            chat_id_to_node_addresses = dict()
            address_chat_id_to_label = dict()
            for chat_id, node_address, node_label in chat_id_node_addresses_label:
                chat_id_to_node_addresses.setdefault(chat_id, []).append(node_address)
                address_chat_id_to_label[node_address + "_" + str(chat_id)] = node_label

            for chat_id, node_addresses in chat_id_to_node_addresses.items():
                chat_node_datas = [
                    NODES[node_address] for node_address in node_addresses
                ]

                chat_config = get_chat_config(chat_id)
                if not chat_config:
                    logger.error(f'Failed to fetch config for chat "{chat_id}"')
                    continue

                # failed txs
                await send_failed_tx_message(chat_node_datas, chat_config, address_chat_id_to_label)

                # overview
                await send_overview_message(chat_node_datas, chat_config, address_chat_id_to_label)

            sleep_time = BOT_CONFIG.MAIN_SLEEP_SEC - (time.time() - start)
            logger.info(f"Sleeping for {sleep_time} seconds.")
            await asyncio.sleep(sleep_time)
        except Exception:
            logger.exception("Main node check loop failed!")


async def check_session_data(chat_ids: list):
    global LAST_SESSION_DATA

    try:
        def parse_ts(ts):
            return f"({CONTRACT_READER.parse_timestamp(ts)})" if ts else ""
        

        session_data = CONTRACT_READER.get_latest_cor_session_data()

        if not session_data:
            return
        
        
        if LAST_SESSION_DATA and LAST_SESSION_DATA.id != session_data.id:
            CHAT_ID_SESSION_MESSAGE_ID.clear()
            return
        
        LAST_SESSION_DATA = session_data
        
        current_dt = datetime.now(tz=timezone.utc)
        current_ts = current_dt.timestamp()
        
        # check prepare step. Max 1h
        if session_data.created and not session_data.started and (session_data.created + 60 * 60) < current_ts:
            msg = f"🚨 Session <b>{session_data.id}</b> stuck in prepare state 🚨"
        # check precommit step. Max 5m
        elif session_data.started and not session_data.ended and (session_data.started + 60 * 5) < current_ts:
            msg = f"🚨 Session <b>{session_data.id}</b> stuck in precommit state 🚨"

        if msg:
            logger.info(f"Session {session_data.id} stuck:\n{session_data}")

            msg += f"\n\nCreated: {session_data.created} {parse_ts(session_data.created)}\nStarted: {session_data.started} {parse_ts(session_data.started)}\nEnded: {session_data.ended} {parse_ts(session_data.ended)}\n\n"
            
            msg += f"<i>Last update: {current_dt.isoformat(sep=' ', timespec='seconds')}</i>"
            for chat_id in chat_ids:
                existing_msg_id = CHAT_ID_SESSION_MESSAGE_ID.get(chat_id, None)
                if existing_msg_id:
                    await BOT_APP.bot.edit_message_text(
                        msg, chat_id, existing_msg_id,
                        parse_mode="HTML",
                    )
                else:
                    message = await BOT_APP.bot.send_message(
                        chat_id,
                        msg,
                        parse_mode="HTML",
                    )
                    CHAT_ID_SESSION_MESSAGE_ID[chat_id] = message.id
                    remove_message_ids(chat_id)

    except Exception:
        logger.exception("Failed to check session data")


async def update_node_datas(all_distinct_node_addresses: list[str]):
    await update_new_eth_balances(all_distinct_node_addresses)

    metrics_per_node = METRIC_SCRAPER.scrape_metrics()

    for node_address in all_distinct_node_addresses:
        node_data = await get_latest_node_data(node_address)
        node_data.metrics = metrics_per_node.get(node_address, [])
        NODES[node_address] = node_data
        await asyncio.sleep(0.33)

    all_nodes_metrics = list(metrics_per_node.values())
    rank_score_calculator.update_global_stats(all_nodes_metrics)
    # for node_data in NODES.values():
    #     node_data.rank_score = rank_score_calculator.calculate_rank_score(node_data.metrics)

    rank_score_per_node = dict()
    for address, metrics in metrics_per_node.items():
        rank_score = rank_score_calculator.calculate_rank_score(metrics)
        rank_score_per_node[address] = rank_score
        if address in NODES:
            NODES[address].rank_score = rank_score

    sorted_addresses_by_rank_score = sorted(rank_score_per_node, key=rank_score_per_node.get, reverse=True)
    for address, node_data in NODES.items():
        try:
            node_data.rank = sorted_addresses_by_rank_score.index(address) + 1
        except ValueError:
            logger.info(f"address is not in rank data {address}")
        except Exception:
            logger.exception("Failed to get rank index")


async def send_failed_tx_message(
    chat_node_datas: list[NodeData], chat_config: ChatConfig, address_chat_id_to_label: dict[str, str],
):
    try:
        if chat_config.notification_failed_tx:
            # if count txs of all nodes smaller some value (around 12) send one message else for each node
            send_per_node = (
                sum([len(node_data.failed_txs) for node_data in chat_node_datas]) > 12
            )

            msg_failed_tx_info = ""
            for node_data in chat_node_datas:
                if node_data.failed_txs:
                    label = truncate_address(address_chat_id_to_label[node_data.address + "_" + str(chat_config.chat_id)])
                    msg_failed_tx_info = f"🚨 <b><u>{len(node_data.failed_txs)} failed tx: {label}</u></b> 🚨\n\n"
                    for failed_tx in node_data.failed_txs:
                        reason = get_failed_tx_reason(failed_tx["hash"])
                        functionName = failed_tx['functionName'] if failed_tx['functionName'] else METHOD_TO_FUCNTION.get(failed_tx['methodId'], "UNKNOWN")

                        msg_failed_tx_info += (
                            f"<b>{reason}</b>\n"
                            #  f"Reason: {reason}\n"
                            + f"Timestamp: {datetime.fromtimestamp(int(failed_tx['timeStamp']), timezone.utc).isoformat(sep=' ', timespec='seconds')}\n"
                            + f"Function: {functionName}\n"
                            + f"Method: {failed_tx['methodId']}\n"
                            + f'<a href="{BOT_CONFIG.ARBISCAN_TX_URL_PREFIX + failed_tx["hash"]}">View tx on Arbiscan 🔍</a>\n\n'
                        )
                    # msg += msg_failed_tx_info + "\n\n"
                    msg_failed_tx_info += "\n\n\n"

                if send_per_node and msg_failed_tx_info:
                    await BOT_APP.bot.send_message(
                        chat_config.chat_id,
                        msg_failed_tx_info,
                        parse_mode="HTML",
                    )
                    # asyncio.sleep(0.3)
                    remove_message_ids(chat_config.chat_id)
                    msg_failed_tx_info = ""
            if not send_per_node and msg_failed_tx_info:
                await BOT_APP.bot.send_message(
                    chat_config.chat_id, msg_failed_tx_info, parse_mode="HTML"
                )
                remove_message_ids(chat_config.chat_id)
    except Exception:
        logger.exception("Error while sending failed tx message!")


def create_rank_overview(chat_node_datas: list[NodeData], new_node_count, role_count):
    rank_tiers = {
        0: {"name": "1-5", "end": 5, "max_spots": 1, "reward": 50},
        1: {"name": "6-10", "end": 10, "max_spots": 1, "reward": 35},
        2: {"name": "11-20", "end": 20, "max_spots": 1, "reward": 25},
        3: {"name": "21-30", "end": 30, "max_spots": 1, "reward": 15},
        4: {"name": "31-100", "end": 100, "max_spots": 5, "reward": 10},
        5: {"name": "101-150", "end": 150, "max_spots": float("inf"), "reward": 5},
        6: {"name": "151+", "end": float("inf"), "max_spots": float("inf"), "reward": 0}
    }

    # Track how many nodes are in each tier
    tier_buckets = defaultdict(int)
    rank_buckets = defaultdict(int)
    # node datas should be sorted by rank if the correct spot is important. But only counts are
    # For each node, find first eligible tier with space

    # reward tiers
    for node_data in chat_node_datas:
        if not node_data.rank:
            tier_buckets[6] += 1
            continue
        for key, tier_data in rank_tiers.items():
            if node_data.rank <= tier_data["end"]:
                if tier_buckets[key] < tier_data["max_spots"]:
                    tier_buckets[key] += 1
                    break  # Assigned, stop checking further tiers
            # If not eligible for current tier, keep checking

    for node_data in chat_node_datas:
        if not node_data.rank:
            rank_buckets[6] += 1
            continue
        for key, tier_data in rank_tiers.items():
            if node_data.rank <= tier_data["end"]:
                rank_buckets[key] += 1
                break  # Assigned, stop checking further tiers
            # If not eligible for current tier, keep checking

    rank_reward = 0
    for key, tier in rank_tiers.items():
        count = tier_buckets.get(key, 0)
        rank_reward += count * tier["reward"]


    base_reward = len(chat_node_datas) * 20

    new_node_multiplier = 0
    if new_node_count >= 5:
        new_node_multiplier = 0.2
    elif new_node_count >= 3:
        new_node_multiplier = 0.1
    new_node_reward = (new_node_count * 20) * new_node_multiplier

    role_multiplier = role_count * 0.05 
    total_reward = (base_reward + new_node_reward) * (1 + role_multiplier) + rank_reward

    
    msg = f"<b><u>Ranks ({sum(rank_buckets.values())}):</u></b>\n"

    for key, count in sorted(rank_buckets.items()):
        if count:
            msg += f"{rank_tiers[key]["name"]}: {count}\n"

    msg += "\n"
    msg += "Estimated reward: "
    if new_node_count:
        msg += f"(${base_reward} + ${new_node_reward:.0f}) "
    else:
        msg += f"${base_reward} "

    if role_multiplier:
        msg += f"* {1 + role_multiplier} "

    if rank_reward:
        msg += f"+ ${rank_reward} "

    msg += f"= ${total_reward:.2f}\n"

    # msg += f"({base_reward} + {new_node_reward:.0f}) * {1 + role_multiplier} + {rank_reward} = ${total_reward:.2f}\n"

    return msg


async def send_overview_message(
    chat_node_datas: list[NodeData], chat_config: ChatConfig, address_chat_id_to_label: dict[str, str],
):
    global CHAT_ID_MESSAGE_IDS
    try:
        latest_updated_at = max([node_data.updated_at for node_data in chat_node_datas])

        msg = ""

        # performance
        if chat_config.performance_style != PERFORMANCE_STYLE.OFF:
            counter_rank_states = Counter(rank_score_calculator.get_rank_status_by_score(node_data.rank_score)['status'] for node_data in chat_node_datas)
            # status_order = ["Elite", "Exceptional", "Excellent", "Very Good", "Good", "Above Average", "Average", "Below Average", "Poor", "No Data"]
            
            status_order = {
                "Elite": "EE",
                "Exceptional": "EL",
                "Excellent": "ET",
                "Very Good": "VG", 
                "Good": "G", 
                "Above Average": "AA", 
                "Average": "A", 
                "Below Average": "BA",
                "Poor": "P",
                "No Data": "ND"
            }

            performance_strs = []
            for name, short_name in status_order.items():
                if name in counter_rank_states:
                    performance_name = short_name
                    if chat_config.performance_style == PERFORMANCE_STYLE.FULL:
                        performance_name = name
                    performance_strs.append(f"{performance_name}: {counter_rank_states[name]}")
            delimiter = ", "
            if chat_config.performance_style == PERFORMANCE_STYLE.FULL:
                msg = f"<b><u>Overall performance ({len(chat_node_datas)}):</u></b>\n"
                delimiter = "\n"
            msg += delimiter.join(performance_strs)
           
            msg += "\n_________________________\n\n"
            msg += create_rank_overview(chat_node_datas, chat_config.new_nodes, chat_config.bonus_roles)
            msg += "_________________________\n\n"
       

        for node_data in chat_node_datas:
            end_time, start_time, healthHistory = create_health_history(
                # node_data.address, now_datetime
                node_data
            )

            warning_metrics = []
            negative_metrics = []
            # old_metrics = NODES_METRICS.get(node_data.address, None)

            if not node_data.metrics:
                metric_msg = "❓\n"
            else:
                warning_metrics = [
                    f"{metric.name} {metric.success_rate}%"
                    for metric in node_data.metrics
                    if metric.visible and metric.success_rate is not None
                    and metric.success_rate > 0
                    and metric.success_rate < chat_config.metrics_warning_threshold
                ]
                negative_metrics = [
                    f"{metric.name} {metric.success_rate}%"
                    for metric in node_data.metrics
                    if metric.visible and metric.success_rate is not None and metric.success_rate <= 0
                ]

                metric_msg = (
                    "" if warning_metrics or negative_metrics else "✅"
                ) + "\n"

                if warning_metrics:
                    metric_msg += "   ⚠️: <i>" + ", ".join(warning_metrics) + "</i>\n"

                if negative_metrics:
                    metric_msg += "   🚨: <i>" + ", ".join(negative_metrics) + "</i>\n"

            balance_warning = node_data.balance < BOT_CONFIG.BALANCE_WARNING_THRESHOLD
            node_stall_warning = (
                node_data.consecutive_pings >= BOT_CONFIG.NODE_STALL_THRESHOLD
            )
            msg_node_stall = (
                f"Node stall: {node_data.consecutive_pings} consecutive pings ⚠️\n"
                if node_stall_warning
                else ""
            )

            if node_data.status == NODE_STATUS.OFFLINE:
                node_status = "🔴"
            elif node_data.status == NODE_STATUS.STALL or (
                node_data.status == NODE_STATUS.ONLINE
                and (warning_metrics or negative_metrics or balance_warning)
            ):
                node_status = "🟡"
            else:
                node_status = "🟢"


            rank_status = rank_score_calculator.get_rank_status_by_score(node_data.rank_score)
            rank_msg = f"Rank: {node_data.rank}\n"
            rank_score_msg = f"Rank score: {node_data.rank_score * 100}% ({rank_status["status"]})\n"

            # reward_msg = "Reward: "
            # if node_data.rank_score >= 0.9:
            #     reward_msg += "🔵 Top"
            # elif node_data.rank_score >= 0.6:
            #     reward_msg += "🟢 Mid"
            # elif node_data.rank_score >= 0.5:
            #     reward_msg += "🟡 Base" # 🟡🟠
            # else:
            #     reward_msg += "🔴 No invcentive"
            # reward_msg += "\n"

            label = truncate_address(address_chat_id_to_label[node_data.address + "_" + str(chat_config.chat_id)], 23)
            msg_node_info = (
                f"<b><u>{label}</u></b>\n"
                + f"Status: {node_status}\n"
                + f"Balance: {round(node_data.balance, 6)} ETH {'⚠️' if balance_warning else ''}\n"
                + rank_msg
                + rank_score_msg
                + msg_node_stall
                + "Metrics: "
                + metric_msg
                + f"Last seen: {naturaltime(latest_updated_at.timestamp() - node_data.last_block_ts)}\n"
                + f'Links: 📊<a href="{BOT_CONFIG.COR_DASHBOARD_URL_PREFIX + node_data.address}">Dashboard</a>   🔍<a href="{BOT_CONFIG.ARBISCAN_ADDRESS_URL_PREFIX + node_data.address}">Arbiscan</a>\n'
                + f"Health: \n{end_time} {healthHistory} {start_time}\n"
            )

            msg += msg_node_info + "\n\n"

            # TODO: rmeove
            # msg += "abcde12345" * 500

            logger.info(f"Message length: {len(msg)}")
        # msg += f"<i>Last update: {latest_updated_at.isoformat(sep=' ', timespec='seconds')}</i>"

        existing_msg_ids = CHAT_ID_MESSAGE_IDS.setdefault(chat_config.chat_id, [])
        notify = any([nd.notify for nd in chat_node_datas])

        msg_parts = split_on_last_double_newline(msg)
        
        # TODO: use all existing msg ids and only send the last one new 
        if len(existing_msg_ids) > len(msg_parts) or (notify and chat_config.notification_node_status):
            existing_msg_ids.clear()

        for i, msg in enumerate(msg_parts):
            msg += f"<i>Last update: {latest_updated_at.isoformat(sep=' ', timespec='seconds')}"
            if len(msg_parts) > 0:
                msg += f" ({i+1}/{len(msg_parts)})"
            msg += "</i>"

            logger.info(f"Message part {i} length: {len(msg)}")
            if (notify and chat_config.notification_node_status) or i >= len(existing_msg_ids):
                message = await BOT_APP.bot.send_message(
                    chat_config.chat_id, msg, parse_mode="HTML"
                )
                existing_msg_ids.append(message.id)
            else:
                message = await BOT_APP.bot.edit_message_text(
                    msg, chat_config.chat_id, existing_msg_ids[i], parse_mode="HTML"
                )
    except telegram.error.BadRequest as e:
        logger.exception("Bad request while sending overview message!")
        if e.message and e.message == "Message is too long":
            try:
                msg = "EXCEEDED MESSAGE LENGTH LIMIT. Try to remove a node."
                if (notify and chat_config.notification_node_status) or not existing_msg_ids:
                    message = await BOT_APP.bot.send_message(
                        chat_config.chat_id, msg, parse_mode="HTML"
                    )
                    CHAT_ID_MESSAGE_IDS[chat_config.chat_id] = [message.id]
                else:
                    message = await BOT_APP.bot.edit_message_text(
                        msg, chat_config.chat_id, existing_msg_ids[-1], parse_mode="HTML"
                    )
            except Exception as e:
                # This porbably means bot is blocked by user. Delete all nodes only used by this chat id + chat config
                logger.exception(f"Error while sending msg too long message for chat: {chat_config.chat_id}")
                if e is telegram.error.Forbidden:
                    logger.exception(f"Chaught forbidden response after msg too long for chat: {chat_config.chat_id}")
                    delete_chat(chat_config.chat_id)
    except telegram.error.Forbidden:
            logger.exception(f"Chaught forbidden response for chat: {chat_config.chat_id}")
            delete_chat(chat_config.chat_id)
    except Exception:
        logger.exception("Error while sending overview message!")


def split_on_last_double_newline(text, max_length=4000):
    parts = []
    while len(text) > max_length:
        # Find the last \n\n before max_length
        split_index = text.rfind('\n\n', 0, max_length)
        if split_index == -1:
            # If no \n\n found, just force split at max_length
            split_index = max_length
        parts.append(text[:split_index].rstrip())
        text = text[split_index:].lstrip()
    if text:
        parts.append(text)
    return parts


async def config_bot():
    await BOT_APP.bot.set_my_commands(
        [
            ("start", "Starts the bot"),
            ("subscribe", "Subscribe a node"),
            ("unsubscribe", "Unsubscribe a node"),
            ("edit_node_label", "Edit label of a node"),
            ("nodes", "List subscribed nodes"),
            ("show_metrics", "Show metrics for a node"),
            # ("update_all_metrics", "Update metrics for all nodes"),
            ("bonus_roles", "Set amount of bonus roles"),
            ("new_nodes", "Set amount of new nodes in this phase"),
            ("notifications", "Toggle notification settings"),
            ("help", "Show some help"),
        ]
    )
    await BOT_APP.bot.set_chat_menu_button()


if __name__ == "__main__":
    boostrap_db()

    # start
    BOT_APP.add_handler(CommandHandler("start", start))
    BOT_APP.add_handler(CommandHandler("help", help))

    # metrics
    BOT_APP.add_handler(CommandHandler("show_metrics", show_metrics_for_address))
    # BOT_APP.add_handler(CallbackQueryHandler(unsubscribe_node_2))
    BOT_APP.add_handler(
        CallbackQueryHandler(
            handle_show_metrics_for_address, pattern="^metrics___0x[a-fA-F0-9]{40}$"
        )
    )

    # BOT_APP.add_handler(CommandHandler("update_all_metrics", update_all_metrics))

    # list nodes
    BOT_APP.add_handler(CommandHandler("nodes", list_subscribed_nodes))

    # subscribe
    subscribe_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("subscribe", subscribe_node_1)],
        states={
            1: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    # & filters.Regex(r"(\b0x[a-fA-F0-9]{40}\b)"),
                    subscribe_node_2,
                )
            ],
        },
        fallbacks=[
            MessageHandler(filters.TEXT, node_address_not_valid)
        ],  # CommandHandler("cancel", cancel),
    )
    BOT_APP.add_handler(subscribe_conv_handler)


    # unsubscribe
    unsubscribe_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("unsubscribe", unsubscribe_node_1)],
        states={
            1: [
                CallbackQueryHandler(unsubscribe_node_2)
            ]
        },
        fallbacks=[
            MessageHandler(filters.TEXT, node_address_not_valid)
        ],  # CommandHandler("cancel", cancel),
    )
    BOT_APP.add_handler(unsubscribe_conv_handler)


    # bonus roles
    bonus_roles_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("bonus_roles", handle_bonus_role_1)],
        states={
            1: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    # & filters.Regex(r"(\b0x[a-fA-F0-9]{40}\b)"),
                    handle_bonus_role_2,
                )
            ],
        },
        fallbacks=[
            MessageHandler(filters.TEXT, default_conv_fallback)
        ]
    )
    BOT_APP.add_handler(bonus_roles_conv_handler)

    # new nodes
    new_nodes_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("new_nodes", handle_new_nodes_1)],
        states={
            1: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    # & filters.Regex(r"(\b0x[a-fA-F0-9]{40}\b)"),
                    handle_new_nodes_2,
                )
            ],
        }, 
        fallbacks=[
            MessageHandler(filters.TEXT, default_conv_fallback)
        ]
    )
    BOT_APP.add_handler(new_nodes_conv_handler)


    # BOT_APP.add_handler(CommandHandler("unsubscribe", unsubscribe_node_1))
    # BOT_APP.add_handler(CallbackQueryHandler(unsubscribe_node_2))
    # BOT_APP.add_handler(
    #     CallbackQueryHandler(unsubscribe_node_2, pattern="^0x[a-fA-F0-9]{40}$")
    # )

    # edit label
    edit_label_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("edit_node_label", edit_node_label_1)],
        states={
            1: [
                CallbackQueryHandler(edit_node_label_2)
            ],
            2: [
                MessageHandler(filters.TEXT, edit_node_label_3)
            ]
        },
        fallbacks=[
            MessageHandler(filters.TEXT, node_address_not_valid)
        ],  # CommandHandler("cancel", cancel),
    )
    BOT_APP.add_handler(edit_label_conv_handler)

    # settings
    BOT_APP.add_handler(CommandHandler("notifications", toggle_notifications))
    BOT_APP.add_handler(
        CallbackQueryHandler(handle_toggle_notifications, pattern="^notification___")
    )

    # admin
    # BOT_APP.add_handler(CommandHandler("add_wl", add_wl))
    # BOT_APP.add_handler(CommandHandler("remove_wl", remove_wl))
    # BOT_APP.add_handler(CommandHandler("list_wl", list_wl))
    # BOT_APP.add_handler(CommandHandler("cortensor_discord_wl", add_self_wl))
    BOT_APP.add_handler(CommandHandler("list_users", list_users))
    BOT_APP.add_handler(CommandHandler("list_nodes", list_nodes))

    ##
    METRIC_SCRAPER = MetricScraper(handle_new_metrics)


    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)  # TODO: needed?
        loop.create_task(config_bot())
        loop.create_task(main())
        loop.create_task(METRIC_SCRAPER.run())
        loop.create_task(BOT_APP.run_polling())
        loop.run_forever()
    finally:
        BOT_DB_CONNECTION.close()
