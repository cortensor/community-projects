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

if CORTENSOR_TLS_INSECURE:
    logger.getChild('config').warning('CORTENSOR_TLS_INSECURE is enabled. SSL certificate verification is DISABLED for Cortensor requests.')
