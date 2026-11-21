"""Regression tests for the live-eval failure (2026-11-17):
HTTP 400 output_token_limit_exceeded must trigger a slim-prompt retry,
and a still-failing issue must not kill the whole eval run."""

import json

import httpx
import pytest

from issue_triage.eval import run_eval
from issue_triage.memory import RepoMemory
from issue_triage.triage import TriageEngine
from tests.conftest import VERDICT_ARGS, llm_stub_handler


def test_reasoning_effort_sent_by_default(clock):
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content.decode()))
        return httpx.Response(200, json={
            "model": "stub",
            "choices": [{"message": {"content": json.dumps(VERDICT_ARGS)}, "finish_reason": "stop"}],
            "usage": {},
        })

    from issue_triage.llm_client import DirectClient

    client = DirectClient(
        base_url="https://stub.invalid", model="stub", min_interval_sec=0,
        transport=httpx.MockTransport(handler),
        sleep=clock.sleep, clock=clock.time,
    )
    client.chat([{"role": "user", "content": "hi"}])
    assert seen.get("reasoning_effort") == "low"
    client.close()


def test_classify_slim_retry_after_400(llm_client, github_client, tmp_path, clock):
    # first call 400s (output token limit), second succeeds on the slim prompt
    from issue_triage.llm_client import DirectClient

    state = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["n"] += 1
        if state["n"] == 1:
            return httpx.Response(400, json={
                "success": False,
                "error": {"message": "The model exhausted its output token limit",
                          "code": "output_token_limit_exceeded"},
            })
        return llm_stub_handler()(request)

    client = DirectClient(
        base_url="https://stub.invalid", model="stub", min_interval_sec=0,
        transport=httpx.MockTransport(handler),
        sleep=clock.sleep, clock=clock.time,
    )
    engine = TriageEngine(llm=client, github=github_client, memory=RepoMemory(tmp_path))
    ctx = engine.fetch_context("openminion/openminion", 778)
    verdict, meta = engine.classify(ctx)
    assert verdict.issue_type == "bug"
    assert meta["slim_retry"] is True
    assert state["n"] == 2
    client.close()


def test_draft_retries_once_after_provider_error(llm_client, github_client, tmp_path, clock):
    # first draft call 400s (upstream glitch), retry with plain-text shape succeeds
    from issue_triage.llm_client import DirectClient

    state = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["n"] += 1
        payload = json.loads(request.content.decode())
        tools = payload.get("tools") or []
        is_draft = any(t["function"]["name"] == "submit_triage_draft" for t in tools)
        if is_draft and state.get("draft_failed") is None:
            state["draft_failed"] = True
            return httpx.Response(400, json={"error": {"code": "BAD_REQUEST"}})
        return llm_stub_handler()(request)

    client = DirectClient(
        base_url="https://stub.invalid", model="stub", min_interval_sec=0,
        transport=httpx.MockTransport(handler),
        sleep=clock.sleep, clock=clock.time,
    )
    engine = TriageEngine(llm=client, github=github_client, memory=RepoMemory(tmp_path))
    ctx = engine.fetch_context("openminion/openminion", 778)
    draft_obj, _ = engine.draft(ctx, engine.classify(ctx)[0])
    assert len(draft_obj.draft) > 0
    assert state["n"] == 3  # classify + failed draft + retried draft
    client.close()


def test_eval_continues_past_failing_issue(github_client, tmp_path, clock):
    # issue 778 classifies fine; issue 777 always 400s -> recorded as error
    from issue_triage.llm_client import DirectClient

    issue_777 = {
        "number": 777, "title": "llm: measured redundant calls",
        "body": "x", "state": "open", "user": {"login": "u"},
        "labels": [{"name": "enhancement"}],
    }

    def gh_handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/issues/777"):
            return httpx.Response(200, json=issue_777)
        if path.endswith("/issues/777/comments"):
            return httpx.Response(200, json=[])
        if path.endswith("/issues/777/timeline"):
            return httpx.Response(200, json=[])
        from tests.conftest import github_stub_handler
        return github_stub_handler()(request)

    def llm_handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        body = payload["messages"][1]["content"]
        if "Issue #777" in body:
            return httpx.Response(400, json={"error": {"code": "output_token_limit_exceeded"}})
        return llm_stub_handler()(request)

    from issue_triage.github_client import GitHubClient

    gh = GitHubClient(transport=httpx.MockTransport(gh_handler))
    llm = DirectClient(
        base_url="https://stub.invalid", model="stub", min_interval_sec=0,
        transport=httpx.MockTransport(llm_handler),
        sleep=clock.sleep, clock=clock.time,
    )
    engine = TriageEngine(llm=llm, github=gh, memory=RepoMemory(tmp_path))
    result = run_eval(engine, "openminion/openminion", 10, issues=[
        {"number": 778, "title": "t", "labels": [{"name": "bug"}]},
        issue_777,
    ])
    assert len(result["records"]) == 1
    assert result["records"][0]["issue_number"] == 778
    assert len(result["errors"]) == 1
    assert result["errors"][0]["issue_number"] == 777
    assert result["metrics"]["n"] == 1
    llm.close()
    gh.close()
