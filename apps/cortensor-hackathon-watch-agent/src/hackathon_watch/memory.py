"""Local JSON memory: known hackathons, first-seen time, reminded flag.

Key = normalised URL (fallback: normalised name). ``check`` only alerts
on entries whose key is absent — nothing is reported twice.

Export / import has two forms:
1. Plain JSON file (``memory export/import``) — the working format.
2. OpenMinion ``MemoryBundle`` (``memory export --bundle``) — the SDK's
   portable bundle format (export -> save -> load -> import round-trip).
   Note the SDK's public ``import_bundle()`` only validates the trust
   mode and returns a summary dict; it writes nothing into any store.
   Our ``import_bundle_file`` does the actual load into this store.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import KnownEntry
from .normalize import entry_key

DEFAULT_MEMORY_PATH = Path("state") / "memory.json"


class WatchMemory:
    def __init__(self, path: str | Path = DEFAULT_MEMORY_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: dict[str, KnownEntry] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return
        items = raw.get("entries", []) if isinstance(raw, dict) else raw
        for item in items if isinstance(items, list) else []:
            try:
                entry = KnownEntry.model_validate(item)
            except Exception:
                continue
            self._entries[entry.key] = entry

    def _save(self) -> None:
        payload = {"version": 1,
                   "entries": [e.model_dump() for e in self._entries.values()]}
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                             encoding="utf-8")

    def __len__(self) -> int:
        return len(self._entries)

    def known(self, key: str) -> bool:
        return key in self._entries

    def get(self, key: str) -> KnownEntry | None:
        return self._entries.get(key)

    def record(self, key: str, name: str, url: str, source: str = "",
               first_seen: str = "", verdict: str | None = None,
               reminded: bool = False) -> KnownEntry:
        entry = KnownEntry(key=key, name=name, url=url, source=source,
                           first_seen=first_seen, reminded=reminded,
                           verdict=verdict)
        self._entries[key] = entry
        self._save()
        return entry

    def mark_reminded(self, key: str) -> None:
        entry = self._entries.get(key)
        if entry is not None and not entry.reminded:
            entry.reminded = True
            self._save()

    def all_entries(self) -> list[KnownEntry]:
        return sorted(self._entries.values(), key=lambda e: e.first_seen or "")

    # -- plain JSON export / import -------------------------------------

    def export_json(self, dest: str | Path) -> Path:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(
            {"version": 1,
             "entries": [e.model_dump() for e in self._entries.values()]},
            indent=2, ensure_ascii=False), encoding="utf-8")
        return dest

    def import_json(self, src: str | Path) -> int:
        raw = json.loads(Path(src).read_text(encoding="utf-8"))
        items = raw.get("entries", []) if isinstance(raw, dict) else raw
        count = 0
        for item in items if isinstance(items, list) else []:
            try:
                entry = KnownEntry.model_validate(item)
            except Exception:
                continue
            self._entries[entry.key] = entry
            count += 1
        self._save()
        return count

    # -- MemoryBundle export / import -----------------------------------

    def export_bundle(self, dest: str | Path) -> Path:
        from openminion.modules.memory.portability import (
            export_bundle, save_bundle)
        items = [{"kind": "hackathon", "id": e.key, "name": e.name,
                  "url": e.url, "source": e.source,
                  "first_seen": e.first_seen, "reminded": e.reminded,
                  "verdict": e.verdict} for e in self._entries.values()]
        bundle = export_bundle(items, metadata={"agent": "hackathon-watch",
                                                "version": 1})
        save_bundle(bundle, str(dest))
        return Path(dest)

    def import_bundle_file(self, src: str | Path,
                           trust_mode: str = "direct") -> int:
        from openminion.modules.memory.portability import (
            import_bundle, load_bundle)
        bundle = load_bundle(str(src))
        info = import_bundle(bundle, trust_mode=trust_mode)
        # MemoryBundle is a dataclass, not a dict.
        items = getattr(bundle, "items", None)
        if items is None and isinstance(bundle, dict):
            items = bundle.get("items", [])
        count = 0
        for item in items:
            if not isinstance(item, dict) or item.get("kind") != "hackathon":
                continue
            url = item.get("url") or ""
            name = item.get("name") or ""
            key = item.get("id") or entry_key(url, name)
            self._entries[key] = KnownEntry(
                key=key, name=name, url=url, source=item.get("source") or "",
                first_seen=item.get("first_seen") or "",
                reminded=bool(item.get("reminded", False)),
                verdict=item.get("verdict"))
            count += 1
        self._save()
        assert info.get("item_count", count) >= 0  # summary only; load above is real
        return count
