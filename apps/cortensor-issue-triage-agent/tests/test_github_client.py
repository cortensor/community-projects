"""GitHub client parsing: issues, comments, timeline, CODEOWNERS, URLs."""

import httpx
import pytest

from issue_triage.github_client import (
    GitHubClient,
    label_names,
    linked_pr_numbers,
    owners_for_path,
    parse_codeowners,
    parse_issue_url,
    parse_repo,
)


def test_parse_repo_ok():
    assert parse_repo("openminion/openminion") == ("openminion", "openminion")


def test_parse_repo_bad():
    with pytest.raises(ValueError):
        parse_repo("not-a-repo")
    with pytest.raises(ValueError):
        parse_repo("a/b/c")


def test_parse_issue_url():
    assert parse_issue_url("https://github.com/openminion/openminion/issues/778") == (
        "openminion/openminion",
        778,
    )
    with pytest.raises(ValueError):
        parse_issue_url("https://github.com/openminion/openminion/pull/1")


def test_get_issue(github_client):
    issue = github_client.get_issue("openminion/openminion", 778)
    assert issue["number"] == 778
    assert label_names(issue) == ["bug", "area:brain"]


def test_list_comments(github_client):
    comments = github_client.list_comments("openminion/openminion", 778)
    assert comments[0]["body"] == "Confirmed."


def test_timeline_linked_prs(github_client):
    timeline = github_client.list_timeline("openminion/openminion", 778)
    assert linked_pr_numbers(timeline) == [770]


def test_list_labels(github_client):
    assert "bug" in github_client.list_labels("openminion/openminion")


def test_codeowners_missing_returns_empty(github_client):
    assert github_client.get_codeowners("openminion/openminion") == []


def test_parse_codeowners():
    text = "# comment\n/src/brain/ @alice @bob\n/docs/ @carol\n"
    entries = parse_codeowners(text)
    assert entries == [("/src/brain/", ["alice", "bob"]), ("/docs/", ["carol"])]


def test_owners_for_path_last_match_wins():
    entries = [("/src/", ["alice"]), ("/src/brain/", ["bob"])]
    assert owners_for_path(entries, "/src/brain/engine.py") == ["bob"]
    assert owners_for_path(entries, "/src/other.py") == ["alice"]
    assert owners_for_path(entries, "/README.md") == []


def test_list_issues_page_param():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["page"] = request.url.params.get("page")
        return httpx.Response(200, json=[{"number": 778}])

    client = GitHubClient(transport=httpx.MockTransport(handler))
    try:
        issues = client.list_issues("openminion/openminion", page=2)
        assert issues[0]["number"] == 778
        assert seen["page"] == "2"
    finally:
        client.close()


def test_write_without_token_refused():
    client = GitHubClient()
    with pytest.raises(RuntimeError, match="GITHUB_TOKEN"):
        client.apply_labels("o/r", 1, ["bug"])
    with pytest.raises(RuntimeError, match="GITHUB_TOKEN"):
        client.post_comment("o/r", 1, "hi")
    client.close()
