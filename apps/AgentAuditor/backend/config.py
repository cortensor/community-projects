"""
Configuration module for Cortensor Agent Auditor
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Cortensor Router Configuration
    cortensor_api_url: str = "http://127.0.0.1:5010"
    cortensor_api_key: str = ""
    cortensor_session_id: int = 0
    
    # Blockchain Configuration
    arbitrum_sepolia_rpc_url: str = "https://sepolia-rollup.arbitrum.io/rpc"
    private_key: str = ""
    session_v2_address: str = ""
    session_queue_v2_address: str = ""
    
    # Cortensor Model Configuration
    cortensor_model_general: str = "cts-llm-2"
    cortensor_model_reasoning: str = "cts-llm-14"
    
    # PoI Configuration
    poi_redundancy: int = 3
    poi_num_nodes: int = 3  # Added
    poi_similarity_threshold: float = 0.6
    
    # PoUW Configuration
    pouw_num_validators: int = 1
    pouw_quality_threshold: float = 0.6  # Added
    pouw_consensus_threshold: float = 0.7  # Added
    pouw_confidence_weight_poi: float = 0.5
    pouw_confidence_weight_pouw: float = 0.5
    
    # Database
    database_url: str = "sqlite:///./agent_auditor.db"
    
    # IPFS Configuration
    ipfs_provider: str = "pinata"
    pinata_api_key: Optional[str] = None
    pinata_secret_key: Optional[str] = None
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str = ""
    secret_key: str = "change-this-secret-key"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


# Global settings instance
settings = Settings()
