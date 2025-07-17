import logging
import sys
import os
from pathlib import Path
import requests
from dotenv import load_dotenv

from app.config import load_and_validate_config
from app.watcher.monitor import NodeMonitor

# Load environment variables from .env file
load_dotenv()

CONFIG_FILE_PATH = Path("config.json")

def setup_logging():
    """Configures the root logger."""
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    # Create a 'logs' directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - [%(module)s.%(funcName)s] - %(message)s",
        handlers=[
            logging.FileHandler("logs/watcher.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info(f"Logging initialized at level: {log_level_str}")
    if log_level == logging.DEBUG:
        logging.debug("Debug mode is enabled. Logging will be verbose.")

def validate_telegram_token(token: str) -> None:
    """Checks if the Telegram Bot Token is valid by calling the getMe API."""
    if not token:
        logging.critical("Telegram Bot Token not found in environment variables. Please set TELEGRAM_BOT_TOKEN.")
        sys.exit(1)

    logging.info("Validating Telegram Bot Token...")
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 401:
            logging.critical(
                "Invalid Telegram Bot Token. "
                "Please check the 'TELEGRAM_BOT_TOKEN' value in your .env file."
            )
            sys.exit(1)
        response.raise_for_status()
        
        bot_info = response.json().get("result", {})
        bot_username = bot_info.get("username", "Unknown")
        logging.info(f"Telegram Bot Token is valid. Bot Name: @{bot_username}")

    except requests.RequestException as e:
        logging.error(
            f"Could not connect to the Telegram API to validate the token. "
            f"Please check your network connection. Error: {e}"
        )
        # We don't exit here, as it might be a temporary network issue.
        # The notifier will handle being disabled.

def main():
    """Main function to initialize and run the node monitor."""
    setup_logging()
    logging.info("Starting Cortensor Watcher Bot...")
    
    config = load_and_validate_config(CONFIG_FILE_PATH)
    
    validate_telegram_token(config.get("telegram_bot_token", ""))
    
    monitor = None  # Initialize to None
    try:
        monitor = NodeMonitor(config)
        monitor.run()
    except KeyboardInterrupt:
        logging.info("Shutdown initiated by user (Ctrl+C).")
    except Exception as e:
        logging.critical("A fatal exception occurred in the main thread.", exc_info=True)
        if monitor and monitor.notifier and monitor.notifier.enabled:
            monitor.notifier.send_watcher_error_message(e)
    finally:
        logging.info("Shutting down...")
        if monitor and monitor.notifier and monitor.notifier.enabled:
            monitor.notifier.stop_listener()
            monitor.notifier.send_watcher_stop_message()
        logging.info("Cortensor Watcher Bot has been shut down.")
        sys.exit(0)


if __name__ == "__main__":
    main()
