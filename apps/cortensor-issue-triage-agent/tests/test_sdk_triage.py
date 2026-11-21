"""Tests for the SDK-backed draft path (sdk_triage).

All tests use stub runners — no model calls, no network. The live evidence
for this path is the real Agent.run draft turn in round 3 (2026-11-17):
raw reply ``triage: {"answer": "Thanks for reporting issue #778. ...",
"freshness": {...}}`` parsed to a usable draft in 65.6 s on Pollinations.
"""

from __future__ import annotations

from issue_triage.config import ProviderSettings
from issue_triage.sdk_triage import (
    extract_json_object,
    parse_sdk_draft,
    run_sdk_draft,
    strip_sdk_prefix,
)

PROVIDER = ProviderSettings(
    preset="openai-compatible",
    base_url="https://stub.invalid",
    model="stub",
    api_key="",
)


def test_strip_sdk_prefix():
    assert strip_sdk_prefix('triage: {"a": 1}') == '{"a": 1}'
    assert strip_sdk_prefix("triage: hello there") == "hello there"
    assert strip_sdk_prefix("plain text") == "plain text"
    assert strip_sdk_prefix("") == ""


def test_extract_json_object_prefixed():
    raw = 'triage: {"issue_type": "bug", "confidence": 0.9}'
    assert extract_json_object(raw) == '{"issue_type": "bug", "confidence": 0.9}'


def test_extract_json_object_prose_wrapped():
    raw = 'Here is the verdict: {"a": 1} hope that helps.'
    assert extract_json_object(raw) == '{"a": 1}'


def test_extract_json_object_braces_in_string():
    raw = '{"rationale": "use {x} here", "n": 2}'
    assert extract_json_object(raw) == raw


def test_extract_json_object_none():
    assert extract_json_object("no json here") is None
    assert extract_json_object('{"unclosed": true') is None


def test_parse_sdk_draft_answer_envelope():
    # The exact shape a real SDK turn returned in round 3 (2026-11-17).
    raw = (
        'triage: {"answer": "Thanks for reporting issue #778. I\'ve triaged '
        'it as a high-severity bug in the brain module that requires '
        'maintainer investigation. Could you provide a minimal test?", '
        '"freshness": {"answer_mode": "local_only"}}'
    )
    draft, shape = parse_sdk_draft(raw)
    assert shape == "answer"
    assert draft is not None
    assert draft.draft.startswith("Thanks for reporting issue #778.")
    assert "freshness" not in draft.draft


def test_parse_sdk_draft_draft_envelope():
    raw = '{"draft": "Hi @x, thanks!", "tone": "friendly"}'
    draft, shape = parse_sdk_draft(raw)
    assert shape == "draft"
    assert draft is not None and draft.draft == "Hi @x, thanks!"
    assert draft.tone == "friendly"


def test_parse_sdk_draft_prose():
    raw = "triage: Hi there, this looks like a bug in the brain module."
    draft, shape = parse_sdk_draft(raw)
    assert shape == "prose"
    assert draft is not None
    assert draft.draft == "Hi there, this looks like a bug in the brain module."


def test_parse_sdk_draft_unusable():
    assert parse_sdk_draft("") == (None, None)
    assert parse_sdk_draft("triage: {}") == (None, None)
    assert parse_sdk_draft('{"foo": 1}') == (None, None)
    assert parse_sdk_draft("triage: ok") == (None, None)  # too short to trust


def test_run_sdk_draft_answer_shape():
    def runner(system, user, provider, timeout):
        assert provider.model == "stub"
        return '{"answer": "Hello draft", "freshness": {}}'

    draft, meta = run_sdk_draft("sys", "usr", PROVIDER, runner=runner)
    assert draft is not None and draft.draft == "Hello draft"
    assert meta["channel"] == "sdk-native"
    assert meta["shape"] == "answer"
    assert meta["model"] == "stub"
    assert meta["latency_ms"] >= 0
    assert "error" not in meta


def test_run_sdk_draft_prose_shape():
    def runner(system, user, provider, timeout):
        return "triage: This is a plain-text draft reply for the issue."

    draft, meta = run_sdk_draft("sys", "usr", PROVIDER, runner=runner)
    assert draft is not None
    assert meta["shape"] == "prose"


def test_run_sdk_draft_unusable_returns_none_with_error():
    def runner(system, user, provider, timeout):
        return '{"foo": 1}'

    draft, meta = run_sdk_draft("sys", "usr", PROVIDER, runner=runner)
    assert draft is None
    assert "error" in meta
    assert meta["shape"] is None


def test_run_sdk_draft_runner_exception_returns_none_with_error():
    def runner(system, user, provider, timeout):
        raise RuntimeError("ProviderError: 402 payment required")

    draft, meta = run_sdk_draft("sys", "usr", PROVIDER, runner=runner)
    assert draft is None
    assert "402" in meta["error"]
    assert meta["channel"] == "sdk-native"
