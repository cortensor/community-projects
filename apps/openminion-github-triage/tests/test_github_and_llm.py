from typing import Any

import httpx

from triage_agent.github_source import GitHubClient
from triage_agent.llm import OpenAICompatibleModelClient
from triage_agent.models import IssueAssessment, IssueInput


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get_json(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        self.calls.append((url, headers))
        if "/issues/" in url:
            return {"number": 7, "title": "Offline issue", "labels": []}
        return {"tag_name": "v1.0.0", "body": "- [x] Tests"}


def test_github_client_uses_injected_transport() -> None:
    transport = FakeTransport()
    client = GitHubClient(token="test-token", transport=transport)
    issue = client.fetch_issue("owner/repo", 7)
    release = client.fetch_release("owner/repo", "v1.0.0")
    assert issue["number"] == 7
    assert release["tag_name"] == "v1.0.0"
    assert transport.calls[0][0] == "https://api.github.com/repos/owner/repo/issues/7"
    assert transport.calls[0][1]["Authorization"] == "Bearer test-token"


def test_openai_compatible_client_with_mock_http() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request.read().decode("utf-8")
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Check the migration evidence."}}]},
        )

    client = OpenAICompatibleModelClient(
        base_url="http://offline.local/v1",
        api_key="local",
        model="test-model",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    issue = IssueInput(number=1, title="Offline", body="No steps")
    assessment = IssueAssessment(
        severity="medium",
        confidence=0.7,
        categories=["reliability"],
        repro_score=0,
        missing_repro_fields=["steps"],
    )
    assert client.review_issue(issue, assessment) == "Check the migration evidence."
    assert captured["url"] == "http://offline.local/v1/chat/completions"
    assert '"model":"test-model"' in captured["body"]

