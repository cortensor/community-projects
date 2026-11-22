"""Pure functions: what is new since the last checkpoint, and what looks risky."""
from __future__ import annotations

from datetime import datetime, timezone

RISK_WORDS = ("breaking", "remove", "removed", "deprecat", "rename", "migration", "security", "regression")
BUG_LABELS = ("bug", "regression", "security")


def new_releases(releases: list[dict], state: dict) -> list[dict]:
    seen = set(state.get("seen_release_ids", []))
    return [r for r in releases if r["id"] not in seen]


def new_or_updated_issues(issues: list[dict], state: dict) -> list[dict]:
    seen = state.get("seen_issue_updates", {})
    return [i for i in issues if seen.get(str(i["id"])) != i.get("updated_at")]


def risk_flags(text: str) -> list[str]:
    low = (text or "").lower()
    return sorted({w for w in RISK_WORDS if w in low})


def is_bug(issue: dict) -> bool:
    labels = [l.lower() for l in issue.get("labels", [])]
    return any(b in l for l in labels for b in BUG_LABELS) or "bug" in (issue.get("title") or "").lower()


def next_state(state: dict, releases: list[dict], issues: list[dict], now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    seen_rel = sorted(set(state.get("seen_release_ids", [])) | {r["id"] for r in releases})
    seen_iss = dict(state.get("seen_issue_updates", {}))
    seen_iss.update({str(i["id"]): i.get("updated_at") for i in issues})
    return {"repo": state["repo"], "seen_release_ids": seen_rel,
            "seen_issue_updates": seen_iss, "last_check": now.isoformat(timespec="seconds")}
