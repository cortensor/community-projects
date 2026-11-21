"""Shared stubs: a fake clock (no real 45 s waits) and loopback HTTP
stubs for the OpenAI-compatible endpoint."""

from __future__ import annotations

import json

import httpx
import pytest

VERDICT_ARGS = {
    "label": "preliminary",
    "reason": "stub verdict",
}

DRAFT_ARGS = {"label": "unsure", "reason": "stub draft"}


class FakeClock:
    def __init__(self):
        self.now = 1000.0
        self.slept: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def llm_stub_handler(tool_calls: bool = True, content_json: bool = True):
    """MockTransport handler for the OpenAI-compatible endpoint."""
    state = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["n"] += 1
        payload = json.loads(request.content.decode())
        tools = payload.get("tools") or []
        if tools and tool_calls:
            name = tools[0]["function"]["name"]
            args = VERDICT_ARGS if "verdict" in name else DRAFT_ARGS
            return httpx.Response(200, json={
                "model": "stub-gpt", "choices": [{
                    "message": {"content": "",
                                "tool_calls": [{"id": "c1", "type": "function",
                                                "function": {"name": name,
                                                             "arguments": json.dumps(args)}}]},
                    "finish_reason": "tool_calls"}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 20,
                          "total_tokens": 120}})
        if content_json:
            return httpx.Response(200, json={
                "model": "stub-gpt", "choices": [{
                    "message": {"content": json.dumps(VERDICT_ARGS)},
                    "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 20,
                          "total_tokens": 120}})
        return httpx.Response(200, json={
            "model": "stub-gpt", "choices": [{
                "message": {"content": "not json at all"},
                "finish_reason": "stop"}],
            "usage": {"total_tokens": 5}})

    handler.state = state
    return handler


@pytest.fixture
def fixtures_dir():
    from pathlib import Path
    return Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture
def tmp_state(tmp_path):
    return tmp_path / "state"
