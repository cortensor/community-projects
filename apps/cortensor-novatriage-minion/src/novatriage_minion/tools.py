"""OpenMinion @tool definitions for NovaTriage Minion."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openminion import MemoryBundle, tool
from openminion.modules.memory.portability import load_bundle

from .onchain_tools import fetch_token_preflight, probe_x402_service
from .solidity_analyzer import analyze_solidity_source


@tool(
    name="analyze_solidity_contract",
    description=(
        "Run deterministic static security analysis on Solidity source code or a .sol file path "
        "for tx.origin, delegatecall, reentrancy, unchecked calls, and mint/drain hooks."
    ),
    min_scope="READ_ONLY",
    idempotent=True,
    tags=("security", "solidity"),
)
def analyze_solidity_contract(
    file_path: str = "",
    source_code: str = "",
    contract_label: str = "",
) -> dict[str, Any]:
    result = analyze_solidity_source(
        source_code=source_code,
        file_path=file_path,
        contract_label=contract_label,
    )
    return result.model_dump(mode="json")


@tool(
    name="fetch_token_onchain_preflight",
    description=(
        "Query live public DexScreener and GoPlus token security endpoints for liquidity, "
        "honeypot flags, buy/sell taxes, and ownership/mintability signals."
    ),
    min_scope="READ_ONLY",
    idempotent=True,
    tags=("onchain", "preflight"),
)
def fetch_token_onchain_preflight(
    token_address: str,
    chain_id: str = "base",
) -> dict[str, Any]:
    result = fetch_token_preflight(token_address, chain_id=chain_id)
    return result.model_dump(mode="json")


@tool(
    name="probe_x402_endpoint",
    description=(
        "Probe an x402 v2 endpoint (/.well-known/x402.json and unpaid HTTP 402 PAYMENT-REQUIRED "
        "challenge header) without making any fake payments."
    ),
    min_scope="READ_ONLY",
    idempotent=True,
    tags=("x402", "http402"),
)
def probe_x402_endpoint(
    base_url: str = "",
    resource_path: str = "/api/v1/solidity-triage",
) -> dict[str, Any]:
    result = probe_x402_service(base_url=base_url, resource_path=resource_path)
    return result.model_dump(mode="json")


@tool(
    name="recall_triage_memory",
    description=(
        "Search an exported OpenMinion MemoryBundle JSON file for prior contract or token risk verdicts."
    ),
    min_scope="READ_ONLY",
    idempotent=True,
    tags=("memory", "audit"),
)
def recall_triage_memory(bundle_path: str, query: str = "") -> dict[str, Any]:
    path = Path(bundle_path).expanduser()
    if not path.exists():
        return {"found": False, "matches": [], "note": f"Memory bundle not found at {path}"}
    bundle: MemoryBundle = load_bundle(path)
    needle = query.strip().lower()
    matches = [
        item
        for item in bundle.items
        if not needle or needle in json.dumps(item, ensure_ascii=True).lower()
    ]
    return {
        "found": bool(matches),
        "bundle_version": bundle.version,
        "total_items": len(bundle.items),
        "matches": matches[:10],
    }


@tool(
    name="write_triage_report",
    description="Persist a verified NovaTriage JSON/Markdown report artifact to disk (policy-gated).",
    min_scope="WRITE_SAFE",
    idempotent=True,
    tags=("artifact", "report"),
)
def write_triage_report(output_path: str, report_json: str) -> dict[str, Any]:
    target = Path(output_path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    parsed = json.loads(report_json)
    target.write_text(json.dumps(parsed, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"ok": True, "written_path": str(target), "bytes": target.stat().st_size}


@tool(
    name="publish_emergency_freeze_notice",
    description=(
        "Emit an irreversible emergency pause/freeze escalation notice for a critical contract. "
        "Denied by default under fail-closed policy."
    ),
    dangerous=True,
    idempotent=False,
    tags=("escalation", "destructive"),
)
def publish_emergency_freeze_notice(target_name: str, reason: str) -> dict[str, Any]:
    return {
        "ok": True,
        "escalated": True,
        "target_name": target_name,
        "reason": reason,
    }
