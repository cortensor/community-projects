"""
Xea Governance Oracle - Configuration

Application settings loaded from environment variables.
"""

import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Redis configuration
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "changeme"

    # IPFS
    ipfs_api_url: str = "http://localhost:5001"

    # LLM Settings (Groq)
    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.3-70b-versatile"

    # Cortensor Testnet Configuration
    cortensor_network: str = "testnet0"  # "testnet0" (default) | "testnet1"
    cortensor_router_url: str = "http://localhost:8080"
    cortensor_api_key: str = ""
    cortensor_session_id: str = ""
    
    # Deprecated / Legacy
    use_mock_miners: bool = False

    # Ethereum signing
    signer_private_key: str = ""
    xea_signer_address: str = ""

    # Application settings
    debug: bool = True
    log_level: str = "INFO"
    
    # Miner orchestration settings
    miner_count: int = 5
    miner_quorum: int = 3
    miner_timeout_seconds: int = 12
    max_retries: int = 3
    
    # Mock miner settings (for local development)
    mock_miner_url: str = "http://localhost:8001"
    # Duplicate removed; strictly use the one defined earlier or here. 
    # Let's ensure strict mode is verified.
    
    # Data directories
    data_dir: str = "/data"

    class Config:
        # Resolve .env file from project root: Xea/.env
        # Xea/backend/app/config.py -> ../../../.env
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
