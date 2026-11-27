"""Unit and end-to-end tests for ProofAudit Minion."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from openminion import ProviderError

from proof_audit.agent import run_proof_audit
from proof_audit.checks import (
    inspect_repo_manifest,
    probe_openai_compatible_endpoint,
    run_repo_smoke_check,
    scan_sdk_surface,
)
from proof_audit.models import ProofAuditReport


def _create_valid_sample_repo(root: Path) -> None:
    (root / "LICENSE").write_text(
        "MIT License\n\nPermission is hereby granted, free of charge, to any person obtaining a copy...",
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        "# Sample OpenMinion Agent\n\nRun `openminion doctor --check-turn --json` before submitting.\n"
        "Uses APIRuntime and Agent for bounded workflows.\n",
        encoding="utf-8",
    )
    (root / "requirements.txt").write_text("openminion==0.1.24\npydantic>=2,<3\n", encoding="utf-8")
    (root / ".gitignore").write_text(".venv/\n__pycache__/\n.openminion/\n.env\n", encoding="utf-8")
    (root / "app.py").write_text(
        "from openminion import APIRuntime, Agent, ProviderError, tool\n\n"
        "@tool(min_scope='READ_ONLY', idempotent=True)\n"
        "def ping(target: str) -> str:\n"
        "    return target\n\n"
        "def run_demo(runtime: APIRuntime) -> None:\n"
        "    with Agent(runtime=runtime, output_type=dict, session_id='s1') as agent:\n"
        "        agent.run('hello', approval_callback=lambda *_: True)\n",
        encoding="utf-8",
    )


class _MockOpenAIState:
    def __init__(self, *, mode: str, target_repo: str) -> None:
        self.mode = mode
        self.target_repo = target_repo
        self.chat_requests: list[dict[str, Any]] = []
        self.turn = 0


def _start_mock_server(*, mode: str, target_repo: str) -> tuple[ThreadingHTTPServer, _MockOpenAIState, str]:
    state = _MockOpenAIState(mode=mode, target_repo=target_repo)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

        def do_GET(self) -> None:  # noqa: N802
            if self.path.endswith("/models"):
                body = json.dumps({"object": "list", "data": [{"id": "mock-model"}]}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(404)
            self.end_headers()

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length).decode("utf-8", errors="ignore")
            payload = json.loads(raw_body) if raw_body else {}
            state.chat_requests.append(payload)
            state.turn += 1

            if state.mode == "error_500":
                err = json.dumps({"error": {"message": "Simulated upstream 500", "type": "server_error"}}).encode(
                    "utf-8"
                )
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(err)))
                self.end_headers()
                self.wfile.write(err)
                return

            tool_names = {
                t.get("function", {}).get("name")
                for t in payload.get("tools", [])
                if isinstance(t, dict)
            }
            has_collector_tools = "inspect_repo_manifest" in tool_names
            messages = payload.get("messages", [])
            has_tool_result = any(m.get("role") == "tool" for m in messages if isinstance(m, dict))

            if has_collector_tools and not has_tool_result:
                message: dict[str, Any] = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_manifest_1",
                            "type": "function",
                            "function": {
                                "name": "inspect_repo_manifest",
                                "arguments": json.dumps({"repo_path": state.target_repo}),
                            },
                        },
                        {
                            "id": "call_smoke_1",
                            "type": "function",
                            "function": {
                                "name": "run_repo_smoke_check",
                                "arguments": json.dumps({"repo_path": state.target_repo}),
                            },
                        },
                    ],
                }
            elif has_collector_tools and has_tool_result:
                message = {
                    "role": "assistant",
                    "content": "Collected manifest and py_compile smoke check results.",
                }
            else:
                report_json = ProofAuditReport(
                    repo_name=Path(state.target_repo).name,
                    verdict="READY",
                    score=100,
                    building_blocks_detected=[
                        "@tool",
                        "APIRuntime",
                        "Agent",
                        "ProviderError",
                        "approval_callback",
                        "openminion CLI/doctor",
                        "output_type",
                        "session_id",
                    ],
                    findings=[],
                    remediation_steps=[],
                    summary="All manifest, SDK surface, endpoint, and py_compile checks passed.",
                ).model_dump_json()
                message = {"role": "assistant", "content": report_json}

            response_payload = {
                "id": f"chatcmpl-mock-{state.turn}",
                "object": "chat.completion",
                "created": 1700000000,
                "model": payload.get("model", "mock-model"),
                "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
            }
            body = json.dumps(response_payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    return server, state, f"http://127.0.0.1:{port}/v1"


class ProofAuditTests(unittest.TestCase):
    def test_1_inspect_repo_manifest_valid_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "valid-repo"
            repo.mkdir()
            _create_valid_sample_repo(repo)
            result = json.loads(inspect_repo_manifest(str(repo)))
            self.assertTrue(result["ok"])
            statuses = {item["check_id"]: item["status"] for item in result["findings"]}
            self.assertEqual(statuses["manifest.license"], "PASS")
            self.assertEqual(statuses["manifest.readme"], "PASS")
            self.assertEqual(statuses["manifest.openminion_pin"], "PASS")
            self.assertEqual(statuses["manifest.gitignore"], "PASS")
            self.assertEqual(statuses["manifest.secrets_hygiene"], "PASS")

    def test_2_inspect_repo_manifest_missing_license_and_pin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "incomplete-repo"
            repo.mkdir()
            (repo / "README.md").write_text("# Incomplete\nShort", encoding="utf-8")
            (repo / "requirements.txt").write_text("pydantic>=2\n", encoding="utf-8")
            result = json.loads(inspect_repo_manifest(str(repo)))
            self.assertFalse(result["ok"])
            statuses = {item["check_id"]: item["status"] for item in result["findings"]}
            self.assertEqual(statuses["manifest.license"], "FAIL")
            self.assertEqual(statuses["manifest.openminion_pin"], "FAIL")

    def test_3_scan_sdk_surface_and_smoke_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "sdk-repo"
            repo.mkdir()
            _create_valid_sample_repo(repo)
            sdk_result = json.loads(scan_sdk_surface(str(repo)))
            detected = set(sdk_result["building_blocks_detected"])
            for expected in ("APIRuntime", "Agent", "@tool", "output_type", "session_id", "approval_callback", "ProviderError"):
                self.assertIn(expected, detected)

            smoke_ok = json.loads(run_repo_smoke_check(str(repo)))
            self.assertEqual(smoke_ok["finding"]["status"], "PASS")
            self.assertEqual(smoke_ok["errors"], [])

            (repo / "broken.py").write_text("def oops(:\n    pass\n", encoding="utf-8")
            smoke_fail = json.loads(run_repo_smoke_check(str(repo)))
            self.assertEqual(smoke_fail["finding"]["status"], "FAIL")
            self.assertEqual(len(smoke_fail["errors"]), 1)

    def test_4_probe_openai_compatible_endpoint(self) -> None:
        server, _, base_url = _start_mock_server(mode="success", target_repo=".")
        try:
            probe = json.loads(probe_openai_compatible_endpoint(base_url))
            self.assertTrue(probe["reachable"])
            self.assertEqual(probe["status_code"], 200)
            self.assertEqual(probe["finding"]["status"], "PASS")
        finally:
            server.shutdown()
            server.server_close()

    def test_5_end_to_end_real_openminion_agent_with_mock_openai(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = tmp_path / "target-repo"
            repo.mkdir()
            _create_valid_sample_repo(repo)
            out_dir = tmp_path / "audit-out"

            server, state, base_url = _start_mock_server(mode="success", target_repo=str(repo))
            prev_key = os.environ.get("OPENAI_COMPATIBLE_API_KEY")
            os.environ["OPENAI_COMPATIBLE_API_KEY"] = "local-mock-credential"
            try:
                outcome = run_proof_audit(
                    str(repo),
                    provider="custom-openai-compatible",
                    model="mock-model",
                    base_url=base_url,
                    probe_url=base_url,
                    out_dir=out_dir,
                    session_id="test-session-123",
                    allow_offline_fallback=False,
                    timeout_seconds=30.0,
                )
            finally:
                if prev_key is None:
                    os.environ.pop("OPENAI_COMPATIBLE_API_KEY", None)
                else:
                    os.environ["OPENAI_COMPATIBLE_API_KEY"] = prev_key
                server.shutdown()
                server.server_close()

            self.assertFalse(outcome.used_offline_fallback)
            self.assertEqual(outcome.session_id, "test-session-123")
            self.assertEqual(outcome.report.verdict, "READY")
            self.assertEqual(outcome.report.score, 100)
            approved_tools = [a["tool_name"] for a in outcome.approvals]
            self.assertIn("run_repo_smoke_check", approved_tools)
            self.assertGreaterEqual(len(state.chat_requests), 3)
            self.assertTrue((out_dir / "facts.json").exists())
            self.assertTrue((out_dir / "report.md").exists())
            self.assertTrue((out_dir / "run.txt").exists())

    def test_6_provider_error_caught_cleanly_on_http_500(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = tmp_path / "target-repo"
            repo.mkdir()
            _create_valid_sample_repo(repo)
            out_dir = tmp_path / "audit-out"

            server, _, base_url = _start_mock_server(mode="error_500", target_repo=str(repo))
            prev_key = os.environ.get("OPENAI_COMPATIBLE_API_KEY")
            os.environ["OPENAI_COMPATIBLE_API_KEY"] = "local-mock-credential"
            try:
                with self.assertRaises(ProviderError):
                    run_proof_audit(
                        str(repo),
                        provider="custom-openai-compatible",
                        model="mock-model",
                        base_url=base_url,
                        probe_url=base_url,
                        allow_offline_fallback=False,
                        timeout_seconds=15.0,
                    )

                fallback_outcome = run_proof_audit(
                    str(repo),
                    provider="custom-openai-compatible",
                    model="mock-model",
                    base_url=base_url,
                    probe_url=base_url,
                    out_dir=out_dir,
                    allow_offline_fallback=True,
                    timeout_seconds=15.0,
                )
            finally:
                if prev_key is None:
                    os.environ.pop("OPENAI_COMPATIBLE_API_KEY", None)
                else:
                    os.environ["OPENAI_COMPATIBLE_API_KEY"] = prev_key
                server.shutdown()
                server.server_close()

            self.assertTrue(fallback_outcome.used_offline_fallback)
            self.assertIsNotNone(fallback_outcome.provider_error)
            self.assertIn("ProviderError", fallback_outcome.provider_error or "")
            self.assertEqual(fallback_outcome.report.verdict, "READY")
            self.assertTrue((out_dir / "report.md").exists())


if __name__ == "__main__":
    unittest.main()
