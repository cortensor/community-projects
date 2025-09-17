import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict

def load_and_validate_config(path: Path) -> Dict[str, Any]:
    """
    Loads configuration from a JSON file, validates its content, and merges
    it with secrets from environment variables.
    """
    logging.info(f"Loading base configuration from '{path}'.")
    if not path.is_file():
        logging.critical(f"Config file not found at '{path}'. Please create it.")
        sys.exit(1)

    try:
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        logging.critical(f"Failed to parse config file '{path}': {e}")
        sys.exit(1)

    node_addresses = config.get("node_addresses", {})
    address_pattern = re.compile(r"^0x[a-fA-F0-9]{40}$")
    valid_addresses = {}
    for name, address in node_addresses.items():
        if address_pattern.match(address):
            valid_addresses[name] = address
        else:
            logging.warning(
                f"Invalid Ethereum address format for node '{name}': {address}. "
                "This node will be skipped."
            )
    config["node_addresses"] = valid_addresses

    logging.info("Loading secrets from environment variables.")
    secrets = {
        "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID"),
        "rpc_url": os.getenv("RPC_URL"),
        # Optional: sudo password to execute privileged commands (writing to /var/log and /var/run)
        "sudo_password": os.getenv("SUDO_PASSWORD"),
        # Optional: Etherscan/Arbiscan API key
        "etherscan_api_key": os.getenv("ETHERSCAN_API_KEY"),
        # Optional: Etherscan/Arbiscan API base override
        "etherscan_api_base": os.getenv("ETHERSCAN_API_BASE"),
        # Optional: Etherscan v2 chain id (e.g., 421614 for Arbitrum Sepolia, 11155111 for Ethereum Sepolia)
        "etherscan_chain_id": os.getenv("ETHERSCAN_CHAIN_ID"),
        # Also accept Arbiscan-specific envs for convenience
        "arbiscan_api_key": os.getenv("ARBISCAN_API_KEY"),
        "arbiscan_api_base": os.getenv("ARBISCAN_API_BASE"),
    }

    # Normalize to a single key/base in config
    if not secrets.get("etherscan_api_key") and secrets.get("arbiscan_api_key"):
        secrets["etherscan_api_key"] = secrets["arbiscan_api_key"]
    if not secrets.get("etherscan_api_base") and secrets.get("arbiscan_api_base"):
        secrets["etherscan_api_base"] = secrets["arbiscan_api_base"]

    missing_required = [key for key in ["telegram_bot_token", "telegram_chat_id", "rpc_url"] if not secrets.get(key)]
    if missing_required:
        logging.critical(
            f"Missing required environment variables: "
            f"{', '.join(key.upper() for key in missing_required)}. "
            "Please define them in your .env file."
        )
        sys.exit(1)

    config.update(secrets)
    # Note: SUDO_PASSWORD is optional; the bot does not perform start/stop operations.
    
    logging.info("Configuration loaded and validated successfully.")
    return config