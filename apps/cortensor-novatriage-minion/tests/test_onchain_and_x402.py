"""Tests for DexScreener/GoPlus preflight and live Cloud Run x402 v2 probing."""

import base64
import json

import httpx

from novatriage_minion.onchain_tools import (
    DEFAULT_X402_BASE_URL,
    decode_x402_payment_required_header,
    fetch_token_preflight,
    probe_x402_service,
)


def test_fetch_token_preflight_mocked_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "dexscreener.com" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "pairs": [
                        {
                            "dexId": "uniswap",
                            "baseToken": {"symbol": "TEST"},
                            "liquidity": {"usd": 125000.5},
                            "volume": {"h24": 42000.0},
                            "priceUsd": "1.23",
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "result": {
                    "0xabc": {
                        "is_honeypot": "0",
                        "buy_tax": "0.01",
                        "sell_tax": "0.02",
                        "is_mintable": "0",
                        "can_take_back_ownership": "0",
                    }
                }
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    res = fetch_token_preflight("0xABC", chain_id="base", client=client)
    assert res.dexscreener_ok is True
    assert res.goplus_ok is True
    assert res.symbol == "TEST"
    assert res.top_dex == "uniswap"
    assert res.liquidity_usd == 125000.5
    assert res.is_honeypot == "0"
    assert res.errors == []


def test_fetch_token_preflight_offline_timeout_graceful() -> None:
    def failing_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("simulated offline timeout", request=request)

    client = httpx.Client(transport=httpx.MockTransport(failing_handler))
    res = fetch_token_preflight("0x123", chain_id="base", client=client)
    assert res.dexscreener_ok is False
    assert res.goplus_ok is False
    assert len(res.errors) == 2
    assert "ConnectTimeout" in res.errors[0]


def test_decode_x402_payment_required_header_roundtrip() -> None:
    sample = {
        "x402Version": 2,
        "accepts": [{"scheme": "exact", "network": "eip155:8453", "amount": "50000"}],
    }
    encoded = base64.b64encode(json.dumps(sample).encode("utf-8")).decode("ascii")
    decoded = decode_x402_payment_required_header(encoded)
    assert decoded["x402Version"] == 2
    assert decoded["accepts"][0]["amount"] == "50000"


def test_live_cloud_run_x402_discovery_and_402_challenge() -> None:
    res = probe_x402_service(
        base_url=DEFAULT_X402_BASE_URL,
        resource_path="/api/v1/solidity-triage",
        timeout_seconds=15.0,
    )
    assert res.discovery_status == 200
    assert res.x402_version == 2
    assert res.pay_to == "0x445F7447532d3e9300194E289C7C023A5f3CFc9E"
    assert res.network == "eip155:8453"
    assert "/api/v1/solidity-triage" in res.resource_paths
    assert res.challenge_status == 402
    assert res.challenge_amount_atomic == "50000"
    assert res.challenge_asset == "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    assert res.challenge_scheme == "exact"
    assert res.challenge_error == ""
