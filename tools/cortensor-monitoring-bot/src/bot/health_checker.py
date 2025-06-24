import logging
import aiohttp
from typing import Dict, Optional, List # FIX: Add this import for type hinting
from datetime import datetime, timezone
import time
import asyncio

# Assuming these modules exist and are correctly imported from your project structure
from . import utils, config

logger = logging.getLogger(__name__)

# Method IDs to human-readable names, useful for the 'Reason' field
METHODS = {
    '0xf21a494b': 'Commit',
    '0x65c815a5': 'Precommit',
    '0xca6726d9': 'Prepare',
    '0x198e2b8a': 'Create',
    '0x5c36b186': 'PING'
}

async def get_health_data(session: aiohttp.ClientSession, address: str) -> Optional[Dict]:
    """
    Performs a comprehensive health check for a given node address.
    It fetches balance, and recent transactions to build a dynamic health bar
    based on activity in the last 30 minutes.

    :param session: The aiohttp client session for making API requests.
    :param address: The Ethereum address of the node to check.
    :return: A dictionary containing detailed health information, or None if an error occurs.
    """
    try:
        # Fetch Balance and a batch of recent transactions concurrently
        balance_wei, transactions = await asyncio.gather(
            fetch_balance(session, address),
            fetch_transactions(session, address)
        )

        if transactions is None: # If fetching transactions failed, we can't proceed
            return None

        # Process the fetched transactions to build the health bar
        health_bar_emojis = []
        thirty_minutes_ago_ts = int(time.time()) - (30 * 60)
        
        # Filter transactions that occurred within the last 30 minutes
        recent_transactions = []
        for tx in transactions:
            tx_timestamp = int(tx.get("timeStamp", 0))
            if tx_timestamp >= thirty_minutes_ago_ts:
                recent_transactions.append(tx)
            else:
                # Since the list is sorted newest to oldest, we can stop here
                break
        
        # Build the health bar from recent transactions (newest on the right)
        if recent_transactions:
            for tx in reversed(recent_transactions):
                health_bar_emojis.append("✅" if tx.get("isError") == "0" else "❌")

        health_bar = "".join(health_bar_emojis) if health_bar_emojis else "No recent activity"

        # Determine other health metrics from the most recent transaction
        last_tx_hash = "N/A"
        last_tx_time_ago = "N/A"
        reason = "N/A"
        detailed_reason = None
        
        if transactions:
            latest_tx = transactions[0]
            last_tx_hash = latest_tx.get('hash')
            last_tx_time_ago = utils.time_ago(int(latest_tx.get("timeStamp", 0)))
            reason = METHODS.get(latest_tx.get('methodId'), "Unknown")
            
            if latest_tx.get("isError") == "1":
                # If the very last transaction failed, get its specific reason
                detailed_reason = await get_failure_reason(session, last_tx_hash)

        # Assemble the final health data dictionary
        status = "Active" if "minutes" in last_tx_time_ago or "seconds" in last_tx_time_ago else "Inactive"
        balance_eth = f"{int(balance_wei) / 1e18:.4f} ETH" if balance_wei is not None else "N/A"

        return {
            "status": status,
            "reason": reason,
            "detailed_reason": detailed_reason,
            "last_transaction_time": last_tx_time_ago,
            "balance": balance_eth,
            "health_bar": health_bar,
            "tx_count": len(health_bar_emojis),
            "hash": last_tx_hash
        }

    except Exception as e:
        logger.error(f"Failed to get health data for {address}: {e}", exc_info=True)
        return None


async def fetch_balance(session: aiohttp.ClientSession, address: str) -> Optional[int]:
    """Helper function to fetch the ETH balance of an address."""
    params = {
        "module": "account",
        "action": "balance",
        "address": address,
        "tag": "latest",
        "apikey": config.ARBISCAN_API_KEY
    }
    api_url = "https://api-sepolia.arbiscan.io/api"
    try:
        async with session.get(api_url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("status") == "1":
                    return int(data.get("result", 0))
    except Exception as e:
        logger.warning(f"Could not fetch balance for {address}: {e}")
    return None


async def fetch_transactions(session: aiohttp.ClientSession, address: str) -> Optional[List[Dict]]:
    """Helper function to fetch a list of recent transactions."""
    params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": 100,
        "sort": "desc",
        "apikey": config.ARBISCAN_API_KEY,
    }
    api_url = "https://api-sepolia.arbiscan.io/api"
    try:
        async with session.get(api_url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("status") == "1" and isinstance(data.get("result"), list):
                    return data["result"]
    except Exception as e:
        logger.warning(f"Could not fetch transactions for {address}: {e}")
    return None

async def get_failure_reason(session: aiohttp.ClientSession, tx_hash: str) -> Optional[str]:
    """An internal helper function to fetch the specific error description for a failed transaction."""
    params = {
        "module": "transaction",
        "action": "gettxreceiptstatus",
        "txhash": tx_hash,
        "apikey": config.ARBISCAN_API_KEY,
    }
    api_url = "https://api-sepolia.arbiscan.io/api"
    try:
        async with session.get(api_url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("result") and data['result'].get('errDescription'):
                    return data['result']['errDescription']
    except Exception as e:
        logger.error(f"Could not fetch failure reason for tx {tx_hash}: {e}")
    return "Failed to get reason"
