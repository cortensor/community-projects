"""MCP Server implementation for Cortensor Network.

This server exposes Cortensor's verifiable AI inference capabilities
through the Model Context Protocol (MCP), enabling integration with
Claude Desktop, Cursor, and other MCP-compatible clients.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    ListToolsResult,
    TextContent,
    Tool,
)

from ..cortensor_client import CortensorClient, CortensorConfig
from ..evidence import EvidenceBundle, create_evidence_bundle


class TaskStore:
    """In-memory store for inference tasks and evidence bundles."""

    def __init__(self) -> None:
        self._tasks: dict[str, dict[str, Any]] = {}
        self._bundles: dict[str, EvidenceBundle] = {}

    def store_task(self, task_id: str, data: dict[str, Any]) -> None:
        self._tasks[task_id] = {
            **data,
            "stored_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        return self._tasks.get(task_id)

    def store_bundle(self, bundle: EvidenceBundle) -> None:
        self._bundles[bundle.bundle_id] = bundle

    def get_bundle(self, bundle_id: str) -> EvidenceBundle | None:
        return self._bundles.get(bundle_id)

    def get_bundle_by_task(self, task_id: str) -> EvidenceBundle | None:
        for bundle in self._bundles.values():
            if bundle.task_id == task_id:
                return bundle
        return None


class CortensorMCPServer:
    """MCP Server that wraps Cortensor Network capabilities."""

    def __init__(self, config: CortensorConfig | None = None):
        self.config = config or CortensorConfig.from_env()
        self.server = Server("cortensor-mcp-gateway")
        self.client: CortensorClient | None = None
        self.task_store = TaskStore()
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Set up MCP request handlers."""

        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """List available Cortensor tools."""
            return ListToolsResult(
                tools=[
                    Tool(
                        name="cortensor_inference",
                        description="Execute verifiable AI inference on Cortensor Network with multi-miner consensus (PoI).",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "prompt": {
                                    "type": "string",
                                    "description": "The prompt to send for inference",
                                },
                                "consensus_threshold": {
                                    "type": "number",
                                    "description": "Minimum consensus score required (0.0-1.0, default 0.66)",
                                    "default": 0.66,
                                },
                                "max_tokens": {
                                    "type": "integer",
                                    "description": "Maximum tokens in response",
                                    "default": 4096,
                                },
                            },
                            "required": ["prompt"],
                        },
                    ),
                    Tool(
                        name="cortensor_verify",
                        description="Verify a previous inference result by task ID.",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "task_id": {
                                    "type": "string",
                                    "description": "The task ID to verify",
                                },
                            },
                            "required": ["task_id"],
                        },
                    ),
                    Tool(
                        name="cortensor_miners",
                        description="Get list of available miners and their status.",
                        inputSchema={
                            "type": "object",
                            "properties": {},
                        },
                    ),
                    Tool(
                        name="cortensor_audit",
                        description="Generate an audit trail / evidence bundle for a task.",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "task_id": {
                                    "type": "string",
                                    "description": "The task ID to audit",
                                },
                                "include_miner_details": {
                                    "type": "boolean",
                                    "description": "Include detailed miner responses",
                                    "default": True,
                                },
                            },
                            "required": ["task_id"],
                        },
                    ),
                    Tool(
                        name="cortensor_health",
                        description="Check Cortensor Router health status.",
                        inputSchema={
                            "type": "object",
                            "properties": {},
                        },
                    ),
                ]
            )

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
            """Handle tool calls."""
            if not self.client:
                return CallToolResult(
                    content=[TextContent(type="text", text="Error: Client not initialized")]
                )

            try:
                if name == "cortensor_inference":
                    return await self._handle_inference(arguments)
                elif name == "cortensor_verify":
                    return await self._handle_verify(arguments)
                elif name == "cortensor_miners":
                    return await self._handle_miners()
                elif name == "cortensor_audit":
                    return await self._handle_audit(arguments)
                elif name == "cortensor_health":
                    return await self._handle_health()
                else:
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"Unknown tool: {name}")]
                    )
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")]
                )

    async def _handle_inference(self, args: dict[str, Any]) -> CallToolResult:
        """Handle cortensor_inference tool call."""
        prompt = args.get("prompt", "")
        consensus_threshold = args.get("consensus_threshold", 0.66)
        max_tokens = args.get("max_tokens", 4096)

        if not self.client:
            raise RuntimeError("Client not initialized")

        response = await self.client.inference(
            prompt=prompt,
            max_tokens=max_tokens,
        )

        # Store task data for later audit
        self.task_store.store_task(
            response.task_id,
            {
                "prompt": prompt,
                "content": response.content,
                "consensus": {
                    "score": response.consensus.score,
                    "agreement_count": response.consensus.agreement_count,
                    "total_miners": response.consensus.total_miners,
                    "divergent_miners": response.consensus.divergent_miners,
                },
                "miner_responses": [
                    {
                        "miner_id": mr.miner_id,
                        "content": mr.content,
                        "latency_ms": mr.latency_ms,
                        "model": mr.model,
                    }
                    for mr in response.miner_responses
                ],
                "is_verified": response.is_verified,
                "latency_ms": response.total_latency_ms,
            },
        )

        # Check consensus threshold
        if response.consensus.score < consensus_threshold:
            warning = f"\n\n[Warning: Consensus score {response.consensus.score:.2f} below threshold {consensus_threshold}]"
        else:
            warning = ""

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"{response.content}{warning}\n\n---\nTask ID: {response.task_id}\nConsensus: {response.consensus.score:.2f} ({response.consensus.agreement_count}/{response.consensus.total_miners} miners)",
                )
            ],
            isError=False,
        )

    async def _handle_verify(self, args: dict[str, Any]) -> CallToolResult:
        """Handle cortensor_verify tool call."""
        task_id = args.get("task_id", "")

        if not self.client:
            raise RuntimeError("Client not initialized")

        status = await self.client.get_task_status(task_id)

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=json.dumps(status, indent=2),
                )
            ]
        )

    async def _handle_miners(self) -> CallToolResult:
        """Handle cortensor_miners tool call."""
        if not self.client:
            raise RuntimeError("Client not initialized")

        miners = await self.client.get_miners()

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Available miners ({len(miners)}):\n" + json.dumps(miners, indent=2),
                )
            ]
        )

    async def _handle_audit(self, args: dict[str, Any]) -> CallToolResult:
        """Handle cortensor_audit tool call."""
        task_id = args.get("task_id", "")
        include_details = args.get("include_miner_details", True)

        # Check for existing bundle
        existing_bundle = self.task_store.get_bundle_by_task(task_id)
        if existing_bundle:
            bundle_dict = existing_bundle.to_dict()
            if not include_details:
                bundle_dict.pop("miner_responses", None)
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Evidence Bundle for {task_id}:\n{json.dumps(bundle_dict, indent=2)}",
                    )
                ]
            )

        # Get stored task data
        task_data = self.task_store.get_task(task_id)
        if not task_data:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Error: Task {task_id} not found. Run cortensor_inference first.",
                    )
                ],
                isError=True,
            )

        # Create evidence bundle
        miner_responses = task_data.get("miner_responses", [])
        if not include_details:
            # Redact content but keep metadata
            miner_responses = [
                {
                    "miner_id": mr["miner_id"],
                    "latency_ms": mr["latency_ms"],
                    "model": mr["model"],
                    "content_hash": self._hash_content(mr["content"]),
                }
                for mr in miner_responses
            ]

        bundle = create_evidence_bundle(
            task_id=task_id,
            task_description=task_data.get("prompt", ""),
            execution_steps=[
                {
                    "step": 1,
                    "action": "inference_request",
                    "timestamp": task_data.get("stored_at"),
                }
            ],
            miner_responses=miner_responses,
            consensus_info=task_data.get("consensus", {}),
            validation_result={
                "is_verified": task_data.get("is_verified", False),
                "verification_method": "multi_miner_consensus",
            },
            final_output=task_data.get("content", ""),
            metadata={
                "latency_ms": task_data.get("latency_ms"),
                "mode": "mock" if self.config.mock_mode else "live",
            },
        )

        # Store bundle for future retrieval
        self.task_store.store_bundle(bundle)

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Evidence Bundle Created:\n{bundle.to_json()}",
                )
            ]
        )

    def _hash_content(self, content: str) -> str:
        """Create a short hash of content for privacy-preserving audit."""
        import hashlib
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def _handle_health(self) -> CallToolResult:
        """Handle cortensor_health tool call."""
        if not self.client:
            raise RuntimeError("Client not initialized")

        is_healthy = await self.client.health_check()

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Cortensor Router Status: {'Healthy' if is_healthy else 'Unhealthy'}\nMode: {'Mock' if self.config.mock_mode else 'Live'}",
                )
            ]
        )

    async def run(self) -> None:
        """Run the MCP server."""
        async with CortensorClient(self.config) as client:
            self.client = client
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options(),
                )


def main() -> None:
    """Entry point for the MCP server."""
    server = CortensorMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
