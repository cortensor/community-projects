# src/config.py
import os
from dotenv import load_dotenv
"""
Global configuration for the Telegram bot.

Additions:
- SYSTEM_PROMPT: steer the model to produce short, factual, to-the-point answers.
- BRIEF_BY_DEFAULT: when True, post-processing will keep answers concise unless
    the user explicitly asks for more details (e.g., "jelaskan", "lebih detail").
"""

# Short, factual, and to-the-point by default
BRIEF_BY_DEFAULT: bool = True

FLEX_OUTPUT: bool = os.getenv("FLEX_OUTPUT", "false").lower() in {"1", "true", "yes"}
DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "en").lower()

# Strict prompt (safe defaults, deterministic rendering)
STRICT_SYSTEM_PROMPT: str = (
    "You are a helpful assistant."
    f" Answer only the user's latest message. Default to {DEFAULT_LANGUAGE} unless the user speaks another language explicitly."
    " Be concise and to the point."
    " If the user greets (e.g., 'Morning', 'Selamat pagi'), reply with a short greeting."
    " Provide more detail ONLY if the user explicitly asks (e.g., 'jelaskan', 'lebih detail', 'explain', 'how', 'why')."
    " Do not include transcripts (no 'User:'/'Assistant:'), no analysis steps, no headings, no 'Step 1', no scaffolding."
    " Do not echo the user's message. Do not include disclaimers or offers like 'Would you like to know more?'."
    " Avoid code blocks unless the user requests code. If code is requested, provide one minimal, correct snippet only."
    " If unsure, say 'Saya tidak yakin' or 'I'm not sure' briefly."
    " Important formatting rules:"
    " - Produce EXACTLY ONE <final>...</final> block and NOTHING ELSE outside it."
    " - Do NOT output any text before or after the <final> block."
    " - When listing multiple items, use a newline-separated numbered list: '1. ...\n2. ...\n3. ...'"
    " - Do NOT escape dots in list markers; use '1. ' not '1\.'."
)

# Flex prompt (more ChatGPT-like, less rigid formatting)
FLEX_SYSTEM_PROMPT: str = (
    "You are a helpful assistant."
    f" Answer only the user's latest message. Default to {DEFAULT_LANGUAGE} unless the user speaks another language explicitly."
    " Be clear and concise by default; add details only when asked."
    " Avoid transcripts or analysis steps."
    " If code is requested, provide one minimal, correct snippet."
    " Use natural Markdown formatting; you do not need to wrap answers in special tags."
)

# Select prompt by mode
SYSTEM_PROMPT: str = FLEX_SYSTEM_PROMPT if FLEX_OUTPUT else STRICT_SYSTEM_PROMPT

# Load environment variables from the .env file in the root directory
load_dotenv()

# --- Telegram Bot Configuration ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# --- Cortensor API Configuration ---
CORTENSOR_API_URL = os.getenv("CORTENSOR_API_URL")
CORTENSOR_API_KEY = os.getenv("CORTENSOR_API_KEY")
CORTENSOR_SESSION_ID = os.getenv("CORTENSOR_SESSION_ID")
CO_TEMPERATURE = float(os.getenv("CORTENSOR_TEMPERATURE", "0.3"))
CO_TOP_P = float(os.getenv("CORTENSOR_TOP_P", "0.9"))
CO_TOP_K = int(os.getenv("CORTENSOR_TOP_K", "40"))
CO_N = int(os.getenv("CORTENSOR_N", "1"))
CO_PRESENCE_PENALTY = float(os.getenv("CORTENSOR_PRESENCE_PENALTY", "0.0"))
CO_FREQUENCY_PENALTY = float(os.getenv("CORTENSOR_FREQUENCY_PENALTY", "0.0"))
CO_STOP = os.getenv("CORTENSOR_STOP")  # comma-separated list or None
CORTENSOR_CLIENT_REFERENCE_TEMPLATE = os.getenv("CORTENSOR_CLIENT_REFERENCE_TEMPLATE", "eliza-chat-(ID)")
CLIENT_REFERENCE_SALT = os.getenv("CLIENT_REFERENCE_SALT", "")

# Feature toggles (safe defaults: disabled)
USE_PER_USER_SESSION = os.getenv("USE_PER_USER_SESSION", "false").lower() in {"1", "true", "yes"}
USE_CHAT_ID_AS_CLIENT_REFERENCE = os.getenv("USE_CHAT_ID_AS_CLIENT_REFERENCE", "true").lower() in {"1", "true", "yes"}

# --- Optional Wikipedia Facts Guard (default enabled) ---
USE_WIKIPEDIA_GUARD = os.getenv("USE_WIKIPEDIA_GUARD", "true").lower() in {"1", "true", "yes"}

# --- Option: include current date in the system prompt ---
INCLUDE_CURRENT_DATE = os.getenv("INCLUDE_CURRENT_DATE", "true").lower() in {"1", "true", "yes"}

# --- Timezone for date/time answers ---
TIMEZONE = os.getenv("TIMEZONE", "Asia/Jakarta")

# --- Optional News Guard (NewsAPI.org) ---
USE_NEWS_GUARD = os.getenv("USE_NEWS_GUARD", "false").lower() in {"1", "true", "yes"}
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

# --- Llama chat template (RAW prompt) ---
USE_LLAMA_CHAT_TEMPLATE = os.getenv("USE_LLAMA_CHAT_TEMPLATE", "true").lower() in {"1", "true", "yes"}

# --- Configuration Validation ---
# Ensure that all critical environment variables are loaded before starting.
if not all([TELEGRAM_BOT_TOKEN, CORTENSOR_API_URL, CORTENSOR_API_KEY, CORTENSOR_SESSION_ID]):
    raise ValueError("FATAL: One or more required environment variables are missing.")
