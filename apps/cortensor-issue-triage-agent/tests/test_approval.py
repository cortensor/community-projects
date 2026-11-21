"""Approval gate state machine: allow / deny / pause-resume / single-use."""

import pytest

from issue_triage.approval import (
    AlreadyConsumedError,
    NotPendingError,
    SnapshotStore,
)
from issue_triage.models import Snapshot, TriageDraft, TriageVerdict


def _snap(sid="s-1", number=1):
    return Snapshot(
        id=sid,
        repo="owner/repo",
        issue_number=number,
        issue_title="t",
        verdict=TriageVerdict(
            issue_type="bug", severity="high", component="x",
            route="ready-to-fix", confidence=0.8, rationale="t",
        ),
        draft=TriageDraft(draft="draft"),
    )


def test_save_and_load_round_trip(tmp_path):
    store = SnapshotStore(tmp_path)
    store.save(_snap())
    loaded = store.load("s-1")
    assert loaded.status == "pending"
    assert loaded.verdict.issue_type == "bug"


def test_pause_resume_stays_pending(tmp_path):
    store = SnapshotStore(tmp_path)
    store.save(_snap())
    assert store.load("s-1").status == "pending"  # no decision: paused, resumable


def test_approve_then_consume_once(tmp_path):
    store = SnapshotStore(tmp_path)
    store.save(_snap())
    store.approve_once("s-1")
    assert store.load("s-1").status == "approved"
    store.consume("s-1")
    assert store.load("s-1").status == "consumed"


def test_second_consume_refused(tmp_path):
    store = SnapshotStore(tmp_path)
    store.save(_snap())
    store.approve_once("s-1")
    store.consume("s-1")
    with pytest.raises(AlreadyConsumedError):
        store.consume("s-1")


def test_approve_after_consume_refused(tmp_path):
    store = SnapshotStore(tmp_path)
    store.save(_snap())
    store.approve_once("s-1")
    store.consume("s-1")
    with pytest.raises(NotPendingError):
        store.approve_once("s-1")


def test_reject_blocks_later_approve(tmp_path):
    store = SnapshotStore(tmp_path)
    store.save(_snap())
    store.reject("s-1")
    assert store.load("s-1").status == "rejected"
    with pytest.raises(NotPendingError):
        store.approve_once("s-1")
    with pytest.raises(NotPendingError):
        store.consume("s-1")


def test_consume_without_approve_refused(tmp_path):
    store = SnapshotStore(tmp_path)
    store.save(_snap())
    with pytest.raises(NotPendingError):
        store.consume("s-1")


def test_load_missing_snapshot_errors(tmp_path):
    store = SnapshotStore(tmp_path)
    with pytest.raises(Exception):
        store.load("nope")


def test_load_by_file_path(tmp_path):
    store = SnapshotStore(tmp_path)
    path = store.save(_snap())
    assert store.load(str(path)).id == "s-1"
