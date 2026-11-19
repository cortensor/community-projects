"""Unit tests for portable OpenMinion MemoryBundle audit history."""

from __future__ import annotations

from pathlib import Path

from cortensor_release_gate.memory_store import (
    diff_findings,
    load_prior_check_ids,
    record_audit_memory,
)


def test_memory_bundle_roundtrip_and_diff(tmp_path: Path) -> None:
    bundle_path = tmp_path / "audit_memory.json"
    assert load_prior_check_ids(bundle_path) == []

    record_audit_memory(
        bundle_path,
        target_path="/tmp/repo",
        decision="BLOCKED",
        blocker_ids=["SEC-DOTENV-FILE", "DOC-MISSING-LICENSE"],
        warning_ids=["WIRE-NO-TESTS"],
    )
    prior = load_prior_check_ids(bundle_path)
    assert prior == ["SEC-DOTENV-FILE", "DOC-MISSING-LICENSE"]

    resolved, persistent = diff_findings(
        prior,
        ["DOC-MISSING-LICENSE", "WIRE-NO-OPENMINION"],
    )
    assert resolved == ["SEC-DOTENV-FILE"]
    assert persistent == ["DOC-MISSING-LICENSE"]
