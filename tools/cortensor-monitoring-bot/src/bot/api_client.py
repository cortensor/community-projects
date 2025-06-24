# bot/api_client.py
import time
import logging
from typing import List, Dict, Any

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from . import config

logger = logging.getLogger(__name__)
_cache = {}

def _cache_get(key):
    entry = _cache.get(key)
    if entry and time.time() - entry[0] < config.CACHE_TTL:
        return entry[1]
    return None

def _cache_set(key, value):
    _cache[key] = (time.time(), value)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=6),
    retry=retry_if_exception_type(Exception)
)
async def http_get_json(session: aiohttp.ClientSession, url: str, params: Dict = None) -> Any:
    """Helper for HTTP GET requests with retries."""
    async with session.get(url, params=params) as resp:
        if 'application/json' not in resp.headers.get('Content-Type', ''):
            raise aiohttp.ContentTypeError(
                resp.request_info, resp.history, status=resp.status,
                message=f"Expected JSON response but got {resp.headers.get('Content-Type')}", headers=resp.headers
            )
        resp.raise_for_status()
        return await resp.json()

async def fetch_full_leaderboard(session: aiohttp.ClientSession) -> List[Dict]:
    """Fetches and caches the entire leaderboard."""
    key = ("full_leaderboard",)
    if data := _cache_get(key):
        return data
    logger.info("Full leaderboard cache miss. Fetching from API...")
    url = f"{config.LB_API_URL}/leaderboard"
    api_response = await http_get_json(session, url)
    if api_response and isinstance(api_response, list):
        _cache_set(key, api_response)
    return api_response or []

async def fetch_last_n_transactions(session: aiohttp.ClientSession, addr: str, n: int = 12) -> List[Dict]:
    """Fetches the last N transactions for a given address."""
    params = {
        "module": "account", "action": "txlist", "address": addr,
        "page": 1, "offset": n, "sort": "desc",
        "apikey": config.ARBISCAN_API_KEY
    }
    result = await http_get_json(session, config.ARBISCAN_API_URL, params)
    return result.get("result", []) if result else []

async def fetch_address_balance(session: aiohttp.ClientSession, address: str) -> str:
    """Fetches the ETH balance for a given address."""
    params = {
        "module": "account", "action": "balance", "address": address,
        "tag": "latest", "apikey": config.ARBISCAN_API_KEY
    }
    result = await http_get_json(session, config.ARBISCAN_API_URL, params)
    return result.get("result", "0")

async def fetch_transaction_status(session: aiohttp.ClientSession, tx_hash: str) -> Dict:
    """Fetches the detailed status and error description of a transaction."""
    params = {
        "module": "transaction",
        "action": "getstatus", # --- MENGGUNAKAN ENDPOINT YANG LEBIH BAIK ---
        "txhash": tx_hash,
        "apikey": config.ARBISCAN_API_KEY
    }
    result = await http_get_json(session, config.ARBISCAN_API_URL, params)
    return result.get("result", {}) if result else {}
