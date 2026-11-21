"""Eval metrics + ground-truth mapping (pure, no model calls) + blind-mode
prompt checks (stubbed LLM, payloads recorded)."""

import httpx
import json

from issue_triage.eval import compute_metrics, ground_truth_type, run_eval
from issue_triage.llm_client import DirectClient
from issue_triage.memory import RepoMemory
from issue_triage.models import EvalRecord
from issue_triage.triage import TriageEngine
from tests.conftest import ISSUE_778, llm_stub_handler


def _record(truth, predicted, confidence=0.9):
    return EvalRecord(
        repo="o/r", issue_number=1, title="t", ground_truth=truth,
        predicted=predicted, severity="high", confidence=confidence,
        correct=truth == predicted,
    )


def test_ground_truth_mapping():
    assert ground_truth_type(["bug"]) == "bug"
    assert ground_truth_type(["enhancement"]) == "feature"
    assert ground_truth_type(["question"]) == "question"
    assert ground_truth_type(["documentation"]) == "docs"
    assert ground_truth_type(["area:brain"]) is None
    assert ground_truth_type([]) is None


def test_ground_truth_ambiguous_is_none():
    assert ground_truth_type(["bug", "enhancement"]) is None
    assert ground_truth_type(["bug", "bug"]) == "bug"


def test_metrics_perfect():
    records = [_record("bug", "bug"), _record("feature", "feature")]
    metrics = compute_metrics(records)
    assert metrics["accuracy"] == 1.0
    assert metrics["per_class"]["bug"]["precision"] == 1.0
    assert metrics["per_class"]["bug"]["recall"] == 1.0


def test_metrics_with_errors():
    records = [
        _record("bug", "bug"),
        _record("bug", "feature"),   # fn bug, fp feature
        _record("feature", "feature"),
        _record("question", "bug"),  # fn question, fp bug
    ]
    metrics = compute_metrics(records)
    assert metrics["accuracy"] == 0.5
    assert metrics["per_class"]["bug"]["precision"] == 0.5  # 1 tp / 2 predicted bug
    assert metrics["per_class"]["bug"]["recall"] == 0.5     # 1 tp / 2 true bug
    assert metrics["per_class"]["feature"]["recall"] == 1.0
    assert metrics["per_class"]["question"]["recall"] == 0.0


def test_calibration_buckets():
    records = [
        _record("bug", "bug", 0.9),
        _record("bug", "bug", 0.85),
        _record("bug", "feature", 0.4),
        _record("feature", "feature", 0.6),
    ]
    metrics = compute_metrics(records)
    buckets = metrics["calibration"]["buckets"]
    assert buckets[">=0.8"]["n"] == 2
    assert buckets[">=0.8"]["accuracy"] == 1.0
    assert buckets["<0.5"]["n"] == 1
    assert buckets["<0.5"]["accuracy"] == 0.0
    assert metrics["calibration"]["mean_confidence_correct"] == 0.783
    assert metrics["calibration"]["mean_confidence_wrong"] == 0.4


def test_metrics_empty():
    metrics = compute_metrics([])
    assert metrics["accuracy"] == 0.0
    assert metrics["n"] == 0


def _recording_engine(github_client, tmp_path, clock):
    """Engine whose LLM payloads are recorded, for prompt assertions."""
    seen: list[dict] = []
    base = llm_stub_handler()

    def recording(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content.decode()))
        return base(request)

    client = DirectClient(
        base_url="https://stub.invalid",
        model="stub",
        min_interval_sec=0,
        transport=httpx.MockTransport(recording),
        sleep=clock.sleep,
        clock=clock.time,
    )
    engine = TriageEngine(llm=client, github=github_client, memory=RepoMemory(tmp_path))
    return engine, seen, client


def _existing_labels_lines(seen):
    lines = []
    for payload in seen:
        for message in payload.get("messages") or []:
            for line in (message.get("content") or "").splitlines():
                if line.startswith("Existing labels:"):
                    lines.append(line)
    return lines


def test_run_eval_blind_hides_labels_from_prompt(github_client, tmp_path, clock):
    engine, seen, client = _recording_engine(github_client, tmp_path, clock)
    try:
        result = run_eval(engine, "openminion/openminion", 1, issues=[ISSUE_778], blind=True)
    finally:
        client.close()
    assert result["mode"] == "label-blind"
    assert result["metrics"]["accuracy"] == 1.0
    assert _existing_labels_lines(seen) == [
        "Existing labels: (hidden — evaluation mode; "
        "classify from the issue text only)"
    ]


def test_run_eval_label_aware_shows_labels(github_client, tmp_path, clock):
    engine, seen, client = _recording_engine(github_client, tmp_path, clock)
    try:
        result = run_eval(engine, "openminion/openminion", 1, issues=[ISSUE_778], blind=False)
    finally:
        client.close()
    assert result["mode"] == "label-aware"
    assert _existing_labels_lines(seen) == ["Existing labels: bug, area:brain"]
