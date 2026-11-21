"""Triage orchestrator with stubbed LLM + stubbed GitHub."""

import json

import pytest

from issue_triage.memory import RepoMemory
from issue_triage.triage import (
    TriageEngine,
    validate_assignee,
    validate_labels,
)


def test_validate_labels_keeps_only_known():
    kept, dropped = validate_labels(
        ["bug", "area:brain", "invented-label"], ["bug", "area:brain"]
    )
    assert kept == ["bug", "area:brain"]
    assert dropped == ["invented-label"]


def test_validate_labels_dedupes():
    kept, dropped = validate_labels(["bug", "bug"], ["bug"])
    assert kept == ["bug"]


def test_validate_assignee_only_allows_known_people():
    assert validate_assignee("alice", ["alice", "bob"]) == "alice"
    assert validate_assignee("@bob", ["alice", "bob"]) == "bob"
    assert validate_assignee("mallory", ["alice", "bob"]) is None
    assert validate_assignee(None, ["alice"]) is None


def _engine(llm_client, github_client, tmp_path):
    return TriageEngine(
        llm=llm_client, github=github_client, memory=RepoMemory(tmp_path)
    )


def test_fetch_context_from_stub_github(llm_client, github_client, tmp_path):
    engine = _engine(llm_client, github_client, tmp_path)
    ctx = engine.fetch_context("openminion/openminion", 778)
    assert ctx.title.startswith("brain:")
    assert ctx.existing_labels == ["bug", "area:brain"]
    assert ctx.linked_prs == [770]
    assert ctx.linked_pr_details == [
        {"number": 770, "title": "Fix brain completion gating",
         "body": "This PR gates completion on verification.",
         "state": "open", "merged": False}
    ]
    assert ctx.comments[0]["author"] == "maintainer"
    assert ctx.contributors == ["alice", "bob"]


def test_fetch_context_without_pr_fetch_leaves_details_empty(
    llm_client, github_client, tmp_path
):
    # eval mode: no PR bodies, prompt stays comparable to the baseline run
    engine = _engine(llm_client, github_client, tmp_path)
    ctx = engine.fetch_context("openminion/openminion", 778, fetch_linked_prs=False)
    assert ctx.linked_prs == [770]
    assert ctx.linked_pr_details == []


def _existing_labels_line(messages):
    user = messages[1]["content"]
    return [ln for ln in user.splitlines() if ln.startswith("Existing labels:")]


def test_classifier_prompt_blind_hides_existing_labels(
    llm_client, github_client, tmp_path
):
    engine = _engine(llm_client, github_client, tmp_path)
    ctx = engine.fetch_context("openminion/openminion", 778)
    line = _existing_labels_line(
        engine._classifier_messages(ctx, hide_existing_labels=True)
    )
    assert line == [
        "Existing labels: (hidden — evaluation mode; "
        "classify from the issue text only)"
    ]


def test_classifier_prompt_aware_shows_existing_labels(
    llm_client, github_client, tmp_path
):
    engine = _engine(llm_client, github_client, tmp_path)
    ctx = engine.fetch_context("openminion/openminion", 778)
    line = _existing_labels_line(engine._classifier_messages(ctx))
    assert line == ["Existing labels: bug, area:brain"]


def test_classifier_prompt_includes_linked_pr_body(
    llm_client, github_client, tmp_path
):
    engine = _engine(llm_client, github_client, tmp_path)
    ctx = engine.fetch_context("openminion/openminion", 778)
    user = engine._classifier_messages(ctx)[1]["content"]
    assert "Fix brain completion gating" in user
    assert "gates completion on verification" in user


def test_classify_end_to_end_stub(llm_client, github_client, tmp_path):
    engine = _engine(llm_client, github_client, tmp_path)
    ctx = engine.fetch_context("openminion/openminion", 778)
    verdict, meta = engine.classify(ctx)
    assert verdict.issue_type == "bug"
    assert verdict.component == "area:brain"
    assert verdict.suggested_labels == ["bug", "area:brain"]
    assert meta["channel"] == "tool_calls"
    assert meta["dropped_labels"] == []


def test_classify_drops_invented_labels(llm_client, github_client, tmp_path, monkeypatch):
    # stub returns a label the repo does not have; engine must drop it
    import issue_triage.triage as triage_mod

    orig = triage_mod.validate_labels
    monkeypatch.setattr(
        triage_mod, "validate_labels",
        lambda proposed, known: orig(proposed, ["bug"]),
    )
    engine = _engine(llm_client, github_client, tmp_path)
    ctx = engine.fetch_context("openminion/openminion", 778)
    verdict, meta = engine.classify(ctx)
    assert verdict.suggested_labels == ["bug"]
    assert meta["dropped_labels"] == ["area:brain"]


def test_run_records_proposed_decision(llm_client, github_client, tmp_path):
    engine = _engine(llm_client, github_client, tmp_path)
    ctx = engine.fetch_context("openminion/openminion", 778)
    result = engine.run(ctx)
    assert result["verdict"].issue_type == "bug"
    assert len(result["draft"].draft) > 0
    assert result["llm_calls"] == 2  # classify + draft, one call each
    decisions = engine.memory.load("openminion/openminion")
    assert len(decisions) == 1
    assert decisions[0].status == "proposed"


def test_classify_400_falls_back_to_plain_text_shape(clock, github_client, tmp_path):
    """The `<|constrain|>commentary` 400 (eval #777/#773): the retry must
    change the request shape — a same-shape slim retry already failed
    once per issue, so repeating it cannot recover."""
    import httpx

    from issue_triage.llm_client import DirectClient
    from tests.conftest import VERDICT_ARGS

    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        seen.append(payload)
        if payload.get("tools") or payload.get("response_format"):
            return httpx.Response(
                400,
                text='{"success":false,"error":{"message":"400 Bad Request: '
                'unexpected tokens remaining in message header: '
                'Some(\\"<|constrain|>commentary\\")","code":"BAD_REQUEST"}}',
            )
        return httpx.Response(200, json={
            "model": "stub",
            "choices": [{"message": {"role": "assistant",
                                     "content": json.dumps(VERDICT_ARGS)},
                         "finish_reason": "stop"}],
            "usage": {},
        })

    client = DirectClient(
        base_url="https://stub.invalid", model="stub", min_interval_sec=0,
        transport=httpx.MockTransport(handler),
        sleep=clock.sleep, clock=clock.time,
    )
    engine = _engine(client, github_client, tmp_path)
    ctx = engine.fetch_context("openminion/openminion", 778)
    verdict, meta = engine.classify(ctx)
    assert verdict.issue_type == "bug"
    assert meta["slim_retry"] is True
    assert len(seen) == 2
    assert "tools" not in seen[1] and "response_format" not in seen[1]
    client.close()


def test_run_via_sdk_waits_for_fresh_window(llm_client, github_client, tmp_path, clock, monkeypatch):
    """The SDK turn must start in a fresh free-tier window, not on top of
    the classify call that just ran (CLI runs 2026-11-17: first SDK call
    200, then 9x 402)."""
    import issue_triage.sdk_triage as sdk_mod
    from issue_triage.config import ProviderSettings
    from issue_triage.models import TriageDraft

    def fake_sdk_draft(system, user, provider, timeout_seconds=240, runner=None):
        return TriageDraft(draft="sdk draft", tone="neutral"), {
            "channel": "sdk-native", "latency_ms": 1, "model": "stub", "shape": "prose",
        }

    monkeypatch.setattr(sdk_mod, "run_sdk_draft", fake_sdk_draft)
    engine = _engine(llm_client, github_client, tmp_path)
    ctx = engine.fetch_context("openminion/openminion", 778)
    provider = ProviderSettings(
        preset="openai-compatible", base_url="https://stub.invalid",
        model="stub", api_key="",
    )
    result = engine.run(ctx, via_sdk=True, provider=provider)
    assert result["draft_via"] == "sdk-native"
    assert result["draft"].draft == "sdk draft"
    assert 45.0 in clock.slept  # the pacing wait before the SDK turn


def test_context_from_fixture(tmp_path):
    raw = json.loads(open("fixtures/openminion-issue-778.json").read())
    ctx = TriageEngine.context_from_fixture("openminion/openminion", raw)
    assert ctx.number == 778
    assert ctx.existing_labels == ["bug", "area:brain", "status:maintainer-investigation"]
    assert len(ctx.repo_labels) == 31
    assert "wireindevice" in ctx.contributors
