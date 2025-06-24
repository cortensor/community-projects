import logging
import aiohttp
from datetime import datetime, timezone
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

async def _get_failure_reason(session: aiohttp.ClientSession, tx_hash: str, api_key: str) -> Optional[str]:
    """
    An internal helper function to fetch the specific error description for a failed transaction.
    """
    params = {
        "module": "transaction",
        "action": "gettxreceiptstatus",
        "txhash": tx_hash,
        "apikey": api_key,
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
    return None


async def check_failed_transactions(session: aiohttp.ClientSession, address: str, api_key: str) -> List[Dict]:
    """
    Checks the Arbiscan API for recent failed transactions and retrieves their specific failure reasons.
    """
    failed_txs = []
    params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": 10,
        "sort": "desc",
        "apikey": api_key,
    }
    api_url = "https://api-sepolia.arbiscan.io/api"

    try:
        async with session.get(api_url, params=params) as response:
            if response.status != 200:
                logger.warning(
                    f"Arbiscan API returned non-200 status [{response.status}] for address {address}"
                )
                return failed_txs

            data = await response.json()

            if data.get("status") == "1" and isinstance(data.get("result"), list):
                max_age_seconds = 300 
                current_timestamp = int(datetime.now(timezone.utc).timestamp())

                for tx in data["result"]:
                    tx_timestamp = int(tx.get("timeStamp", 0))
                    if (current_timestamp - tx_timestamp) > max_age_seconds:
                        break
                    
                    if tx.get("isError") == "1":
                        tx_hash = tx.get('hash')
                        
                        # --- LOGIC IMPROVEMENT HERE ---
                        # Fetch the specific error reason
                        detailed_reason = await _get_failure_reason(session, tx_hash, api_key)
                        
                        # Provide a fallback message if no specific reason is found
                        if not detailed_reason:
                            detailed_reason = "Execution reverted without a reason string."
                        
                        timestamp_str = datetime.fromtimestamp(tx_timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
                        
                        # Always include the "Reason:" line in the output
                        full_reason = (
                            f"Transaction failed at {timestamp_str}.\n"
                            f"Reason: {detailed_reason}\n"
                            f"View details: https://sepolia.arbiscan.io/tx/{tx_hash}"
                        )
                        failed_txs.append({
                            "hash": tx_hash,
                            "reason": full_reason
                        })
    except Exception as e:
        logger.error(f"An error occurred while checking Arbiscan for {address}: {e}", exc_info=True)

    return failed_txs
