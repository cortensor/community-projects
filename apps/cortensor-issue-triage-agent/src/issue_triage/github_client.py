"""Read-mostly GitHub API client (public reads need no auth).

Write operations (``apply_labels`` / ``post_comment``) require a token and
are only ever called from the approval path after a human says yes.
No token is ever written to disk by this package.
"""

from __future__ import annotations

import base64
import re
from typing import Any

import httpx

from .config import fix_proxy_env

API_BASE = "https://api.github.com"
USER_AGENT = "issue-triage/0.1.0 (cortensor-hackathon-5)"

_CODEOWNERS_LINE_RE = re.compile(r"^(\S+)\s+(.+)$")


def parse_repo(repo: str) -> tuple[str, str]:
    parts = repo.strip().split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"repo must be 'owner/name', got {repo!r}")
    return parts[0], parts[1]


def parse_issue_url(url: str) -> tuple[str, int]:
    """Accept https://github.com/owner/repo/issues/123 (trailing bits ignored)."""
    match = re.match(
        r"https?://github\.com/([^/]+)/([^/]+)/issues/(\d+)", url.strip()
    )
    if not match:
        raise ValueError(f"not a GitHub issue URL: {url!r}")
    return f"{match.group(1)}/{match.group(2)}", int(match.group(3))


def parse_codeowners(text: str) -> list[tuple[str, list[str]]]:
    """Parse a CODEOWNERS file into (pattern, owners) pairs."""
    out: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = _CODEOWNERS_LINE_RE.match(line)
        if match:
            owners = [o.lstrip("@") for o in match.group(2).split()]
            out.append((match.group(1), owners))
    return out


def owners_for_path(entries: list[tuple[str, list[str]]], path: str) -> list[str]:
    """Last matching CODEOWNERS pattern wins (GitHub semantics)."""
    path = path.lstrip("/")
    owners: list[str] = []
    for pattern, people in entries:
        pat = pattern.lstrip("/")
        if pat.endswith("/*"):
            if path.startswith(pat[:-1]):
                owners = people
        elif "*" in pat:
            if re.match(re.escape(pat).replace(r"\*", ".*") + "$", path):
                owners = people
        elif path == pat or path.startswith(pat.rstrip("/") + "/"):
            owners = people
    return owners


class GitHubClient:
    def __init__(self, token: str | None = None, transport: httpx.BaseTransport | None = None):
        fix_proxy_env()
        headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.Client(
            base_url=API_BASE, headers=headers, timeout=httpx.Timeout(30.0, connect=10.0),
            transport=transport,
        )
        self.token_present = bool(token)

    # -- reads ----------------------------------------------------------
    def get_issue(self, repo: str, number: int) -> dict[str, Any]:
        owner, name = parse_repo(repo)
        resp = self._client.get(f"/repos/{owner}/{name}/issues/{number}")
        resp.raise_for_status()
        return resp.json()

    def list_comments(self, repo: str, number: int, per_page: int = 10) -> list[dict[str, Any]]:
        owner, name = parse_repo(repo)
        resp = self._client.get(
            f"/repos/{owner}/{name}/issues/{number}/comments",
            params={"per_page": per_page},
        )
        resp.raise_for_status()
        return resp.json()

    def list_timeline(self, repo: str, number: int, per_page: int = 30) -> list[dict[str, Any]]:
        owner, name = parse_repo(repo)
        resp = self._client.get(
            f"/repos/{owner}/{name}/issues/{number}/timeline",
            params={"per_page": per_page},
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        return resp.json()

    def get_pull_summary(self, repo: str, number: int) -> dict[str, Any] | None:
        """Title/body/state of a linked PR, or None if it cannot be read.

        The classifier used to see only linked PR *numbers* ("Linked PRs:
        #770"), which say nothing. A title + body snippet is real evidence.
        """
        owner, name = parse_repo(repo)
        resp = self._client.get(f"/repos/{owner}/{name}/pulls/{number}")
        if resp.status_code in (404, 403):
            return None
        resp.raise_for_status()
        data = resp.json()
        return {
            "number": number,
            "title": data.get("title") or "",
            "body": data.get("body") or "",
            "state": data.get("state") or "",
            "merged": bool(data.get("merged")),
        }

    def list_labels(self, repo: str) -> list[str]:
        owner, name = parse_repo(repo)
        resp = self._client.get(f"/repos/{owner}/{name}/labels", params={"per_page": 100})
        resp.raise_for_status()
        return [label["name"] for label in resp.json()]

    def list_issues(
        self, repo: str, state: str = "all", per_page: int = 30, page: int = 1
    ) -> list[dict[str, Any]]:
        owner, name = parse_repo(repo)
        resp = self._client.get(
            f"/repos/{owner}/{name}/issues",
            params={"state": state, "per_page": per_page, "page": page, "sort": "created", "direction": "desc"},
        )
        resp.raise_for_status()
        # The list endpoint mixes pull requests in; callers filter on "pull_request".
        return resp.json()

    def list_contributors(self, repo: str, per_page: int = 10) -> list[dict[str, Any]]:
        owner, name = parse_repo(repo)
        resp = self._client.get(
            f"/repos/{owner}/{name}/contributors", params={"per_page": per_page}
        )
        if resp.status_code in (403, 404):
            return []
        resp.raise_for_status()
        return resp.json()

    def get_codeowners(self, repo: str) -> list[tuple[str, list[str]]]:
        owner, name = parse_repo(repo)
        for path in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"):
            resp = self._client.get(f"/repos/{owner}/{name}/contents/{path}")
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            data = resp.json()
            content = data.get("content", "")
            if data.get("encoding") == "base64":
                content = base64.b64decode(content).decode("utf-8", "replace")
            return parse_codeowners(content)
        return []

    def find_comment(self, repo: str, number: int, body: str) -> dict[str, Any] | None:
        """Return the first comment on the issue whose body matches exactly,
        or None. Crash-safety for the approval path: if a previous execute
        attempt posted the comment but died before consuming the snapshot,
        the retry must not post it a second time."""
        for comment in self.list_comments(repo, number, per_page=100):
            if (comment.get("body") or "").strip() == body.strip():
                return comment
        return None

    # -- writes (approval-gated only) -----------------------------------
    def _require_token(self) -> None:
        if not self.token_present:
            raise RuntimeError("GITHUB_TOKEN is required for write operations")

    def apply_labels(self, repo: str, number: int, labels: list[str]) -> list[str]:
        self._require_token()
        owner, name = parse_repo(repo)
        resp = self._client.post(
            f"/repos/{owner}/{name}/issues/{number}/labels", json={"labels": labels}
        )
        resp.raise_for_status()
        return [label["name"] for label in resp.json()]

    def post_comment(self, repo: str, number: int, body: str) -> dict[str, Any]:
        self._require_token()
        owner, name = parse_repo(repo)
        resp = self._client.post(
            f"/repos/{owner}/{name}/issues/{number}/comments", json={"body": body}
        )
        resp.raise_for_status()
        return resp.json()

    def close(self) -> None:
        self._client.close()


def linked_pr_numbers(timeline: list[dict[str, Any]]) -> list[int]:
    """Issue numbers of PRs referenced / cross-referenced in the timeline."""
    out: list[int] = []
    for event in timeline:
        if event.get("event") in ("cross-referenced", "referenced"):
            source = event.get("source") or {}
            issue = source.get("issue") or {}
            number = issue.get("number")
            if issue.get("pull_request") and isinstance(number, int) and number not in out:
                out.append(number)
    return out


def label_names(issue: dict[str, Any]) -> list[str]:
    return [label["name"] for label in issue.get("labels") or []]
