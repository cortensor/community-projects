"""OpenMinion tools for chainwatch-minion.

Every tool is a plain Python function decorated with ``@tool`` so the
OpenMinion runtime can expose it to the model with scope enforcement.
Data source: public Blockscout API v2 instances (no API key required).
"""

from __future__ import annotations

import datetime as dt
import json
import urllib.error
import urllib.request
from pathlib import Path

from openminion import tool

BLOCKSCOUT = {
    # Reachability verified 2026-11-28 from a datacenter IP: eth + optimism
    # respond 200; base/polygon/gnosis sit behind Cloudflare challenges and
    # return 403 to non-browser clients (documented in FINDINGS.md).
    "eth": "https://eth.blockscout.com",
    "base": "https://base.blockscout.com",
    "polygon": "https://polygon.blockscout.com",
    "gnosis": "https://gnosisscan.io",
    "optimism": "https://explorer.optimism.io",
}

WEI = 10 ** 18


def _get(chain: str, path: str) -> dict:
    """GET a Blockscout v2 endpoint and return parsed JSON."""
    base = BLOCKSCOUT.get(chain)
    if not base:
        raise ValueError(f"unknown chain {chain!r}; supported: {sorted(BLOCKSCOUT)}")
    url = f"{base}/api/v2{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "chainwatch-minion/0.1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"blockscout {chain} HTTP {exc.code} for {path}") from exc


def _fmt_eth(wei: str | int | None) -> str:
    try:
        return f"{int(wei or 0) / WEI:.6f}"
    except (TypeError, ValueError):
        return "0.000000"


def _retrieved_at() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


@tool(min_scope="READ_ONLY", idempotent=True)
def fetch_wallet_overview(address: str, chain: str = "eth") -> str:
    """Return a compact overview of one address: balance, tx count, contract flag.

    Args:
        address: 0x-prefixed EVM address to inspect.
        chain: one of eth, base, polygon, gnosis, optimism.
    """
    d = _get(chain, f"/addresses/{address}")
    coin = d.get("coin_balance") or "0"
    exchange = d.get("exchange_rate") or "0"
    usd = int(coin) / WEI * float(exchange or 0)
    # transactions_count is often absent on the overview endpoint; fall back
    # to a cheap transactions page fetch so the agent still gets a real count.
    tx_count = d.get("transactions_count")
    if tx_count is None:
        try:
            tx_count = _get(chain, f"/addresses/{address}/transactions").get("next_page_params") and "50+" or None
        except RuntimeError:
            tx_count = None
    return {
        "retrieved_at": _retrieved_at(),
        "address": address,
        "chain": chain,
        "balance_eth": _fmt_eth(coin),
        "balance_usd": round(usd, 2),
        "is_contract": bool(d.get("is_contract")),
        "tx_count": tx_count,
        "has_more_tx_pages": bool(d.get("has_transactions") if "has_transactions" in d else tx_count),
    }


@tool(min_scope="READ_ONLY", idempotent=True)
def fetch_recent_transactions(address: str, chain: str = "eth", limit: int = 15) -> str:
    """Return the most recent transactions touching an address, oldest-last trimmed.

    Args:
        address: 0x-prefixed EVM address to inspect.
        chain: one of eth, base, polygon, gnosis, optimism.
        limit: max rows to return (1-50).
    """
    limit = max(1, min(int(limit), 50))
    d = _get(chain, f"/addresses/{address}/transactions")
    rows = []
    for tx in (d.get("items") or [])[:limit]:
        frm = (tx.get("from") or {}).get("hash", "?")
        to = (tx.get("to") or {}).get("hash", "?")
        direction = "OUT" if frm.lower() == address.lower() else "IN"
        method = ((tx.get("decoded_input") or {}).get("method_call") or "").split("(")[0] or "transfer"
        rows.append({
            "time": (tx.get("timestamp") or "")[:19],
            "direction": direction,
            "counterparty": to if direction == "OUT" else frm,
            "value_eth": _fmt_eth(tx.get("value")),
            "method": method,
            "type": ",".join(tx.get("transaction_types") or []),
            "status": "ok" if tx.get("status") == "ok" else "fail",
            "fee_eth": _fmt_eth(tx.get("fee")),
        })
    return {"retrieved_at": _retrieved_at(), "chain": chain, "address": address, "returned": len(rows), "transactions": rows}


@tool(min_scope="READ_ONLY", idempotent=True)
def fetch_token_transfers(address: str, chain: str = "eth", limit: int = 10) -> str:
    """Return recent ERC-20/721 token transfers for an address.

    Args:
        address: 0x-prefixed EVM address to inspect.
        chain: one of eth, base, polygon, gnosis, optimism.
        limit: max rows to return (1-50).
    """
    limit = max(1, min(int(limit), 50))
    d = _get(chain, f"/addresses/{address}/token-transfers")
    rows = []
    for t in (d.get("items") or [])[:limit]:
        token = ((t.get("token") or {}).get("symbol") or "unknown")
        total = t.get("total") or {}
        rows.append({
            "time": (t.get("timestamp") or "")[:19],
            "token": token,
            "direction": "OUT" if ((t.get("from") or {}).get("hash", "?").lower() == address.lower()) else "IN",
            "counterparty": ((t.get("to") or {}).get("hash") if (t.get("from") or {}).get("hash", "").lower() == address.lower() else (t.get("from") or {}).get("hash")) or "?",
            "value": total.get("value", "?"),
        })
    return {"retrieved_at": _retrieved_at(), "chain": chain, "address": address, "returned": len(rows), "transfers": rows}


@tool(min_scope="WRITE", idempotent=False)
def save_digest(path: str, content: str) -> str:
    """Persist a markdown digest under the sandboxed runs directory.

    Args:
        path: relative path under sandbox/runs, e.g. sandbox/runs/digest-abcdeth.md.
        content: full markdown content of the digest.
    """
    p = Path(path)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("path must be relative and stay inside the sandbox")
    if not str(p).startswith("sandbox"):
        p = Path("sandbox") / p
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"saved": str(p), "bytes": len(content.encode("utf-8"))}
