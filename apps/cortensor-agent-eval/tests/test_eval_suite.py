"""End-to-end tests for Cortensor Agent Eval against OpenMinion 0.1.24."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from cortensor_agent_eval.policy import FailClosedApprovalGate
from cortensor_agent_eval.runner import run_eval_suite


class _MockOpenAIServer:
    """Thread-safe local OpenAI-compatible HTTP server for deterministic tests."""

    def __init__(self, *, fail_with_500: bool = False) -> None:
        self.fail_with_500 = fail_with_500
        self.requests: list[dict] = []
        server_ref = self

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):  # noqa: A002
                return

            def do_GET(self) -> None:
                if self.path.endswith("/models"):
                    payload = json.dumps(
                        {"object": "list", "data": [{"id": "mock-eval-model"}]}
                    ).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return
                self.send_response(404)
                self.end_headers()

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                raw_body = self.rfile.read(length).decode("utf-8")
                body = json.loads(raw_body)
                server_ref.requests.append(body)

                if server_ref.fail_with_500:
                    err = json.dumps({"error": {"message": "upstream outage"}}).encode(
                        "utf-8"
                    )
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(err)))
                    self.end_headers()
                    self.wfile.write(err)
                    return

                tools = body.get("tools") or []
                tool_names = [t.get("function", {}).get("name", "") for t in tools]
                messages = body.get("messages") or []
                all_text = " ".join(str(m.get("content") or "") for m in messages)
                last_user = ""
                for msg in reversed(messages):
                    if msg.get("role") == "user":
                        last_user = str(msg.get("content") or "")
                        break

                if "submit_output" in tool_names or (
                    "EvalReport" in all_text and "suite_name" in all_text
                ):
                    resp = {
                        "id": f"cmpl-{len(server_ref.requests)}",
                        "object": "chat.completion",
                        "model": "mock-eval-model",
                        "choices": [
                            {
                                "index": 0,
                                "finish_reason": "stop",
                                "message": {
                                    "role": "assistant",
                                    "content": json.dumps(
                                        {
                                            "verdict": "READY",
                                            "score": 100,
                                            "summary": "All 5 OpenMinion benchmark cases passed cleanly.",
                                            "strengths": ["Deterministic tool execution"],
                                            "risks": [],
                                            "recommendations": ["Ready for Cortensor submission"],
                                        }
                                    ),
                                },
                            }
                        ],
                    }
                elif "probe_inference_endpoint" in tool_names and "probe_inference_endpoint" in last_user:
                    resp = {
                        "id": f"cmpl-{len(server_ref.requests)}",
                        "object": "chat.completion",
                        "model": "mock-eval-model",
                        "choices": [
                            {
                                "index": 0,
                                "finish_reason": "tool_calls",
                                "message": {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": "call_probe_1",
                                            "type": "function",
                                            "function": {
                                                "name": "probe_inference_endpoint",
                                                "arguments": json.dumps(
                                                    {
                                                        "base_url": f"http://127.0.0.1:{server_ref.port}/v1",
                                                        "timeout_seconds": 3.0,
                                                    }
                                                ),
                                            },
                                        }
                                    ],
                                },
                            }
                        ],
                    }
                elif "score_case_output" in tool_names and "score_case_output" in last_user:
                    resp = {
                        "id": f"cmpl-{len(server_ref.requests)}",
                        "object": "chat.completion",
                        "model": "mock-eval-model",
                        "choices": [
                            {
                                "index": 0,
                                "finish_reason": "tool_calls",
                                "message": {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": "call_score_1",
                                            "type": "function",
                                            "function": {
                                                "name": "score_case_output",
                                                "arguments": json.dumps(
                                                    {
                                                        "case_id": "subagent_check",
                                                        "observed": "PASS: verified",
                                                        "expected": "PASS",
                                                    }
                                                ),
                                            },
                                        }
                                    ],
                                },
                            }
                        ],
                    }
                elif "write_eval_artifact" in tool_names:
                    resp = {
                        "id": f"cmpl-{len(server_ref.requests)}",
                        "object": "chat.completion",
                        "model": "mock-eval-model",
                        "choices": [
                            {
                                "index": 0,
                                "finish_reason": "tool_calls",
                                "message": {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": "call_write_1",
                                            "type": "function",
                                            "function": {
                                                "name": "write_eval_artifact",
                                                "arguments": json.dumps(
                                                    {
                                                        "filename": "summary_note.txt",
                                                        "content": "OpenMinion eval artifact verified.",
                                                    }
                                                ),
                                            },
                                        }
                                    ],
                                },
                            }
                        ],
                    }
                else:
                    resp = {
                        "id": f"cmpl-{len(server_ref.requests)}",
                        "object": "chat.completion",
                        "model": "mock-eval-model",
                        "choices": [
                            {
                                "index": 0,
                                "finish_reason": "stop",
                                "message": {
                                    "role": "assistant",
                                    "content": "PASS: session continuity confirmed.",
                                },
                            }
                        ],
                    }

                payload = json.dumps(resp).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self._server = HTTPServer(("127.0.0.1", 0), _Handler)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self) -> "_MockOpenAIServer":
        self._thread.start()
        return self

    def __exit__(self, *args: object) -> None:
        self._server.shutdown()
        self._server.server_close()


def test_fail_closed_approval_gate_single_use() -> None:
    gate = FailClosedApprovalGate()
    assert gate("write_eval_artifact", {"filename": "a.txt"}, "ap-1") is True
    assert gate("write_eval_artifact", {"filename": "b.txt"}, "ap-2") is False
    assert gate("purge_eval_history", {"confirm_phrase": "yes"}, "ap-3") is False
    assert [r.decision for r in gate.records] == ["approved", "denied", "denied"]


def test_fail_closed_approval_gate_blocks_path_traversal() -> None:
    gate = FailClosedApprovalGate()
    assert gate("write_eval_artifact", {"filename": "../escape.txt"}, "ap-1") is False
    assert gate("write_eval_artifact", {"filename": "sub/file.txt"}, "ap-2") is False
    assert gate("write_eval_artifact", {"filename": "C:\\evil.txt"}, "ap-3") is False
    assert all(r.reason == "invalid_or_traversal_artifact_filename" for r in gate.records)


def test_probe_ssrf_blocks_private_hosts_by_default(tmp_path: Path) -> None:
    from cortensor_agent_eval.tools import build_eval_tools

    counters: dict[str, int] = {}
    tools_map = build_eval_tools(workspace_dir=tmp_path, counters=counters)
    res_loopback = json.loads(tools_map["probe_inference_endpoint"]("http://127.0.0.1:8080/v1"))
    res_meta = json.loads(tools_map["probe_inference_endpoint"]("http://169.254.169.254/latest"))
    assert res_loopback["reachable"] is False
    assert res_loopback["detail"].startswith("Blocked:")
    assert res_meta["reachable"] is False
    assert res_meta["detail"].startswith("Blocked:")


def test_full_end_to_end_eval_suite(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    with _MockOpenAIServer() as srv:
        outcome = run_eval_suite(
            suite_name="mock-e2e",
            provider="openai",
            model="mock-eval-model",
            base_url=f"http://127.0.0.1:{srv.port}/v1",
            api_key="sk-mock",
            out_dir=out_dir,
            session_id="sess-e2e-001",
            allow_offline_fallback=False,
            allow_private_probe=True,
        )

    assert outcome.report.verdict == "READY"
    assert outcome.report.score == 100
    assert outcome.summary.passed_cases == 5
    assert outcome.summary.total_cases == 5
    assert outcome.summary.session_persisted is True
    assert outcome.summary.memory_bundle_items == 6
    assert outcome.summary.tool_inventory_count >= 100
    assert outcome.summary.stream_events_observed > 0
    assert outcome.summary.self_model_health != ""
    assert outcome.probe.reachable is True
    assert (out_dir / "facts.json").exists()
    assert (out_dir / "report.md").exists()
    assert (out_dir / "memory_bundle.json").exists()
    assert (out_dir / "summary_note.txt").exists()


def test_openminion_subagent_agent_id_finding_reproducer(tmp_path: Path) -> None:
    """Reproduce openminion 0.1.24 finding: subagent() drops parent.agent_id."""
    from openminion import APIRuntime, Agent, subagent
    from cortensor_agent_eval.policy import build_isolated_config
    from cortensor_agent_eval.tools import build_eval_tools

    work_dir = tmp_path / "rt"
    cfg_path = build_isolated_config(
        work_dir=work_dir,
        provider="openai",
        model="mock-eval-model",
        base_url="https://api.openai.com/v1",
        api_key="sk-repro",
    )
    counters: dict[str, int] = {}
    tools_map = build_eval_tools(workspace_dir=tmp_path, counters=counters)
    rt = APIRuntime.from_config_path(str(cfg_path), home_root=work_dir, data_root=work_dir)
    try:
        parent = Agent(
            runtime=rt,
            agent_id="evaluator",
            name="parent-eval",
            tools=[tools_map["score_case_output"]],
        )
        child = subagent(
            parent,
            name="child-eval",
            tools=[tools_map["score_case_output"]],
        )
        assert parent.agent_id == "evaluator"
        # Known SDK 0.1.24 quirk: child.agent_id is None instead of inheriting parent.agent_id
        assert child.agent_id is None
    finally:
        rt.close()


def test_provider_error_fallback_mode(tmp_path: Path) -> None:
    out_dir = tmp_path / "fallback-out"
    with _MockOpenAIServer(fail_with_500=True) as srv:
        outcome = run_eval_suite(
            suite_name="fallback-check",
            provider="openai",
            model="mock-eval-model",
            base_url=f"http://127.0.0.1:{srv.port}/v1",
            api_key="sk-mock",
            out_dir=out_dir,
            allow_offline_fallback=True,
            allow_private_probe=True,
        )

    assert outcome.used_offline_fallback is True
    assert outcome.provider_error is not None
    assert outcome.report.verdict == "FAILED"
    assert (out_dir / "facts.json").exists()
    assert (out_dir / "report.md").exists()
