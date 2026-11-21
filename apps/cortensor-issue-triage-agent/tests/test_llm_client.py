"""DirectClient: dual-channel parsing, pacing, 402 handling, extraction."""

import json

import httpx
import pytest

from issue_triage.llm_client import (
    DirectClient,
    RateLimitedError,
    VerdictParseError,
    extract_json_object,
    parse_typed,
)
from issue_triage.models import TriageVerdict
from tests.conftest import VERDICT_ARGS, llm_stub_handler


def make_client(handler, clock, min_interval=45):
    return DirectClient(
        base_url="https://stub.invalid",
        model="stub",
        min_interval_sec=min_interval,
        transport=httpx.MockTransport(handler),
        sleep=clock.sleep,
        clock=clock.time,
    )


def test_extract_json_object_plain():
    assert extract_json_object('{"a": 1}') == '{"a": 1}'


def test_extract_json_object_with_prose_and_prefix():
    text = "agent_id: triage\nHere is the verdict: {\"a\": 1} done."
    assert extract_json_object(text) == '{"a": 1}'


def test_extract_json_object_nested_braces():
    text = 'prefix {"a": {"b": [1, {"c": 2}]}} suffix'
    assert json.loads(extract_json_object(text)) == {"a": {"b": [1, {"c": 2}]}}


def test_extract_json_object_no_json_raises():
    with pytest.raises(ValueError):
        extract_json_object("no json at all")


def test_parse_typed_rejects_illegal_enum():
    with pytest.raises(Exception):
        parse_typed('{"issue_type": "failure", "severity": "high", "component": "x",'
                    ' "route": "ready-to-fix", "confidence": 0.9, "rationale": "x"}',
                    TriageVerdict)


def test_parse_typed_normalises_enum_synonym():
    # "enhancement" is a real GitHub label; the model answers it for a
    # feature request — the verdict must map it, not fail validation
    verdict = parse_typed(
        '{"issue_type": "enhancement", "severity": "high", "component": "x",'
        ' "route": "ready-to-fix", "confidence": 0.9, "rationale": "x"}',
        TriageVerdict,
    )
    assert verdict.issue_type == "feature"


def test_tool_calls_channel_preferred(llm_client):
    verdict, result = llm_client.chat_typed(
        [{"role": "user", "content": "x"}],
        TriageVerdict,
        tools=[{"type": "function", "function": {"name": "submit_triage_verdict"}}],
    )
    assert verdict.issue_type == "bug"
    assert result.channel == "tool_calls"
    assert result.usage["total_tokens"] == 30


def test_text_json_channel_fallback(clock):
    client = make_client(llm_stub_handler(tool_calls=False), clock)
    verdict, result = client.chat_typed(
        [{"role": "user", "content": "x"}], TriageVerdict, tools=None
    )
    assert verdict.issue_type == "bug"
    assert result.channel == "text"
    client.close()


def test_tool_calls_invalid_falls_back_to_text(clock):
    # tool call carries an illegal enum; text content is valid -> text wins
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "model": "stub",
            "choices": [{"message": {
                "role": "assistant",
                "content": json.dumps(VERDICT_ARGS),
                "tool_calls": [{"id": "c", "type": "function",
                                "function": {"name": "submit_triage_verdict",
                                             "arguments": json.dumps({**VERDICT_ARGS, "issue_type": "failure"})}}],
            }, "finish_reason": "tool_calls"}],
            "usage": {},
        })

    client = make_client(handler, clock)
    verdict, _ = client.chat_typed(
        [{"role": "user", "content": "x"}], TriageVerdict,
        tools=[{"type": "function", "function": {"name": "submit_triage_verdict"}}],
    )
    assert verdict.issue_type == "bug"
    client.close()


def test_both_channels_invalid_raises(clock):
    client = make_client(llm_stub_handler(tool_calls=False, content_json=False), clock)
    with pytest.raises(VerdictParseError):
        client.chat_typed([{"role": "user", "content": "x"}], TriageVerdict)
    client.close()


def test_pacing_enforced_between_calls(llm_client, clock):
    llm_client.chat([{"role": "user", "content": "one"}])
    assert clock.slept == []
    llm_client.chat([{"role": "user", "content": "two"}])
    assert clock.slept == [45.0]
    assert clock.now == 1000.0 + 45.0


def test_no_pacing_when_interval_zero(clock):
    client = make_client(llm_stub_handler(), clock, min_interval=0)
    client.chat([{"role": "user", "content": "one"}])
    client.chat([{"role": "user", "content": "two"}])
    assert clock.slept == []
    client.close()


def test_402_retries_once_after_retry_after(clock):
    state = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["n"] += 1
        if state["n"] == 1:
            return httpx.Response(
                402,
                text="Free limit reached: 1 reply every 45 seconds per IP. Retry after 19s",
                headers={"retry-after": "19"},
            )
        return httpx.Response(200, json={
            "model": "stub",
            "choices": [{"message": {"content": '{"ok": true}'}, "finish_reason": "stop"}],
            "usage": {},
        })

    client = make_client(handler, clock, min_interval=45)
    result = client.chat([{"role": "user", "content": "hi"}])
    assert result.content == '{"ok": true}'
    # waits max(retry-after=19, interval=45) = 45 before the retry
    assert clock.slept == [45.0]
    assert state["n"] == 2
    client.close()


def test_402_twice_raises_rate_limited(clock):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(402, text="Free limit reached. Retry after 30s")

    client = make_client(handler, clock, min_interval=45)
    with pytest.raises(RateLimitedError) as exc_info:
        client.chat([{"role": "user", "content": "hi"}])
    assert exc_info.value.retry_after == 30
    client.close()


def test_http_500_raises_runtime_error(clock):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = make_client(handler, clock, min_interval=0)
    with pytest.raises(RuntimeError, match="HTTP 500"):
        client.chat([{"role": "user", "content": "hi"}])
    client.close()
