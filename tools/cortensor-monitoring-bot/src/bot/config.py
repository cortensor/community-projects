# bot/config.py
import os
from dotenv import load_dotenv

# load_dotenv() is now called in main.py

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ARBISCAN_API_KEY = os.getenv("ARBISCAN_API_KEY")
ARBISCAN_API_URL = os.getenv("ARBISCAN_API_URL", "https://api-sepolia.arbiscan.io/api")
LB_API_URL = os.getenv("LB_API_URL", "https://lb-be-5.cortensor.network")
CACHE_TTL = int(os.getenv("CACHE_TTL", "180"))
