"""Tiny GitHub reader (public REST API) with a fixture mode for offline demos."""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

API = "https://api.github.com"
DEMO_DIR = Path(__file__).resolve().parent.parent / "data" / "demo"


class GitHubError(RuntimeError):
    pass


def _get(path: str) -> list | dict:
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "minion-radar",
    })
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:  # network, 403 rate limit, 404
        raise GitHubError(f"GitHub request failed for {path}: {exc}") from exc


def _slim_release(r: dict) -> dict:
    return {
        "id": r["id"], "tag": r.get("tag_name"), "name": r.get("name") or r.get("tag_name"),
        "published_at": r.get("published_at"), "url": r.get("html_url"),
        "body": (r.get("body") or "")[:4000], "prerelease": bool(r.get("prerelease")),
    }


def _slim_issue(i: dict) -> dict:
    return {
        "id": i["id"], "number": i["number"], "title": i.get("title"),
        "kind": "pr" if "pull_request" in i else "issue", "state": i.get("state"),
        "labels": [l.get("name") for l in i.get("labels", []) if isinstance(l, dict)],
        "updated_at": i.get("updated_at"), "url": i.get("html_url"),
        "body": (i.get("body") or "")[:1500],
    }


def fetch_releases(repo: str, demo: bool = False, limit: int = 10) -> list[dict]:
    if demo:
        return json.loads((DEMO_DIR / "releases.json").read_text())
    return [_slim_release(r) for r in _get(f"/repos/{repo}/releases?per_page={limit}")]


def fetch_issues(repo: str, demo: bool = False, limit: int = 30) -> list[dict]:
    if demo:
        return json.loads((DEMO_DIR / "issues.json").read_text())
    rows = _get(f"/repos/{repo}/issues?state=all&sort=updated&direction=desc&per_page={limit}")
    return [_slim_issue(i) for i in rows]
