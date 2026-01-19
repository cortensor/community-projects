"""Cortensor Governance Agent - MCP Client for Cortensor Network."""

__version__ = "0.1.0"

from .client import CortensorMCPClient
from .agent import GovernanceAgent

__all__ = ["CortensorMCPClient", "GovernanceAgent", "__version__"]
