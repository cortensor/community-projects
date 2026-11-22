"""Local checkpoint memory: which release and issue ids the builder has already seen."""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_DIR = Path(".radar")


def _path(repo: str, root: Path = DEFAULT_DIR) -> Path:
    return root / (repo.replace("/", "__") + ".json")


def load(repo: str, root: Path = DEFAULT_DIR) -> dict:
    p = _path(repo, root)
    if not p.exists():
        return {"repo": repo, "seen_release_ids": [], "seen_issue_updates": {}, "last_check": None}
    return json.loads(p.read_text())


def save(state: dict, root: Path = DEFAULT_DIR) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    p = _path(state["repo"], root)
    p.write_text(json.dumps(state, indent=2))
    return p
