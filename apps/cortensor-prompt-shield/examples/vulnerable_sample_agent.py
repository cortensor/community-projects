"""Deliberately misconfigured sample OpenMinion agent for demonstrating AST @tool security findings."""

from __future__ import annotations

import subprocess
from pathlib import Path

from openminion import tool


@tool
def fetch_miner_metrics(node_id: str) -> str:
    """Fetch telemetry for a Cortensor miner node (missing explicit min_scope)."""

    return f"node={node_id} status=online"


@tool(min_scope="READ_ONLY", idempotent=True)
def sync_router_cache(cache_path: str, payload: str) -> str:
    """Incorrectly tagged READ_ONLY despite performing filesystem write!"""

    Path(cache_path).write_text(payload, encoding="utf-8")
    return "synced"


@tool(min_scope="WRITE_SAFE")
def restart_node_service(service_name: str) -> str:
    subprocess.run(["echo", "restarting", service_name], check=False)
    return f"restarted {service_name}"
