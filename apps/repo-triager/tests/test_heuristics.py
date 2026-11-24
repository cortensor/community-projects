"""Deterministic triage heuristics."""

from __future__ import annotations

import pytest

from repo_triager.heuristics import (
    component_hint,
    heuristic_decision,
    issue_type_hint,
    labels_for_decision,
    severity_hint,
    severity_score,
    similar_issues,
    similarity,
    tokenize,
)
from repo_triager.models import Issue


def make_issue(number=1, title="", body="", labels=None):
    return Issue(number=number, title=title, body=body, labels=labels or [])


def test_tokenize_drops_stopwords_and_short_tokens():
    tokens = tokenize("The session store does not close, and it leaks")
    assert "session" in tokens
    assert "leaks" in tokens
    assert "the" not in tokens
    assert "it" not in tokens


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Data loss when the cache is purged", "S2"),
        ("Every turn hangs forever and corrupts the session file", "S1"),
        ("Docs typo in README quick start", "S4"),
        ("Feature request: add file.mkdir", "S3"),
    ],
)
def test_severity_bands(text, expected):
    severity, _ = severity_hint(make_issue(title=text))
    assert severity == expected


def test_severity_uses_labels():
    bug = make_issue(title="small problem", labels=["bug"])
    enhancement = make_issue(title="small problem", labels=["enhancement"])
    assert severity_score(bug)[0] > severity_score(enhancement)[0]


def test_author_marked_fix_in_release_lowers_severity():
    plain = make_issue(title="session diff hashes ids", labels=["bug"])
    released = make_issue(
        title="session diff hashes ids", labels=["bug", "status:awaiting-release"]
    )
    assert severity_score(released)[0] < severity_score(plain)[0]


def test_component_prefers_area_label():
    issue = make_issue(
        title="memctl cannot run",
        body="the memory CLI needs memory.yaml that nothing creates",
        labels=["bug", "area:config"],
    )
    component, ranked = component_hint(issue)
    assert component == "area:config"
    assert ranked[0][1] >= 12


def test_component_falls_back_to_keywords():
    issue = make_issue(
        title="OpenAI provider fails behind a proxy",
        body="the ollama adapter raises Invalid port",
    )
    component, _ = component_hint(issue)
    assert component == "area:providers"


def test_component_empty_when_nothing_matches():
    issue = make_issue(title="hello", body="nothing to see")
    component, ranked = component_hint(issue)
    assert component == ""
    assert ranked == []


@pytest.mark.parametrize(
    "issue,expected",
    [
        (make_issue(title="Crash on startup", labels=["bug"]), "bug"),
        (make_issue(title="Add file.copy tool"), "enhancement"),
        (make_issue(title="Docs: typo in README"), "documentation"),
        (make_issue(title="Why is the daemon needed?"), "question"),
    ],
)
def test_issue_type(issue, expected):
    assert issue_type_hint(issue) == expected


def test_similarity_prefers_near_duplicates():
    first = make_issue(
        title="localhost provider breaks with bracketed IPv6 no_proxy entries",
        body="Invalid port ':1]' is raised before the request",
    )
    second = make_issue(
        title="ollama provider fails when no_proxy has bracketed IPv6 entries",
        body="port parsing raises Invalid port ':1]'",
    )
    other = make_issue(title="docs typo in readme", body="small typo")
    assert similarity(first, second) > similarity(first, other)


def test_similar_issues_excludes_self_and_sorts(snapshot):
    issue = snapshot.issue(834)
    assert issue is not None
    candidates = similar_issues(issue, snapshot.issues, limit=5)
    assert candidates
    assert all(candidate.number != issue.number for candidate in candidates)
    assert candidates == sorted(candidates, key=lambda item: (-item.score, item.number))


def test_labels_respect_taxonomy(snapshot):
    issue = snapshot.issue(859)
    assert issue is not None
    labels = labels_for_decision(
        issue, "S2", "area:tools", "bug", snapshot.labels, duplicates=[]
    )
    assert {"bug", "area:tools"} <= set(labels)
    unknown = labels_for_decision(issue, "S2", "area:nope", "bug", snapshot.labels, [])
    assert "area:nope" not in unknown


def test_heuristic_decision_is_complete(snapshot):
    issue = snapshot.issue(853)
    assert issue is not None
    decision, ranked = heuristic_decision(issue, snapshot.labels, snapshot.issues)
    assert decision.issue_number == 853
    assert decision.source == "heuristic"
    assert decision.severity in {"S1", "S2", "S3", "S4"}
    assert decision.component == "area:sdk"
    assert decision.reply_draft
    assert set(decision.labels) <= snapshot.label_names
