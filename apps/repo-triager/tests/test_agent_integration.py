"""End-to-end: the real OpenMinion runtime, a scripted model, real tools.

These tests boot ``APIRuntime`` from a temporary OpenMinion home, run the
``Agent`` turns, and assert on what the runtime actually did (tool events, the
policy decision, the staged files, the memory record).  They are marked
``integration`` because each turn costs a handful of scripted model calls.
"""

from __future__ import annotations

import pytest

from repo_triager.agent import TriagerAgent, validate_decision
from repo_triager.policy import OperatorPolicy

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def agent(runtime_session, settings, snapshot):
    instance = TriagerAgent(settings, snapshot)
    yield instance
    instance.close()


def test_analysis_returns_a_structured_decision(agent, issue_859, settings):
    decision, phase, context = agent.analyse(
        issue_859, session_id="itest-analysis", scenario="issue-859"
    )
    assert decision.issue_number == 859
    assert decision.severity == "S2"
    assert decision.component == "area:tools"
    assert decision.labels == ["bug", "area:tools"]
    assert decision.source == "model"
    assert validate_decision(decision, issue_859, agent.snapshot) == []
    # The runtime really executed the read-only tools.
    tools_used = [event["tool"] for event in context.tool_events]
    assert tools_used == [
        "triage_precheck",
        "get_issue",
        "search_duplicate_issues",
    ]
    assert int(phase.metadata["llm_calls"]) >= 1
    assert int(phase.metadata["tool_calls"]) >= 3


def test_write_gate_allows_and_stages(agent, issue_859, settings):
    decision, phase, context = agent.analyse(
        issue_859, session_id="itest-allow", scenario="issue-859"
    )
    policy = OperatorPolicy(mode="auto")
    staged = agent.stage(
        decision,
        context,
        session_id="itest-allow:stage",
        policy=policy,
        scenario="stage-859",
    )
    assert context.applied is True
    assert staged.policy_events[0]["tool"] == "stage_triage"
    assert staged.policy_events[0]["decision"] == "allow"
    assert staged.policy_events[0]["policy"].startswith("operator-flag: auto")
    markdown, payload = context.outbox_paths
    assert markdown.endswith("0859.md")
    assert payload.endswith("0859.json")


def test_write_gate_denies_and_writes_nothing(agent, issue_853, settings):
    decision, _phase, context = agent.analyse(
        issue_853, session_id="itest-deny", scenario="issue-853"
    )
    outbox_before = list(settings.outbox_dir.rglob("*"))
    staged = agent.stage(
        decision,
        context,
        session_id="itest-deny:stage",
        policy=OperatorPolicy(mode="deny"),
        scenario="stage-853",
    )
    assert context.applied is False
    assert context.outbox_paths == []
    assert staged.policy_events[0]["decision"] == "deny"
    assert "not run" in staged.text.lower() or "denied" in staged.text.lower()
    assert list(settings.outbox_dir.rglob("*")) == outbox_before


def test_memory_write_then_analysis_session_recall(agent, issue_859):
    decision, _phase, _context = agent.analyse(
        issue_859, session_id="itest-memory", scenario="issue-859"
    )
    remembered = agent.remember(
        decision, session_id="itest-memory:memory", scenario="remember-859"
    )
    assert "remembered" in remembered.text.lower()
    assert remembered.policy_events[0]["tool"] == "memory.write"


def test_delegation_returns_a_verdict(agent, issue_859):
    confirmed, reason, _metadata = agent.deep_dedupe(
        issue_859, session_id="itest-dedupe", scenario="dedupe-859"
    )
    assert isinstance(confirmed, list)
    assert reason


def test_fallback_keeps_the_pipeline_alive(agent, issue_859):
    decision, phase, _context, notes = agent.analyse_or_fallback(
        issue_859, session_id="itest-fallback", scenario="missing-scenario"
    )
    assert decision.issue_number == 859
    assert decision.source in {"heuristic", "model"}
    if notes:
        assert "heuristic fallback" in notes[0]


def test_pause_flow_uses_the_runtime_confirmation(agent, issue_859, capsys):
    """`pause` mode leaves the decision to OpenMinion's own confirmation turn."""

    decision, _phase, context = agent.analyse(
        issue_859, session_id="itest-pause", scenario="issue-859"
    )
    policy = OperatorPolicy(mode="auto")
    staged = agent.stage(
        decision,
        context,
        session_id="itest-pause:stage",
        policy=policy,
        pause=True,
        scenario="stage-859",
    )
    printed = capsys.readouterr().out
    assert "Policy confirmation required" in printed
    assert context.applied is True
    assert staged.policy_events[0]["policy"] == "paused turn answered 'yes'"
