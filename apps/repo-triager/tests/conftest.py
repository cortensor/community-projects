"""Shared fixtures: a scripted provider, a temp workspace, and one shared runtime."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_triager.config import RuntimeSession, Settings
from repo_triager.github import load_fixture_snapshot
from repo_triager.scripted_demo import scripts_for_issues

FIXTURE = Path(__file__).parent / "fixtures" / "issues_openminion.json"


@pytest.fixture(scope="session")
def snapshot():
    return load_fixture_snapshot(FIXTURE)


@pytest.fixture()
def issue_859(snapshot):
    issue = snapshot.issue(859)
    assert issue is not None
    return issue


@pytest.fixture()
def issue_853(snapshot):
    issue = snapshot.issue(853)
    assert issue is not None
    return issue


@pytest.fixture(scope="session")
def workspace(tmp_path_factory):
    return tmp_path_factory.mktemp("repo-triager-ws")


@pytest.fixture(scope="session")
def settings(workspace):
    settings = Settings(
        repo="openminion/openminion",
        workspace=workspace,
        provider_mode="scripted",
    )
    settings.ensure_dirs()
    return settings


@pytest.fixture(scope="session")
def runtime_session(settings, snapshot):
    """Boot OpenMinion once for the whole integration module."""

    issues = [issue for issue in (snapshot.issue(859), snapshot.issue(853)) if issue]
    scripts = scripts_for_issues(snapshot, issues)
    with RuntimeSession(settings, provider_mode="scripted", scripted_scripts=scripts) as session:
        yield session


@pytest.fixture(scope="session")
def runtime(runtime_session, settings):
    from repo_triager.agent import open_runtime

    rt = open_runtime(settings)
    yield rt
    rt.close()


@pytest.fixture()
def request_log(tmp_path):
    return tmp_path / "requests.jsonl"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


@pytest.fixture(autouse=True)
def _quiet_env(monkeypatch):
    monkeypatch.setenv("REPO_TRIAGER_LOG_LEVEL", "ERROR")
    monkeypatch.delenv("OPENMINION_HOME", raising=False)
