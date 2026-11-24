"""The read-only GitHub client and the offline snapshot path."""

from __future__ import annotations

import pytest

from repo_triager.github import (
    GitHubError,
    fetch_repo_snapshot,
    get_snapshot,
    load_cache,
    save_cache,
)
from repo_triager.config import Settings


def test_fixture_snapshot_has_issues_and_labels(snapshot):
    assert snapshot.repo == "openminion/openminion"
    assert len(snapshot.issues) >= 40
    assert len(snapshot.labels) >= 30
    assert all(issue.url.startswith("https://github.com/") for issue in snapshot.issues[:5])


def test_save_and_load_cache_roundtrip(snapshot, tmp_path):
    path = tmp_path / "cache.json"
    save_cache(snapshot, path)
    loaded = load_cache(path)
    assert loaded is not None
    assert len(loaded.issues) == len(snapshot.issues)
    assert loaded.issue(859).title == snapshot.issue(859).title  # type: ignore[union-attr]


def test_load_cache_missing_and_broken(tmp_path):
    assert load_cache(tmp_path / "nope.json") is None
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert load_cache(broken) is None


def test_get_snapshot_offline_is_repo_agnostic(tmp_path):
    settings = Settings(workspace=tmp_path, repo="other/repo")
    snapshot = get_snapshot(settings, source="offline")
    assert snapshot.repo == "other/repo"
    assert snapshot.issues


def test_get_snapshot_cache_mode_errors_without_cache(tmp_path):
    settings = Settings(workspace=tmp_path, repo="other/repo")
    with pytest.raises(GitHubError):
        get_snapshot(settings, source="cache")


def test_get_snapshot_prefers_cache_when_not_refreshing(tmp_path, snapshot):
    settings = Settings(workspace=tmp_path, repo="openminion/openminion")
    settings.ensure_dirs()
    trimmed = snapshot.model_copy(update={"issues": snapshot.issues[:1]})
    save_cache(trimmed, settings.cache_path())
    resolved = get_snapshot(settings, source="live", refresh=False)
    assert len(resolved.issues) == 1


@pytest.mark.integration
def test_live_fetch_reads_public_repository():
    """One real read-only request; skipped when the network is unavailable."""

    try:
        snapshot = fetch_repo_snapshot("openminion/openminion", limit=5)
    except GitHubError as exc:  # pragma: no cover - offline CI
        pytest.skip(f"network unavailable: {exc}")
    assert snapshot.source == "github-api"
    assert snapshot.issues
    assert snapshot.labels
    assert all(issue.title for issue in snapshot.issues)
