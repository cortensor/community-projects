"""Shared stubs: a fake clock (no real 45 s waits) and loopback HTTP stubs
for both the OpenAI-compatible endpoint and the GitHub API."""

from __future__ import annotations

import json

import httpx
import pytest

VERDICT_ARGS = {
    "issue_type": "bug",
    "severity": "high",
    "component": "area:brain",
    "suggested_labels": ["bug", "area:brain"],
    "assignee": None,
    "route": "ready-to-fix",
    "confidence": 0.8,
    "rationale": "stub verdict",
    "evidence": ["stub"],
    "duplicate_of": None,
}

DRAFT_ARGS = {"draft": "Thanks for reporting — we are looking into it.", "tone": "neutral"}


class FakeClock:
    def __init__(self):
        self.now = 1000.0
        self.slept: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def llm_stub_handler(tool_calls: bool = True, content_json: bool = True):
    """MockTransport handler for the OpenAI-compatible endpoint."""
    state = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["n"] += 1
        payload = json.loads(request.content.decode())
        tools = payload.get("tools") or []
        if tools and tool_calls:
            name = tools[0]["function"]["name"]
            args = VERDICT_ARGS if "verdict" in name else DRAFT_ARGS
            message = {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call-stub",
                        "type": "function",
                        "function": {"name": name, "arguments": json.dumps(args)},
                    }
                ],
            }
        else:
            # no tools: plain-text JSON. Tell draft apart from classify by
            # the prompt wording (the draft retry sends no tools).
            joined = " ".join(m.get("content") or "" for m in payload.get("messages") or [])
            args = DRAFT_ARGS if "Draft the first triage reply" in joined else VERDICT_ARGS
            message = {"role": "assistant", "content": json.dumps(args) if content_json else "no json here"}
        return httpx.Response(
            200,
            json={
                "model": "stub-model",
                "choices": [{"message": message, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            },
        )

    handler.calls = state
    return handler


ISSUE_778 = {
    "number": 778,
    "title": "brain: completion still rests on confidence",
    "body": "The completion path trusts confidence and closes unverified work.",
    "state": "open",
    "user": {"login": "reporter-x"},
    "labels": [{"name": "bug"}, {"name": "area:brain"}],
}

REPO_LABELS = ["bug", "area:brain", "enhancement", "question", "documentation", "duplicate"]


def github_stub_handler():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/issues/778"):
            return httpx.Response(200, json=ISSUE_778)
        if path.endswith("/issues/778/comments"):
            return httpx.Response(200, json=[{"user": {"login": "maintainer"}, "body": "Confirmed."}])
        if path.endswith("/issues/778/timeline"):
            return httpx.Response(
                200,
                json=[
                    {"event": "cross-referenced",
                     "source": {"issue": {"number": 770, "pull_request": {"url": "x"}}}},
                    {"event": "commented"},
                ],
            )
        if path.endswith("/pulls/770"):
            return httpx.Response(200, json={
                "number": 770, "title": "Fix brain completion gating",
                "body": "This PR gates completion on verification.",
                "state": "open", "merged": False,
            })
        if path.endswith("/labels"):
            return httpx.Response(200, json=[{"name": n} for n in REPO_LABELS])
        if path.endswith("/contributors"):
            return httpx.Response(200, json=[{"login": "alice"}, {"login": "bob"}])
        if "/contents/" in path:
            return httpx.Response(404, json={"message": "Not Found"})
        if path.endswith("/issues"):
            return httpx.Response(200, json=[ISSUE_778])
        return httpx.Response(404, json={"message": "not stubbed: " + path})

    return handler


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def llm_client(clock):
    from issue_triage.llm_client import DirectClient

    client = DirectClient(
        base_url="https://stub.invalid",
        model="stub",
        min_interval_sec=45,
        transport=httpx.MockTransport(llm_stub_handler()),
        sleep=clock.sleep,
        clock=clock.time,
    )
    yield client
    client.close()


@pytest.fixture
def github_client():
    from issue_triage.github_client import GitHubClient

    client = GitHubClient(transport=httpx.MockTransport(github_stub_handler()))
    yield client
    client.close()
