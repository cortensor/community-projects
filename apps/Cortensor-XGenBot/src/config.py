import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env from workspace root
ENV_LOADED = load_dotenv(dotenv_path=os.path.join(os.getcwd(), '.env')) or load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CORTENSOR_API_URL = os.getenv('CORTENSOR_API_URL')
CORTENSOR_API_KEY = os.getenv('CORTENSOR_API_KEY')
CORTENSOR_SESSION_ID = os.getenv('CORTENSOR_SESSION_ID')

MODEL_PROVIDER = os.getenv('MODEL_PROVIDER', 'deepseek')
MODEL_NAME = os.getenv('MODEL_NAME', 'deepseek-r1')
DEFAULT_TONE = os.getenv('DEFAULT_TONE', 'concise')
DEFAULT_HASHTAGS = (os.getenv('DEFAULT_HASHTAGS') or '').strip()
CORTENSOR_TLS_INSECURE = os.getenv('CORTENSOR_TLS_INSECURE', 'false').lower() in ('1','true','yes','on')
CORTENSOR_TIMEOUT = int(os.getenv('CORTENSOR_TIMEOUT', '45'))
DB_PATH = os.getenv('DB_PATH', os.path.join(os.getcwd(), 'data', 'tweetxgen.db'))

# Prompt mode: 0 = normal (legacy), 1 = RAW (we prepend a system/raw base prompt and send prompt_type to router)
try:
    PROMPT_TYPE = int(os.getenv('PROMPT_TYPE', '0'))
except Exception:
    PROMPT_TYPE = 0

# Optional base RAW prompt (only used if PROMPT_TYPE == 1). Keep concise; dynamic instructions appended after.
RAW_PROMPT = (os.getenv('RAW_PROMPT') or '').strip()

# Dynamic length limits (default aligns with X/Twitter). Increase TWEET_CHAR_LIMIT for long-form previews.
try:
    TWEET_CHAR_LIMIT = int(os.getenv('TWEET_CHAR_LIMIT', '280'))
except Exception:
    TWEET_CHAR_LIMIT = 280

try:
    PREVIEW_CHAR_LIMIT = int(os.getenv('PREVIEW_CHAR_LIMIT', '3900'))  # Telegram limit ~4096
except Exception:
    PREVIEW_CHAR_LIMIT = 3900

# Thread role pattern (comma separated) e.g.: hook,context,insight,detail,cta
THREAD_ROLE_PATTERN = (os.getenv('THREAD_ROLE_PATTERN') or '').strip()
try:
    THREAD_CONTINUE_BATCH = int(os.getenv('THREAD_CONTINUE_BATCH', '3'))
except Exception:
    THREAD_CONTINUE_BATCH = 3

# Optional enumeration format for thread preview.
# Values:
#   'none'     -> no enumeration
#   'ofx'      -> <i/N> prefix (e.g., <1/5> )
#   'fraction' -> i/N prefix (e.g., 1/5 )
# Default changed to 'fraction' per user request (adds 1/N continuity markers).
THREAD_ENUM_FORMAT = (os.getenv('THREAD_ENUM_FORMAT') or 'fraction').strip().lower()

# If true, send thread preview as multiple Telegram messages (one per post) to avoid single-message length limits.
THREAD_SPLIT_SEND = (os.getenv('THREAD_SPLIT_SEND', 'false').lower() in ('1','true','yes','on'))

# Optional comma or newline separated list of words to strip from generated copy.
_irrelevant_raw = (os.getenv('IRRELEVANT_WORDS') or '').replace('\n', ',')
IRRELEVANT_WORDS = [w.strip().lower() for w in _irrelevant_raw.split(',') if w.strip()]

if CORTENSOR_TLS_INSECURE:
    logger.getChild('config').warning('CORTENSOR_TLS_INSECURE is enabled. SSL certificate verification is DISABLED for Cortensor requests.')
