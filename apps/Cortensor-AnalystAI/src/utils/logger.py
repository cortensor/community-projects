import logging
import sys
from src.config import LOG_LEVEL

def setup_logging():
    """Configures the root logger for the application."""
    logging.basicConfig(
        level=LOG_LEVEL.upper(),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
    # Silence overly verbose libraries
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.INFO)

    logger = logging.getLogger(__name__)
    logger.info("Logging configured successfully.")
