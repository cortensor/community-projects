import os
import logging
import urllib3
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELTELEGRAM_BOT_TOKEN")

# Cortensor API
CORTENSOR_API_URL = os.getenv("CORTENSOR_API_URL")
CORTENSOR_API_KEY = os.getenv("CORTENSOR_API_KEY")
CORTENSOR_SESSION_ID = os.getenv("CORTENSOR_SESSION_ID")
CORTENSOR_TLS_INSECURE = os.getenv("CORTENSOR_TLS_INSECURE", "false").lower() in ("1", "true", "yes")
CORTENSOR_HOST_HEADER = os.getenv("CORTENSOR_HOST_HEADER")
# Use RAW prompt by default for Cortensor (1 = RAW)
CORTENSOR_PROMPT_TYPE = os.getenv("CORTENSOR_PROMPT_TYPE", "1")

# Agent defaults
DEFAULT_AGENT_STYLE = os.getenv("DEFAULT_AGENT_STYLE", "friendly_buddy")
MODEL_PROVIDER_DEFAULT = os.getenv("MODEL_PROVIDER", "deepseek")
MODEL_NAME_DEFAULT = os.getenv("MODEL_NAME", "deepseek-r1")

# Memory settings
MEMORY_ENABLED = os.getenv("MEMORY_ENABLED", "true").lower() in ("1", "true", "yes")
try:
    MEMORY_MAX_TURNS = int(os.getenv("MEMORY_MAX_TURNS", "8"))
except ValueError:
    MEMORY_MAX_TURNS = 8

# Child-safe filtering
CHILD_FILTER_ENABLED = os.getenv("CHILD_FILTER_ENABLED", "true").lower() in ("1", "true", "yes")
CHILD_FILTER_MODE = os.getenv("CHILD_FILTER_MODE", "strict")  # "strict" or "normal"

# Language enforcement
FORCE_ENGLISH = os.getenv("FORCE_ENGLISH", "true").lower() in ("1", "true", "yes")

# Parent mode
PARENT_PIN = os.getenv("PARENT_PIN", "")

# Warnings and TLS adjustments
if os.getenv("TELTELEGRAM_BOT_TOKEN") and not os.getenv("TELEGRAM_BOT_TOKEN"):
    logger.warning("Environment variable typo detected: TELTELEGRAM_BOT_TOKEN. Using it as fallback. Please rename to TELEGRAM_BOT_TOKEN in .env.")
if TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_TOKEN.startswith("YOUR_"):
    logger.warning("TELEGRAM_BOT_TOKEN looks like a placeholder. The bot will not start correctly.")
if CORTENSOR_API_URL and CORTENSOR_API_URL.startswith("YOUR_"):
    logger.warning("CORTENSOR_API_URL looks like a placeholder. Requests will fail.")
if CORTENSOR_API_KEY and CORTENSOR_API_KEY.startswith("YOUR_"):
    logger.warning("CORTENSOR_API_KEY looks like a placeholder. Requests will fail.")
if CORTENSOR_SESSION_ID and str(CORTENSOR_SESSION_ID).startswith("YOUR_"):
    logger.warning("CORTENSOR_SESSION_ID looks like a placeholder. Requests may fail.")
if CORTENSOR_TLS_INSECURE:
    logger.warning("CORTENSOR_TLS_INSECURE is enabled. SSL certificate verification is DISABLED for Cortensor requests.")
    try:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except Exception:
        pass
