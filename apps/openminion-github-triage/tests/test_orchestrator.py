import json
from pathlib import Path

from triage_agent.llm import FakeModelClient
from triage_agent.orchestrator import TriageAgent


SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def test_issue_triage_end_to_end_with_fake_model(tmp_path: Path) -> None:
    issue_payload = json.loads((SAMPLES / "issue.json").read_text(encoding="utf-8"))
    agent = TriageAgent(
        session_db=tmp_path / "triage.db",
        model_client=FakeModelClient("Offline review only."),
    )
    report = agent.triage_issue("example/project", issue_payload)
    assert report.issue is not None
    assert report.issue.severity == "high"
    assert report.model_notes == "Offline review only."
    assert report.diagnostics["task_state"]["verification_mode"] == "rule_based"
    assert len(report.diagnostics["phase_statuses"]) == 2
    assert report.diagnostics["event_count"] >= 3


def test_release_triage_end_to_end(tmp_path: Path) -> None:
    release_payload = json.loads((SAMPLES / "release.json").read_text(encoding="utf-8"))
    agent = TriageAgent(session_db=tmp_path / "triage.db")
    report = agent.triage_release("example/project", release_payload)
    assert report.release is not None
    assert report.release.verdict == "hold"
    assert report.release.unchecked_count == 1
    assert report.diagnostics["event_count"] >= 3
    turns = agent.store.list_turns(report.diagnostics["session_id"])
    assert len(turns) == 1
    assert turns[0]["role"] == "assistant"
    persisted = json.loads(turns[0]["content"])
    assert persisted["kind"] == "release"
    assert persisted["release"]["verdict"] == "hold"

