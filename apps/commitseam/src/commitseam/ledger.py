from __future__ import annotations

import sqlite3
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Literal, Sequence, TypeVar

from commitseam.junit_parser import FailureItem

T = TypeVar("T")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS expected_items (
    request_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    payload_digest TEXT NOT NULL,
    test_name TEXT NOT NULL,
    failure_kind TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (request_id, item_id)
);

CREATE TABLE IF NOT EXISTS rerun_jobs (
    request_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    payload_digest TEXT NOT NULL,
    created_by_attempt_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (request_id, item_id)
);

CREATE TABLE IF NOT EXISTS attempt_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    attempt_id TEXT NOT NULL,
    session_id TEXT,
    fault_seam TEXT NOT NULL,
    result TEXT NOT NULL,
    job_id TEXT,
    error_code TEXT,
    detail TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


class FaultMode(str, Enum):
    NONE = "none"
    PRE_COMMIT = "pre-commit"
    POST_COMMIT = "post-commit"

    @classmethod
    def coerce(cls, value: FaultMode | str) -> FaultMode:
        if isinstance(value, cls):
            return value
        normalized = str(value).strip().lower()
        for member in cls:
            if member.value == normalized:
                return member
        raise ValueError(f"Unsupported fault_seam: {value!r}")


class InjectedFaultError(RuntimeError):
    def __init__(
        self,
        seam: FaultMode,
        *,
        request_id: str,
        item_id: str,
        attempt_id: str,
        committed_job_id: str | None = None,
    ) -> None:
        self.seam = seam
        self.request_id = request_id
        self.item_id = item_id
        self.attempt_id = attempt_id
        self.committed_job_id = committed_job_id
        super().__init__(
            f"Injected {seam.value} fault for request_id={request_id} item_id={item_id} attempt_id={attempt_id}"
        )


@dataclass(frozen=True)
class EnqueueResult:
    action: Literal["created", "reused", "conflict", "denied"]
    request_id: str
    item_id: str
    job_id: str | None
    recovered_job_id: str | None
    created_by_attempt_id: str | None
    error_code: str | None = None


class QueueLedger:
    """Durable SQLite WAL queue ledger guaranteeing exactly-once enqueue per (request_id, item_id)."""

    def __init__(
        self,
        db_path: Path | str,
        *,
        busy_timeout_ms: int = 5000,
        max_busy_retries: int = 5,
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.busy_timeout_ms = busy_timeout_ms
        self.max_busy_retries = max_busy_retries
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=self.busy_timeout_ms / 1000.0,
            isolation_level=None,
        )
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=FULL;")
            conn.execute(f"PRAGMA busy_timeout={int(self.busy_timeout_ms)};")
            conn.execute("PRAGMA foreign_keys=ON;")
            return conn
        except Exception:
            conn.close()
            raise

    def _run_with_busy_retry(self, fn: Callable[[sqlite3.Connection], T]) -> T:
        last_exc: sqlite3.OperationalError | None = None
        for attempt in range(self.max_busy_retries + 1):
            conn: sqlite3.Connection | None = None
            try:
                conn = self._connect()
                return fn(conn)
            except sqlite3.OperationalError as exc:
                msg = str(exc).lower()
                if "locked" in msg or "busy" in msg:
                    last_exc = exc
                    if attempt < self.max_busy_retries:
                        time.sleep(0.02 * (attempt + 1))
                        continue
                raise
            finally:
                if conn is not None:
                    conn.close()
        assert last_exc is not None
        raise last_exc

    def _init_schema(self) -> None:
        def _op(conn: sqlite3.Connection) -> None:
            conn.executescript(SCHEMA_SQL)

        self._run_with_busy_retry(_op)

    def register_expected(self, request_id: str, items: Sequence[FailureItem]) -> int:
        def _op(conn: sqlite3.Connection) -> int:
            conn.execute("BEGIN IMMEDIATE")
            try:
                inserted = 0
                for item in items:
                    cur = conn.execute(
                        """
                        INSERT OR IGNORE INTO expected_items
                            (request_id, item_id, payload_digest, test_name, failure_kind)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            request_id,
                            item.item_id,
                            item.payload_digest,
                            item.test_name,
                            item.failure_kind,
                        ),
                    )
                    if cur.rowcount > 0:
                        inserted += 1
                conn.execute("COMMIT")
                return inserted
            except Exception:
                conn.execute("ROLLBACK")
                raise

        return self._run_with_busy_retry(_op)

    def expected_items(self, request_id: str) -> list[dict[str, str]]:
        def _op(conn: sqlite3.Connection) -> list[dict[str, str]]:
            rows = conn.execute(
                """
                SELECT request_id, item_id, payload_digest, test_name, failure_kind, created_at
                FROM expected_items
                WHERE request_id = ?
                ORDER BY item_id ASC
                """,
                (request_id,),
            ).fetchall()
            return [dict(row) for row in rows]

        return self._run_with_busy_retry(_op)

    def committed_jobs(self, request_id: str) -> list[dict[str, Any]]:
        def _op(conn: sqlite3.Connection) -> list[dict[str, Any]]:
            rows = conn.execute(
                """
                SELECT request_id, item_id, job_id, payload_digest, created_by_attempt_id, created_at
                FROM rerun_jobs
                WHERE request_id = ?
                ORDER BY item_id ASC
                """,
                (request_id,),
            ).fetchall()
            return [dict(row) for row in rows]

        return self._run_with_busy_retry(_op)

    def pending_items(self, request_id: str) -> list[dict[str, str]]:
        def _op(conn: sqlite3.Connection) -> list[dict[str, str]]:
            rows = conn.execute(
                """
                SELECT e.request_id, e.item_id, e.payload_digest, e.test_name, e.failure_kind, e.created_at
                FROM expected_items e
                LEFT JOIN rerun_jobs r
                    ON r.request_id = e.request_id AND r.item_id = e.item_id
                WHERE e.request_id = ? AND r.job_id IS NULL
                ORDER BY e.item_id ASC
                """,
                (request_id,),
            ).fetchall()
            return [dict(row) for row in rows]

        return self._run_with_busy_retry(_op)

    def record_denial(
        self,
        *,
        request_id: str,
        item_id: str,
        attempt_id: str,
        session_id: str | None = None,
        detail: str = "approval_denied",
    ) -> EnqueueResult:
        def _op(conn: sqlite3.Connection) -> EnqueueResult:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    """
                    INSERT INTO attempt_events
                        (request_id, item_id, attempt_id, session_id, fault_seam, result, job_id, error_code, detail)
                    VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?)
                    """,
                    (
                        request_id,
                        item_id,
                        attempt_id,
                        session_id,
                        FaultMode.NONE.value,
                        "denied",
                        detail,
                    ),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
            return EnqueueResult(
                action="denied",
                request_id=request_id,
                item_id=item_id,
                job_id=None,
                recovered_job_id=None,
                created_by_attempt_id=None,
            )

        return self._run_with_busy_retry(_op)

    def enqueue(
        self,
        *,
        request_id: str,
        item_id: str,
        payload_digest: str,
        attempt_id: str,
        session_id: str | None = None,
        fault_seam: FaultMode | str = FaultMode.NONE,
    ) -> EnqueueResult:
        seam = FaultMode.coerce(fault_seam)

        def _op(conn: sqlite3.Connection) -> EnqueueResult:
            conn.execute("BEGIN IMMEDIATE")
            try:
                existing = conn.execute(
                    """
                    SELECT job_id, payload_digest, created_by_attempt_id
                    FROM rerun_jobs
                    WHERE request_id = ? AND item_id = ?
                    """,
                    (request_id, item_id),
                ).fetchone()

                if existing is not None:
                    existing_job_id = str(existing["job_id"])
                    existing_digest = str(existing["payload_digest"])
                    creator_attempt = str(existing["created_by_attempt_id"])
                    if existing_digest == payload_digest:
                        conn.execute(
                            """
                            INSERT INTO attempt_events
                                (request_id, item_id, attempt_id, session_id, fault_seam, result, job_id, error_code, detail)
                            VALUES (?, ?, ?, ?, ?, 'reused', ?, NULL, 'idempotent_replay')
                            """,
                            (request_id, item_id, attempt_id, session_id, seam.value, existing_job_id),
                        )
                        conn.execute("COMMIT")
                        return EnqueueResult(
                            action="reused",
                            request_id=request_id,
                            item_id=item_id,
                            job_id=existing_job_id,
                            recovered_job_id=existing_job_id,
                            created_by_attempt_id=creator_attempt,
                        )

                    conn.execute(
                        """
                        INSERT INTO attempt_events
                            (request_id, item_id, attempt_id, session_id, fault_seam, result, job_id, error_code, detail)
                        VALUES (?, ?, ?, ?, ?, 'conflict', ?, 'ERR_PAYLOAD_CONFLICT', 'payload_digest_mismatch')
                        """,
                        (request_id, item_id, attempt_id, session_id, seam.value, existing_job_id),
                    )
                    conn.execute("COMMIT")
                    return EnqueueResult(
                        action="conflict",
                        request_id=request_id,
                        item_id=item_id,
                        job_id=existing_job_id,
                        recovered_job_id=existing_job_id,
                        created_by_attempt_id=creator_attempt,
                        error_code="ERR_PAYLOAD_CONFLICT",
                    )

                expected_row = conn.execute(
                    """
                    SELECT payload_digest
                    FROM expected_items
                    WHERE request_id = ? AND item_id = ?
                    """,
                    (request_id, item_id),
                ).fetchone()
                if expected_row is not None and str(expected_row["payload_digest"]) != payload_digest:
                    conn.execute(
                        """
                        INSERT INTO attempt_events
                            (request_id, item_id, attempt_id, session_id, fault_seam, result, job_id, error_code, detail)
                        VALUES (?, ?, ?, ?, ?, 'conflict', NULL, 'ERR_PAYLOAD_CONFLICT', 'expected_payload_digest_mismatch')
                        """,
                        (request_id, item_id, attempt_id, session_id, seam.value),
                    )
                    conn.execute("COMMIT")
                    return EnqueueResult(
                        action="conflict",
                        request_id=request_id,
                        item_id=item_id,
                        job_id=None,
                        recovered_job_id=None,
                        created_by_attempt_id=None,
                        error_code="ERR_PAYLOAD_CONFLICT",
                    )

                job_id = f"job-{uuid.uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO rerun_jobs
                        (request_id, item_id, job_id, payload_digest, created_by_attempt_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (request_id, item_id, job_id, payload_digest, attempt_id),
                )

                if seam == FaultMode.PRE_COMMIT:
                    # Simulate a crash strictly before COMMIT: roll back the job insert,
                    # then record the aborted attempt event in an isolated audit write.
                    conn.execute("ROLLBACK")
                    conn.execute("BEGIN IMMEDIATE")
                    conn.execute(
                        """
                        INSERT INTO attempt_events
                            (request_id, item_id, attempt_id, session_id, fault_seam, result, job_id, error_code, detail)
                        VALUES (?, ?, ?, ?, ?, 'pre_commit_abort', NULL, 'INJECTED_PRE_COMMIT', 'aborted_before_commit')
                        """,
                        (request_id, item_id, attempt_id, session_id, seam.value),
                    )
                    conn.execute("COMMIT")
                    raise InjectedFaultError(
                        FaultMode.PRE_COMMIT,
                        request_id=request_id,
                        item_id=item_id,
                        attempt_id=attempt_id,
                        committed_job_id=None,
                    )

                event_result = "post_commit_crash" if seam == FaultMode.POST_COMMIT else "created"
                event_error = "INJECTED_POST_COMMIT" if seam == FaultMode.POST_COMMIT else None
                event_detail = "committed_then_crashed_before_return" if seam == FaultMode.POST_COMMIT else "committed"
                conn.execute(
                    """
                    INSERT INTO attempt_events
                        (request_id, item_id, attempt_id, session_id, fault_seam, result, job_id, error_code, detail)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (request_id, item_id, attempt_id, session_id, seam.value, event_result, job_id, event_error, event_detail),
                )
                conn.execute("COMMIT")

                if seam == FaultMode.POST_COMMIT:
                    raise InjectedFaultError(
                        FaultMode.POST_COMMIT,
                        request_id=request_id,
                        item_id=item_id,
                        attempt_id=attempt_id,
                        committed_job_id=job_id,
                    )

                return EnqueueResult(
                    action="created",
                    request_id=request_id,
                    item_id=item_id,
                    job_id=job_id,
                    recovered_job_id=None,
                    created_by_attempt_id=attempt_id,
                )
            except Exception:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise

        return self._run_with_busy_retry(_op)

    def attempt_events(self, request_id: str) -> list[dict[str, Any]]:
        def _op(conn: sqlite3.Connection) -> list[dict[str, Any]]:
            rows = conn.execute(
                """
                SELECT id, request_id, item_id, attempt_id, session_id, fault_seam, result, job_id, error_code, detail, created_at
                FROM attempt_events
                WHERE request_id = ?
                ORDER BY id ASC
                """,
                (request_id,),
            ).fetchall()
            return [dict(row) for row in rows]

        return self._run_with_busy_retry(_op)

    @staticmethod
    def _build_reconcile_summary(
        request_id: str,
        expected: list[dict[str, str]],
        jobs: list[dict[str, Any]],
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        expected_by_id = {row["item_id"]: row for row in expected}
        committed_ids = [row["item_id"] for row in jobs]
        committed_set = set(committed_ids)
        pending_ids = [row["item_id"] for row in expected if row["item_id"] not in committed_set]
        has_duplicates = len(committed_ids) != len(committed_set)
        digest_mismatches = [
            row["item_id"]
            for row in jobs
            if row["item_id"] in expected_by_id
            and row["payload_digest"] != expected_by_id[row["item_id"]]["payload_digest"]
        ]
        unknown_request = len(expected) == 0
        exact_once_ok = (
            not unknown_request
            and not has_duplicates
            and len(pending_ids) == 0
            and len(digest_mismatches) == 0
            and committed_set == set(expected_by_id)
        )
        return {
            "request_id": request_id,
            "unknown_request": unknown_request,
            "expected_count": len(expected),
            "committed_enqueue_count": len(jobs),
            "pending_item_ids": pending_ids,
            "has_duplicates": has_duplicates,
            "digest_mismatches": digest_mismatches,
            "exact_once_ok": exact_once_ok,
            "jobs": jobs,
            "events": events,
        }

    @classmethod
    def _read_snapshot(cls, conn: sqlite3.Connection, request_id: str) -> dict[str, Any]:
        conn.execute("BEGIN DEFERRED")
        try:
            expected = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT request_id, item_id, payload_digest, test_name, failure_kind, created_at
                    FROM expected_items
                    WHERE request_id = ?
                    ORDER BY item_id ASC
                    """,
                    (request_id,),
                ).fetchall()
            ]
            jobs = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT request_id, item_id, job_id, payload_digest, created_by_attempt_id, created_at
                    FROM rerun_jobs
                    WHERE request_id = ?
                    ORDER BY item_id ASC
                    """,
                    (request_id,),
                ).fetchall()
            ]
            events = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT id, request_id, item_id, attempt_id, session_id, fault_seam, result, job_id, error_code, detail, created_at
                    FROM attempt_events
                    WHERE request_id = ?
                    ORDER BY id ASC
                    """,
                    (request_id,),
                ).fetchall()
            ]
        finally:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
        return cls._build_reconcile_summary(request_id, expected, jobs, events)

    def reconcile(self, request_id: str) -> dict[str, Any]:
        return self._run_with_busy_retry(lambda conn: self._read_snapshot(conn, request_id))

    @classmethod
    def reconcile_readonly(cls, db_path: Path | str, request_id: str) -> dict[str, Any]:
        """Take an atomic read-only snapshot without creating tables or altering journal mode."""
        path = Path(db_path)
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, isolation_level=None)
        try:
            conn.row_factory = sqlite3.Row
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            required = {"expected_items", "rerun_jobs", "attempt_events"}
            if not required.issubset(tables):
                missing = sorted(required - tables)
                raise ValueError(f"Queue database {path} is missing required tables: {', '.join(missing)}")
            return cls._read_snapshot(conn, request_id)
        finally:
            conn.close()
