"""Decision validation, repair, and the report renderer."""

from __future__ import annotations

from repo_triager.agent import repair_decision, validate_decision
from repo_triager.models import RunReport, TriageDecision
from repo_triager.report import render_markdown


def test_clean_decision_has_no_problems(snapshot, issue_859):
    decision = TriageDecision(
        issue_number=859,
        severity="S2",
        component="area:tools",
        labels=["bug", "area:tools"],
        reply_draft="thanks",
    )
    assert validate_decision(decision, issue_859, snapshot) == []


def test_unknown_labels_are_reported_and_dropped(snapshot, issue_859):
    decision = TriageDecision(
        issue_number=859,
        severity="S2",
        component="area:tools",
        labels=["bug", "priority:p0"],
        reply_draft="thanks",
    )
    problems = validate_decision(decision, issue_859, snapshot)
    assert any(problem.field == "labels" for problem in problems)
    repaired = repair_decision(decision, issue_859, snapshot, problems)
    assert repaired.labels == ["bug"]


def test_unknown_duplicate_is_reported_and_dropped(snapshot, issue_859):
    decision = TriageDecision(
        issue_number=859,
        severity="S2",
        labels=["bug"],
        duplicate_of=[999_999],
        reply_draft="thanks",
    )
    problems = validate_decision(decision, issue_859, snapshot)
    repaired = repair_decision(decision, issue_859, snapshot, problems)
    assert repaired.duplicate_of == []


def test_self_duplicate_is_rejected(snapshot, issue_859):
    decision = TriageDecision(
        issue_number=859, severity="S2", labels=["bug"], duplicate_of=[859], reply_draft="x"
    )
    problems = validate_decision(decision, issue_859, snapshot)
    assert any("cannot duplicate itself" in problem.message for problem in problems)


def test_wrong_issue_number_is_corrected(snapshot, issue_859):
    decision = TriageDecision(
        issue_number=1, severity="S2", labels=["bug"], reply_draft="x"
    )
    problems = validate_decision(decision, issue_859, snapshot)
    repaired = repair_decision(decision, issue_859, snapshot, problems)
    assert repaired.issue_number == 859


def test_missing_component_asks_for_a_maintainer(snapshot, issue_859):
    decision = TriageDecision(
        issue_number=859,
        severity="S2",
        component="area:invented",
        labels=["bug"],
        reply_draft="x",
    )
    problems = validate_decision(decision, issue_859, snapshot)
    repaired = repair_decision(decision, issue_859, snapshot, problems)
    assert repaired.component == ""
    assert repaired.next_action == "needs-maintainer-input"


def test_report_markdown_summarises_records(snapshot, issue_859):
    from repo_triager.agent import build_record

    decision = TriageDecision(
        issue_number=859,
        severity="S2",
        severity_reason="a reason",
        component="area:tools",
        labels=["bug", "area:tools"],
        reply_draft="a draft",
        source="model",
    )
    report = RunReport(
        run_id="run-1",
        repo=snapshot.repo,
        started_at="2026-01-01T00:00:00+00:00",
        finished_at="2026-01-01T00:01:00+00:00",
        provider="scripted",
        source="offline",
        session_id="s",
        records=[
            build_record(
                decision,
                issue_859,
                policy_events=[{"tool": "stage_triage", "decision": "allow", "policy": "test"}],
                applied=True,
                outbox=["var/outbox/x.md"],
            )
        ],
    )
    markdown = render_markdown(report)
    assert "Repo Triager report" in markdown
    assert "#859" in markdown
    assert "S2" in markdown
    assert "a draft" in markdown
    assert "stage_triage → allow" in markdown
    assert report.summary_counts() == {"S2": 1}
