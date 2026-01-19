"""Cortensor Client - MCP and REST API support.

Implements:
- MCP 2024-11-05 protocol for router1-t0.cortensor.app
- Direct REST API for self-hosted router nodes

Usage:
    # MCP mode (default)
    client = CortensorClient()
    client.connect()

    # REST API mode (self-hosted router)
    client = CortensorClient(
        mode="rest",
        rest_endpoint="http://45.32.121.182:5010",
        api_key="your-api-key"
    )
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Literal

import requests

logger = logging.getLogger(__name__)


@dataclass
class CortensorSession:
    """Active session state."""
    mcp_session_id: str | None = None
    cortensor_session_id: int | None = None
    protocol_version: str = "2024-11-05"


@dataclass
class ToolResult:
    """Result from calling a Cortensor tool."""
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class CortensorClient:
    """Cortensor Client supporting MCP and REST API.

    Provides unified access to Cortensor tools:
    - completions / delegate: Delegate inference tasks
    - validate: Validate task results
    - create_session: Create Cortensor sessions
    - tasks: Get task history
    - miners: List available nodes
    """

    DEFAULT_MCP_ENDPOINT = "https://router1-t0.cortensor.app/mcp"

    def __init__(
        self,
        mode: Literal["mcp", "rest"] = "mcp",
        mcp_endpoint: str | None = None,
        rest_endpoint: str | None = None,
        api_key: str | None = None,
        timeout: int = 60
    ):
        self.mode = mode
        self.mcp_endpoint = mcp_endpoint or self.DEFAULT_MCP_ENDPOINT
        self.rest_endpoint = rest_endpoint
        self.api_key = api_key
        self.timeout = timeout
        self._session = CortensorSession()
        self._request_id = 0
        self._http = requests.Session()

    @property
    def is_connected(self) -> bool:
        if self.mode == "mcp":
            return self._session.mcp_session_id is not None
        return self.rest_endpoint is not None

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _mcp_request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        is_notification: bool = False
    ) -> dict[str, Any] | None:
        """Send JSON-RPC request to MCP server."""
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }

        if not is_notification:
            payload["id"] = self._next_id()

        headers = {"Content-Type": "application/json"}
        if self._session.mcp_session_id and method != "initialize":
            headers["Mcp-Session-Id"] = self._session.mcp_session_id

        try:
            resp = self._http.post(
                self.mcp_endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )

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

    def _rest_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Send REST API request to router."""
        if not self.rest_endpoint:
            raise RuntimeError("REST endpoint not configured")

        url = f"{self.rest_endpoint.rstrip('/')}{endpoint}"
        headers = {"Content-Type": "application/json"}

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            if method.upper() == "GET":
                resp = self._http.get(url, headers=headers, timeout=self.timeout)
            else:
                resp = self._http.post(
                    url, json=data or {}, headers=headers, timeout=self.timeout
                )

            resp.raise_for_status()
            return resp.json()

        except requests.RequestException as e:
            logger.error(f"REST request failed: {e}")
            return {"error": str(e)}

    def connect(self) -> CortensorSession:
        """Initialize connection."""
        if self.mode == "rest":
            logger.info(f"REST mode: using {self.rest_endpoint}")
            return self._session

        # MCP mode: Initialize
        result = self._mcp_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "cortensor-governance-agent",
                "version": "0.1.0"
            }
        })

        if not result or "session_id" not in result:
            raise ConnectionError("Failed to initialize MCP session")

        self._session.mcp_session_id = result["session_id"]
        resp = result.get("response", {})
        self._session.protocol_version = (
            resp.get("result", {}).get("protocolVersion", "2024-11-05")
        )

        # Send initialized notification
        self._mcp_request("notifications/initialized", {}, is_notification=True)

        logger.info(f"Connected to Cortensor MCP: {self._session.mcp_session_id}")
        return self._session

    def list_tools(self) -> list[dict[str, Any]]:
        """List available MCP tools (MCP mode only)."""
        if self.mode != "mcp":
            return []

        if not self.is_connected:
            raise RuntimeError("Not connected. Call connect() first.")

        result = self._mcp_request("tools/list", {})
        if result is None or "error" in result:
            err = result.get("error") if result else "No response"
            raise RuntimeError(f"Failed to list tools: {err}")

        return result.get("result", {}).get("tools", [])

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> ToolResult:
        """Call a Cortensor tool."""
        if self.mode == "rest":
            return self._call_rest_tool(name, arguments)

        if not self.is_connected:
            raise RuntimeError("Not connected. Call connect() first.")

        result = self._mcp_request("tools/call", {
            "name": name,
            "arguments": arguments or {}
        })

        if result is None:
            return ToolResult(success=False, error="No response from server")

        if "error" in result:
            err = result["error"]
            msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            return ToolResult(success=False, error=msg)

        content = result.get("result", {}).get("content", [])

        # Parse content blocks
        data: dict[str, Any] = {}
        for block in content:
            if block.get("type") == "text":
                try:
                    data = json.loads(block.get("text", "{}"))
                except json.JSONDecodeError:
                    data = {"text": block.get("text")}

        return ToolResult(success=True, data=data)

    def _call_rest_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None
    ) -> ToolResult:
        """Map tool call to REST API endpoint."""
        args = arguments or {}

        endpoint_map = {
            "cortensor_about": ("GET", "/api/v1/about"),
            "cortensor_status": ("GET", "/api/v1/status"),
            "cortensor_miners": ("GET", "/api/v1/miners"),
            "cortensor_sessions": ("GET", "/api/v1/sessions"),
            "cortensor_ping": ("GET", "/api/v1/ping"),
            "cortensor_info": ("GET", "/api/v1/info"),
            "cortensor_create_session": ("POST", "/api/v1/create"),
            "cortensor_completions": ("POST", "/api/v1/completions"),
            "cortensor_delegate": ("POST", "/api/v1/delegate"),
            "cortensor_validate": ("POST", "/api/v1/validate"),
        }

        if name not in endpoint_map:
            return ToolResult(success=False, error=f"Unknown tool: {name}")

        method, endpoint = endpoint_map[name]

        # Handle session_id in URL for some endpoints
        session_id = args.pop("session_id", None)
        if session_id and name in ("cortensor_completions", "cortensor_tasks"):
            endpoint = f"{endpoint}/{session_id}"

        result = self._rest_request(method, endpoint, args if method == "POST" else None)

        if "error" in result:
            return ToolResult(success=False, data=result, error=result["error"])

        return ToolResult(success=True, data=result)

    # Convenience methods

    def create_session(
        self,
        name: str,
        min_nodes: int = 1,
        max_nodes: int = 5,
        validator_nodes: int = 1
    ) -> ToolResult:
        """Create a Cortensor session for task execution."""
        result = self.call_tool("cortensor_create_session", {
            "name": name,
            "min_nodes": min_nodes,
            "max_nodes": max_nodes,
            "validator_nodes": validator_nodes,
            "mode": 0
        })

        if result.success and "session_id" in result.data:
            self._session.cortensor_session_id = result.data["session_id"]

        return result

    def delegate(
        self,
        prompt: str,
        session_id: int | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> ToolResult:
        """Delegate inference task to Cortensor network."""
        sid = session_id or self._session.cortensor_session_id
        if not sid:
            raise RuntimeError("No session_id. Create or provide one.")

        return self.call_tool("cortensor_delegate", {
            "session_id": sid,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        })

    def completions(
        self,
        prompt: str,
        session_id: int | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> ToolResult:
        """Generate completions (alias for delegate)."""
        sid = session_id or self._session.cortensor_session_id
        if not sid:
            raise RuntimeError("No session_id. Create or provide one.")

        return self.call_tool("cortensor_completions", {
            "session_id": sid,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        })

    def validate(
        self,
        task_id: int,
        miner_address: str,
        result_data: str,
        session_id: int | None = None
    ) -> ToolResult:
        """Validate task result from a miner."""
        sid = session_id or self._session.cortensor_session_id
        if not sid:
            raise RuntimeError("No session_id.")

        return self.call_tool("cortensor_validate", {
            "session_id": sid,
            "task_id": task_id,
            "miner_address": miner_address,
            "result_data": result_data
        })

    def get_tasks(self, session_id: int | None = None) -> ToolResult:
        """Get tasks for a session."""
        sid = session_id or self._session.cortensor_session_id
        if not sid:
            raise RuntimeError("No session_id.")

        return self.call_tool("cortensor_tasks", {"session_id": sid})

    def get_miners(self) -> ToolResult:
        """List available miners/nodes."""
        return self.call_tool("cortensor_miners", {})

    def get_status(self) -> ToolResult:
        """Get router status."""
        return self.call_tool("cortensor_status", {})

    def get_about(self) -> ToolResult:
        """Get router metadata."""
        return self.call_tool("cortensor_about", {})

    def ping(self) -> ToolResult:
        """Health check."""
        return self.call_tool("cortensor_ping", {})

    def close(self) -> None:
        """Close session."""
        self._session = CortensorSession()
        self._http.close()
        logger.info("Disconnected from Cortensor")


# Backward compatibility alias
CortensorMCPClient = CortensorClient
