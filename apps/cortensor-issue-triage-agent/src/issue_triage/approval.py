"""Fail-closed human approval gate.

``triage`` never writes to GitHub. It only produces a verdict + draft and
saves a *pending* snapshot under ``.issue-triage/pending/``. Nothing is
posted until a human runs ``approve --snapshot <id> --yes``.

State machine: ``pending -> approved -> consumed`` (single use; a second
approve is refused) or ``pending -> rejected``. Without a decision the
snapshot stays pending forever and can be resumed from the file.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import Snapshot


class SnapshotError(RuntimeError):
    pass


class AlreadyConsumedError(SnapshotError):
    pass


class NotPendingError(SnapshotError):
    pass


class SnapshotStore:
    def __init__(self, root: str | Path = ".issue-triage/pending"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, snapshot_id: str) -> Path:
        safe = snapshot_id.replace("/", "_")
        return self.root / f"{safe}.json"

    def save(self, snapshot: Snapshot) -> Path:
        path = self.path_for(snapshot.id)
        path.write_text(
            json.dumps(snapshot.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def load(self, snapshot_id: str) -> Snapshot:
        path = self.path_for(snapshot_id)
        if not path.is_file():
            # also accept a direct file path
            direct = Path(snapshot_id)
            if direct.is_file():
                path = direct
            else:
                raise SnapshotError(f"snapshot not found: {snapshot_id}")
        return Snapshot.model_validate_json(path.read_text(encoding="utf-8"))

    def mark(self, snapshot: Snapshot, status: str, note: str = "") -> Snapshot:
        from .models import utcnow_iso

        snapshot.status = status  # type: ignore[assignment]
        snapshot.decided_at = utcnow_iso()
        if note:
            snapshot.note = note
        self.save(snapshot)
        return snapshot

    def approve_once(self, snapshot_id: str) -> Snapshot:
        """Transition pending -> approved. Refuses anything already decided
        (anti-replay: an approved snapshot must go through ``consume``)."""
        snapshot = self.load(snapshot_id)
        if snapshot.status != "pending":
            raise NotPendingError(
                f"snapshot {snapshot.id} is {snapshot.status}, not pending; refusing"
            )
        return self.mark(snapshot, "approved")

    def consume(self, snapshot_id: str) -> Snapshot:
        """Transition approved -> consumed. Single use: a second consume
        raises :class:`AlreadyConsumedError`."""
        snapshot = self.load(snapshot_id)
        if snapshot.status == "consumed":
            raise AlreadyConsumedError(f"snapshot {snapshot.id} already consumed; refusing replay")
        if snapshot.status != "approved":
            raise NotPendingError(
                f"snapshot {snapshot.id} is {snapshot.status}; approve it before consuming"
            )
        return self.mark(snapshot, "consumed")

    def reject(self, snapshot_id: str, note: str = "") -> Snapshot:
        snapshot = self.load(snapshot_id)
        if snapshot.status != "pending":
            raise NotPendingError(
                f"snapshot {snapshot.id} is {snapshot.status}, not pending; refusing"
            )
        return self.mark(snapshot, "rejected", note=note or "rejected by human reviewer")
