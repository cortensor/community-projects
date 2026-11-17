"""Shared test fixtures for real openminion loopback integration tests."""

from __future__ import annotations

import json
import socket
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest


@dataclass
class RecordedRequest:
    """HTTP request captured by the loopback OpenAI/Cortensor stub."""

    method: str
    path: str
    headers: dict[str, str]
    body: dict[str, Any]


class LoopbackLLMServer:
    """Deterministic local HTTP stub for /v1/chat/completions and /api/v2/completions."""

    def __init__(self) -> None:
        self.requests: list[RecordedRequest] = []
        self._queue: list[dict[str, Any]] = []
        self._default_step: dict[str, Any] | None = None
        self._lock = threading.Lock()
        self._server = self._start_server()
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="loopback-llm-server",
            daemon=True,
        )
        self._thread.start()

    @property
    def port(self) -> int:
        return int(self._server.server_address[1])

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1"

    @property
    def router_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/api/v2/completions"

    def enqueue(self, *steps: dict[str, Any]) -> None:
        """Append scripted responses consumed FIFO per request."""
        with self._lock:
            self._queue.extend(steps)

    def set_default(self, step: dict[str, Any]) -> None:
        """Set a fallback response when the scripted queue is exhausted."""
        with self._lock:
            self._default_step = step

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)

    def _next_step(self) -> dict[str, Any]:
        with self._lock:
            if self._queue:
                return self._queue.pop(0)
            if self._default_step is not None:
                return self._default_step
            return {
                "type": "error",
                "status": 500,
                "message": "No scripted response left in LoopbackLLMServer.",
            }

    def _start_server(self) -> ThreadingHTTPServer:
        parent = self

        class _Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                return

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", "0") or "0")
                raw = self.rfile.read(length) if length > 0 else b"{}"
                try:
                    parsed = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    parsed = {"_raw": raw.decode("utf-8", errors="replace")}

                headers_lower = {k.lower(): v for k, v in self.headers.items()}
                parent.requests.append(
                    RecordedRequest(
                        method="POST",
                        path=self.path,
                        headers=headers_lower,
                        body=parsed,
                    )
                )

                step = _maybe_internal_classifier_step(parsed) or parent._next_step()
                status, payload = _render_step_response(step, parsed)
                encoded = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(encoded)

            def do_GET(self) -> None:  # noqa: N802
                if self.path.rstrip("/") == "/v1/models":
                    payload = {"object": "list", "data": [{"id": "stub-model", "object": "model"}]}
                    encoded = json.dumps(payload).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(encoded)))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(encoded)
                    return
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.send_header("Connection", "close")
                self.end_headers()

        return ThreadingHTTPServer(("127.0.0.1", 0), _Handler)


def _maybe_internal_classifier_step(request_body: dict[str, Any]) -> dict[str, Any] | None:
    """Respond to openminion's internal FreshnessContract submit_output classifier."""
    tool_choice = request_body.get("tool_choice")
    if not isinstance(tool_choice, dict):
        return None
    fn = tool_choice.get("function")
    if not isinstance(fn, dict) or fn.get("name") != "submit_output":
        return None

    tools = request_body.get("tools") or []
    schema_title = ""
    if tools and isinstance(tools[0], dict):
        schema_title = str(
            tools[0].get("function", {}).get("parameters", {}).get("title", "")
        )
    if schema_title == "FreshnessContract":
        return {
            "type": "tool_calls",
            "calls": [
                {
                    "id": "call_freshness_1",
                    "name": "submit_output",
                    "arguments": {
                        "intent": "fact_verification",
                        "domain": "general",
                        "time_sensitive": False,
                        "needs_live_data": False,
                        "needs_sources": True,
                        "needs_exact_date": False,
                        "answer_mode": "local_only",
                        "reason": "Evidence verification uses provided READ_ONLY tools.",
                        "confidence": 0.95,
                    },
                }
            ],
        }
    if schema_title == "FinalizationStatus":
        return {
            "type": "tool_calls",
            "calls": [
                {
                    "id": "call_finalization_1",
                    "name": "submit_output",
                    "arguments": {
                        "status": "final_answer",
                        "reasoning": "All required evidence tools executed cleanly.",
                    },
                }
            ],
        }
    return None


def _render_step_response(step: dict[str, Any], request_body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    step_type = step.get("type", "json")
    model = str(request_body.get("model") or "stub-model")

    if step_type == "error":
        status = int(step.get("status", 500))
        return status, {
            "error": {
                "message": str(step.get("message", "Stub internal server error")),
                "type": "server_error",
                "code": str(step.get("code", "stub_error")),
            }
        }

    if step_type == "tool_calls":
        raw_calls = step.get("calls", [])
        formatted_calls = []
        for idx, call in enumerate(raw_calls, start=1):
            args = call.get("arguments", {})
            args_str = args if isinstance(args, str) else json.dumps(args)
            formatted_calls.append(
                {
                    "id": str(call.get("id") or f"call_{idx}"),
                    "type": "function",
                    "function": {
                        "name": str(call["name"]),
                        "arguments": args_str,
                    },
                }
            )
        return int(step.get("status", 200)), {
            "id": "chatcmpl-stub-tool",
            "object": "chat.completion",
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": formatted_calls,
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        }

    if step_type == "text":
        content = str(step.get("content", ""))
    else:
        payload = step.get("payload", {})
        content = payload if isinstance(payload, str) else json.dumps(payload)
        has_tool_history = any(
            isinstance(msg, dict) and msg.get("role") == "tool"
            for msg in request_body.get("messages", [])
        )
        if has_tool_history and "<finalization_status>" not in content:
            content = (
                f"{content}\n"
                '<finalization_status>{"status": "final_answer"}</finalization_status>'
            )

    return int(step.get("status", 200)), {
        "id": "chatcmpl-stub-final",
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 12, "completion_tokens": 15, "total_tokens": 27},
    }


def json_step(payload: dict[str, Any] | str) -> dict[str, Any]:
    return {"type": "json", "payload": payload}


def text_step(content: str) -> dict[str, Any]:
    return {"type": "text", "content": content}


def tool_calls_step(*calls: dict[str, Any]) -> dict[str, Any]:
    return {"type": "tool_calls", "calls": list(calls)}


def error_step(status: int = 500, message: str = "Simulated provider failure") -> dict[str, Any]:
    return {"type": "error", "status": status, "message": message}


@pytest.fixture(autouse=True)
def _clean_loopback_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent proxy or ambient openminion env vars from hijacking tests."""
    for var in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "OPENMINION_HOME",
        "OPENMINION_DATA_ROOT",
        "OPENMINION_CONFIG_PATH",
        "OPENAI_BASE_URL",
        "CORTENSOR_PORTAL_URL",
        "CORTENSOR_ROUTER_URL",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")


@pytest.fixture()
def loopback_server() -> LoopbackLLMServer:
    server = LoopbackLLMServer()
    try:
        yield server
    finally:
        server.close()


@pytest.fixture()
def unused_loopback_url() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    return f"http://127.0.0.1:{port}/v1"
