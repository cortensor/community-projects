from triage_agent.analyzer import assess_issue, assess_release
from triage_agent.models import IssueInput, ReleaseInput


def test_security_issue_and_complete_reproduction() -> None:
    issue = IssueInput(
        number=9,
        title="Credential leak in logs",
        body=(
            "Steps to reproduce: run the importer with auth debug enabled.\n"
            "Expected: tokens are redacted.\n"
            "Actual: tokens appear in the log.\n"
            "Environment: Python 3.13\n"
            "Logs:\n```\nsecret=abc\n```"
        ),
        labels=["security"],
    )
    result = assess_issue(issue)
    assert result.severity == "critical"
    assert result.repro_score == 100
    assert result.missing_repro_fields == []
    assert "security-sensitive" in result.risk_flags


def test_incomplete_bug_is_medium_and_flagged() -> None:
    issue = IssueInput(
        number=10,
        title="Button fails sometimes",
        body="It sometimes breaks.",
        labels=["bug"],
    )
    result = assess_issue(issue)
    assert result.severity == "medium"
    assert result.repro_score < 40
    assert "repro-incomplete" in result.risk_flags
    assert "steps" in result.missing_repro_fields


def test_release_with_unchecked_item_is_held() -> None:
    release = ReleaseInput(
        tag_name="v2.0.0",
        name="v2.0.0",
        body="- [x] Tests\n- [ ] Migration notes\n\nBreaking changes: CLI rename.",
        assets=[{"name": "pkg.whl"}],
    )
    result = assess_release(release)
    assert result.verdict == "hold"
    assert result.checked_count == 1
    assert result.unchecked_count == 1
    assert result.blockers == ["unchecked release item: Migration notes"]


def test_complete_release_can_ship() -> None:
    release = ReleaseInput(
        tag_name="v1.2.3",
        name="v1.2.3",
        body="- [x] Tests\n- [x] Changelog",
        assets=[{"name": "pkg.whl"}],
    )
    assert assess_release(release).verdict == "ship"


def test_invalid_version_is_a_blocker() -> None:
    release = ReleaseInput(tag_name="latest", name="latest", body="- [x] Tests")
    result = assess_release(release)
    assert result.verdict == "hold"
    assert "release tag is not semantic versioning" in result.blockers

