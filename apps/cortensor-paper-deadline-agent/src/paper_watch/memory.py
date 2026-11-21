"""Reminded-set memory: plain local JSON, never inside the repo.

A deadline is "reminded" once it has been shown by ``paper-watch
deadlines``. Key = ``abbreviation|YYYY-MM-DD|deadline_kind`` (see
``Deadline.memory_key``). Default location is the user data directory
(``$XDG_DATA_HOME/paper-watch/reminded.json`` or
``~/.local/share/paper-watch/reminded.json``); ``PAPER_WATCH_MEMORY``
overrides it (tests use a temp file). Export/import are plain file
copies of this JSON — deliberately boring and inspectable.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

__all__ = ["RemindedMemory", "default_memory_path"]


def default_memory_path() -> Path:
    override = os.environ.get("PAPER_WATCH_MEMORY")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "paper-watch" / "reminded.json"


class RemindedMemory:
    """A small set of reminded deadline keys with timestamps."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_memory_path()
        self._entries: dict[str, str] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self._entries = {}
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            entries = raw.get("reminded", {}) if isinstance(raw, dict) else {}
            self._entries = {str(k): str(v) for k, v in entries.items()}
        except (ValueError, OSError):
            self._entries = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": "paper-watch-reminded-v1",
            "reminded": self._entries,
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def __contains__(self, key: str) -> bool:
        return key in self._entries

    def __len__(self) -> int:
        return len(self._entries)

    def mark(self, keys: list[str]) -> int:
        """Mark keys as reminded. Returns the number of newly marked keys."""
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        new = 0
        for key in keys:
            if key not in self._entries:
                new += 1
            self._entries[key] = now
        if new:
            self.save()
        return new

    def keys(self) -> list[str]:
        return sorted(self._entries)

    def export_to(self, dest: str | Path) -> Path:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.save()
        shutil.copyfile(self.path, dest)
        return dest

    def import_from(self, src: str | Path) -> int:
        """Merge entries from an exported file. Returns newly added count."""
        src = Path(src)
        raw = json.loads(src.read_text(encoding="utf-8"))
        entries = raw.get("reminded", {}) if isinstance(raw, dict) else {}
        before = len(self._entries)
        for key, ts in entries.items():
            self._entries.setdefault(str(key), str(ts))
        self.save()
        return len(self._entries) - before
