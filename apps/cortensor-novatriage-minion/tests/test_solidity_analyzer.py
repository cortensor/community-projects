"""Deterministic Solidity static analyzer tests."""

from pathlib import Path

import pytest

from novatriage_minion.solidity_analyzer import analyze_solidity_source


SAMPLES_DIR = Path(__file__).resolve().parents[1] / "samples"


def test_vulnerable_vault_detects_all_critical_patterns() -> None:
    result = analyze_solidity_source(file_path=str(SAMPLES_DIR / "VulnerableVault.sol"))
    rule_ids = {item.rule_id for item in result.findings}

    assert result.contract_label == "VulnerableVault.sol"
    assert result.lines_scanned == 51
    assert result.risk_score == 100
    assert result.risk_tier == "CRITICAL"
    assert {
        "TX_ORIGIN_AUTH",
        "UNTRUSTED_DELEGATECALL",
        "REENTRANCY_BEFORE_WRITE",
        "UNCHECKED_LOW_LEVEL_CALL",
        "ARBITRARY_MINT",
        "BLACKLIST_HOOK",
        "OWNER_DRAIN_HOOK",
        "FLOATING_OR_LEGACY_PRAGMA",
    }.issubset(rule_ids)


def test_safe_treasury_scores_minimal() -> None:
    result = analyze_solidity_source(file_path=str(SAMPLES_DIR / "SafeTreasury.sol"))

    assert result.contract_label == "SafeTreasury.sol"
    assert result.finding_count == 0
    assert result.risk_score == 0
    assert result.risk_tier == "MINIMAL"


def test_selfdestruct_and_empty_source_handling() -> None:
    res = analyze_solidity_source(
        source_code="pragma solidity 0.8.24;\ncontract Boom { function kill() external { selfdestruct(payable(msg.sender)); } }\n",
        contract_label="Boom.sol",
    )
    assert any(f.rule_id == "SELFDESTRUCT_PRESENT" for f in res.findings)
    assert res.risk_score == 20
    assert res.risk_tier == "MEDIUM"

    with pytest.raises(ValueError, match="non-empty"):
        analyze_solidity_source(source_code="   ")
