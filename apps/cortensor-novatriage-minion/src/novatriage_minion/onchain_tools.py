"""Live public DexScreener / GoPlus preflight and Cloud Run x402 v2 verification clients."""

from __future__ import annotations

import base64
import json
import os
from typing import Any

import httpx

from .models import TokenPreflightResult, X402ProbeResult


DEFAULT_X402_BASE_URL = "https://novacraft-x402-api-981337528602.us-central1.run.app"
_GOPLUS_CHAIN_MAP: dict[str, str] = {
    "ethereum": "1",
    "eth": "1",
    "bsc": "56",
    "polygon": "137",
    "arbitrum": "42161",
    "base": "8453",
    "optimism": "10",
    "avalanche": "43114",
}


def _resolve_timeout(timeout_seconds: float | None = None) -> float:
    if timeout_seconds is not None and timeout_seconds > 0:
        return timeout_seconds
    raw = os.getenv("NOVATRIAGE_HTTP_TIMEOUT", "10.0").strip()
    try:
        return max(1.0, float(raw))
    except ValueError:
        return 10.0


def fetch_token_preflight(
    token_address: str,
    *,
    chain_id: str = "base",
    timeout_seconds: float | None = None,
    client: httpx.Client | None = None,
) -> TokenPreflightResult:
    """Query public DexScreener and GoPlus APIs with clean offline/timeout handling."""
    address = token_address.strip()
    chain = chain_id.strip().lower() or "base"
    goplus_chain = _GOPLUS_CHAIN_MAP.get(chain, chain if chain.isdigit() else "8453")
    timeout = _resolve_timeout(timeout_seconds)

    errors: list[str] = []
    dex_ok = False
    goplus_ok = False
    pair_count = 0
    top_dex = ""
    symbol = ""
    liquidity_usd: float | None = None
    volume_24h_usd: float | None = None
    price_usd = ""
    is_honeypot = "unknown"
    buy_tax = "unknown"
    sell_tax = "unknown"
    is_mintable = "unknown"
    can_take_back_ownership = "unknown"

    owns_client = client is None
    http = client or httpx.Client(timeout=timeout, follow_redirects=True)
    try:
        try:
            dex_resp = http.get(f"https://api.dexscreener.com/latest/dex/tokens/{address}")
            dex_resp.raise_for_status()
            dex_payload = dex_resp.json()
            pairs = list(dex_payload.get("pairs") or [])
            dex_ok = True
            pair_count = len(pairs)
            if pairs:
                pairs.sort(
                    key=lambda p: float(((p.get("liquidity") or {}).get("usd") or 0.0)),
                    reverse=True,
                )
                top = pairs[0]
                top_dex = str(top.get("dexId") or "")
                symbol = str(((top.get("baseToken") or {}).get("symbol")) or "")
                liq_val = (top.get("liquidity") or {}).get("usd")
                vol_val = (top.get("volume") or {}).get("h24")
                liquidity_usd = float(liq_val) if liq_val is not None else None
                volume_24h_usd = float(vol_val) if vol_val is not None else None
                price_usd = str(top.get("priceUsd") or "")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"dexscreener: {type(exc).__name__}: {exc}")

        try:
            gp_url = (
                f"https://api.gopluslabs.io/api/v1/token_security/{goplus_chain}"
                f"?contract_addresses={address}"
            )
            gp_resp = http.get(gp_url)
            gp_resp.raise_for_status()
            gp_payload = gp_resp.json()
            result_map = dict(gp_payload.get("result") or {})
            entry = result_map.get(address.lower()) or result_map.get(address) or {}
            goplus_ok = True
            if isinstance(entry, dict) and entry:
                is_honeypot = str(entry.get("is_honeypot", "unknown"))
                buy_tax = str(entry.get("buy_tax", "unknown"))
                sell_tax = str(entry.get("sell_tax", "unknown"))
                is_mintable = str(entry.get("is_mintable", "unknown"))
                can_take_back_ownership = str(entry.get("can_take_back_ownership", "unknown"))
                if not symbol:
                    symbol = str(entry.get("token_symbol") or "")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"goplus: {type(exc).__name__}: {exc}")
    finally:
        if owns_client:
            http.close()

    return TokenPreflightResult(
        token_address=address,
        chain_id=chain,
        dexscreener_ok=dex_ok,
        goplus_ok=goplus_ok,
        pair_count=pair_count,
        top_dex=top_dex,
        symbol=symbol,
        liquidity_usd=liquidity_usd,
        volume_24h_usd=volume_24h_usd,
        price_usd=price_usd,
        is_honeypot=is_honeypot,
        buy_tax=buy_tax,
        sell_tax=sell_tax,
        is_mintable=is_mintable,
        can_take_back_ownership=can_take_back_ownership,
        errors=errors,
    )


def decode_x402_payment_required_header(header_value: str) -> dict[str, Any]:
    """Decode base64-encoded x402 v2 PAYMENT-REQUIRED header JSON."""
    raw = header_value.strip()
    if not raw:
        return {}
    padded = raw + ("=" * ((4 - len(raw) % 4) % 4))
    decoded = base64.b64decode(padded.encode("ascii")).decode("utf-8")
    payload = json.loads(decoded)
    return dict(payload) if isinstance(payload, dict) else {}


def probe_x402_service(
    *,
    base_url: str = "",
    resource_path: str = "/api/v1/solidity-triage",
    sample_body: dict[str, Any] | None = None,
    timeout_seconds: float | None = None,
    client: httpx.Client | None = None,
) -> X402ProbeResult:
    """Verify /.well-known/x402.json and parse unpaid HTTP 402 PAYMENT-REQUIRED challenge."""
    resolved_base = (base_url or os.getenv("NOVATRIAGE_X402_BASE_URL", "") or DEFAULT_X402_BASE_URL).rstrip("/")
    path = resource_path if resource_path.startswith("/") else f"/{resource_path}"
    timeout = _resolve_timeout(timeout_seconds)

    discovery_status: int | None = None
    x402_version: int | None = None
    service_name = ""
    pay_to = ""
    network = ""
    facilitator = ""
    resource_paths: list[str] = []
    challenge_status: int | None = None
    challenge_amount_atomic = ""
    challenge_asset = ""
    challenge_scheme = ""
    challenge_error = ""

    owns_client = client is None
    http = client or httpx.Client(timeout=timeout, follow_redirects=True)
    try:
        try:
            well_known = http.get(f"{resolved_base}/.well-known/x402.json")
            discovery_status = well_known.status_code
            if well_known.status_code == 200:
                meta = well_known.json()
                x402_version = int(meta["x402Version"]) if meta.get("x402Version") is not None else None
                service_name = str(meta.get("service") or "")
                pay_to = str(meta.get("payTo") or "")
                network = str(meta.get("network") or "")
                facilitator = str(meta.get("facilitator") or "")
                resource_paths = [
                    str(item.get("path") or "")
                    for item in (meta.get("resources") or [])
                    if isinstance(item, dict) and item.get("path")
                ]
        except Exception as exc:  # noqa: BLE001
            challenge_error = f"discovery: {type(exc).__name__}: {exc}"

        try:
            body = sample_body or {
                "contractName": "ProbeSample",
                "sourceCode": "pragma solidity ^0.8.20; contract ProbeSample { uint256 x; }",
            }
            resp = http.post(f"{resolved_base}{path}", json=body)
            challenge_status = resp.status_code
            hdr = resp.headers.get("payment-required") or resp.headers.get("PAYMENT-REQUIRED") or ""
            if hdr:
                decoded = decode_x402_payment_required_header(hdr)
                if x402_version is None and decoded.get("x402Version") is not None:
                    x402_version = int(decoded["x402Version"])
                accepts = list(decoded.get("accepts") or [])
                if accepts and isinstance(accepts[0], dict):
                    first = accepts[0]
                    challenge_amount_atomic = str(first.get("amount") or "")
                    challenge_asset = str(first.get("asset") or "")
                    challenge_scheme = str(first.get("scheme") or "")
                    if not pay_to:
                        pay_to = str(first.get("payTo") or "")
                    if not network:
                        network = str(first.get("network") or "")
        except Exception as exc:  # noqa: BLE001
            prefix = f"{challenge_error}; " if challenge_error else ""
            challenge_error = f"{prefix}challenge: {type(exc).__name__}: {exc}"
    finally:
        if owns_client:
            http.close()

    return X402ProbeResult(
        base_url=resolved_base,
        discovery_status=discovery_status,
        x402_version=x402_version,
        service_name=service_name,
        pay_to=pay_to,
        network=network,
        facilitator=facilitator,
        resource_paths=resource_paths,
        challenge_endpoint=f"{resolved_base}{path}",
        challenge_status=challenge_status,
        challenge_amount_atomic=challenge_amount_atomic,
        challenge_asset=challenge_asset,
        challenge_scheme=challenge_scheme,
        challenge_error=challenge_error,
    )
