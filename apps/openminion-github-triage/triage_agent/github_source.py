from __future__ import annotations

import json
import os
from typing import Any, Protocol
from urllib.parse import quote
from urllib.request import Request, urlopen


class JsonTransport(Protocol):
    def get_json(self, url: str, headers: dict[str, str]) -> dict[str, Any]: ...


class HttpJsonTransport:
    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self.timeout_seconds = timeout_seconds

    def get_json(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        request = Request(url, headers=headers, method="GET")
        with urlopen(request, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("GitHub response was not a JSON object")
        return payload


class GitHubClient:
    def __init__(
        self,
        *,
        token: str | None = None,
        transport: JsonTransport | None = None,
        api_base: str = "https://api.github.com",
    ) -> None:
        self.token = token if token is not None else os.getenv("GITHUB_TOKEN", "")
        self.transport = transport or HttpJsonTransport()
        self.api_base = api_base.rstrip("/")

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "openminion-triage-agent/0.1",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    @staticmethod
    def _repo_parts(repo: str) -> tuple[str, str]:
        owner, separator, name = repo.strip().partition("/")
        if not separator or not owner or not name:
            raise ValueError("repo must use owner/name format")
        return quote(owner, safe=""), quote(name, safe="")

    def fetch_issue(self, repo: str, number: int) -> dict[str, Any]:
        owner, name = self._repo_parts(repo)
        if number <= 0:
            raise ValueError("issue number must be positive")
        return self.transport.get_json(
            f"{self.api_base}/repos/{owner}/{name}/issues/{number}",
            self._headers(),
        )

    def fetch_release(self, repo: str, tag: str) -> dict[str, Any]:
        owner, name = self._repo_parts(repo)
        if not tag.strip():
            raise ValueError("release tag is required")
        return self.transport.get_json(
            f"{self.api_base}/repos/{owner}/{name}/releases/tags/{quote(tag, safe='')}",
            self._headers(),
        )


def load_json_file(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload

