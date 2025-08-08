# src/config.py

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Telegram Bot Configuration ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# DEBUG PRINTS - JANGAN HAPUS INI UNTUK SEMENTARA
print(f"DEBUG: TELEGRAM_BOT_TOKEN loaded as: {TELEGRAM_BOT_TOKEN[:5]}... (first 5 chars)")
print(f"DEBUG: TELEGRAM_BOT_TOKEN type: {type(TELEGRAM_BOT_TOKEN)}")

# --- Cortensor Node Configuration ---
CORTENSOR_API_URL = os.getenv("CORTENSOR_API_URL")
CORTENSOR_API_KEY = os.getenv("CORTENSOR_API_KEY")
CORTENSOR_SESSION_ID = os.getenv("CORTENSOR_SESSION_ID")

# --- External Service API Keys ---
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")
FMP_API_KEY = os.getenv("FMP_API_KEY")

# --- Application Settings ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/tasks.db")
SCHEDULER_DB_PATH = os.getenv("SCHEDULER_DB_PATH", "data/schedules_jobs.db")
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Asia/Jakarta")            
CACHE_PATH = os.getenv("CACHE_PATH", "data/cache.db")
CACHE_EXPIRATION_MINUTES = int(os.getenv("CACHE_EXPIRATION_MINUTES", 60))
RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", 3))
RETRY_DELAY_SECONDS = int(os.getenv("RETRY_DELAY_SECONDS", 10))