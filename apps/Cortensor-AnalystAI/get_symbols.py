import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- API Keys from your config ---
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")
FMP_API_KEY = os.getenv("FMP_API_KEY")

# --- API URLs ---
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
FMP_API_URL = "https://financialmodelingprep.com/api/v3"

def get_all_crypto_symbols() -> list[dict]:
    """
    Fetches a list of all supported cryptocurrencies (ID, name, symbol) from CoinGecko.
    This endpoint (coins/list) usually doesn't require a paid API key,
    but it's good practice to include it for consistency or if you have a Pro API key.
    """
    url = f"{COINGECKO_API_URL}/coins/list"
    headers = {}
    if COINGECKO_API_KEY:
        headers["x-cg-demo-api-key"] = COINGECKO_API_KEY # For CoinGecko Demo API Key

    print("Fetching all crypto symbols from CoinGecko...")
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        data = response.json()
        
        symbols = []
        for coin in data:
            symbols.append({
                "id": coin.get("id"),
                "symbol": coin.get("symbol"),
                "name": coin.get("name")
            })
        print(f"Successfully fetched {len(symbols)} crypto symbols.")
        return symbols
    except requests.exceptions.RequestException as e:
        print(f"Error fetching crypto symbols: {e}")
        return []

def get_all_stock_symbols() -> list[dict]:
    """
    Attempts to fetch a list of all supported stock symbols (symbol, name, exchange) from FMP.
    Requires FMP_API_KEY.
    
    NOTE: FMP's comprehensive "all symbols" list endpoints (like `/stock/list` or `/api/v3/company/stock/list`)
    are often part of premium subscriptions or have very strict rate limits on free tiers.
    The `/ref-data/symbols` endpoint attempted here might also be limited or return no data on free plans
    if it's considered a bulk data endpoint.
    """
    if not FMP_API_KEY:
        print("FMP_API_KEY is not configured. Cannot fetch stock symbols.")
        return []

    # This endpoint is generally for reference data, but a full list may still be premium-tier.
    url = f"{FMP_API_URL}/ref-data/symbols?apikey={FMP_API_KEY}" 

    print("Fetching all stock symbols from FMP...")
    try:
        response = requests.get(url, timeout=60) # Increased timeout as list can be large
        response.raise_for_status()
        data = response.json()
        
        symbols = []
        for stock in data:
            symbols.append({
                "symbol": stock.get("symbol"),
                "name": stock.get("name"),
                "exchange": stock.get("exchange")
            })
        print(f"Successfully fetched {len(symbols)} stock symbols.")
        return symbols
    except requests.exceptions.RequestException as e:
        print(f"Error fetching stock symbols from FMP: {e}")
        print("--- IMPORTANT ---")
        print("Note: FMP's full symbol list API often requires a premium subscription or may have strict rate limits on free tiers.")
        print("If you need a comprehensive list of all symbols, consider a paid FMP plan or an alternative data source.")
        print("-----------------")
        return []

if __name__ == "__main__":
    print("--- Fetching Cryptocurrency Symbols ---")
    crypto_symbols = get_all_crypto_symbols()
    if crypto_symbols:
        print("\n--- Example Crypto Symbols (first 10) ---")
        for i, coin in enumerate(crypto_symbols[:10]):
            print(f"ID: {coin['id']}, Symbol: {coin['symbol']}, Name: {coin['name']}")
    else:
        print("No crypto symbols fetched.")

    print("\n--- Fetching Stock Symbols ---")
    stock_symbols = get_all_stock_symbols()
    if stock_symbols:
        print("\n--- Example Stock Symbols (first 10) ---")
        for i, stock in enumerate(stock_symbols[:10]):
            print(f"Symbol: {stock['symbol']}, Name: {stock['name']}, Exchange: {stock['exchange']}")
    else:
        print("No stock symbols fetched.")

    print("\nScript finished.")