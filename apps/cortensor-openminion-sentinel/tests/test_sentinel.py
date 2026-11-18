"""Unit and OpenMinion integration tests for Cortensor OpenMinion Sentinel."""

from __future__ import annotations

import json
import unittest

from openminion import MemoryBundle

from sentinel.engine import run_consensus_audit
from sentinel.probes import run_openminion_probes
from sentinel.rpc_tools import (
    DEFAULT_TARGETS,
    ZERO_ADDRESS,
    analyze_control_plane,
    classify_control_plane_risk,
    decode_address_array,
    decode_address_word,
    decode_uint_word,
)


class RpcAndClassificationTests(unittest.TestCase):
    def test_abi_word_and_array_decoders(self) -> None:
        raw_addr = "0x000000000000000000000000a354f35829ae975e850e23e9615b11da1b3dc4de"
        self.assertEqual(
            decode_address_word(raw_addr),
            "0xa354f35829ae975e850e23e9615b11da1b3dc4de",
        )
        self.assertEqual(decode_address_word("0x" + "0" * 64), ZERO_ADDRESS)
        self.assertEqual(decode_uint_word("0x" + "0" * 63 + "6"), 6)
        self.assertIsNone(decode_uint_word("0x"))

        # ABI-encoded dynamic address[] with 2 entries: offset=32, length=2, addr1, addr2
        offset = "0000000000000000000000000000000000000000000000000000000000000020"
        length = "0000000000000000000000000000000000000000000000000000000000000002"
        a1 = "0000000000000000000000001111111111111111111111111111111111111111"
        a2 = "0000000000000000000000002222222222222222222222222222222222222222"
        decoded = decode_address_array("0x" + offset + length + a1 + a2)
        self.assertEqual(
            decoded,
            [
                "0x1111111111111111111111111111111111111111",
                "0x2222222222222222222222222222222222222222",
            ],
        )

    def test_risk_classification_tiers(self) -> None:
        # 6/9 Safe non-proxy -> LOW risk
        tier_low, score_low, _ = classify_control_plane_risk(
            is_contract=True,
            eip1967_implementation=ZERO_ADDRESS,
            eip1967_admin=ZERO_ADDRESS,
            governance_or_owner="0xfeb4acf3df3cdea7399794d0869ef76a6efaff52",
            governance_kind="multisig",
            safe_threshold=6,
            safe_owner_count=9,
            timelock_delay_seconds=None,
        )
        self.assertEqual(tier_low, "LOW")
        self.assertLess(score_low, 30)

        # Proxy + bare EOA -> CRITICAL risk
        tier_crit, score_crit, _ = classify_control_plane_risk(
            is_contract=True,
            eip1967_implementation="0x1111111111111111111111111111111111111111",
            eip1967_admin="0x2222222222222222222222222222222222222222",
            governance_or_owner="0x3333333333333333333333333333333333333333",
            governance_kind="eoa",
            safe_threshold=None,
            safe_owner_count=None,
            timelock_delay_seconds=None,
        )
        self.assertEqual(tier_crit, "CRITICAL")
        self.assertGreaterEqual(score_crit, 75)

    def test_offline_control_plane_fixture_analysis(self) -> None:
        report = analyze_control_plane(
            chain=DEFAULT_TARGETS[0]["chain"],
            address=DEFAULT_TARGETS[0]["address"],
            target_id=DEFAULT_TARGETS[0]["id"],
            name=DEFAULT_TARGETS[0]["name"],
            offline=True,
        )
        self.assertTrue(report.is_contract)
        self.assertEqual(report.governance_kind, "multisig")
        self.assertEqual(report.safe_threshold, 6)
        self.assertEqual(report.risk_tier, "LOW")


class OpenMinionSentinelTests(unittest.TestCase):
    def test_eight_openminion_sdk_probes(self) -> None:
        summary = run_openminion_probes()
        self.assertEqual(summary["total_probes"], 8)
        self.assertEqual(
            summary["failed"],
            0,
            msg=f"Probe failures: {json.dumps(summary['probes'], indent=2)}",
        )

    def test_dual_agent_consensus_and_fail_closed_handoff(self) -> None:
        target = dict(DEFAULT_TARGETS[0])
        agreed = run_consensus_audit(
            target=target,
            offline_rpc=True,
            provider_mode="cortensor",
            use_loopback=True,
            force_disagree=False,
        )
        self.assertEqual(agreed.primary_run_state, "completed")
        self.assertEqual(agreed.skeptic_run_state, "completed")
        self.assertEqual(agreed.consensus_status, "AGREED")
        self.assertEqual(agreed.final_risk_tier, "LOW")
        self.assertFalse(agreed.escalated_via_handoff)

        bundle = MemoryBundle.from_json(agreed.memory_bundle_json)
        self.assertEqual(bundle.version, "memory_bundle.v1")
        self.assertEqual(len(bundle.items), 1)

        fail_closed = run_consensus_audit(
            target=target,
            offline_rpc=True,
            provider_mode="cortensor",
            use_loopback=True,
            force_disagree=True,
        )
        self.assertEqual(fail_closed.consensus_status, "DISAGREEMENT_FAIL_CLOSED")
        self.assertEqual(fail_closed.final_risk_tier, "HIGH")
        self.assertTrue(fail_closed.escalated_via_handoff)
        self.assertIn("INCIDENT_LOGGED", fail_closed.handoff_output)


if __name__ == "__main__":
    unittest.main()
