# src/config.py

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Telegram Bot Configuration ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# --- Cortensor Node Configuration ---
CORTENSOR_API_URL = os.getenv("CORTENSOR_API_URL")
CORTENSOR_API_KEY = os.getenv("CORTENSOR_API_KEY")
CORTENSOR_SESSION_ID = os.getenv("CORTENSOR_SESSION_ID")

# --- Cortensor AI Model Parameters ---
CORTENSOR_TEMPERATURE = float(os.getenv("CORTENSOR_TEMPERATURE", "0.3"))
CORTENSOR_PROMPT_TYPE = int(os.getenv("CORTENSOR_PROMPT_TYPE", "1"))
CORTENSOR_MAX_TOKENS = int(os.getenv("CORTENSOR_MAX_TOKENS", "5024"))
CORTENSOR_TIMEOUT = int(os.getenv("CORTENSOR_TIMEOUT", "300"))
CORTENSOR_REQUEST_TIMEOUT = int(os.getenv("CORTENSOR_REQUEST_TIMEOUT", "320"))

# --- External Service API Keys ---
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")
FMP_API_KEY = os.getenv("FMP_API_KEY")

# --- External API URLs ---
COINGECKO_API_URL = os.getenv("COINGECKO_API_URL", "https://api.coingecko.com/api/v3")
FMP_API_URL = os.getenv("FMP_API_URL", "https://financialmodelingprep.com/stable")
NEWSAPI_URL = os.getenv("NEWSAPI_URL", "https://newsapi.org/v2")
EXCHANGE_RATE_API_URL = os.getenv("EXCHANGE_RATE_API_URL", "https://api.exchangerate-api.com/v4/latest")

# --- Application Settings ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/tasks.db")
SCHEDULER_DB_PATH = os.getenv("SCHEDULER_DB_PATH", "data/schedules_jobs.db")
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Asia/Jakarta")            
CACHE_PATH = os.getenv("CACHE_PATH", "data/cache.db")
CACHE_EXPIRATION_MINUTES = int(os.getenv("CACHE_EXPIRATION_MINUTES", "60"))
RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "3"))
RETRY_DELAY_SECONDS = int(os.getenv("RETRY_DELAY_SECONDS", "10"))

# --- Currency & Exchange Rate Settings ---
EXCHANGE_RATE_CACHE_DURATION = int(os.getenv("EXCHANGE_RATE_CACHE_DURATION", "3600"))
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "USD")

# --- News Fetch Settings ---
NEWS_LOOKBACK_DAYS = int(os.getenv("NEWS_LOOKBACK_DAYS", "2"))
NEWS_EXTENDED_LOOKBACK_DAYS = int(os.getenv("NEWS_EXTENDED_LOOKBACK_DAYS", "7"))
NEWS_PAGE_SIZE = int(os.getenv("NEWS_PAGE_SIZE", "5"))
NEWS_FUZZY_MATCH_THRESHOLD = int(os.getenv("NEWS_FUZZY_MATCH_THRESHOLD", "75"))

# --- API Request Timeouts (seconds) ---
DEFAULT_API_TIMEOUT = int(os.getenv("DEFAULT_API_TIMEOUT", "10"))
FMP_PROFILE_TIMEOUT = int(os.getenv("FMP_PROFILE_TIMEOUT", "5"))

# --- User Default Settings ---
DEFAULT_ALERTS_THRESHOLD = float(os.getenv("DEFAULT_ALERTS_THRESHOLD", "5.0"))
DEFAULT_DATA_RETENTION_DAYS = int(os.getenv("DEFAULT_DATA_RETENTION_DAYS", "30"))