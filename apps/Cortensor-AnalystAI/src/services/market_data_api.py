# src/services/market_data_api.py

import logging
import requests
import yfinance as yf # Import yfinance di sini
from thefuzz import fuzz
from src.config import COINGECKO_API_KEY, FMP_API_KEY
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# --- API URLs ---
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
FMP_API_URL = "https://financialmodelingprep.com/api/v3"

def calculate_price_change(prices: list) -> float:
    """Calculates percentage change between the first and last price in a list."""
    if not prices or len(prices) < 2:
        return 0.0
    # Mengambil harga terbaru (akhir list) dan harga terlama (awal list)
    start_price = prices[0]
    end_price = prices[-1]
    if start_price == 0: # Hindari pembagian dengan nol
        return 0.0
    return ((end_price - start_price) / start_price) * 100

def get_crypto_data(topic: str) -> dict | None:
    """Fetches crypto data from CoinGecko, including historical changes."""
    headers = {"x-cg-demo-api-key": COINGECKO_API_KEY, "Accept": "application/json"}
    try:
        search_response = requests.get(f"{COINGECKO_API_URL}/search", headers=headers, params={'query': topic}, timeout=10)
        search_data = search_response.json()
        if not search_data.get('coins'):
            return None
        
        best_match_coin = None
        highest_ratio = 0
        for coin in search_data['coins']:
            ratio_name = fuzz.ratio(topic.lower(), coin['name'].lower())
            ratio_symbol = fuzz.ratio(topic.lower(), coin['symbol'].lower())
            current_ratio = max(ratio_name, ratio_symbol)

            if current_ratio > highest_ratio and current_ratio >= 80:
                highest_ratio = current_ratio
                best_match_coin = coin
        
        if not best_match_coin:
            logger.warning(f"No sufficiently close crypto match found for '{topic}'.")
            return None

        coin_id = best_match_coin['id']
        logger.info(f"Found crypto '{best_match_coin['name']}' ({best_match_coin['symbol']}) with ID: {coin_id}")

        market_response = requests.get(f"{COINGECKO_API_URL}/coins/{coin_id}", headers=headers, timeout=10)
        market_data = market_response.json()
        data = market_data.get('market_data', {})

        # --- Ambil data historis untuk kripto (7 dan 30 hari) ---
        # Untuk 7 hari, gunakan days=7
        # Untuk 30 hari, gunakan days=30
        
        # CoinGecko API requires 'vs_currency' and 'days' for market_chart
        prices_7d = []
        prices_30d = []

        try:
            # Ambil data 7 hari
            url_7d = f"{COINGECKO_API_URL}/coins/{coin_id}/market_chart?vs_currency=usd&days=7"
            response_7d = requests.get(url_7d, headers=headers, timeout=10)
            if response_7d.status_code == 200:
                prices_7d = [p[1] for p in response_7d.json().get('prices', [])]
            
            # Ambil data 30 hari
            url_30d = f"{COINGECKO_API_URL}/coins/{coin_id}/market_chart?vs_currency=usd&days=30"
            response_30d = requests.get(url_30d, headers=headers, timeout=10)
            if response_30d.status_code == 200:
                prices_30d = [p[1] for p in response_30d.json().get('prices', [])]

        except Exception as hist_e:
            logger.warning(f"Could not fetch historical crypto data for '{coin_id}': {hist_e}")

        price_change_7d_pct = calculate_price_change(prices_7d)
        price_change_30d_pct = calculate_price_change(prices_30d)

        return {
            "type": "Crypto", "name": market_data.get('name'), "symbol": market_data.get('symbol', '').upper(),
            "price_change_24h_pct": data.get('price_change_percentage_24h'), "current_price": data.get('current_price', {}).get('usd'),
            "trading_volume_24h": data.get('total_volume', {}).get('usd'), "high_24h": data.get('high_24h', {}).get('usd'),
            "low_24h": data.get('low_24h', {}).get('usd'), "market_cap": data.get('market_cap', {}).get('usd'),
            "circulating_supply": data.get('circulating_supply'),
            "price_change_7d_pct": price_change_7d_pct, # Tambahkan ini
            "price_change_30d_pct": price_change_30d_pct, # Tambahkan ini
            "price_source": "CoinGecko",
            "market_cap_source": "CoinGecko",
        }
    except Exception as e:
        logger.error(f"Error fetching crypto data for '{topic}': {e}")
        return None

def get_stock_data_from_fmp(symbol: str) -> dict | None:
    """
    Fetches stock data from FMP and Yahoo Finance for historical data.
    """
    if not FMP_API_KEY:
        logger.warning("FMP_API_KEY is not configured.")
        return None
    try:
        logger.info(f"Fetching stock data for exact symbol '{symbol.upper()}' from FMP.")
        quote_url = f"{FMP_API_URL}/quote/{symbol.upper()}?apikey={FMP_API_KEY}"
        quote_res = requests.get(quote_url, timeout=10)
        quote_data_list = quote_res.json()

        if not quote_data_list:
            logger.warning(f"FMP API returned no data for exact symbol '{symbol.upper()}'.")
            return None
        
        quote_data = quote_data_list[0] if isinstance(quote_data_list, list) else quote_data_list

        # --- Ambil data historis untuk saham dari yfinance ---
        price_change_7d_pct = 0.0
        price_change_30d_pct = 0.0
        try:
            stock_ticker = yf.Ticker(symbol.upper())
            # Data 7 hari (ambil 8 hari untuk menghitung perubahan dari hari ke-7)
            hist_7d = stock_ticker.history(period="8d")
            if not hist_7d.empty and len(hist_7d) >= 2:
                price_change_7d_pct = calculate_price_change(hist_7d['Close'].tolist())

            # Data 30 hari (ambil 31 hari untuk menghitung perubahan dari hari ke-30)
            hist_30d = stock_ticker.history(period="31d")
            if not hist_30d.empty and len(hist_30d) >= 2:
                price_change_30d_pct = calculate_price_change(hist_30d['Close'].tolist())
            
            logger.debug(f"Historical stock data for {symbol}: 7d={price_change_7d_pct:.2f}%, 30d={price_change_30d_pct:.2f}%")

        except Exception as hist_e:
            logger.warning(f"Could not fetch historical stock data for '{symbol}' from yfinance: {hist_e}")

        return {
            "type": "Stock", "name": quote_data.get('name'), "symbol": quote_data.get('symbol'),
            "company_name": quote_data.get('name'),
            "price_change_pct": quote_data.get('changesPercentage'), "current_price": quote_data.get('price'),
            "trading_volume": quote_data.get('volume'), "high_52w": quote_data.get('yearHigh'),
            "low_52w": quote_data.get('yearLow'), "market_cap": quote_data.get('marketCap'),
            "pe_ratio": quote_data.get('pe', 'N/A'), "eps_ttm": quote_data.get('eps', 'N/A'),
            "dividend_yield": 0.0, "revenue_ttm": None, "debt_equity_ratio": None,
            "price_change_7d_pct": price_change_7d_pct, # Tambahkan ini
            "price_change_30d_pct": price_change_30d_pct, # Tambahkan ini
            "price_source": "FMP",
            "market_cap_source": "FMP",
        }
    except Exception as e:
        logger.error(f"An error occurred in get_stock_data_from_fmp for '{symbol}': {e}")
        return None

def get_market_data(topic: str) -> dict | None:
    """
    Fetches market data by trying Stock first, then Crypto.
    """
    logger.info(f"Attempting to fetch data for user topic: '{topic}'")
    
    stock_result = get_stock_data_from_fmp(topic)
    if stock_result:
        return stock_result

    crypto_result = get_crypto_data(topic)
    if crypto_result:
        return crypto_result

    logger.warning(f"Could not fetch any market data for '{topic}'. Please check the ticker symbol.")
    return None