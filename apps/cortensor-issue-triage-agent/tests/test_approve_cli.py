"""Approval CLI regression tests (no network, no model).

Covers the 2026-11-17 approval bug: a tokenless ``approve --yes`` used to
call ``approve_once()`` before checking for a token, moving the snapshot
to "approved" — and the later token-bearing run was then refused by
``approve_once`` ("not pending"), so the snapshot could never execute.
A tokenless run must now leave the snapshot pending, and a token-bearing
run must resume from either "pending" or a stranded "approved".
Also covers the partial-write case (labels applied, comment post fails)
and the comment-dedup guard (crash between post and consume).
"""

import pytest
from typer.testing import CliRunner

import issue_triage.cli as cli_mod
from issue_triage.approval import SnapshotStore
from issue_triage.cli import app
from issue_triage.models import Snapshot, TriageDraft, TriageVerdict

runner = CliRunner()


def _snap(sid="s-1", number=1):
    return Snapshot(
        id=sid,
        repo="owner/repo",
        issue_number=number,
        issue_title="t",
        verdict=TriageVerdict(
            issue_type="bug", severity="high", component="x",
            suggested_labels=["bug"],
            route="ready-to-fix", confidence=0.8, rationale="t",
        ),
        draft=TriageDraft(draft="hello, maintainer"),
    )


class FakeGitHub:
    """Stub for issue_triage.cli.GitHubClient; behaviour toggled per test."""

    instances: list = []

    def __init__(self, token=None):
        self.token = token
        self.labels_applied: list[list[str]] = []
        self.comments_posted: list[str] = []
        self.fail_post = False
        self.existing_comment: dict | None = None
        FakeGitHub.instances.append(self)

    def apply_labels(self, repo, number, labels):
        self.labels_applied.append(list(labels))
        return list(labels)

    def post_comment(self, repo, number, body):
        if self.fail_post:
            raise RuntimeError("network down mid-write")
        self.comments_posted.append(body)
        return {"html_url": f"https://github.com/{repo}/issues/{number}#c1"}

    def find_comment(self, repo, number, body):
        if self.existing_comment is not None:
            return self.existing_comment
        return None

    def close(self):
        pass


@pytest.fixture(autouse=True)
def _reset_fake():
    FakeGitHub.instances.clear()
    yield
    FakeGitHub.instances.clear()


def _store_with_snapshot(tmp_path, monkeypatch, status=None):
    monkeypatch.chdir(tmp_path)
    store = SnapshotStore(tmp_path / ".issue-triage" / "pending")
    # SnapshotStore() in the CLI uses the default root ".issue-triage/pending"
    # relative to CWD, so save through a store rooted there.
    cli_store = SnapshotStore(".issue-triage/pending")
    cli_store.save(_snap())
    if status == "approved":
        cli_store.approve_once("s-1")
    return cli_store


def test_tokenless_approve_leaves_pending(tmp_path, monkeypatch):
    store = _store_with_snapshot(tmp_path, monkeypatch)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(cli_mod, "GitHubClient", FakeGitHub)
    result = runner.invoke(app, ["approve", "--snapshot", "s-1", "--yes"])
    assert result.exit_code == 0
    assert "gh api" in result.output
    assert "nothing was executed" in result.output
    assert store.load("s-1").status == "pending"
    assert FakeGitHub.instances == []  # no GitHub client built at all


def test_tokenless_then_token_approve_consumes(tmp_path, monkeypatch):
    store = _store_with_snapshot(tmp_path, monkeypatch)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(cli_mod, "GitHubClient", FakeGitHub)
    first = runner.invoke(app, ["approve", "--snapshot", "s-1", "--yes"])
    assert first.exit_code == 0
    assert store.load("s-1").status == "pending"
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    second = runner.invoke(app, ["approve", "--snapshot", "s-1", "--yes"])
    assert second.exit_code == 0
    assert "labels applied: bug" in second.output
    assert "comment posted:" in second.output
    assert store.load("s-1").status == "consumed"
    assert len(FakeGitHub.instances) == 1
    assert FakeGitHub.instances[0].comments_posted == ["hello, maintainer"]


def test_stranded_approved_snapshot_resumes_with_token(tmp_path, monkeypatch):
    # A snapshot left "approved" by the old buggy tokenless path.
    store = _store_with_snapshot(tmp_path, monkeypatch, status="approved")
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setattr(cli_mod, "GitHubClient", FakeGitHub)
    result = runner.invoke(app, ["approve", "--snapshot", "s-1", "--yes"])
    assert result.exit_code == 0
    assert store.load("s-1").status == "consumed"


def test_partial_write_stays_approved_then_retries(tmp_path, monkeypatch):
    store = _store_with_snapshot(tmp_path, monkeypatch)
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    failing = FakeGitHub(token="fake-token")
    failing.fail_post = True
    monkeypatch.setattr(cli_mod, "GitHubClient", lambda token=None: failing)
    first = runner.invoke(app, ["approve", "--snapshot", "s-1", "--yes"])
    assert first.exit_code == 1
    assert "stays 'approved'" in first.output
    assert store.load("s-1").status == "approved"
    assert failing.labels_applied == [["bug"]]
    assert failing.comments_posted == []
    # Retry with a working client: labels re-applied (idempotent), comment
    # posted exactly once, snapshot consumed.
    working = FakeGitHub(token="fake-token")
    monkeypatch.setattr(cli_mod, "GitHubClient", lambda token=None: working)
    second = runner.invoke(app, ["approve", "--snapshot", "s-1", "--yes"])
    assert second.exit_code == 0
    assert store.load("s-1").status == "consumed"
    assert working.comments_posted == ["hello, maintainer"]


def test_comment_dedup_skips_repost(tmp_path, monkeypatch):
    store = _store_with_snapshot(tmp_path, monkeypatch)
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    client = FakeGitHub(token="fake-token")
    client.existing_comment = {"id": 99, "body": "hello, maintainer"}
    monkeypatch.setattr(cli_mod, "GitHubClient", lambda token=None: client)
    result = runner.invoke(app, ["approve", "--snapshot", "s-1", "--yes"])
    assert result.exit_code == 0
    assert "already present" in result.output
    assert client.comments_posted == []
    assert store.load("s-1").status == "consumed"


def test_approve_consumed_or_rejected_refused(tmp_path, monkeypatch):
    store = _store_with_snapshot(tmp_path, monkeypatch)
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setattr(cli_mod, "GitHubClient", FakeGitHub)
    ok = runner.invoke(app, ["approve", "--snapshot", "s-1", "--yes"])
    assert ok.exit_code == 0
    again = runner.invoke(app, ["approve", "--snapshot", "s-1", "--yes"])
    assert again.exit_code == 1
    assert "consumed" in again.output
