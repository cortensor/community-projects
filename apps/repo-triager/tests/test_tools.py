"""Tools execute against a fake context without any runtime or model."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_triager.models import TriageDecision
from repo_triager.tools import (
    ToolContext,
    get_issue,
    label_taxonomy,
    list_open_issues,
    render_plan_markdown,
    search_duplicate_issues,
    stage_triage,
    triage_precheck,
    use_context,
)

CALL = lambda fn: fn  # decorated tools stay callable directly


@pytest.fixture()
def context(snapshot, tmp_path):
    return ToolContext(
        repo=snapshot.repo,
        snapshot=snapshot,
        outbox_dir=Path(tmp_path) / "outbox",
    )


def test_read_tools_return_issue_json(context, issue_859):
    with use_context(context):
        payload = json.loads(get_issue(859))
        assert payload["number"] == 859
        assert payload["labels"]
        assert len(payload["body"]) <= 1420


def test_get_issue_unknown_number(context):
    with use_context(context):
        payload = json.loads(get_issue(999_999))
        assert "error" in payload


def test_list_open_issues_limit_and_shape(context):
    with use_context(context):
        items = json.loads(list_open_issues(5))
        assert len(items) == 5
        assert {"number", "title", "labels", "comments"} <= set(items[0])


def test_search_duplicate_issues_returns_ranked_candidates(context):
    with use_context(context):
        items = json.loads(search_duplicate_issues("session store leaks temp directory", 857, 5))
        assert items
        assert items[0]["score"] >= items[-1]["score"]
        assert all(item["number"] != 857 for item in items)


def test_label_taxonomy_lists_area_labels(context, snapshot):
    with use_context(context):
        labels = json.loads(label_taxonomy())
        assert len(labels) == len(snapshot.labels)
        assert any(label["name"].startswith("area:") for label in labels)


def test_triage_precheck_matches_heuristics(context, issue_859):
    with use_context(context):
        payload = json.loads(triage_precheck(859))
        assert payload["issue_number"] == 859
        assert payload["severity_suggestion"] in {"S1", "S2", "S3", "S4"}
        assert payload["component_ranking"]


def test_stage_triage_requires_pending_decision(context):
    with use_context(context):
        payload = json.loads(
            stage_triage(
                issue_number=859,
                severity="S2",
                component="area:tools",
                labels=["bug"],
                reply_draft="draft",
            )
        )
        assert payload["error"] == "no pending decision for this run"
        assert not context.applied


def test_stage_triage_rejects_unknown_labels(context):
    context.pending_decision = TriageDecision(issue_number=859, severity="S2")
    with use_context(context):
        payload = json.loads(
            stage_triage(
                issue_number=859,
                severity="S2",
                component="area:tools",
                labels=["bug", "area:made-up"],
                reply_draft="draft",
            )
        )
        assert payload["error"] == "plan rejected"
        assert any("made-up" in problem for problem in payload["problems"])
        assert not context.applied


def test_stage_triage_rejects_unknown_duplicates(context):
    context.pending_decision = TriageDecision(issue_number=859, severity="S2")
    with use_context(context):
        payload = json.loads(
            stage_triage(
                issue_number=859,
                severity="S2",
                component="area:tools",
                labels=["bug"],
                reply_draft="draft",
                duplicate_of=[424242],
            )
        )
        assert payload["error"] == "plan rejected"


def test_stage_triage_writes_local_outbox(context):
    context.pending_decision = TriageDecision(issue_number=859, severity="S2")
    with use_context(context):
        payload = json.loads(
            stage_triage(
                issue_number=859,
                severity="S2",
                component="area:tools",
                labels=["bug", "area:tools"],
                reply_draft="Thanks — this is an S2.",
                duplicate_of=[],
                next_action="ready-to-label",
            )
        )
    assert payload["staged"] is True
    assert context.applied is True
    markdown, payload_json = context.outbox_paths
    text = Path(markdown).read_text(encoding="utf-8")
    assert "#859" in text
    assert "dry run" in text
    assert json.loads(Path(payload_json).read_text(encoding="utf-8"))["labels"] == [
        "bug",
        "area:tools",
    ]
    assert context.tool_events[-1]["tool"] == "stage_triage"


def test_stage_triage_rejects_wrong_issue(context):
    context.pending_decision = TriageDecision(issue_number=853, severity="S2")
    with use_context(context):
        payload = json.loads(
            stage_triage(
                issue_number=859,
                severity="S2",
                component="area:tools",
                labels=["bug"],
                reply_draft="draft",
            )
        )
        assert payload["error"].startswith("issue_number does not match")


def test_render_plan_markdown_contains_gate_facts(issue_859):
    decision = TriageDecision(
        issue_number=859,
        severity="S2",
        severity_reason="reason",
        component="area:tools",
        labels=["bug"],
        duplicate_of=[853],
        reply_draft="hello",
    )
    markdown = render_plan_markdown(decision, issue_859)
    assert "Severity: **S2**" in markdown
    assert "#853" in markdown
    assert "nothing was written to GitHub" in markdown
