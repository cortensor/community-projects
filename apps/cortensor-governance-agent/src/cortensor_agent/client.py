"""MCP Client for Cortensor Router.

Implements the MCP 2024-11-05 protocol to communicate with Cortensor's
HTTP-based MCP server at router1-t0.cortensor.app.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import requests

logger = logging.getLogger(__name__)


@dataclass
class MCPSession:
    """Represents an active MCP session."""
    mcp_session_id: str
    cortensor_session_id: int | None = None
    protocol_version: str = "2024-11-05"


@dataclass
class ToolResult:
    """Result from calling an MCP tool."""
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class CortensorMCPClient:
    """MCP Client for Cortensor Router.

    Connects to Cortensor's MCP server and provides access to:
    - cortensor_completions: Delegate inference tasks
    - cortensor_validate: Validate task results
    - cortensor_create_session: Create Cortensor sessions
    - cortensor_tasks: Get task history
    - cortensor_miners: List available nodes
    """

    DEFAULT_ENDPOINT = "https://router1-t0.cortensor.app/mcp"

    def __init__(self, endpoint: str | None = None, timeout: int = 60):
        self.endpoint = endpoint or self.DEFAULT_ENDPOINT
        self.timeout = timeout
        self._session: MCPSession | None = None
        self._request_id = 0
        self._http = requests.Session()

    @property
    def is_connected(self) -> bool:
        return self._session is not None

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _send_request(self, method: str, params: dict | None = None,
                      is_notification: bool = False) -> dict[str, Any] | None:
        """Send JSON-RPC request to MCP server."""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }

        if not is_notification:
            payload["id"] = self._next_id()

        headers = {"Content-Type": "application/json"}
        if self._session and method != "initialize":
            headers["Mcp-Session-Id"] = self._session.mcp_session_id

        try:
            resp = self._http.post(
                self.endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )

            # Extract session ID from initialize response
            if method == "initialize" and "Mcp-Session-Id" in resp.headers:
                return {
                    "response": resp.json(),
                    "session_id": resp.headers["Mcp-Session-Id"]
                }

            if is_notification:
                return None

            return resp.json()

        except requests.RequestException as e:
            logger.error(f"MCP request failed: {e}")
            raise ConnectionError(f"Failed to communicate with Cortensor: {e}")

    def connect(self) -> MCPSession:
        """Initialize MCP connection and return session."""
        # Step 1: Initialize
        result = self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "cortensor-governance-agent",
                "version": "0.1.0"
            }
        })

        if not result or "session_id" not in result:
            raise ConnectionError("Failed to initialize MCP session")

        self._session = MCPSession(
            mcp_session_id=result["session_id"],
            protocol_version=result["response"]["result"].get("protocolVersion", "2024-11-05")
        )

        # Step 2: Send initialized notification
        self._send_request("notifications/initialized", {}, is_notification=True)

        logger.info(f"Connected to Cortensor MCP: {self._session.mcp_session_id}")
        return self._session

    def list_tools(self) -> list[dict]:
        """List available MCP tools."""
        if not self.is_connected:
            raise RuntimeError("Not connected. Call connect() first.")

        result = self._send_request("tools/list", {})
        if "error" in result:
            raise RuntimeError(f"Failed to list tools: {result['error']}")

        return result.get("result", {}).get("tools", [])

    def call_tool(self, name: str, arguments: dict | None = None) -> ToolResult:
        """Call an MCP tool by name."""
        if not self.is_connected:
            raise RuntimeError("Not connected. Call connect() first.")

        result = self._send_request("tools/call", {
            "name": name,
            "arguments": arguments or {}
        })

        if "error" in result:
            return ToolResult(
                success=False,
                error=result["error"].get("message", str(result["error"]))
            )

        content = result.get("result", {}).get("content", [])

        # Parse content - MCP returns array of content blocks
        data = {}
        for block in content:
            if block.get("type") == "text":
                try:
                    data = json.loads(block.get("text", "{}"))
                except json.JSONDecodeError:
                    data = {"text": block.get("text")}

        return ToolResult(success=True, data=data)

    # Convenience methods for Cortensor tools

    def create_session(self, name: str, min_nodes: int = 1,
                       max_nodes: int = 5, validator_nodes: int = 1) -> ToolResult:
        """Create a Cortensor session for task execution."""
        result = self.call_tool("cortensor_create_session", {
            "name": name,
            "min_nodes": min_nodes,
            "max_nodes": max_nodes,
            "validator_nodes": validator_nodes,
            "mode": 0  # ephemeral
        })

        if result.success and "session_id" in result.data:
            self._session.cortensor_session_id = result.data["session_id"]

        return result

    def completions(self, prompt: str, max_tokens: int = 1024,
                    temperature: float = 0.7) -> ToolResult:
        """Delegate inference task to Cortensor network."""
        if not self._session or not self._session.cortensor_session_id:
            raise RuntimeError("No active Cortensor session. Call create_session() first.")

        return self.call_tool("cortensor_completions", {
            "session_id": self._session.cortensor_session_id,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        })

    def validate(self, task_id: int, miner_address: str,
                 result_data: str) -> ToolResult:
        """Validate task result from a miner."""
        if not self._session or not self._session.cortensor_session_id:
            raise RuntimeError("No active Cortensor session.")

        return self.call_tool("cortensor_validate", {
            "session_id": self._session.cortensor_session_id,
            "task_id": task_id,
            "miner_address": miner_address,
            "result_data": result_data
        })

    def get_tasks(self) -> ToolResult:
        """Get tasks for current session."""
        if not self._session or not self._session.cortensor_session_id:
            raise RuntimeError("No active Cortensor session.")

        return self.call_tool("cortensor_tasks", {
            "session_id": self._session.cortensor_session_id
        })

    def get_miners(self) -> ToolResult:
        """List available miners/nodes."""
        return self.call_tool("cortensor_miners", {})

    def get_status(self) -> ToolResult:
        """Get router status."""
        return self.call_tool("cortensor_status", {})

    def ping(self) -> ToolResult:
        """Health check."""
        return self.call_tool("cortensor_ping", {})

    def close(self):
        """Close the MCP session."""
        self._session = None
        self._http.close()
        logger.info("Disconnected from Cortensor MCP")
