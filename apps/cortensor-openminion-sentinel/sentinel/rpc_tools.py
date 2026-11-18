"""Read-only EVM control-plane inspector for DeFi vaults, proxies, Safes, and timelocks."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

EIP1967_IMPL_SLOT = (
    "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
)
EIP1967_ADMIN_SLOT = (
    "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
)

SELECTOR_OWNER = "0x8da5cb5b"
SELECTOR_GOVERNANCE = "0x5aa6e675"
SELECTOR_GET_THRESHOLD = "0xe75235b8"
SELECTOR_GET_OWNERS = "0xa0e67e2b"
SELECTOR_GET_MIN_DELAY = "0xf27a0c92"
SELECTOR_DELAY = "0x6a42b8f8"

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

CHAIN_RPCS: dict[str, str] = {
    "ethereum": os.environ.get("ETH_RPC_URL", "https://ethereum-rpc.publicnode.com"),
    "base": os.environ.get("BASE_RPC_URL", "https://mainnet.base.org"),
}

DEFAULT_TARGETS: tuple[dict[str, str], ...] = (
    {
        "id": "yearn-og-usdc",
        "name": "Yearn OG USDC (yvUSDC v2)",
        "chain": "ethereum",
        "address": "0xa354F35829Ae975e850e23e9615b11Da1B3dC4DE",
    },
    {
        "id": "spark-usdc-vault",
        "name": "Spark sUSDC Vault (Base)",
        "chain": "base",
        "address": "0x3128a0F7f0ea68E7B7c9B00AFa7E41045828e858",
    },
    {
        "id": "base-usdc-fiat-token",
        "name": "Circle USDC (Base FiatTokenProxy)",
        "chain": "base",
        "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    },
)

# Deterministic offline fallback snapshots so tests/air-gapped demos remain reproducible
OFFLINE_FIXTURES: dict[str, dict[str, Any]] = {
    "ethereum:0xa354f35829ae975e850e23e9615b11da1b3dc4de": {
        "chain": "ethereum",
        "address": "0xa354F35829Ae975e850e23e9615b11Da1B3dC4DE",
        "is_contract": True,
        "code_size_bytes": 45,
        "eip1967_implementation": ZERO_ADDRESS,
        "eip1967_admin": ZERO_ADDRESS,
        "governance_or_owner": "0xfeb4acf3df3cdea7399794d0869ef76a6efaff52",
        "governance_kind": "multisig",
        "safe_threshold": 6,
        "safe_owner_count": 9,
        "timelock_delay_seconds": None,
        "source": "offline-fixture",
    },
    "base:0x3128a0f7f0ea68e7b7c9b00afa7e41045828e858": {
        "chain": "base",
        "address": "0x3128a0F7f0ea68E7B7c9B00AFa7E41045828e858",
        "is_contract": True,
        "code_size_bytes": 163,
        "eip1967_implementation": "0x6acc02ddd82206a44ff4ec13977e63d1a29c7723",
        "eip1967_admin": ZERO_ADDRESS,
        "governance_or_owner": ZERO_ADDRESS,
        "governance_kind": "unknown",
        "safe_threshold": None,
        "safe_owner_count": None,
        "timelock_delay_seconds": None,
        "source": "offline-fixture",
    },
    "base:0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": {
        "chain": "base",
        "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "is_contract": True,
        "code_size_bytes": 1852,
        "eip1967_implementation": ZERO_ADDRESS,
        "eip1967_admin": ZERO_ADDRESS,
        "governance_or_owner": "0x3abd6f64a422225e61e435bae41db12096106df7",
        "governance_kind": "eoa",
        "safe_threshold": None,
        "safe_owner_count": None,
        "timelock_delay_seconds": None,
        "source": "offline-fixture",
    },
}


@dataclass(frozen=True)
class ControlPlaneReport:
    """Structured security assessment for one smart-contract control plane."""

    target_id: str
    name: str
    chain: str
    address: str
    source: str
    is_contract: bool
    code_size_bytes: int
    eip1967_implementation: str
    eip1967_admin: str
    governance_or_owner: str
    governance_kind: str
    safe_threshold: int | None
    safe_owner_count: int | None
    timelock_delay_seconds: int | None
    risk_tier: str
    risk_score: int
    findings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def rpc_call(
    rpc_url: str, method: str, params: list[Any], timeout_seconds: float = 8.0
) -> Any:
    """Execute one read-only JSON-RPC call cleanly."""
    payload = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    ).encode("utf-8")
    req = Request(
        rpc_url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "cortensor-openminion-sentinel/0.1.0"},
        method="POST",
    )
    with urlopen(req, timeout=timeout_seconds) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    if "error" in raw and raw["error"]:
        raise RuntimeError(f"RPC {method} failed: {raw['error']}")
    return raw.get("result")


def decode_address_word(hex_word: str | None) -> str:
    """Decode the rightmost 20 bytes from a 32-byte EVM hex word."""
    if not hex_word or not isinstance(hex_word, str):
        return ZERO_ADDRESS
    clean = hex_word.lower().removeprefix("0x")
    if len(clean) < 40:
        return ZERO_ADDRESS
    addr = "0x" + clean[-40:]
    return ZERO_ADDRESS if addr == ZERO_ADDRESS else addr


def decode_uint_word(hex_word: str | None) -> int | None:
    """Decode a big-endian uint256 hex word, or return None on empty output."""
    if not hex_word or not isinstance(hex_word, str):
        return None
    clean = hex_word.lower().removeprefix("0x")
    if not clean or len(clean) > 64:
        return None
    try:
        return int(clean, 16)
    except ValueError:
        return None


def decode_address_array(hex_payload: str | None) -> list[str]:
    """Decode an ABI-encoded address[] return buffer (Safe getOwners)."""
    if not hex_payload or not isinstance(hex_payload, str):
        return []
    clean = hex_payload.lower().removeprefix("0x")
    if len(clean) < 128:
        return []
    try:
        offset = int(clean[0:64], 16) * 2
        if offset + 64 > len(clean):
            return []
        count = int(clean[offset : offset + 64], 16)
        start = offset + 64
        if count > 100 or start + count * 64 > len(clean):
            return []
        return [
            decode_address_word(clean[start + i * 64 : start + (i + 1) * 64])
            for i in range(count)
        ]
    except ValueError:
        return []


def _try_eth_call(rpc_url: str, to: str, data: str) -> str | None:
    try:
        res = rpc_call(rpc_url, "eth_call", [{"to": to, "data": data}, "latest"])
        return res if isinstance(res, str) and res != "0x" else None
    except Exception:
        return None


def classify_control_plane_risk(
    *,
    is_contract: bool,
    eip1967_implementation: str,
    eip1967_admin: str,
    governance_or_owner: str,
    governance_kind: str,
    safe_threshold: int | None,
    safe_owner_count: int | None,
    timelock_delay_seconds: int | None,
) -> tuple[str, int, list[str]]:
    """Deterministically score control-plane upgrade/custody exposure."""
    findings: list[str] = []
    score = 10

    if not is_contract:
        findings.append("Target address has zero deployed bytecode (EOA / undeployed).")
        return "CRITICAL", 95, findings

    if eip1967_implementation != ZERO_ADDRESS:
        findings.append(
            f"Mutable EIP-1967 proxy detected (implementation={eip1967_implementation})."
        )
        score += 25
    else:
        findings.append("Non-proxy or custom storage layout (empty EIP-1967 implementation slot).")

    if eip1967_admin != ZERO_ADDRESS:
        findings.append(f"EIP-1967 ProxyAdmin slot set ({eip1967_admin}).")
        score += 10

    if governance_or_owner == ZERO_ADDRESS:
        findings.append("No owner()/governance() address exposed via standard ABI selectors.")
        score += 20
    elif governance_kind == "eoa":
        findings.append(
            f"Privileged authority {governance_or_owner} is a bare EOA (single-key risk)."
        )
        score += 45
    elif governance_kind == "multisig":
        thresh = safe_threshold or 0
        owners = safe_owner_count or 0
        findings.append(
            f"Gnosis Safe governance detected at {governance_or_owner} ({thresh}/{owners} threshold)."
        )
        if thresh <= 1:
            findings.append("Single-signer multisig threshold (1/N) raises admin takeover risk.")
            score += 35
        elif thresh < 3:
            findings.append("Low multisig quorum (<3 signers).")
            score += 15
    elif governance_kind == "timelock":
        delay = timelock_delay_seconds or 0
        findings.append(
            f"Timelock governance at {governance_or_owner} (delay={delay}s)."
        )
        if delay < 3600:
            findings.append("Short timelock delay (<1h) limits incident response window.")
            score += 20
    else:
        findings.append(f"Governance controller is a smart contract ({governance_or_owner}).")
        score += 5

    score = max(0, min(100, score))
    if score >= 75:
        tier = "CRITICAL"
    elif score >= 50:
        tier = "HIGH"
    elif score >= 30:
        tier = "MEDIUM"
    else:
        tier = "LOW"
    return tier, score, findings


def analyze_control_plane(
    *,
    chain: str,
    address: str,
    target_id: str = "custom",
    name: str = "Custom Contract",
    offline: bool = False,
) -> ControlPlaneReport:
    """Inspect a contract's proxy, Safe, and timelock control plane."""
    chain_key = chain.strip().lower()
    addr_norm = address.strip()
    fixture_key = f"{chain_key}:{addr_norm.lower()}"

    facts: dict[str, Any] | None = None
    if not offline and chain_key in CHAIN_RPCS:
        rpc_url = CHAIN_RPCS[chain_key]
        try:
            code = rpc_call(rpc_url, "eth_getCode", [addr_norm, "latest"]) or "0x"
            clean_code = str(code).removeprefix("0x")
            is_contract = len(clean_code) > 0
            impl = decode_address_word(
                rpc_call(rpc_url, "eth_getStorageAt", [addr_norm, EIP1967_IMPL_SLOT, "latest"])
            )
            admin = decode_address_word(
                rpc_call(rpc_url, "eth_getStorageAt", [addr_norm, EIP1967_ADMIN_SLOT, "latest"])
            )

            gov_raw = _try_eth_call(rpc_url, addr_norm, SELECTOR_GOVERNANCE) or _try_eth_call(
                rpc_url, addr_norm, SELECTOR_OWNER
            )
            gov_addr = decode_address_word(gov_raw)
            gov_kind = "unknown"
            safe_threshold: int | None = None
            safe_owner_count: int | None = None
            timelock_delay: int | None = None

            if gov_addr != ZERO_ADDRESS:
                gov_code = str(
                    rpc_call(rpc_url, "eth_getCode", [gov_addr, "latest"]) or "0x"
                ).removeprefix("0x")
                if not gov_code:
                    gov_kind = "eoa"
                else:
                    thresh_word = _try_eth_call(rpc_url, gov_addr, SELECTOR_GET_THRESHOLD)
                    owners_buf = _try_eth_call(rpc_url, gov_addr, SELECTOR_GET_OWNERS)
                    delay_word = _try_eth_call(rpc_url, gov_addr, SELECTOR_GET_MIN_DELAY) or _try_eth_call(
                        rpc_url, gov_addr, SELECTOR_DELAY
                    )
                    if thresh_word is not None and owners_buf is not None:
                        gov_kind = "multisig"
                        safe_threshold = decode_uint_word(thresh_word)
                        safe_owner_count = len(decode_address_array(owners_buf))
                    elif delay_word is not None:
                        gov_kind = "timelock"
                        timelock_delay = decode_uint_word(delay_word)
                    else:
                        gov_kind = "contract"

            facts = {
                "is_contract": is_contract,
                "code_size_bytes": len(clean_code) // 2,
                "eip1967_implementation": impl,
                "eip1967_admin": admin,
                "governance_or_owner": gov_addr,
                "governance_kind": gov_kind,
                "safe_threshold": safe_threshold,
                "safe_owner_count": safe_owner_count,
                "timelock_delay_seconds": timelock_delay,
                "source": f"live-rpc:{chain_key}",
            }
        except (URLError, TimeoutError, RuntimeError, ValueError, OSError):
            facts = None

    if facts is None:
        facts = dict(
            OFFLINE_FIXTURES.get(
                fixture_key,
                {
                    "is_contract": True,
                    "code_size_bytes": 0,
                    "eip1967_implementation": ZERO_ADDRESS,
                    "eip1967_admin": ZERO_ADDRESS,
                    "governance_or_owner": ZERO_ADDRESS,
                    "governance_kind": "unknown",
                    "safe_threshold": None,
                    "safe_owner_count": None,
                    "timelock_delay_seconds": None,
                    "source": "offline-fallback",
                },
            )
        )

    tier, score, findings = classify_control_plane_risk(
        is_contract=facts["is_contract"],
        eip1967_implementation=facts["eip1967_implementation"],
        eip1967_admin=facts["eip1967_admin"],
        governance_or_owner=facts["governance_or_owner"],
        governance_kind=facts["governance_kind"],
        safe_threshold=facts["safe_threshold"],
        safe_owner_count=facts["safe_owner_count"],
        timelock_delay_seconds=facts["timelock_delay_seconds"],
    )

    return ControlPlaneReport(
        target_id=target_id,
        name=name,
        chain=chain_key,
        address=addr_norm,
        source=facts["source"],
        is_contract=facts["is_contract"],
        code_size_bytes=facts["code_size_bytes"],
        eip1967_implementation=facts["eip1967_implementation"],
        eip1967_admin=facts["eip1967_admin"],
        governance_or_owner=facts["governance_or_owner"],
        governance_kind=facts["governance_kind"],
        safe_threshold=facts["safe_threshold"],
        safe_owner_count=facts["safe_owner_count"],
        timelock_delay_seconds=facts["timelock_delay_seconds"],
        risk_tier=tier,
        risk_score=score,
        findings=findings,
    )
