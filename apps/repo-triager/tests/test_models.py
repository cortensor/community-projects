"""Typed records: clamping, dedupe, and snapshot lookup."""

from __future__ import annotations

import pytest

from repo_triager.models import Issue, RepoSnapshot, TriageDecision, ValidationProblem


def test_confidence_is_clamped():
    assert TriageDecision(issue_number=1, severity="S2", confidence=3.7).confidence == 1.0
    assert TriageDecision(issue_number=1, severity="S2", confidence=-2).confidence == 0.0


def test_duplicate_numbers_are_deduplicated_in_order():
    decision = TriageDecision(
        issue_number=1, severity="S3", duplicate_of=[5, 5, 9, 5, 2]
    )
    assert decision.duplicate_of == [5, 9, 2]


def test_severity_must_be_a_band():
    with pytest.raises(ValueError):
        TriageDecision(issue_number=1, severity="critical")  # type: ignore[arg-type]


def test_snapshot_lookup_and_label_names(snapshot):
    assert snapshot.issue(859) is not None
    assert snapshot.issue(999_999) is None
    assert "area:tools" in snapshot.label_names


def test_issue_search_text_joins_title_and_body():
    issue = Issue(number=7, title="Title", body="Body")
    assert issue.search_text == "Title\nBody"


def test_snapshot_validates_from_fixture_payload():
    snapshot = RepoSnapshot.model_validate(
        {
            "repo": "a/b",
            "labels": [{"name": "bug"}],
            "issues": [{"number": 1, "title": "t", "body": "b", "labels": ["bug"]}],
        }
    )
    assert snapshot.issue(1).title == "t"  # type: ignore[union-attr]


def test_validation_problem_is_serialisable():
    problem = ValidationProblem(field="labels", message="unknown")
    assert problem.model_dump() == {"field": "labels", "message": "unknown"}
