"""Tests for OpenMinion 0.1 BuildingBlockProbeRunner, doc scrubbing, and CLI probe."""

from __future__ import annotations

import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from cortensor_verifier.cli import main
from cortensor_verifier.models import ProbeCheckResult
from cortensor_verifier.probe import (
    EXPECTED_PROBE_IDS,
    BuildingBlockProbeRunner,
    ProbeSuiteReport,
    assert_no_plaintext_secrets,
    build_empirical_dx_findings,
    export_probe_docs,
    infer_calibration_status,
    render_building_blocks_tested_md,
    render_what_we_learned_md,
    sanitize_base_url,
)
from tests.conftest import (
    LoopbackLLMServer,
    RecordedRequest,
    _maybe_internal_classifier_step,
    _render_step_response,
    error_step,
    json_step,
    text_step,
    tool_calls_step,
)


def _extract_closure_action_summary(messages: list[Any]) -> str:
    """Recover action_summary / closure_action_summary from ClosureJudgment prompts."""
    for msg in reversed(messages):
        if not isinstance(msg, dict):
            continue
        content = str(msg.get("content", "") or "")
        match = re.search(r'"closure_action_summary"\s*:\s*"((?:\\.|[^"\\])*)"', content)
        if match:
            try:
                decoded = json.loads(f'"{match.group(1)}"')
                if isinstance(decoded, str) and decoded.strip():
                    return decoded.strip()
            except json.JSONDecodeError:
                pass
        ctx_match = re.search(
            r"(?ms)^action_summary:\s*(.+?)(?=\nclosure_action_outputs:|\nclosure_intent_outcomes:|\n\[|\Z)",
            content,
        )
        if ctx_match:
            extracted = ctx_match.group(1).strip()
            if extracted:
                return extracted
    return "Tool execution completed cleanly."


def _probe_internal_classifier_step(request_body: dict[str, Any]) -> dict[str, Any] | None:
    """Handle FreshnessContract, FinalizationStatus, AND ClosureJudgment classifiers."""
    base_step = _maybe_internal_classifier_step(request_body)
    if base_step is not None:
        return base_step

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
    if schema_title == "ClosureJudgment":
        summary = _extract_closure_action_summary(request_body.get("messages", []))
        return {
            "type": "tool_calls",
            "calls": [
                {
                    "id": "call_closure_1",
                    "name": "submit_output",
                    "arguments": {
                        "satisfied": True,
                        "reason": "Tool execution completed cleanly.",
                        "next_action": "close",
                        "final_answer": summary,
                    },
                }
            ],
        }
    return None


def _smart_probe_step(request_body: dict[str, Any]) -> dict[str, Any]:
    """Deterministically act as an OpenAI-compatible model for the 10 probe scenarios."""
    messages = [m for m in request_body.get("messages", []) if isinstance(m, dict)]
    user_messages = [str(m.get("content", "")) for m in messages if m.get("role") == "user"]
    last_user = user_messages[-1] if user_messages else ""
    tool_msgs = [m for m in messages if m.get("role") == "tool"]

    tools = request_body.get("tools") or []
    available_tools = {
        str(t.get("function", {}).get("name", ""))
        for t in tools
        if isinstance(t, dict) and isinstance(t.get("function"), dict)
    }

    if "PROBE_STRUCTURED_NEGATIVE" in last_user:
        return text_step("MALFORMED_NON_JSON_PROBE")

    if "PROBE_STRUCTURED" in last_user:
        return json_step(
            {
                "status": "OK",
                "block": "structured_pydantic_output",
                "score": 0.99,
            }
        )

    if "PROBE_SUBAGENT" in last_user:
        if not tool_msgs and "probe_subagent_tool" in available_tools:
            return tool_calls_step(
                {
                    "id": "call_subagent_tool_1",
                    "name": "probe_subagent_tool",
                    "arguments": {"item": "subagent-check"},
                }
            )
        return json_step(
            {
                "status": "OK",
                "block": "subagent_delegation",
                "score": 0.97,
            }
        )

    if "PROBE_TOOLS_FORCED" in last_user:
        if not tool_msgs and "probe_echo_tag" in available_tools:
            return tool_calls_step(
                {
                    "id": "call_forced_echo_1",
                    "name": "probe_echo_tag",
                    "arguments": {"tag": "forced-c3"},
                }
            )
        content = str(tool_msgs[-1].get("content", "")) if tool_msgs else "missing"
        return text_step(f"FORCED_TOOL_OK: {content}")

    if "PROBE_TOOLS_AUTO" in last_user:
        if not tool_msgs and "probe_lookup_fact" in available_tools:
            return tool_calls_step(
                {
                    "id": "call_auto_lookup_1",
                    "name": "probe_lookup_fact",
                    "arguments": {"topic": "cortensor-poi"},
                }
            )
        content = str(tool_msgs[-1].get("content", "")) if tool_msgs else "missing"
        return text_step(f"AUTO_TOOL_OK: {content}")

    if (
        "PROBE_POLICY_ALLOW" in last_user
        or "PROBE_POLICY_DENY" in last_user
        or "PROBE_POLICY_PAUSE" in last_user
        or (
            last_user.strip().lower() == "allow_once"
            and any("PROBE_POLICY_PAUSE" in um for um in user_messages)
        )
    ):
        if "PROBE_POLICY_ALLOW" in last_user:
            att_id = "att-allow"
        elif "PROBE_POLICY_DENY" in last_user:
            att_id = "att-deny"
        else:
            att_id = "att-pause-resume"
        if not tool_msgs and "probe_publish_attestation" in available_tools:
            return tool_calls_step(
                {
                    "id": "call_policy_gate_1",
                    "name": "probe_publish_attestation",
                    "arguments": {"attestation_id": att_id},
                }
            )
        content = str(tool_msgs[-1].get("content", "")) if tool_msgs else "no_tool_result"
        return text_step(f"POLICY_GATE_OBSERVED: {content}")

    if "PROBE_SESSION_STORE" in last_user:
        return text_step("Session marker SESSION_TOKEN_ALPHA_42 stored.")

    if "PROBE_SESSION_RECALL" in last_user:
        prior_text = "\n".join(
            str(m.get("content", ""))
            for m in messages[:-1]
            if m.get("role") in {"user", "assistant"}
        )
        if "SESSION_TOKEN_ALPHA_42" in prior_text:
            return text_step("RECALLED: SESSION_TOKEN_ALPHA_42")
        return text_step("RECALLED: NONE")

    if "PROBE_HANDOFF" in last_user:
        if "transfer_to_specialist" in available_tools and not tool_msgs:
            return tool_calls_step(
                {
                    "id": "call_handoff_specialist_1",
                    "name": "transfer_to_specialist",
                    "arguments": {"message": "Verify handoff claim payload."},
                }
            )
        if "transfer_to_specialist" in available_tools and tool_msgs:
            return text_step(f"HANDOFF_COMPLETE: {tool_msgs[-1].get('content', '')}")
        return text_step("SPECIALIST_ACK: Handoff task verified.")

    if "Verify handoff claim payload" in last_user:
        return text_step("SPECIALIST_ACK: Handoff task verified.")

    if "PROBE_STREAM_TURN" in last_user:
        return text_step("STREAM_TELEMETRY_OK: Turn completed cleanly.")

    if "PROBE_ISOLATION" in last_user:
        return text_step("ISOLATION_OK")

    return text_step("PROBE_STUB_OK")


def _render_sse_chunks(payload: dict[str, Any]) -> bytes:
    """Convert a standard OpenAI chat completion payload into SSE text/event-stream bytes."""
    model = str(payload.get("model") or "stub-model")
    comp_id = str(payload.get("id") or "chatcmpl-sse-stub")
    choices = payload.get("choices") or [{}]
    message = choices[0].get("message", {}) if choices else {}
    finish_reason = choices[0].get("finish_reason") or "stop"
    usage = payload.get("usage") or {
        "prompt_tokens": 12,
        "completion_tokens": 15,
        "total_tokens": 27,
    }

    events: list[dict[str, Any]] = []
    content = message.get("content")
    tool_calls = message.get("tool_calls")

    if content:
        midpoint = max(1, len(content) // 2)
        for part in (content[:midpoint], content[midpoint:]):
            if not part:
                continue
            events.append(
                {
                    "id": comp_id,
                    "object": "chat.completion.chunk",
                    "model": model,
                    "choices": [{"index": 0, "delta": {"content": part}, "finish_reason": None}],
                }
            )
    elif tool_calls:
        for idx, tc in enumerate(tool_calls):
            events.append(
                {
                    "id": comp_id,
                    "object": "chat.completion.chunk",
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": idx,
                                        "id": tc.get("id", f"call_{idx}"),
                                        "type": "function",
                                        "function": {
                                            "name": tc["function"]["name"],
                                            "arguments": tc["function"]["arguments"],
                                        },
                                    }
                                ]
                            },
                            "finish_reason": None,
                        }
                    ],
                }
            )

    events.append(
        {
            "id": comp_id,
            "object": "chat.completion.chunk",
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": finish_reason}],
            "usage": usage,
        }
    )

    lines = [f"data: {json.dumps(evt)}\n\n" for evt in events]
    lines.append("data: [DONE]\n\n")
    return "".join(lines).encode("utf-8")


class ProbeLoopbackServer(LoopbackLLMServer):
    """SSE, delay, and ClosureJudgment-aware subclass of LoopbackLLMServer."""

    def __init__(self, *, smart_dispatch: bool = True) -> None:
        self.smart_dispatch = smart_dispatch
        super().__init__()

    def _resolve_probe_step(self, parsed: dict[str, Any]) -> dict[str, Any]:
        classifier_step = _probe_internal_classifier_step(parsed)
        if classifier_step is not None:
            return classifier_step
        with self._lock:
            if self._queue:
                return self._queue.pop(0)
            if self._default_step is not None:
                return self._default_step
        if self.smart_dispatch:
            return _smart_probe_step(parsed)
        return self._next_step()

    def _start_server(self) -> ThreadingHTTPServer:
        parent = self

        class _ProbeHandler(BaseHTTPRequestHandler):
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

                step = parent._resolve_probe_step(parsed)
                delay_s = float(step.get("delay_seconds", 0.0) or 0.0)
                if delay_s > 0.0:
                    time.sleep(delay_s)

                status, payload = _render_step_response(step, parsed)
                wants_stream = bool(parsed.get("stream")) and status < 400
                try:
                    if wants_stream:
                        encoded = _render_sse_chunks(payload)
                        self.send_response(status)
                        self.send_header("Content-Type", "text/event-stream")
                        self.send_header("Cache-Control", "no-cache")
                        self.send_header("Content-Length", str(len(encoded)))
                        self.send_header("Connection", "close")
                        self.end_headers()
                        self.wfile.write(encoded)
                    else:
                        encoded = json.dumps(payload).encode("utf-8")
                        self.send_response(status)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(encoded)))
                        self.send_header("Connection", "close")
                        self.end_headers()
                        self.wfile.write(encoded)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                    return

            def do_GET(self) -> None:  # noqa: N802
                if self.path.rstrip("/") == "/v1/models":
                    payload = {
                        "object": "list",
                        "data": [{"id": "stub-model", "object": "model"}],
                    }
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

        return ThreadingHTTPServer(("127.0.0.1", 0), _ProbeHandler)


@pytest.fixture()
def probe_server() -> ProbeLoopbackServer:
    server = ProbeLoopbackServer()
    try:
        yield server
    finally:
        server.close()


def test_probe_runner_executes_all_ten_building_blocks_against_real_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe_server: ProbeLoopbackServer,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-probe-secret-value-123456")
    runner = BuildingBlockProbeRunner(
        preset="openai-compatible",
        base_url=probe_server.base_url,
        model="stub-model",
        api_key_env="OPENAI_API_KEY",
        home_root=tmp_path / "probe-home",
        data_root=tmp_path / "probe-state",
    )
    report = runner.run_all()

    assert isinstance(report, ProbeSuiteReport)
    assert report.total_probes == 10
    assert report.passed_probes == 10
    assert report.failed_probes == 0
    assert report.all_passed is True
    assert [item.probe_id for item in report.probes] == list(EXPECTED_PROBE_IDS)

    for item in report.probes:
        assert isinstance(item, ProbeCheckResult)
        assert item.passed is True
        assert item.latency_ms is not None and item.latency_ms >= 0.0
        assert item.detail

    by_id = {item.probe_id: item for item in report.probes}
    assert by_id["structured_pydantic_output"].metadata["negative_validation_error"] is True
    assert by_id["policy_confirmation_gate"].metadata["allow_executed"] is True
    assert by_id["policy_confirmation_gate"].metadata["deny_blocked"] is True
    assert by_id["policy_confirmation_gate"].metadata["pause_blocked"] is True
    assert by_id["policy_confirmation_gate"].metadata["resume_executed"] is True
    assert by_id["policy_confirmation_gate"].metadata["paused_thread_id"]
    assert by_id["policy_confirmation_gate"].metadata["pending_confirmation_id"]
    assert "att-pause-resume" in by_id["policy_confirmation_gate"].metadata["executed_ids"]
    assert by_id["session_continuity"].metadata["same_session_recalled"] is True
    assert by_id["session_continuity"].metadata["second_session_isolated"] is True
    assert by_id["session_continuity"].metadata["thread_id"]
    assert by_id["memory_bundle_portability"].metadata["item_count"] == 1
    assert by_id["subagent_delegation"].metadata["parent_transcript_inherited"] is False
    assert by_id["agent_handoff"].metadata["tool_name"] == "transfer_to_specialist"
    assert by_id["submit_turn_streaming_telemetry"].metadata["chunk_count"] >= 2
    assert by_id["submit_turn_streaming_telemetry"].metadata["duration_ms"] > 0
    assert by_id["submit_turn_streaming_telemetry"].metadata["stats_input_tokens"] > 0
    assert by_id["submit_turn_streaming_telemetry"].metadata["stats_output_tokens"] > 0
    assert by_id["error_and_timeout_contracts"].metadata["http_500_attempts"] >= 2
    assert by_id["error_and_timeout_contracts"].metadata["timeout_raised"] is True
    assert by_id["error_and_timeout_contracts"].metadata["http_connection_reuse_enabled"] is False
    wire = by_id["error_and_timeout_contracts"].metadata["provider_wire_formats"]
    assert wire["anthropic_path"] == "/anthropic/v1/messages"
    assert wire["anthropic_x_api_key"] is True
    assert wire["anthropic_version_header"] is True
    assert wire["cortensor_path"] == "/cortensor/api/v2/completions"
    assert wire["cortensor_bearer_auth"] is True
    assert wire["openai_sse_usage_without_vendor"] is False
    assert wire["openai_sse_usage_with_vendor"] is True

    forced_reqs = [
        req
        for req in probe_server.requests
        if any(
            isinstance(m, dict)
            and m.get("role") == "user"
            and "PROBE_TOOLS_FORCED" in str(m.get("content", ""))
            for m in req.body.get("messages", [])
        )
    ]
    assert forced_reqs
    forced_tool_names = {
        t["function"]["name"]
        for t in forced_reqs[0].body.get("tools", [])
        if isinstance(t, dict) and isinstance(t.get("function"), dict)
    }
    assert "probe_echo_tag" in forced_tool_names
    assert "probe_lookup_fact" not in forced_tool_names

    handoff_reqs = [
        req
        for req in probe_server.requests
        if any(
            isinstance(t, dict)
            and isinstance(t.get("function"), dict)
            and t["function"].get("name") == "transfer_to_specialist"
            for t in req.body.get("tools", [])
        )
    ]
    assert handoff_reqs


def test_probe_dx_findings_reflect_only_executed_and_passed_probes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe_server: ProbeLoopbackServer,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-subset-probe-key-999")
    subset_runner = BuildingBlockProbeRunner(
        preset="openai-compatible",
        base_url=probe_server.base_url,
        model="stub-model",
        api_key_env="OPENAI_API_KEY",
        home_root=tmp_path / "subset-home",
        data_root=tmp_path / "subset-state",
        probe_ids=["agent_runtime_isolation", "policy_confirmation_gate"],
    )
    subset_report = subset_runner.run_all()
    assert subset_report.total_probes == 2
    assert subset_report.passed_probes == 2
    assert len(subset_report.dx_findings) == 2

    findings_blob = json.dumps(subset_report.dx_findings)
    assert "pause_blocked=True" in findings_blob
    assert "resume_executed=True" in findings_blob
    assert "AnthropicProvider" not in findings_blob
    assert "FreshnessContract" not in findings_blob

    assert (
        build_empirical_dx_findings(
            [
                ProbeCheckResult(
                    probe_id="structured_pydantic_output",
                    name="Block 2",
                    passed=False,
                    detail="Simulated failure",
                ),
                ProbeCheckResult(
                    probe_id="error_and_timeout_contracts",
                    name="Block 10",
                    passed=False,
                    detail="Simulated failure",
                ),
            ]
        )
        == []
    )


def test_probe_doc_export_scrubs_secrets_and_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret_token = "sk-top-secret-live-token-987654"
    monkeypatch.setenv("OPENAI_API_KEY", secret_token)
    probes = [
        ProbeCheckResult(
            probe_id=pid,
            name=f"Probe {pid}",
            passed=True,
            detail=f"Observed secret={secret_token} Bearer {secret_token} during check.",
            latency_ms=12.5,
            metadata={"callback_count": 2, "http_500_attempts": 6, "chunk_count": 12},
        )
        for pid in EXPECTED_PROBE_IDS
    ]
    report = ProbeSuiteReport(
        sdk_version="0.1.21",
        preset="openai-compatible",
        model="stub-model",
        base_url_host="http://127.0.0.1:49999/v1",
        calibration_status="[Loopback Stub Baseline — awaiting C4 live LLM calibration]",
        generated_at="2026-11-14T00:00:00+00:00",
        total_probes=len(probes),
        passed_probes=len(probes),
        failed_probes=0,
        total_latency_ms=125.0,
        probes=probes,
        dx_findings=build_empirical_dx_findings(probes),
    )
    docs_dir = tmp_path / "docs"
    tested_path, learned_path = export_probe_docs(
        report,
        docs_dir=docs_dir,
        secret_env_names=["OPENAI_API_KEY"],
    )

    assert tested_path.exists() and learned_path.exists()
    tested_text = tested_path.read_text(encoding="utf-8")
    learned_text = learned_path.read_text(encoding="utf-8")
    assert "[Loopback Stub Baseline — awaiting C4 live LLM calibration]" in tested_text
    assert "[Loopback Stub Baseline — awaiting C4 live LLM calibration]" in learned_text
    assert secret_token not in tested_text
    assert secret_token not in learned_text
    assert "[REDACTED_SECRET]" in tested_text
    assert "FreshnessContract" in learned_text
    assert "ClosureJudgment" in learned_text
    assert "http_connection_reuse_enabled" in learned_text

    with pytest.raises(ValueError, match="unredacted"):
        assert_no_plaintext_secrets(
            f"Leaked key: {secret_token}",
            extra_secrets=[secret_token],
        )


def test_cli_probe_exports_sanitized_docs_and_json_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    probe_server: ProbeLoopbackServer,
) -> None:
    secret_value = "sk-cli-probe-secret-token-xyz123"
    monkeypatch.setenv("OPENAI_API_KEY", secret_value)

    home_root = tmp_path / "cli-probe-home"
    data_root = tmp_path / "cli-probe-state"
    docs_dir = tmp_path / "cli-docs"
    out_file = tmp_path / "probe-report.json"

    rc = main(
        [
            "probe",
            "--preset",
            "openai-compatible",
            "--base-url",
            probe_server.base_url,
            "--model",
            "stub-model",
            "--api-key-env",
            "OPENAI_API_KEY",
            "--home-root",
            str(home_root),
            "--data-root",
            str(data_root),
            "--export-docs",
            "--docs-dir",
            str(docs_dir),
            "--output",
            str(out_file),
        ]
    )

    assert rc == 0
    stdout_report = ProbeSuiteReport.model_validate_json(capsys.readouterr().out)
    assert stdout_report.passed_probes == 10
    assert out_file.exists()
    assert (docs_dir / "BUILDING_BLOCKS_TESTED.md").exists()
    assert (docs_dir / "WHAT_WE_LEARNED.md").exists()

    agent_configs = list(home_root.rglob("agents.json"))
    assert agent_configs
    for artifact in [
        out_file,
        docs_dir / "BUILDING_BLOCKS_TESTED.md",
        docs_dir / "WHAT_WE_LEARNED.md",
        *agent_configs,
    ]:
        assert secret_value not in artifact.read_text(encoding="utf-8")


def test_cli_probe_returns_nonzero_when_probe_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fail-probe-token-0001")
    failing_server = ProbeLoopbackServer(smart_dispatch=False)
    failing_server.set_default(error_step(status=400, message="Forced non-retryable probe failure"))
    try:
        rc = main(
            [
                "probe",
                "--preset",
                "openai-compatible",
                "--base-url",
                failing_server.base_url,
                "--model",
                "stub-model",
                "--api-key-env",
                "OPENAI_API_KEY",
                "--home-root",
                str(tmp_path / "fail-home"),
                "--data-root",
                str(tmp_path / "fail-state"),
                "--probes",
                "agent_runtime_isolation",
                "--max-retries",
                "1",
            ]
        )
    finally:
        failing_server.close()

    assert rc != 0
    captured = capsys.readouterr()
    parsed = ProbeSuiteReport.model_validate_json(captured.out)
    assert parsed.total_probes == 1
    assert parsed.failed_probes == 1


def test_sanitize_base_url_redacts_third_party_relay_hosts_while_keeping_official_hosts() -> None:
    private_sanitized = sanitize_base_url("https://private-relay.example.org:8443/v1?token=abc")
    assert private_sanitized == "https://<configured-openai-compatible-relay>/v1"
    assert "private-relay.example.org" not in private_sanitized
    assert infer_calibration_status(private_sanitized) == "[Live LLM Calibrated]"

    loopback = sanitize_base_url("http://127.0.0.1:51234/v1")
    assert loopback == "http://127.0.0.1:51234/v1"
    assert infer_calibration_status(loopback) == "[Loopback Stub Baseline — awaiting C4 live LLM calibration]"

    cortensor = sanitize_base_url("https://router.cortensor.network/v1")
    assert cortensor == "https://router.cortensor.network/v1"
    assert infer_calibration_status(cortensor) == "[Live LLM Calibrated]"

    openai_official = sanitize_base_url("https://api.openai.com/v1")
    assert openai_official == "https://api.openai.com/v1"
    assert infer_calibration_status(openai_official) == "[Live LLM Calibrated]"


def test_empirical_dx_findings_interpolate_actual_probe_metadata_without_fallback_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe_server: ProbeLoopbackServer,
) -> None:
    broken_fallbacks = [
        "calls=0",
        "digest_seen=False",
        "other_session_isolated=False",
        "bundle_id=n/a",
        "payload_keys=[]",
        "handoff_tool_calls=0",
        "reply_len=0",
        "block=n/a",
    ]

    # (a) Live BuildingBlockProbeRunner run against deterministic loopback stub
    monkeypatch.setenv("OPENAI_API_KEY", "sk-empirical-dx-stub-123456")
    runner = BuildingBlockProbeRunner(
        preset="openai-compatible",
        base_url=probe_server.base_url,
        model="stub-model",
        api_key_env="OPENAI_API_KEY",
        home_root=tmp_path / "emp-home",
        data_root=tmp_path / "emp-state",
    )
    report = runner.run_all()
    assert report.passed_probes == 10
    assert len(report.dx_findings) == 10

    by_id = {item.probe_id: item for item in report.probes}
    live_observations = "\n".join(item["observation"] for item in report.dx_findings)
    for item in report.dx_findings:
        for bad in broken_fallbacks:
            assert bad not in item["observation"], (
                f"Fallback sentinel {bad!r} leaked into {item['title']!r}: {item['observation']!r}"
            )
    for expected in (
        f"db_count={by_id['agent_runtime_isolation'].metadata['db_count']}",
        "probe_echo_tag",
        "call_count=2",
        "forced_invoked=True",
        "second_session_isolated=True",
        "item_count=1",
        "export_bundle()",
        "import_bundle()",
        "handoff_invocations=1",
        "transfer_to_specialist",
        "subagent_calls=['subagent-check']",
        "tool_allowlist=['probe_subagent_tool']",
        "status=OK",
        "score=0.99",
        "negative_validation_error=True",
    ):
        assert expected in live_observations

    # (b) Calibrated sample fixture probes passed directly into build_empirical_dx_findings()
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "calibrated_sample_run.json"
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    fixture_probes = [ProbeCheckResult(**p) for p in raw["probe_report"]["probes"]]
    fixture_findings = build_empirical_dx_findings(fixture_probes)
    assert len(fixture_findings) == 10

    fixture_observations = "\n".join(item["observation"] for item in fixture_findings)
    for item in fixture_findings:
        for bad in broken_fallbacks:
            assert bad not in item["observation"], (
                f"Fallback sentinel {bad!r} leaked into fixture finding {item['title']!r}: {item['observation']!r}"
            )
    for expected in (
        "db_count=14",
        "probe_echo_tag",
        "second_session_isolated=True",
        "item_count=1",
        "handoff_invocations=1",
        "transfer_to_specialist",
        "subagent_calls=['subagent-check']",
        "tool_allowlist=['probe_subagent_tool']",
    ):
        assert expected in fixture_observations


def _extract_markdown_section(markdown: str, heading: str) -> str:
    marker = f"## {heading}"
    assert marker in markdown, f"Missing markdown section {marker!r}"
    after = markdown.split(marker, 1)[1]
    next_idx = after.find("\n## ")
    return after if next_idx == -1 else after[:next_idx]


def test_render_what_we_learned_includes_what_worked_cleanly_from_passed_probes() -> None:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "calibrated_sample_run.json"
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    report = ProbeSuiteReport.model_validate(raw["probe_report"])

    rendered = render_what_we_learned_md(report)
    assert "## Empirical SDK & DX Findings" in rendered
    assert "## Observed Runtime Measurements" in rendered

    worked = _extract_markdown_section(rendered, "What Worked Cleanly in OpenMinion 0.1")
    for expected in (
        "APIRuntime",
        "secret_free_config=True",
        "min_scope='READ_ONLY'",
        "tool_choice='forced'",
        "MemoryBundle",
        "second_session_isolated=True",
        "Handoff",
        "PolicyGrantInput",
        "pause_blocked=True",
        "resume_executed=True",
        "TurnChunk",
        "Pydantic",
        "negative_validation_error=True",
    ):
        assert expected in worked

    # Subset fidelity: unexecuted or failed probes must not leak into What Worked Cleanly
    subset_probes = [
        p
        for p in report.probes
        if p.probe_id in {"agent_runtime_isolation", "memory_bundle_portability"}
    ] + [
        ProbeCheckResult(
            probe_id="tool_and_forced_tools",
            name="Forced tools",
            passed=False,
            detail="Simulated failure",
        )
    ]
    subset_report = ProbeSuiteReport(
        sdk_version=report.sdk_version,
        preset=report.preset,
        model=report.model,
        base_url_host=report.base_url_host,
        calibration_status=report.calibration_status,
        generated_at=report.generated_at,
        total_probes=len(subset_probes),
        passed_probes=2,
        failed_probes=1,
        total_latency_ms=10.0,
        probes=subset_probes,
        dx_findings=build_empirical_dx_findings(subset_probes),
    )
    subset_worked = _extract_markdown_section(
        render_what_we_learned_md(subset_report),
        "What Worked Cleanly in OpenMinion 0.1",
    )
    assert "APIRuntime" in subset_worked
    assert "MemoryBundle" in subset_worked
    assert "tool_choice='forced'" not in subset_worked
    assert "TurnChunk" not in subset_worked

    # Zero passed probes must not fabricate clean-run bullets
    empty_report = subset_report.model_copy(
        update={"probes": [], "total_probes": 0, "passed_probes": 0, "failed_probes": 0, "dx_findings": []}
    )
    empty_worked = _extract_markdown_section(
        render_what_we_learned_md(empty_report),
        "What Worked Cleanly in OpenMinion 0.1",
    )
    assert "APIRuntime" not in empty_worked
    assert "no building-block probes passed" in empty_worked.lower()


def test_render_what_we_learned_includes_what_broke_and_rough_edges() -> None:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "calibrated_sample_run.json"
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    report = ProbeSuiteReport.model_validate(raw["probe_report"])

    rendered = render_what_we_learned_md(report)
    rough = _extract_markdown_section(rendered, "What Broke & Rough Edges Encountered")
    for expected in (
        "Agent.run",
        "thread_id",
        "TurnTelemetry",
        "TurnResponse.stats",
        "tokens_in=0",
        "input_tokens=11841",
        "handoff.target.run",
        "handoff.py:168-170",
        "service_vendor",
        "task_update",
        "task_context.py:173-191",
        "90.0s",
        "http_500_attempts=6",
    ):
        assert expected in rough

    # Failed probes in a run must also surface factually without fabricating passed telemetry
    failing_report = ProbeSuiteReport(
        sdk_version=report.sdk_version,
        preset=report.preset,
        model=report.model,
        base_url_host=report.base_url_host,
        calibration_status=report.calibration_status,
        generated_at=report.generated_at,
        total_probes=1,
        passed_probes=0,
        failed_probes=1,
        total_latency_ms=42.0,
        probes=[
            ProbeCheckResult(
                probe_id="agent_handoff",
                name="Handoff Peer Agent Transfer Tool",
                passed=False,
                detail="FAILED (TurnTimeoutError): handoff exceeded 90s default",
                latency_ms=42.0,
                metadata={"error_type": "TurnTimeoutError"},
            )
        ],
        dx_findings=[],
    )
    failing_rendered = render_what_we_learned_md(failing_report)
    failing_rough = _extract_markdown_section(
        failing_rendered,
        "What Broke & Rough Edges Encountered",
    )
    failing_proposals = _extract_markdown_section(
        failing_rendered,
        "Actionable SDK Improvement Proposals (Repro + Expected vs. Actual)",
    )
    assert "agent_handoff" in failing_rough
    assert "TurnTimeoutError" in failing_rough
    assert "input_tokens=11841" not in failing_rough
    assert "session_continuity" not in failing_rough
    assert "FreshnessContract" not in failing_rough
    assert "handoff.py:168-170" not in failing_rough
    assert "**Target Module**:" not in failing_proposals

    # Single-probe pass emits only that probe's rough edge & proposal (zero unexecuted prose)
    partial_report = failing_report.model_copy(
        update={
            "total_probes": 1,
            "passed_probes": 1,
            "failed_probes": 0,
            "probes": [
                next(p for p in report.probes if p.probe_id == "submit_turn_streaming_telemetry")
            ],
        }
    )
    partial_rendered = render_what_we_learned_md(partial_report)
    partial_proposals = _extract_markdown_section(
        partial_rendered,
        "Actionable SDK Improvement Proposals (Repro + Expected vs. Actual)",
    )
    assert partial_proposals.count("**Target Module**:") == 1
    assert "openminion/services/runtime/daemon.py:549-555" in partial_proposals
    assert "openminion/api/handoff.py:168-170" not in partial_proposals


def test_render_what_we_learned_includes_actionable_proposals_and_passes_secret_check() -> None:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "calibrated_sample_run.json"
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    report = ProbeSuiteReport.model_validate(raw["probe_report"])

    rendered = render_what_we_learned_md(report)
    assert_no_plaintext_secrets(rendered)

    proposals = _extract_markdown_section(
        rendered,
        "Actionable SDK Improvement Proposals (Repro + Expected vs. Actual)",
    )
    assert proposals.count("**Target Module**:") >= 5
    assert proposals.count("**Minimal Repro**:") >= 5
    assert proposals.count("**Expected vs. Actual**:") >= 5
    assert proposals.count("**Recommended Upstream Fix**:") >= 5

    for expected in (
        "openminion/services/runtime/daemon.py:549-555",
        "openminion/api/handoff.py:168-170",
        "openminion/modules/brain/loop/context/task_context.py:173-191",
        "openminion/api/agent.py:167-170",
        "openminion/modules/llm/providers/openai/adapter.py:901-907",
    ):
        assert expected in proposals


def test_export_probe_docs_scrubs_secrets_in_new_dx_sections(tmp_path: Path) -> None:
    pattern_secret = "sk-live-pattern-secret-1234567890"
    custom_secret = "custom_extra_token_val_987654"
    report = ProbeSuiteReport(
        sdk_version="0.1.21",
        preset="openai-compatible",
        model="stub-model",
        base_url_host="http://127.0.0.1:49999/v1",
        calibration_status="[Stubbed Scrub Verification]",
        generated_at="2026-11-15T00:00:00+00:00",
        total_probes=2,
        passed_probes=1,
        failed_probes=1,
        total_latency_ms=40.0,
        probes=[
            ProbeCheckResult(
                probe_id="session_continuity",
                name="Session Memory & Thread Continuity",
                passed=True,
                detail=f"Completed with token {pattern_secret}",
                latency_ms=20.0,
                metadata={
                    "recalled_token": True,
                    "thread_id": f"thr-{pattern_secret}",
                    "continuity_calls": 2,
                },
            ),
            ProbeCheckResult(
                probe_id="agent_handoff",
                name="Handoff Peer Agent Transfer Tool",
                passed=False,
                detail=f"FAILED (RuntimeError): auth leak {custom_secret}",
                latency_ms=20.0,
                metadata={"error_type": f"Err-{custom_secret}"},
            ),
        ],
        dx_findings=[],
    )

    direct_rendered = render_what_we_learned_md(report)
    assert pattern_secret not in direct_rendered
    assert "[REDACTED_SECRET]" in _extract_markdown_section(
        direct_rendered,
        "What Worked Cleanly in OpenMinion 0.1",
    )

    _, learned_path = export_probe_docs(
        report,
        docs_dir=tmp_path / "docs",
        extra_secrets=[custom_secret],
    )
    exported_text = learned_path.read_text(encoding="utf-8")
    assert pattern_secret not in exported_text
    assert custom_secret not in exported_text
    assert_no_plaintext_secrets(exported_text, extra_secrets=[custom_secret])
    worked_section = _extract_markdown_section(exported_text, "What Worked Cleanly in OpenMinion 0.1")
    broke_section = _extract_markdown_section(exported_text, "What Broke & Rough Edges Encountered")
    assert "[REDACTED_SECRET]" in worked_section
    assert "[REDACTED_SECRET]" in broke_section


def test_checked_in_probe_docs_match_calibrated_sample_deterministically() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sample = json.loads((repo_root / "fixtures" / "calibrated_sample_run.json").read_text(encoding="utf-8"))
    report = ProbeSuiteReport.model_validate(sample["probe_report"])

    expected_learned = render_what_we_learned_md(report)
    expected_tested = render_building_blocks_tested_md(report)

    actual_learned = (repo_root / "docs" / "WHAT_WE_LEARNED.md").read_text(encoding="utf-8")
    actual_tested = (repo_root / "docs" / "BUILDING_BLOCKS_TESTED.md").read_text(encoding="utf-8")

    assert actual_learned == expected_learned
    assert actual_tested == expected_tested
    assert_no_plaintext_secrets(actual_learned)
    assert_no_plaintext_secrets(actual_tested)


def test_upstream_openminion_bonus_drafts_are_complete_and_secret_free() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    drafts_path = repo_root / "docs" / "UPSTREAM_OPENMINION_BONUS_DRAFTS.md"
    assert drafts_path.exists(), "Missing docs/UPSTREAM_OPENMINION_BONUS_DRAFTS.md"

    text = drafts_path.read_text(encoding="utf-8")
    assert_no_plaintext_secrets(text)
    assert "openminion/openminion" in text
    assert "0.1.21" in text
    assert "manual human filing" in text.lower()
    assert "Hackathon #5 Bonus Track" in text

    for required_ref in (
        "openminion/services/runtime/daemon.py",
        "549-555",
        "openminion/api/handoff.py",
        "168-170",
        "openminion/modules/brain/loop/context/task_context.py",
        "173-191",
        "```diff",
    ):
        assert required_ref in text





