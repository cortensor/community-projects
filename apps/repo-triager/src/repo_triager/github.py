"""A read-only GitHub client plus the offline snapshot loader.

Only GET requests are implemented on purpose: Repo Triager plans and stages
triage work locally and never writes to a repository.  ``RepoSnapshot`` is the
single shape both the API path and the offline fixture produce.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from repo_triager.config import Settings, find_fixture
from repo_triager.models import Issue, LabelSpec, RepoSnapshot

API_ROOT = "https://api.github.com"
USER_AGENT = "repo-triager/0.1 (+local triage agent)"


class GitHubError(RuntimeError):
    """A read-only GitHub request failed."""


def _request(url: str, token: str, *, timeout: int = 30) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:  # pragma: no cover - network path
        body = exc.read().decode("utf-8", "replace")[:400]
        if token and exc.code in (401, 403):
            # A stale GITHUB_TOKEN/GH_TOKEN must not hide public read access.
            print(
                f"warning: GitHub rejected the configured token (HTTP {exc.code}); "
                "retrying anonymously (lower rate limit)",
                file=sys.stderr,
            )
            return _request(url, "", timeout=timeout)
        raise GitHubError(f"GitHub GET {url} failed: HTTP {exc.code} {body}") from exc
    except urllib.error.URLError as exc:  # pragma: no cover - network path
        raise GitHubError(f"GitHub GET {url} failed: {exc.reason}") from exc


def _issue_from_payload(payload: dict) -> Issue:
    return Issue(
        number=int(payload["number"]),
        title=str(payload.get("title") or ""),
        body=str(payload.get("body") or ""),
        labels=[str(item.get("name")) for item in payload.get("labels") or []],
        comments=int(payload.get("comments") or 0),
        state=str(payload.get("state") or "open"),
        url=str(payload.get("html_url") or ""),
        created_at=str(payload.get("created_at") or ""),
        updated_at=str(payload.get("updated_at") or ""),
    )


def fetch_repo_snapshot(
    repo: str,
    *,
    token: str = "",
    limit: int = 30,
    state: str = "open",
) -> RepoSnapshot:
    """Read labels and issues for ``owner/name`` (public read-only access)."""

    labels_payload = _request(f"{API_ROOT}/repos/{repo}/labels?per_page=100", token)
    # Pull more rows than requested: the issues endpoint also returns pull
    # requests, which are dropped below.
    per_page = max(20, min(100, limit * 3))
    issues_payload = _request(
        f"{API_ROOT}/repos/{repo}/issues?state={urllib.parse.quote(state)}"
        f"&per_page={per_page}&sort=created&direction=desc",
        token,
    )
    labels = [
        LabelSpec(name=str(item.get("name")), description=str(item.get("description") or ""))
        for item in labels_payload or []
    ]
    issues = [
        _issue_from_payload(item)
        for item in issues_payload or []
        if "pull_request" not in item
    ][: max(1, limit)]
    return RepoSnapshot(
        repo=repo,
        captured_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        source="github-api",
        labels=labels,
        issues=issues,
    )


def load_fixture_snapshot(path: Path | None = None, *, repo: str | None = None) -> RepoSnapshot:
    fixture = find_fixture(path)
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    snapshot = RepoSnapshot.model_validate(payload)
    if repo and repo != snapshot.repo:
        snapshot = snapshot.model_copy(update={"repo": repo})
    return snapshot


def save_cache(snapshot: RepoSnapshot, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(snapshot.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8"
    )


def load_cache(path: Path) -> RepoSnapshot | None:
    if not path.exists():
        return None
    try:
        return RepoSnapshot.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValueError):
        return None


def get_snapshot(
    settings: Settings,
    *,
    repo: str | None = None,
    limit: int = 30,
    refresh: bool = False,
    source: str | None = None,
) -> RepoSnapshot:
    """Resolve a snapshot from the API, a cache file, or the offline fixture."""

    repo = repo or settings.repo
    mode = (source or settings.source).lower()
    if mode == "offline":
        return load_fixture_snapshot(repo=repo)
    if mode == "cache":
        cached = load_cache(settings.cache_path(repo))
        if cached is None:
            raise GitHubError(
                f"no cache for {repo}; run `repo-triager fetch --repo {repo}` first"
            )
        return cached
    if not refresh:
        cached = load_cache(settings.cache_path(repo))
        if cached is not None:
            return cached
    snapshot = fetch_repo_snapshot(repo, token=settings.github_token, limit=limit)
    save_cache(snapshot, settings.cache_path(repo))
    return snapshot
