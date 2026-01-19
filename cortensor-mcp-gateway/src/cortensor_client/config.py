"""Configuration for Cortensor client."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class CortensorConfig:
    """Configuration for connecting to Cortensor Network."""

    router_url: str = field(default_factory=lambda: os.getenv("CORTENSOR_ROUTER_URL", "http://127.0.0.1:5010"))
    ws_url: str = field(default_factory=lambda: os.getenv("CORTENSOR_WS_URL", "ws://127.0.0.1:9001"))
    api_key: str = field(default_factory=lambda: os.getenv("CORTENSOR_API_KEY", "default-dev-token"))
    session_id: int = field(default_factory=lambda: int(os.getenv("CORTENSOR_SESSION_ID", "0")))
    timeout: int = field(default_factory=lambda: int(os.getenv("CORTENSOR_TIMEOUT", "60")))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("CORTENSOR_MAX_TOKENS", "4096")))
    min_miners: int = field(default_factory=lambda: int(os.getenv("CORTENSOR_MIN_MINERS", "3")))
    mock_mode: bool = field(default_factory=lambda: os.getenv("CORTENSOR_MOCK_MODE", "false").lower() == "true")

    @classmethod
    def from_env(cls) -> CortensorConfig:
        """Load configuration from environment variables."""
        return cls()

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        if not self.mock_mode:
            if not self.router_url:
                errors.append("CORTENSOR_ROUTER_URL is required")
            if not self.api_key:
                errors.append("CORTENSOR_API_KEY is required")
        return errors
