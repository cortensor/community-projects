"""Offline unit tests for TriageMinion's deterministic logic.

These cover the parts that must be right even when no model is involved:
memory planning (skip/change detection) and report rendering. The model-backed
path is exercised by the recorded live runs under `examples/`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage import plan_work, render_report  # noqa: E402


def issue(number, updated_at, title="t"):
    return {"number": number, "updated_at": updated_at, "title": title}


def test_first_run_triages_everything():
    fresh, changed, skipped = plan_work([issue(1, "a"), issue(2, "b")], {"issues": {}})
    assert [i["number"] for i in fresh] == [1, 2]
    assert changed == [] and skipped == []


def test_unchanged_issue_is_skipped():
    state = {"issues": {"1": {"updated_at": "a"}}}
    fresh, changed, skipped = plan_work([issue(1, "a")], state)
    assert fresh == [] and changed == []
    assert [i["number"] for i in skipped] == [1]


def test_changed_issue_is_retriaged():
    state = {"issues": {"1": {"updated_at": "a"}}}
    fresh, changed, skipped = plan_work([issue(1, "b")], state)
    assert fresh == [] and skipped == []
    assert [i["number"] for i in changed] == [1]


def test_report_renders_verdicts_and_skips():
    verdict = {
        "issue_number": 7, "title": "Crash on empty input",
        "classification": "bug", "priority": "high",
        "suggested_labels": ["bug"], "justification": "crash",
        "draft_response": "Thanks!", "html_url": "https://example.com/7",
    }
    md = render_report("o/r", [verdict], [issue(3, "x", "old")], [], [], "ollama/qwen2.5:3b")
    assert "Issue #7" in md and "high" in md and "#3" in md
    assert "nothing was posted to GitHub" in md


if __name__ == "__main__":
    test_first_run_triages_everything()
    test_unchanged_issue_is_skipped()
    test_changed_issue_is_retriaged()
    test_report_renders_verdicts_and_skips()
    print("4 passed")
