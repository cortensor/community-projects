import json

import httpx
import pytest

from hackathon_watch.config import resolve_provider
from hackathon_watch.llm_client import (
    DirectClient, RateLimitedError, VerdictParseError, extract_json_object,
    parse_typed)
from hackathon_watch.models import HackathonEntry, SuitabilityVerdict
from hackathon_watch.suitability import (
    build_classify_messages, verdict_tool_schema)
from conftest import FakeClock, llm_stub_handler


def _sample_entry():
    return HackathonEntry(name="T", url="https://example.test/t",
                          source="dorahacks")


def _client(handler, clock=None):
    provider = resolve_provider("openai-compatible")
    return DirectClient(provider, min_interval_sec=45,
                        transport=httpx.MockTransport(handler),
                        sleep=(clock.sleep if clock else None),
                        clock=(clock.time if clock else None))


def test_extract_json_object_strips_agent_id_prefix_and_prose():
    text = 'agent_id: watch\nSure! {"label": "unsure", "reason": "x"} done.'
    assert extract_json_object(text) == '{"label": "unsure", "reason": "x"}'


def test_extract_json_object_rejects_no_json():
    with pytest.raises(ValueError):
        extract_json_object("no json here")


def test_classify_via_tool_calls_channel():
    client = _client(llm_stub_handler(tool_calls=True))
    verdict = client.classify(
        SuitabilityVerdict, build_classify_messages(_sample_entry()),
        tools=verdict_tool_schema())
    assert verdict.label == "preliminary"
    assert client.calls_made == 1
    assert client.tokens_used == 120


def test_classify_via_text_json_channel():
    client = _client(llm_stub_handler(tool_calls=False, content_json=True))
    verdict = client.classify(
        SuitabilityVerdict, build_classify_messages(_sample_entry()),
        tools=verdict_tool_schema())
    assert verdict.label == "preliminary"


def test_classify_unparsable_raises_verdict_parse_error():
    client = _client(llm_stub_handler(tool_calls=False, content_json=False))
    with pytest.raises(VerdictParseError):
        client.classify(
            SuitabilityVerdict, build_classify_messages(_sample_entry()),
            tools=verdict_tool_schema())


def test_402_retries_once_after_retry_after_then_raises():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(402, text="Free limit reached: 1 reply every "
                                        "45 seconds per IP. Retry after 45s")

    clock = FakeClock()
    client = _client(handler, clock=clock)
    with pytest.raises(RateLimitedError) as excinfo:
        client.complete([{"role": "user", "content": "hi"}])
    assert excinfo.value.retry_after == 45
    assert calls["n"] == 2
    # The client waited Retry-After + 2 s before the second attempt.
    assert clock.slept == [47.0]


def test_pacing_waits_between_calls():
    clock = FakeClock()
    client = _client(llm_stub_handler(), clock=clock)
    client.complete([{"role": "user", "content": "hi"}])
    client.complete([{"role": "user", "content": "hi"}])
    # Second call waited the remainder of the 45 s window.
    assert clock.slept and clock.slept[-1] > 40


def test_parse_typed_rejects_wrong_label():
    with pytest.raises(Exception):
        parse_typed('{"label": "banana", "reason": "x"}', SuitabilityVerdict)
