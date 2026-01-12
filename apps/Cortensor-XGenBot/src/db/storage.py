import os
import sqlite3
from typing import Optional, Dict, Any

from ..config import DB_PATH, logger

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS user_settings (
    user_id TEXT PRIMARY KEY,
    tone TEXT,
    length TEXT,
    n INTEGER,
    hashtags TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    mode TEXT NOT NULL,
    tone TEXT,
    length TEXT,
    hashtags TEXT,
    payload TEXT NOT NULL, -- JSON: posts, topic/reply_ctx, timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_history_user ON user_history(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS user_voices (
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    prompt TEXT NOT NULL,
    PRIMARY KEY(user_id, name)
);

CREATE TABLE IF NOT EXISTS user_tags (
    user_id TEXT PRIMARY KEY,
    tags TEXT -- comma-separated or space-delimited
);

CREATE TABLE IF NOT EXISTS user_sessions (
    user_id TEXT PRIMARY KEY,
    state_json TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def _connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def load_user_defaults(user_id: str) -> Dict[str, Any]:
    conn = _connect()
    try:
        cur = conn.execute(
            "SELECT tone, length, n, hashtags FROM user_settings WHERE user_id = ?",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return {}
        return {
            "tone": row["tone"],
            "length": row["length"],
            "n": row["n"],
            "hashtags": row["hashtags"] or "",
        }
    finally:
        conn.close()


# Import config for defaults (lazy to avoid circular imports)
def _get_config_defaults():
    try:
        from ..config import DEFAULT_TONE, DEFAULT_LENGTH, DEFAULT_THREAD_N, DEFAULT_HASHTAGS
        return {
            "tone": DEFAULT_TONE or "concise",
            "length": DEFAULT_LENGTH or "medium",
            "n": DEFAULT_THREAD_N or 6,
            "hashtags": (DEFAULT_HASHTAGS or "").strip(),
        }
    except Exception:
        return {
            "tone": os.getenv("DEFAULT_TONE", "concise"),
            "length": os.getenv("DEFAULT_LENGTH", "medium"),
            "n": int(os.getenv("DEFAULT_THREAD_N", "6")),
            "hashtags": (os.getenv("DEFAULT_HASHTAGS") or "").strip(),
        }

essential_defaults = _get_config_defaults()


def save_user_defaults(user_id: str, values: Dict[str, Any]) -> None:
    data = {**essential_defaults, **(values or {})}
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO user_settings (user_id, tone, length, n, hashtags)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                tone=excluded.tone,
                length=excluded.length,
                n=excluded.n,
                hashtags=excluded.hashtags,
                updated_at=CURRENT_TIMESTAMP
            """,
            (user_id, data.get("tone"), data.get("length"), int(data.get("n", 6)), data.get("hashtags", "")),
        )
        conn.commit()
    finally:
        conn.close()


# History
def save_history(user_id: str, mode: str, tone: str, length: str, hashtags: str, payload_json: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO user_history (user_id, mode, tone, length, hashtags, payload) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, mode, tone, length, hashtags or "", payload_json),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent_history(user_id: str, limit: int = 3) -> list[Dict[str, Any]]:
    conn = _connect()
    try:
        cur = conn.execute(
            "SELECT id, mode, tone, length, hashtags, payload, created_at FROM user_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, int(limit)),
        )
        rows = cur.fetchall()
        out = []
        for r in rows:
            out.append({k: r[k] for k in r.keys()})
        return out
    finally:
        conn.close()


def get_history_by_id(user_id: str, hist_id: int) -> Optional[Dict[str, Any]]:
    conn = _connect()
    try:
        cur = conn.execute(
            "SELECT id, mode, tone, length, hashtags, payload, created_at FROM user_history WHERE user_id = ? AND id = ?",
            (user_id, int(hist_id)),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {k: row[k] for k in row.keys()}
    finally:
        conn.close()


# Voices
def save_voice(user_id: str, name: str, prompt: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO user_voices (user_id, name, prompt) VALUES (?, ?, ?) ON CONFLICT(user_id, name) DO UPDATE SET prompt=excluded.prompt",
            (user_id, name.strip(), prompt.strip()),
        )
        conn.commit()
    finally:
        conn.close()


def list_voices(user_id: str) -> list[Dict[str, Any]]:
    conn = _connect()
    try:
        cur = conn.execute("SELECT name, prompt FROM user_voices WHERE user_id = ? ORDER BY name", (user_id,))
        return [{"name": r["name"], "prompt": r["prompt"]} for r in cur.fetchall()]
    finally:
        conn.close()


# Tags
def save_tags(user_id: str, tags: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO user_tags (user_id, tags) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET tags=excluded.tags",
            (user_id, tags.strip()),
        )
        conn.commit()
    finally:
        conn.close()


def load_tags(user_id: str) -> str:
    conn = _connect()
    try:
        cur = conn.execute("SELECT tags FROM user_tags WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return (row["tags"] if row else "") or ""
    finally:
        conn.close()


# Session state
def save_session_state(user_id: str, state_json: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO user_sessions (user_id, state_json) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET state_json=excluded.state_json, updated_at=CURRENT_TIMESTAMP",
            (user_id, state_json),
        )
        conn.commit()
    finally:
        conn.close()


def load_session_state(user_id: str) -> Optional[str]:
    conn = _connect()
    try:
        cur = conn.execute("SELECT state_json FROM user_sessions WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return row["state_json"] if row else None
    finally:
        conn.close()
