"""CLI surface: parser wiring, issue selection, stored reports."""

from __future__ import annotations

import json

import pytest

from repo_triager.agent import build_record
from repo_triager.cli import _issues_from_args, build_parser, main
from repo_triager.models import RunReport, TriageDecision
from repo_triager.report import write_report


def test_parser_exposes_every_command():
    parser = build_parser()
    args = parser.parse_args(["triage", "--issue", "859", "--apply", "deny"])
    assert args.issue == 859
    assert args.apply == "deny"
    assert args.repo == "openminion/openminion"
    for command in ("doctor", "fetch", "labels", "batch", "demo", "skills", "schedule", "report"):
        assert parser.parse_args([command]).func is not None


def test_parser_rejects_unknown_apply_mode():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["triage", "--issue", "1", "--apply", "maybe"])


def test_issue_selection_by_number_and_limit(snapshot):
    args = build_parser().parse_args(["batch", "--limit", "3"])
    assert len(_issues_from_args(snapshot, args)) == 3

    args = build_parser().parse_args(["batch", "--issues", "859,853"])
    picked = _issues_from_args(snapshot, args)
    assert [issue.number for issue in picked] == [859, 853]

    args = build_parser().parse_args(["triage", "--issue", "834"])
    assert [issue.number for issue in _issues_from_args(snapshot, args)] == [834]


def test_report_command_renders_latest_run(tmp_path, snapshot, capsys, issue_859):
    settings_home = tmp_path / "var"
    runs = settings_home / "runs" / "run-1"
    decision = TriageDecision(
        issue_number=859, severity="S2", component="area:tools", labels=["bug"], reply_draft="hi"
    )
    report = RunReport(
        run_id="run-1",
        repo=snapshot.repo,
        started_at="2026-01-01T00:00:00+00:00",
        source="offline",
        records=[build_record(decision, issue_859, applied=True)],
    )
    write_report(report, runs)

    exit_code = main(["--home", str(settings_home), "report"])
    captured = capsys.readouterr().out
    assert exit_code == 0
    assert "Repo Triager report" in captured
    assert "#859" in captured


def test_triage_unknown_issue_exits_with_a_message(tmp_path, capsys):
    with pytest.raises(SystemExit):
        main(
            [
                "--home",
                str(tmp_path / "var"),
                "triage",
                "--issue",
                "999999",
                "--provider",
                "scripted",
            ]
        )


def test_report_json_roundtrip(tmp_path, snapshot, issue_859):
    decision = TriageDecision(issue_number=859, severity="S3", labels=["bug"], reply_draft="hi")
    report = RunReport(
        run_id="run-2",
        repo=snapshot.repo,
        started_at="2026-01-01T00:00:00+00:00",
        records=[build_record(decision, issue_859)],
    )
    _markdown, payload = write_report(report, tmp_path / "run")
    loaded = json.loads(payload.read_text())
    assert loaded["run_id"] == "run-2"
    assert loaded["records"][0]["decision"]["severity"] == "S3"
