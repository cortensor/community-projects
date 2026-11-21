"""Loopback stub: a real SDK Agent against a local fake OpenAI endpoint.

Zero LLM cost. The stub answers every POST /v1/chat/completions with a
canned JSON reply, so we can verify the SDK wiring (runtime build, agent
run, reply text) without any model.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from paper_watch.agent import build_runtime, extract_json_object
from paper_watch.config import ProviderSettings


class _StubHandler(BaseHTTPRequestHandler):
    calls: list = []

    def log_message(self, *args):  # keep test output clean
        pass

    def do_GET(self):
        if self.path.endswith("/models"):
            body = json.dumps({"data": [{"id": "stub"}]}).encode()
        else:
            body = b"{}"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length)
        _StubHandler.calls.append(json.loads(raw or b"{}"))
        payload = {
            "id": "stub-1",
            "object": "chat.completion",
            "created": 0,
            "model": "stub",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": '{"answer": "4", "confidence": 0.9}',
                },
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        }
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture()
def stub_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StubHandler)
    _StubHandler.calls = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}/v1"
    server.shutdown()
    server.server_close()


def test_agent_run_against_loopback_stub(stub_server, tmp_path):
    from openminion import Agent

    provider = ProviderSettings(
        preset="openai-compatible", base_url=stub_server, model="stub",
        api_key="stub-key", api_key_env="STUB_API_KEY", timeout_seconds=30,
    )
    runtime = build_runtime(provider, tmp_path / "home", tmp_path / "data")
    try:
        agent = Agent(
            instructions="Reply with ONLY one JSON object.",
            runtime=runtime, name="stub-probe",
        )
        res = agent.run("What is 2+2?", timeout_seconds=60)
        obj = extract_json_object(res.text)
        assert obj == {"answer": "4", "confidence": 0.9}
        assert len(_StubHandler.calls) >= 1
        # The SDK really posted an OpenAI-style chat payload.
        assert _StubHandler.calls[0]["messages"][0]["role"] in ("system", "user")
    finally:
        runtime.close()
