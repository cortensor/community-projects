"""SQLite persistence for generated briefs (stdlib sqlite3)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import RepairBrief

DEFAULT_DB = Path("outputs") / "fixbrief.db"


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS briefs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            device TEXT NOT NULL,
            symptom TEXT NOT NULL,
            language TEXT NOT NULL,
            generated_by TEXT NOT NULL,
            session_id TEXT,
            brief_json TEXT NOT NULL
        )
        """
    )
    return conn


def save_brief(
    brief: RepairBrief, session_id: str | None = None, db_path: Path | None = None
) -> int:
    path = db_path or DEFAULT_DB
    conn = _connect(path)
    try:
        cursor = conn.execute(
            "INSERT INTO briefs (created_at, device, symptom, language, "
            "generated_by, session_id, brief_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                brief.device,
                brief.symptom,
                brief.language.value,
                brief.generated_by,
                session_id,
                brief.model_dump_json(),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def list_briefs(db_path: Path | None = None, limit: int = 20) -> list[dict]:
    path = db_path or DEFAULT_DB
    if not path.exists():
        return []
    conn = _connect(path)
    try:
        rows = conn.execute(
            "SELECT id, created_at, device, symptom, language, generated_by, "
            "session_id FROM briefs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    keys = ["id", "created_at", "device", "symptom", "language", "generated_by", "session_id"]
    return [dict(zip(keys, row)) for row in rows]


def get_brief(brief_id: int, db_path: Path | None = None) -> RepairBrief | None:
    path = db_path or DEFAULT_DB
    if not path.exists():
        return None
    conn = _connect(path)
    try:
        row = conn.execute(
            "SELECT brief_json FROM briefs WHERE id = ?", (brief_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return RepairBrief.model_validate(json.loads(row[0]))
