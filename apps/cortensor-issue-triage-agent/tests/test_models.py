"""Verdict / draft model validation: illegal values must fail loudly."""

import pytest
from pydantic import ValidationError

from issue_triage.models import TriageDraft, TriageVerdict

BASE = {
    "issue_type": "bug",
    "severity": "high",
    "component": "area:brain",
    "route": "ready-to-fix",
    "confidence": 0.8,
    "rationale": "test",
}


def test_valid_verdict():
    v = TriageVerdict.model_validate(BASE)
    assert v.issue_type == "bug"
    assert v.suggested_labels == []
    assert v.assignee is None


def test_illegal_issue_type_rejected():
    with pytest.raises(ValidationError):
        TriageVerdict.model_validate({**BASE, "issue_type": "failure"})


def test_illegal_severity_rejected():
    with pytest.raises(ValidationError):
        TriageVerdict.model_validate({**BASE, "severity": "urgent"})


def test_illegal_route_rejected():
    with pytest.raises(ValidationError):
        TriageVerdict.model_validate({**BASE, "route": "ship-it"})


def test_confidence_out_of_range_rejected():
    with pytest.raises(ValidationError):
        TriageVerdict.model_validate({**BASE, "confidence": 1.5})
    with pytest.raises(ValidationError):
        TriageVerdict.model_validate({**BASE, "confidence": -0.1})


def test_confidence_bounds_accepted():
    assert TriageVerdict.model_validate({**BASE, "confidence": 0}).confidence == 0
    assert TriageVerdict.model_validate({**BASE, "confidence": 1}).confidence == 1


def test_all_issue_types_accepted():
    for t in ("bug", "feature", "question", "docs", "chore", "duplicate"):
        assert TriageVerdict.model_validate({**BASE, "issue_type": t}).issue_type == t


def test_draft_requires_text():
    with pytest.raises(ValidationError):
        TriageDraft.model_validate({})
    assert TriageDraft.model_validate({"draft": "hi"}).draft == "hi"


def test_synonym_enhancement_maps_to_feature():
    # the 2026-11-16 eval lost #767 this way: the model answered
    # "enhancement" (a real GitHub label) for a feature request
    assert TriageVerdict.model_validate({**BASE, "issue_type": "enhancement"}).issue_type == "feature"


def test_synonym_variants_normalised():
    assert TriageVerdict.model_validate({**BASE, "issue_type": "Enhancement"}).issue_type == "feature"
    assert TriageVerdict.model_validate({**BASE, "issue_type": "feature_request"}).issue_type == "feature"
    assert TriageVerdict.model_validate({**BASE, "issue_type": "bug report"}).issue_type == "bug"
    assert TriageVerdict.model_validate({**BASE, "issue_type": "documentation"}).issue_type == "docs"
    assert TriageVerdict.model_validate({**BASE, "issue_type": "doc"}).issue_type == "docs"
    assert TriageVerdict.model_validate({**BASE, "severity": "blocker"}).severity == "critical"
    assert TriageVerdict.model_validate({**BASE, "severity": "minor"}).severity == "low"
    assert TriageVerdict.model_validate({**BASE, "route": "needs_info"}).route == "needs-info"
    assert TriageVerdict.model_validate({**BASE, "route": "Ready To Fix"}).route == "ready-to-fix"


def test_unknown_enum_still_rejected_after_normalisation():
    with pytest.raises(ValidationError):
        TriageVerdict.model_validate({**BASE, "issue_type": "failure"})
    with pytest.raises(ValidationError):
        TriageVerdict.model_validate({**BASE, "issue_type": "wontfix"})
    with pytest.raises(ValidationError):
        TriageVerdict.model_validate({**BASE, "severity": "urgent"})
    with pytest.raises(ValidationError):
        TriageVerdict.model_validate({**BASE, "route": "ship-it"})
