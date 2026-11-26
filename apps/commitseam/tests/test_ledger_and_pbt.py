from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings, strategies as st

from commitseam.audit import export_memory_bundle, redact_secrets
from commitseam.junit_parser import FailureItem, parse_junit_failures
from commitseam.ledger import EnqueueResult, FaultMode, InjectedFaultError, QueueLedger

SAMPLE_JUNIT_XML = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="payments" tests="4" failures="2" errors="1" skipped="1">
    <testcase classname="tests.test_payments" name="test_charge_retry">
      <failure message="AssertionError: expected 200 got 503" type="AssertionError">Timeout on gateway</failure>
    </testcase>
    <testcase classname="tests.test_payments" name="test_happy_path"/>
    <testcase classname="tests.test_auth" name="test_token_refresh">
      <error message="RuntimeError: expired lease" type="RuntimeError">Lease expired</error>
    </testcase>
    <testcase classname="tests.test_ledger" name="test_balance_fold">
      <failure message="AssertionError: balance mismatch" type="AssertionError">Expected 100</failure>
    </testcase>
    <testcase classname="tests.test_skipped" name="test_skip_me">
      <skipped message="optional"/>
    </testcase>
  </testsuite>
</testsuites>
"""


# ---------------------------------------------------------------------------
# Independent Oracle Helpers (used by Role 2 PBT & Role 3 Oracle Calibration)
# ---------------------------------------------------------------------------

def oracle_check_enqueue_conservation(
    jobs_rows: list[tuple[str, str, str, str]],
    replays: list[tuple[str, str, str, str | None]],
    initial_job_ids: dict[tuple[str, str], str] | None = None,
) -> tuple[bool, str]:
    """Verify exact-once uniqueness per (request_id, item_id) and stable job_id across replays."""
    seen: dict[tuple[str, str], tuple[str, str]] = {}
    for req_id, item_id, job_id, digest in jobs_rows:
        key = (req_id, item_id)
        if key in seen:
            return False, f"duplicate row for {key}"
        if initial_job_ids is not None and key in initial_job_ids and job_id != initial_job_ids[key]:
            return False, f"stored job_id drifted for {key}: got={job_id}, initial={initial_job_ids[key]}"
        seen[key] = (job_id, digest)
    for req_id, item_id, action, returned_job_id in replays:
        key = (req_id, item_id)
        if key not in seen:
            return False, f"replay missing committed key {key}"
        expected_job_id = initial_job_ids[key] if (initial_job_ids and key in initial_job_ids) else seen[key][0]
        if action != "reused" or returned_job_id != expected_job_id:
            return False, f"replay drift for {key}: action={action}, got={returned_job_id}, want={expected_job_id}"
    return True, "ok"


def oracle_check_completeness(
    expected_ids: set[str],
    committed_ids: list[str],
    always_pre_commit_ids: set[str],
    pending_ids: set[str],
) -> tuple[bool, str]:
    """Verify 0->1 and 1->1 completeness: zero duplicates, zero missing recoverable items."""
    if len(committed_ids) != len(set(committed_ids)):
        return False, "duplicate committed item_ids"
    committed_set = set(committed_ids)
    recoverable = expected_ids - always_pre_commit_ids
    if committed_set != recoverable:
        return False, f"committed={sorted(committed_set)} != recoverable={sorted(recoverable)}"
    if pending_ids != always_pre_commit_ids:
        return False, f"pending={sorted(pending_ids)} != always_pre_commit={sorted(always_pre_commit_ids)}"
    return True, "ok"


def oracle_check_no_secret_leak(serialized_text: str, marker: str) -> tuple[bool, str]:
    if marker in serialized_text:
        return False, "synthetic secret marker leaked into serialized output"
    return True, "ok"


# ---------------------------------------------------------------------------
# Role 1: Concrete Capability Examples (Core Acceptance Suite)
# ---------------------------------------------------------------------------

def test_junit_parser_deterministic_and_persists_expected_items(tmp_path: Path) -> None:
    xml_path = tmp_path / "junit.xml"
    xml_path.write_text(SAMPLE_JUNIT_XML, encoding="utf-8")

    items_a = parse_junit_failures(xml_path)
    items_b = parse_junit_failures(SAMPLE_JUNIT_XML)

    assert items_a == items_b
    assert [it.item_id for it in items_a] == [
        "tests.test_auth::test_token_refresh",
        "tests.test_ledger::test_balance_fold",
        "tests.test_payments::test_charge_retry",
    ]
    assert items_a[0].failure_kind == "error"
    assert items_a[1].failure_kind == "failure"
    assert all(len(it.payload_digest) == 64 for it in items_a)

    ledger = QueueLedger(tmp_path / "queue.sqlite")
    inserted = ledger.register_expected("req-001", items_a)
    assert inserted == 3
    expected = ledger.expected_items("req-001")
    assert [row["item_id"] for row in expected] == [it.item_id for it in items_a]
    assert [row["item_id"] for row in ledger.pending_items("req-001")] == [it.item_id for it in items_a]


def test_ledger_enqueue_atomic_reuse_and_payload_conflict(tmp_path: Path) -> None:
    ledger = QueueLedger(tmp_path / "queue.sqlite")
    items = parse_junit_failures(SAMPLE_JUNIT_XML)
    ledger.register_expected("req-100", items)
    target = items[0]

    first = ledger.enqueue(
        request_id="req-100",
        item_id=target.item_id,
        payload_digest=target.payload_digest,
        attempt_id="att-1",
        session_id="sess-1",
    )
    assert first.action == "created"
    assert first.job_id is not None
    assert first.recovered_job_id is None
    assert first.created_by_attempt_id == "att-1"

    replay = ledger.enqueue(
        request_id="req-100",
        item_id=target.item_id,
        payload_digest=target.payload_digest,
        attempt_id="att-2",
        session_id="sess-2",
    )
    assert replay.action == "reused"
    assert replay.job_id == first.job_id
    assert replay.recovered_job_id == first.job_id
    assert replay.created_by_attempt_id == "att-1"

    conflict = ledger.enqueue(
        request_id="req-100",
        item_id=target.item_id,
        payload_digest="mutated-digest-value",
        attempt_id="att-3",
        session_id="sess-3",
    )
    assert conflict.action == "conflict"
    assert conflict.error_code == "ERR_PAYLOAD_CONFLICT"
    assert conflict.job_id == first.job_id

    jobs = ledger.committed_jobs("req-100")
    assert len(jobs) == 1
    assert jobs[0]["job_id"] == first.job_id
    assert jobs[0]["payload_digest"] == target.payload_digest
    assert jobs[0]["created_by_attempt_id"] == "att-1"


def test_dual_crash_seams_pre_commit_0_to_1_and_post_commit_1_to_1(tmp_path: Path) -> None:
    ledger = QueueLedger(tmp_path / "queue.sqlite")
    items = parse_junit_failures(SAMPLE_JUNIT_XML)
    item_pre, item_post = items[0], items[1]

    # Seam B: pre-commit crash aborts before SQLite COMMIT (0 -> 1 on retry)
    ledger.register_expected("req-pre", [item_pre])
    with pytest.raises(InjectedFaultError) as pre_exc:
        ledger.enqueue(
            request_id="req-pre",
            item_id=item_pre.item_id,
            payload_digest=item_pre.payload_digest,
            attempt_id="att-pre-1",
            session_id="sess-pre-1",
            fault_seam=FaultMode.PRE_COMMIT,
        )
    assert pre_exc.value.seam == FaultMode.PRE_COMMIT
    assert pre_exc.value.committed_job_id is None
    assert len(ledger.committed_jobs("req-pre")) == 0
    assert [p["item_id"] for p in ledger.pending_items("req-pre")] == [item_pre.item_id]

    rec_pre = ledger.enqueue(
        request_id="req-pre",
        item_id=item_pre.item_id,
        payload_digest=item_pre.payload_digest,
        attempt_id="att-pre-2",
        session_id="sess-pre-2",
        fault_seam=FaultMode.NONE,
    )
    assert rec_pre.action == "created"
    assert rec_pre.job_id is not None
    assert len(ledger.committed_jobs("req-pre")) == 1
    assert ledger.pending_items("req-pre") == []
    assert ledger.reconcile("req-pre")["exact_once_ok"] is True

    # Seam A: post-commit crash aborts AFTER COMMIT and BEFORE return (1 -> 1 same job_id on retry)
    ledger.register_expected("req-post", [item_post])
    with pytest.raises(InjectedFaultError) as post_exc:
        ledger.enqueue(
            request_id="req-post",
            item_id=item_post.item_id,
            payload_digest=item_post.payload_digest,
            attempt_id="att-post-1",
            session_id="sess-post-1",
            fault_seam=FaultMode.POST_COMMIT,
        )
    assert post_exc.value.seam == FaultMode.POST_COMMIT
    committed_job_id = post_exc.value.committed_job_id
    assert committed_job_id is not None
    assert len(ledger.committed_jobs("req-post")) == 1
    assert ledger.pending_items("req-post") == []

    # Naive replay of the same item must reuse the exact committed job_id with 0 duplicates
    rec_post = ledger.enqueue(
        request_id="req-post",
        item_id=item_post.item_id,
        payload_digest=item_post.payload_digest,
        attempt_id="att-post-2",
        session_id="sess-post-2",
        fault_seam=FaultMode.NONE,
    )
    assert rec_post.action == "reused"
    assert rec_post.job_id == committed_job_id
    assert rec_post.recovered_job_id == committed_job_id
    assert rec_post.created_by_attempt_id == "att-post-1"
    assert len(ledger.committed_jobs("req-post")) == 1
    assert ledger.reconcile("req-post")["exact_once_ok"] is True


def test_denial_non_mutation_and_memory_bundle_export_redaction(tmp_path: Path) -> None:
    ledger = QueueLedger(tmp_path / "queue.sqlite")
    items = parse_junit_failures(SAMPLE_JUNIT_XML)
    target = items[0]
    ledger.register_expected("req-deny", [target])

    denied = ledger.record_denial(
        request_id="req-deny",
        item_id=target.item_id,
        attempt_id="att-deny-1",
        session_id="sess-deny-1",
        detail="operator declined enqueue",
    )
    assert denied.action == "denied"
    assert denied.job_id is None
    assert ledger.committed_jobs("req-deny") == []
    assert [p["item_id"] for p in ledger.pending_items("req-deny")] == [target.item_id]
    events = ledger.attempt_events("req-deny")
    assert len(events) == 1
    assert events[0]["result"] == "denied"

    # Export MemoryBundle with synthetic secret markers in ledger item_id & redactor; must be read-only & redacted
    fake_secret = "FAKE_SECRET_TOKEN_999"
    fake_api_key = "sk" + "-live-synthetic-1234567890"
    fake_home = "/" + "Users" + "/demo_operator"
    secret_item = FailureItem(
        item_id=f"tests.test_s::test_leak_{fake_secret}",
        test_name=f"test_leak_{fake_secret}",
        classname="tests.test_s",
        failure_kind="failure",
        message="m",
        payload_digest="abcd1234abcd1234",
    )
    ledger.register_expected("req-deny", [secret_item])
    ledger.record_denial(
        request_id="req-deny",
        item_id=secret_item.item_id,
        attempt_id="att-deny-2",
        session_id="sess-deny-2",
    )
    pending_before = ledger.pending_items("req-deny")
    bundle, serialized = export_memory_bundle(
        ledger,
        request_id="req-deny",
        mode="OFFLINE_REPLAY",
        scenario="approval_denial",
    )
    assert ledger.pending_items("req-deny") == pending_before
    assert not (fake_secret in serialized), "synthetic fake secret leaked into MemoryBundle JSON"
    redacted_extra = json.dumps(
        redact_secrets(
            {
                "note": f"authorization Bearer {fake_secret}",
                "api_key": fake_api_key,
                "local_path": f"{fake_home}/Desktop/secret.xml",
            }
        )
    )
    assert not (fake_api_key in redacted_extra), "synthetic sk key leaked after redaction"
    assert not (fake_home in redacted_extra), "synthetic local home path leaked after redaction"
    parsed = json.loads(serialized)
    assert parsed["metadata"]["mode"] == "OFFLINE_REPLAY"
    assert parsed["metadata"]["scenario"] == "approval_denial"
    assert bundle.to_json() == serialized


# ---------------------------------------------------------------------------
# Role 2: Conditional Property-Based Testing Guardians (P1..P5)
# ---------------------------------------------------------------------------

_ID_ST = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-", min_size=1, max_size=16)
_DIGEST_ST = st.text(alphabet="0123456789abcdef", min_size=8, max_size=32)


@settings(max_examples=100, deadline=None)
@given(
    req_id=_ID_ST,
    batch=st.lists(
        st.tuples(_ID_ST, _DIGEST_ST),
        min_size=1,
        max_size=6,
        unique_by=lambda x: x[0],
    ),
    replay_indices=st.lists(st.integers(min_value=0, max_value=5), min_size=1, max_size=12),
)
def test_p1_idempotent_enqueue_conservation(
    req_id: str,
    batch: list[tuple[str, str]],
    replay_indices: list[int],
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ledger = QueueLedger(Path(tmp) / "p1.sqlite")
        items = [
            FailureItem(item_id=iid, test_name=iid, classname="tests.pbt", failure_kind="failure", message="m", payload_digest=dg)
            for iid, dg in batch
        ]
        ledger.register_expected(req_id, items)

        created_jobs: dict[str, str] = {}
        for idx, (iid, dg) in enumerate(batch):
            res = ledger.enqueue(request_id=req_id, item_id=iid, payload_digest=dg, attempt_id=f"c-{idx}")
            assert res.action == "created"
            assert res.job_id is not None
            created_jobs[iid] = res.job_id

        replays: list[tuple[str, str, str, str | None]] = []
        for r_idx, raw_i in enumerate(replay_indices):
            iid, dg = batch[raw_i % len(batch)]
            res = ledger.enqueue(request_id=req_id, item_id=iid, payload_digest=dg, attempt_id=f"r-{r_idx}")
            replays.append((req_id, iid, res.action, res.recovered_job_id))

        with sqlite3.connect(Path(tmp) / "p1.sqlite") as conn:
            rows = conn.execute(
                "SELECT request_id, item_id, job_id, payload_digest FROM rerun_jobs WHERE request_id = ?",
                (req_id,),
            ).fetchall()
        ok, msg = oracle_check_enqueue_conservation(
            rows,
            replays,
            initial_job_ids={(req_id, iid): jid for iid, jid in created_jobs.items()},
        )
        assert ok, msg
        assert len(rows) == len(batch)


@settings(max_examples=100, deadline=None)
@given(
    req_id=_ID_ST,
    batch=st.lists(
        st.tuples(_ID_ST, _DIGEST_ST),
        min_size=1,
        max_size=5,
        unique_by=lambda x: x[0],
    ),
    schedules=st.lists(
        st.lists(st.sampled_from([FaultMode.NONE, FaultMode.PRE_COMMIT, FaultMode.POST_COMMIT]), min_size=1, max_size=4),
        min_size=1,
        max_size=5,
    ),
)
def test_p2_dual_crash_seam_completeness(
    req_id: str,
    batch: list[tuple[str, str]],
    schedules: list[list[FaultMode]],
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ledger = QueueLedger(Path(tmp) / "p2.sqlite")
        items = [
            FailureItem(item_id=iid, test_name=iid, classname="tests.pbt", failure_kind="failure", message="m", payload_digest=dg)
            for iid, dg in batch
        ]
        ledger.register_expected(req_id, items)

        always_pre_commit: set[str] = set()
        post_commit_ids: dict[str, str] = {}

        for idx, (iid, dg) in enumerate(batch):
            item_sched = schedules[idx % len(schedules)]
            if all(m == FaultMode.PRE_COMMIT for m in item_sched):
                always_pre_commit.add(iid)

            for round_idx, seam in enumerate(item_sched):
                # Re-run if item is pending OR we are replaying after a post-commit crash
                try:
                    res = ledger.enqueue(
                        request_id=req_id,
                        item_id=iid,
                        payload_digest=dg,
                        attempt_id=f"a-{idx}-{round_idx}",
                        fault_seam=seam,
                    )
                    if iid in post_commit_ids:
                        assert res.action == "reused"
                        assert res.recovered_job_id == post_commit_ids[iid]
                except InjectedFaultError as exc:
                    if exc.seam == FaultMode.POST_COMMIT:
                        assert exc.committed_job_id is not None
                        post_commit_ids[iid] = exc.committed_job_id

        jobs = ledger.committed_jobs(req_id)
        pending = {p["item_id"] for p in ledger.pending_items(req_id)}
        ok, msg = oracle_check_completeness(
            expected_ids={iid for iid, _ in batch},
            committed_ids=[j["item_id"] for j in jobs],
            always_pre_commit_ids=always_pre_commit,
            pending_ids=pending,
        )
        assert ok, msg


@settings(max_examples=100, deadline=None)
@given(
    req_id=_ID_ST,
    item_id=_ID_ST,
    d1=_DIGEST_ST,
    d2=_DIGEST_ST,
)
def test_p3_payload_conflict_immutability(req_id: str, item_id: str, d1: str, d2: str) -> None:
    if d1 == d2:
        d2 = d1 + "ff"
    with tempfile.TemporaryDirectory() as tmp:
        ledger = QueueLedger(Path(tmp) / "p3.sqlite")
        first = ledger.enqueue(request_id=req_id, item_id=item_id, payload_digest=d1, attempt_id="att-1")
        assert first.action == "created"
        assert first.job_id is not None

        conflict = ledger.enqueue(request_id=req_id, item_id=item_id, payload_digest=d2, attempt_id="att-2")
        assert conflict.action == "conflict"
        assert conflict.error_code == "ERR_PAYLOAD_CONFLICT"

        jobs = ledger.committed_jobs(req_id)
        assert len(jobs) == 1
        assert jobs[0]["job_id"] == first.job_id
        assert jobs[0]["payload_digest"] == d1


@settings(max_examples=100, deadline=None)
@given(
    req_id=_ID_ST,
    batch=st.lists(
        st.tuples(_ID_ST, _DIGEST_ST, st.booleans()),
        min_size=1,
        max_size=6,
        unique_by=lambda x: x[0],
    ),
)
def test_p4_approval_denial_non_mutation(
    req_id: str,
    batch: list[tuple[str, str, bool]],
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ledger = QueueLedger(Path(tmp) / "p4.sqlite")
        items = [
            FailureItem(item_id=iid, test_name=iid, classname="tests.pbt", failure_kind="failure", message="m", payload_digest=dg)
            for iid, dg, _ in batch
        ]
        ledger.register_expected(req_id, items)

        approved_ids: set[str] = set()
        denied_ids: set[str] = set()
        for idx, (iid, dg, allow) in enumerate(batch):
            if allow:
                ledger.enqueue(request_id=req_id, item_id=iid, payload_digest=dg, attempt_id=f"ok-{idx}")
                approved_ids.add(iid)
            else:
                res = ledger.record_denial(request_id=req_id, item_id=iid, attempt_id=f"no-{idx}")
                assert res.action == "denied"
                denied_ids.add(iid)

        committed = {j["item_id"] for j in ledger.committed_jobs(req_id)}
        assert committed == approved_ids
        assert committed.isdisjoint(denied_ids)


@settings(max_examples=100, deadline=None)
@given(
    req_id=_ID_ST,
    item_id=_ID_ST,
    digest=_DIGEST_ST,
    secret_suffix=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", min_size=3, max_size=10),
)
def test_p5_memory_bundle_independence_and_secret_redaction(
    req_id: str,
    item_id: str,
    digest: str,
    secret_suffix: str,
) -> None:
    marker = f"FAKE_SECRET_TOKEN_{secret_suffix}"
    with tempfile.TemporaryDirectory() as tmp:
        ledger = QueueLedger(Path(tmp) / "p5.sqlite")
        item = FailureItem(
            item_id=f"{item_id}_{marker}",
            test_name=item_id,
            classname="tests.pbt",
            failure_kind="failure",
            message="m",
            payload_digest=digest,
        )
        ledger.register_expected(req_id, [item])
        ledger.record_denial(request_id=req_id, item_id=item.item_id, attempt_id="att-p5")
        pending_before = ledger.pending_items(req_id)

        _, serialized = export_memory_bundle(
            ledger,
            request_id=req_id,
            mode="OFFLINE_REPLAY",
            scenario=f"Bearer {marker}",
        )
        assert ledger.pending_items(req_id) == pending_before
        ok, msg = oracle_check_no_secret_leak(serialized, marker)
        assert ok, msg


# ---------------------------------------------------------------------------
# Role 3: Independent Oracle Calibration Controls
# ---------------------------------------------------------------------------

def test_oracle_calibration_catches_known_bad_states() -> None:
    # 1. Duplicate row without UNIQUE constraint
    ok_dup, _ = oracle_check_enqueue_conservation(
        jobs_rows=[("r1", "i1", "job-1", "d1"), ("r1", "i1", "job-2", "d1")],
        replays=[],
    )
    assert ok_dup is False

    # 2. Mutated job_id on replay (including joint DB + replay drift against initial job_id)
    ok_mut, _ = oracle_check_enqueue_conservation(
        jobs_rows=[("r1", "i1", "job-999", "d1")],
        replays=[("r1", "i1", "reused", "job-999")],
        initial_job_ids={("r1", "i1"): "job-1"},
    )
    assert ok_mut is False

    # 3. Omitted recoverable item on retry
    ok_miss, _ = oracle_check_completeness(
        expected_ids={"i1", "i2"},
        committed_ids=["i1"],
        always_pre_commit_ids=set(),
        pending_ids={"i2"},
    )
    assert ok_miss is False

    # 4. Leaked synthetic secret marker
    ok_leak, _ = oracle_check_no_secret_leak('{"token":"FAKE_SECRET_TOKEN_999"}', "FAKE_SECRET_TOKEN_999")
    assert ok_leak is False

    # 5. Redactor actually transforms a seeded synthetic secret (positive control against vacuous pass)
    redacted = redact_secrets({"auth": "Bearer FAKE_SECRET_TOKEN_999", "err": "org_01syntheticorg123456"})
    redacted_json = json.dumps(redacted)
    assert not ("FAKE_SECRET_TOKEN_999" in redacted_json), "redactor failed positive control"
    assert not ("org_01syntheticorg123456" in redacted_json), "redactor failed org ID positive control"


def test_regression_blind_verifier_counterexamples(tmp_path: Path) -> None:
    # Counterexample 1: secret marker placed in dict KEY must also be redacted
    redacted_dict = json.dumps(redact_secrets({"FAKE_SECRET_blind_fixture_123": "plain"}))
    assert not ("FAKE_SECRET_blind_fixture_123" in redacted_dict), "secret key leaked after redaction"

    # Counterexample 2: duplicate (classname, name) in opposite XML order must yield identical item & digest
    xml_order_a = (
        '<testsuite><testcase classname="C" name="t"><failure/></testcase>'
        '<testcase classname="C" name="t"><error/></testcase></testsuite>'
    )
    xml_order_b = (
        '<testsuite><testcase classname="C" name="t"><error/></testcase>'
        '<testcase classname="C" name="t"><failure/></testcase></testsuite>'
    )
    assert parse_junit_failures(xml_order_a) == parse_junit_failures(xml_order_b)


def test_review_regressions_expected_digest_unknown_req_and_pii(tmp_path: Path) -> None:
    ledger = QueueLedger(tmp_path / "rev.sqlite")
    item = FailureItem(
        item_id="tests.test_a::test_one[alice@example.com]",
        test_name="test_one[alice@example.com]",
        classname="tests.test_a",
        failure_kind="failure",
        message="boom",
        payload_digest="aaaa1111bbbb2222",
    )
    ledger.register_expected("req-exp", [item])

    # Enqueue with digest mismatching registered expected_items must fail with ERR_PAYLOAD_CONFLICT
    bad = ledger.enqueue(
        request_id="req-exp",
        item_id=item.item_id,
        payload_digest="cccc3333dddd4444",
        attempt_id="att-bad",
    )
    assert bad.action == "conflict"
    assert bad.error_code == "ERR_PAYLOAD_CONFLICT"
    assert ledger.committed_jobs("req-exp") == []

    # Unknown request_id must NOT report exact_once_ok=True
    unknown = QueueLedger.reconcile_readonly(tmp_path / "rev.sqlite", "req-typo")
    assert unknown["unknown_request"] is True
    assert unknown["exact_once_ok"] is False

    # Email PII inside parameterized item_id is redacted on export
    _, exported = export_memory_bundle(ledger, request_id="req-exp", mode="OFFLINE_REPLAY")
    assert not ("alice@example.com" in exported), "email PII leaked into MemoryBundle export"
