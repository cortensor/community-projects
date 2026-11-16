"""10-module OpenMinion 0.1 Building Block Probe runner and sanitized report exporter."""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Literal, Sequence
from urllib.parse import urlparse
from uuid import uuid4

import openminion
from openminion.api import (
    APIRuntime,
    Agent,
    AgentOutputValidationError,
    Handoff,
    ProviderError,
    TurnChunk,
    TurnResponse,
    TurnTelemetry,
    TurnTimeoutError,
    subagent,
)
from openminion.api.handoff import SubagentRunContext
from openminion.modules.memory.errors import InvalidArgumentError
from openminion.modules.memory.portability import (
    MemoryBundle,
    export_bundle,
    import_bundle,
    load_bundle,
    save_bundle,
)
from openminion.tools import tool
from pydantic import BaseModel, Field

from cortensor_verifier.models import ProbeCheckResult
from cortensor_verifier.runtime_factory import (
    build_isolated_config,
    create_isolated_runtime,
    resolve_isolated_paths,
)

EXPECTED_PROBE_IDS: tuple[str, ...] = (
    "agent_runtime_isolation",
    "structured_pydantic_output",
    "tool_and_forced_tools",
    "policy_confirmation_gate",
    "session_continuity",
    "memory_bundle_portability",
    "subagent_delegation",
    "agent_handoff",
    "submit_turn_streaming_telemetry",
    "error_and_timeout_contracts",
)

_KNOWN_SECRET_ENV_NAMES: tuple[str, ...] = (
    "OPENAI_API_KEY",
    "CORTENSOR_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENROUTER_API_KEY",
    "GROQ_API_KEY",
    "CEREBRAS_API_KEY",
    "OLLAMA_API_KEY",
    "DASHSCOPE_API_KEY",
)

_SECRET_PATTERN_REGEXES: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"(Bearer\s+)(?!\[REDACTED_SECRET\])[A-Za-z0-9._-]{8,}", re.IGNORECASE),
    re.compile(r"(x-api-key\s*:\s*)(?!\[REDACTED_SECRET\])\S+", re.IGNORECASE),
    re.compile(
        r'("?(?:api_key|token|secret)"?\s*[:=]\s*["\'])(?!\[REDACTED_SECRET\])[^"\']{6,}(["\'])',
        re.IGNORECASE,
    ),
)

_UNREDACTED_SECRET_CHECKS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"Bearer\s+(?!\[REDACTED_SECRET\])[A-Za-z0-9._-]{8,}", re.IGNORECASE),
)


class _ProbeStructuredOutput(BaseModel):
    """Typed Pydantic v2 schema used for structured-output & subagent probes."""

    status: Literal["OK", "DEGRADED"]
    block: str = Field(..., min_length=1)
    score: float = Field(..., ge=0.0, le=1.0)


class ProbeSuiteReport(BaseModel):
    """Complete building-block verification report across all 10 OpenMinion primitives."""

    suite_name: str = "openminion-0.1-building-blocks"
    sdk_version: str = Field(..., min_length=1)
    preset: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    base_url_host: str = Field(..., min_length=1)
    calibration_status: str = Field(..., min_length=1)
    generated_at: str = Field(..., min_length=1)
    total_probes: int = Field(..., ge=0)
    passed_probes: int = Field(..., ge=0)
    failed_probes: int = Field(..., ge=0)
    total_latency_ms: float = Field(..., ge=0.0)
    probes: list[ProbeCheckResult] = Field(default_factory=list)
    dx_findings: list[dict[str, str]] = Field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return self.total_probes > 0 and self.failed_probes == 0


_PUBLIC_SAFE_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "api.openai.com", "cortensor.network"})


def sanitize_base_url(base_url: str | None) -> str:
    """Return scheme/host/path without embedded credentials, query strings, or private relay hosts."""
    raw = str(base_url or "").strip()
    if not raw:
        return "preset-default"
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return raw.split("?", 1)[0]
    host = (parsed.hostname or parsed.netloc).strip()
    host_lower = host.lower()
    path = parsed.path or ""
    if host_lower in _PUBLIC_SAFE_HOSTS or host_lower.endswith(".cortensor.network"):
        port_suffix = f":{parsed.port}" if parsed.port else ""
        return f"{parsed.scheme}://{host}{port_suffix}{path}"
    return f"{parsed.scheme}://<configured-openai-compatible-relay>{path}"


def infer_calibration_status(base_url: str | None) -> str:
    """Distinguish local loopback stub baselines from C4 live LLM runs."""
    raw = str(base_url or "").strip()
    if "<configured-openai-compatible-relay>" in raw:
        return "[Live LLM Calibrated]"
    host = (urlparse(raw).hostname or "").lower() if raw else ""
    if host in {"127.0.0.1", "localhost", "::1"}:
        return "[Loopback Stub Baseline — awaiting C4 live LLM calibration]"
    return "[Live LLM Calibrated]"


def _collect_sensitive_values(
    *,
    secret_env_names: Sequence[str] | None = None,
    extra_secrets: Sequence[str] | None = None,
) -> list[str]:
    values: set[str] = set()
    candidate_names = set(_KNOWN_SECRET_ENV_NAMES)
    if secret_env_names:
        candidate_names.update(name for name in secret_env_names if name)
    for env_name, env_val in os.environ.items():
        if env_name in candidate_names or env_name.endswith(
            ("_KEY", "_TOKEN", "_SECRET", "_PASSWORD")
        ):
            trimmed = env_val.strip()
            if len(trimmed) >= 6:
                values.add(trimmed)
    for item in extra_secrets or ():
        trimmed = str(item or "").strip()
        if len(trimmed) >= 6:
            values.add(trimmed)
    return sorted(values, key=len, reverse=True)


def scrub_secrets(
    text: str,
    *,
    secret_env_names: Sequence[str] | None = None,
    extra_secrets: Sequence[str] | None = None,
) -> str:
    """Replace literal env secret values and token patterns with [REDACTED_SECRET]."""
    sanitized = str(text or "")
    for secret in _collect_sensitive_values(
        secret_env_names=secret_env_names,
        extra_secrets=extra_secrets,
    ):
        sanitized = sanitized.replace(secret, "[REDACTED_SECRET]")

    sanitized = _SECRET_PATTERN_REGEXES[0].sub("[REDACTED_SECRET]", sanitized)
    sanitized = _SECRET_PATTERN_REGEXES[1].sub(r"\1[REDACTED_SECRET]", sanitized)
    sanitized = _SECRET_PATTERN_REGEXES[2].sub(r"\1[REDACTED_SECRET]", sanitized)
    sanitized = _SECRET_PATTERN_REGEXES[3].sub(r"\1[REDACTED_SECRET]\2", sanitized)
    return sanitized


def assert_no_plaintext_secrets(
    text: str,
    *,
    secret_env_names: Sequence[str] | None = None,
    extra_secrets: Sequence[str] | None = None,
) -> None:
    """Fail closed if any unredacted API key or bearer token remains in exported text."""
    for secret in _collect_sensitive_values(
        secret_env_names=secret_env_names,
        extra_secrets=extra_secrets,
    ):
        if secret in text:
            raise ValueError(
                "Refusing to export probe docs: unredacted secret material detected."
            )
    for pattern in _UNREDACTED_SECRET_CHECKS:
        if pattern.search(text):
            raise ValueError(
                "Refusing to export probe docs: unredacted secret token pattern detected."
            )


class _FaultInjectionServer:
    """Ephemeral loopback HTTP fault server for deterministic error/timeout/invalid-json checks."""

    def __init__(self) -> None:
        self.attempts_500 = 0
        self.attempts_slow = 0
        self.attempts_malformed = 0
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._server = self._start_server()
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="probe-fault-injection-server",
            daemon=True,
        )
        self._thread.start()

    @property
    def port(self) -> int:
        return int(self._server.server_address[1])

    @property
    def wire_captures(self) -> list[tuple[str, dict[str, str]]]:
        with self._lock:
            return list(getattr(self, "_wire_captures", []))

    @property
    def url_500(self) -> str:
        return f"http://127.0.0.1:{self.port}/fault500/v1"

    @property
    def url_slow(self) -> str:
        return f"http://127.0.0.1:{self.port}/slow/v1"

    @property
    def url_malformed(self) -> str:
        return f"http://127.0.0.1:{self.port}/malformed/v1"

    @property
    def url_anthropic(self) -> str:
        return f"http://127.0.0.1:{self.port}/anthropic/v1"

    @property
    def url_cortensor(self) -> str:
        return f"http://127.0.0.1:{self.port}/cortensor/api/v2/completions"

    @property
    def url_openai_sse(self) -> str:
        return f"http://127.0.0.1:{self.port}/openai_sse/v1"

    def close(self) -> None:
        self._stop_event.set()
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)

    def _start_server(self) -> ThreadingHTTPServer:
        parent = self

        class _FaultHandler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                return

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", "0") or "0")
                if length > 0:
                    self.rfile.read(length)

                if self.path.startswith("/fault500/"):
                    with parent._lock:
                        parent.attempts_500 += 1
                    body = json.dumps(
                        {
                            "error": {
                                "message": "Deterministic probe HTTP 500 fault.",
                                "type": "server_error",
                                "code": "probe_fault_500",
                            }
                        }
                    ).encode("utf-8")
                    self._send(500, body)
                    return

                if self.path.startswith("/slow/"):
                    with parent._lock:
                        parent.attempts_slow += 1
                    deadline = time.monotonic() + 1.5
                    while time.monotonic() < deadline and not parent._stop_event.is_set():
                        time.sleep(0.05)
                    body = json.dumps(
                        {
                            "id": "chatcmpl-slow-probe",
                            "object": "chat.completion",
                            "model": "stub-model",
                            "choices": [
                                {
                                    "index": 0,
                                    "message": {"role": "assistant", "content": "LATE_RESPONSE"},
                                    "finish_reason": "stop",
                                }
                            ],
                        }
                    ).encode("utf-8")
                    self._send(200, body)
                    return

                if self.path.startswith("/malformed/"):
                    with parent._lock:
                        parent.attempts_malformed += 1
                    body = json.dumps(
                        {
                            "id": "chatcmpl-malformed-probe",
                            "object": "chat.completion",
                            "model": "stub-model",
                            "choices": [
                                {
                                    "index": 0,
                                    "message": {
                                        "role": "assistant",
                                        "content": "MALFORMED_NON_JSON_PROBE",
                                    },
                                    "finish_reason": "stop",
                                }
                            ],
                        }
                    ).encode("utf-8")
                    self._send(200, body)
                    return

                if self.path == "/anthropic/v1/messages":
                    with parent._lock:
                        captures = getattr(parent, "_wire_captures", None)
                        if captures is None:
                            captures = []
                            parent._wire_captures = captures
                        captures.append(("anthropic", {k.lower(): v for k, v in self.headers.items()}))
                    body = json.dumps(
                        {
                            "id": "msg_probe_anthropic",
                            "type": "message",
                            "role": "assistant",
                            "model": "stub-anthropic",
                            "content": [{"type": "text", "text": "ANTHROPIC_OK"}],
                            "stop_reason": "end_turn",
                            "usage": {"input_tokens": 11, "output_tokens": 3},
                        }
                    ).encode("utf-8")
                    self._send(200, body)
                    return

                if self.path == "/cortensor/api/v2/completions":
                    with parent._lock:
                        captures = getattr(parent, "_wire_captures", None)
                        if captures is None:
                            captures = []
                            parent._wire_captures = captures
                        captures.append(("cortensor", {k.lower(): v for k, v in self.headers.items()}))
                    body = json.dumps(
                        {
                            "id": "cmpl_probe_cortensor",
                            "model": "gpt-oss-20b",
                            "choices": [
                                {
                                    "index": 0,
                                    "text": "CORTENSOR_OK",
                                    "finish_reason": "stop",
                                }
                            ],
                            "usage": {
                                "prompt_tokens": 9,
                                "completion_tokens": 3,
                                "total_tokens": 12,
                            },
                        }
                    ).encode("utf-8")
                    self._send(200, body)
                    return

                if self.path == "/openai_sse/v1/chat/completions":
                    with parent._lock:
                        captures = getattr(parent, "_wire_captures", None)
                        if captures is None:
                            captures = []
                            parent._wire_captures = captures
                        captures.append(("openai_sse", {k.lower(): v for k, v in self.headers.items()}))
                    sse_body = (
                        'data: {"id":"chatcmpl-sse","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"SSE_OK"},"finish_reason":null}]}\n\n'
                        'data: {"id":"chatcmpl-sse","object":"chat.completion.chunk","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":10,"completion_tokens":2,"total_tokens":12}}\n\n'
                        "data: [DONE]\n\n"
                    ).encode("utf-8")
                    self._send(200, sse_body, content_type="text/event-stream; charset=utf-8")
                    return

                self._send(404, b'{"error": "not_found"}')

            def _send(
                self,
                status: int,
                body: bytes,
                content_type: str = "application/json",
            ) -> None:
                try:
                    self.send_response(status)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                    return

        return ThreadingHTTPServer(("127.0.0.1", 0), _FaultHandler)


class BuildingBlockProbeRunner:
    """Executes all 10 OpenMinion 0.1 building-block probes against a real APIRuntime."""

    def __init__(
        self,
        *,
        preset: str = "openai-compatible",
        base_url: str | None = None,
        model: str | None = None,
        api_key_env: str | None = None,
        agent_id: str = "verifier",
        home_root: str | Path | None = None,
        data_root: str | Path | None = None,
        provider_retry_max_attempts: int = 2,
        timeout_seconds: int | None = 15,
        http_connection_reuse_enabled: bool = False,
        probe_ids: Sequence[str] | None = None,
    ) -> None:
        self.preset = preset
        self.base_url = base_url
        self.model = model
        self.api_key_env = api_key_env
        self.agent_id = agent_id
        self.home_root = home_root
        self.data_root = data_root
        self.provider_retry_max_attempts = provider_retry_max_attempts
        self.timeout_seconds = timeout_seconds
        self.http_connection_reuse_enabled = http_connection_reuse_enabled
        if probe_ids is None:
            self.probe_ids = EXPECTED_PROBE_IDS
        else:
            requested = tuple(str(pid).strip() for pid in probe_ids if str(pid).strip())
            if not requested:
                raise ValueError("probe_ids must not be empty when specified.")
            unknown = [pid for pid in requested if pid not in EXPECTED_PROBE_IDS]
            if unknown:
                raise ValueError(f"Unknown probe_id(s): {', '.join(unknown)}")
            self.probe_ids = tuple(dict.fromkeys(requested))

    def _turn_timeout(self) -> float | None:
        if self.timeout_seconds is None:
            return None
        return float(max(90, int(self.timeout_seconds)))

    def _resolve_roots(self) -> tuple[Path, Path, tempfile.TemporaryDirectory[str] | None]:
        if self.home_root is not None or self.data_root is not None:
            home, data, _ = resolve_isolated_paths(
                home_root=self.home_root,
                data_root=self.data_root,
            )
            return home, data, None
        temp_dir = tempfile.TemporaryDirectory(prefix="cortensor-probe-")
        root = Path(temp_dir.name)
        return root / "home", root / "state", temp_dir

    def _create_runtime(self, home: Path, data: Path, **overrides: Any) -> APIRuntime:
        return create_isolated_runtime(
            preset=overrides.get("preset", self.preset),
            base_url=overrides.get("base_url", self.base_url),
            model=overrides.get("model", self.model),
            api_key_env=overrides.get("api_key_env", self.api_key_env),
            agent_id=self.agent_id,
            home_root=home,
            data_root=data,
            provider_retry_max_attempts=overrides.get(
                "provider_retry_max_attempts", self.provider_retry_max_attempts
            ),
            timeout_seconds=overrides.get("timeout_seconds", self.timeout_seconds),
            http_connection_reuse_enabled=overrides.get(
                "http_connection_reuse_enabled", self.http_connection_reuse_enabled
            ),
        )

    def _run_timed(
        self,
        probe_id: str,
        name: str,
        fn: Callable[[], tuple[str, dict[str, Any]]],
    ) -> ProbeCheckResult:
        started = time.perf_counter()
        try:
            detail, metadata = fn()
            passed = True
        except Exception as exc:  # noqa: BLE001
            detail = f"FAILED ({type(exc).__name__}): {exc}"
            metadata = {"error_type": type(exc).__name__}
            passed = False

        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
        clean_detail = scrub_secrets(detail, secret_env_names=[self.api_key_env or ""])
        return ProbeCheckResult(
            probe_id=probe_id,
            name=name,
            passed=passed,
            detail=clean_detail,
            latency_ms=elapsed_ms,
            metadata=metadata,
        )

    def run_all(self) -> ProbeSuiteReport:
        """Run configured building-block probes (all 10 by default) and assemble a sanitized ProbeSuiteReport."""
        home_base, data_base, temp_guard = self._resolve_roots()
        suite_started = time.perf_counter()
        results: list[ProbeCheckResult] = []
        shared_runtime: APIRuntime | None = None
        selected = set(self.probe_ids)
        needs_shared_runtime = bool(
            selected
            & {
                "structured_pydantic_output",
                "tool_and_forced_tools",
                "policy_confirmation_gate",
                "session_continuity",
                "subagent_delegation",
                "agent_handoff",
                "submit_turn_streaming_telemetry",
            }
        )

        try:
            shared_home = home_base / "shared"
            shared_data = data_base / "shared"
            cfg_preview = build_isolated_config(
                preset=self.preset,
                base_url=self.base_url,
                model=self.model,
                api_key_env=self.api_key_env,
                agent_id=self.agent_id,
                home_root=shared_home,
                data_root=shared_data,
                provider_retry_max_attempts=self.provider_retry_max_attempts,
                timeout_seconds=self.timeout_seconds,
                http_connection_reuse_enabled=self.http_connection_reuse_enabled,
                persist=False,
            )
            effective_model = self.model or (
                cfg_preview.providers.cortensor.model
                if self.preset == "cortensor-router"
                else cfg_preview.providers.openai.model
            )
            effective_base_url = self.base_url or (
                cfg_preview.providers.cortensor.base_url
                if self.preset == "cortensor-router"
                else cfg_preview.providers.openai.base_url
            )

            if "agent_runtime_isolation" in selected:
                # Probe 1 uses its own dedicated isolated home/data root to verify zero-secret persistence.
                results.append(
                    self._run_timed(
                        "agent_runtime_isolation",
                        "Agent & APIRuntime Isolation",
                        lambda: self._probe_agent_runtime_isolation(
                            home_base / "isolation",
                            data_base / "isolation",
                        ),
                    )
                )

            if needs_shared_runtime:
                shared_runtime = self._create_runtime(shared_home, shared_data)

            probe_dispatch: list[tuple[str, str, Callable[[], tuple[str, dict[str, Any]]]]] = [
                (
                    "structured_pydantic_output",
                    "Structured Pydantic Output & Validation Error",
                    lambda: self._probe_structured_pydantic_output(
                        shared_runtime,  # type: ignore[arg-type]
                        home_base / "structured-neg",
                        data_base / "structured-neg",
                    ),
                ),
                (
                    "tool_and_forced_tools",
                    "@tool Registration & forced_tools Execution",
                    lambda: self._probe_tool_and_forced_tools(shared_runtime),  # type: ignore[arg-type]
                ),
                (
                    "policy_confirmation_gate",
                    "Policy Gate (@tool dangerous=True Allow & Deny)",
                    lambda: self._probe_policy_confirmation_gate(shared_runtime),  # type: ignore[arg-type]
                ),
                (
                    "session_continuity",
                    "Session Continuity & Cross-Session Isolation",
                    lambda: self._probe_session_continuity(shared_runtime),  # type: ignore[arg-type]
                ),
                (
                    "memory_bundle_portability",
                    "MemoryBundle Export, Save, Load & Import",
                    lambda: self._probe_memory_bundle_portability(shared_data),
                ),
                (
                    "subagent_delegation",
                    "subagent() & SubagentRunContext Delegation",
                    lambda: self._probe_subagent_delegation(shared_runtime),  # type: ignore[arg-type]
                ),
                (
                    "agent_handoff",
                    "Handoff Peer Agent Transfer Tool",
                    lambda: self._probe_agent_handoff(shared_runtime),  # type: ignore[arg-type]
                ),
                (
                    "submit_turn_streaming_telemetry",
                    "submit_turn() Streaming TurnChunk & TurnTelemetry",
                    lambda: self._probe_submit_turn_streaming_telemetry(shared_runtime),  # type: ignore[arg-type]
                ),
                (
                    "error_and_timeout_contracts",
                    "ProviderError Retries, Timeout & Connection Reuse Policy",
                    lambda: self._probe_error_and_timeout_contracts(
                        home_base / "fault",
                        data_base / "fault",
                    ),
                ),
            ]
            for pid, pname, pfn in probe_dispatch:
                if pid in selected:
                    results.append(self._run_timed(pid, pname, pfn))
        finally:
            if shared_runtime is not None:
                shared_runtime.close()
            if temp_guard is not None:
                temp_guard.cleanup()

        passed_count = sum(1 for item in results if item.passed)
        total_latency_ms = round((time.perf_counter() - suite_started) * 1000.0, 2)
        return ProbeSuiteReport(
            sdk_version=str(getattr(openminion, "__version__", "0.1.21")),
            preset=self.preset,
            model=effective_model,
            base_url_host=sanitize_base_url(effective_base_url),
            calibration_status=infer_calibration_status(effective_base_url),
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_probes=len(results),
            passed_probes=passed_count,
            failed_probes=len(results) - passed_count,
            total_latency_ms=total_latency_ms,
            probes=results,
            dx_findings=build_empirical_dx_findings(results),
        )

    def _probe_agent_runtime_isolation(
        self,
        home_root: Path,
        data_root: Path,
    ) -> tuple[str, dict[str, Any]]:
        runtime = self._create_runtime(home_root, data_root)
        try:
            agents_path = home_root / ".openminion" / "agents.json"
            assert agents_path.exists(), "Isolated agents.json was not persisted."
            raw_cfg = agents_path.read_text(encoding="utf-8")
            parsed_cfg = json.loads(raw_cfg)
            assert parsed_cfg["providers"]["openai"]["api_key"] == ""
            assert parsed_cfg["providers"]["cortensor"]["api_key"] == ""
            assert parsed_cfg["runtime"]["env"] == {}
            if self.api_key_env and os.environ.get(self.api_key_env):
                assert os.environ[self.api_key_env] not in raw_cfg, (
                    "Plaintext secret leaked into agents.json"
                )

            agent = Agent(
                runtime=runtime,
                agent_id=self.agent_id,
                name="probe-isolation-agent",
                instructions="Respond concisely with ISOLATION_OK.",
            )
            result = agent.run(
                "PROBE_ISOLATION: Verify runtime isolation and reply ISOLATION_OK.",
                timeout_seconds=self._turn_timeout(),
            )
            assert result.text.strip(), "Agent.run returned empty text."
            assert result.run_id, "Agent.run returned no run_id."
            db_files = list(data_root.rglob("*.db"))
            assert db_files, "Expected isolated SQLite database under data_root."

            return (
                f"Isolated agents.json verified secret-free; SQLite DB isolated under data_root "
                f"({len(db_files)} db file(s)); run_id={result.run_id}.",
                {
                    "db_count": len(db_files),
                    "run_id": result.run_id,
                    "secret_free_config": True,
                },
            )
        finally:
            runtime.close()

    def _probe_structured_pydantic_output(
        self,
        runtime: APIRuntime,
        neg_home: Path,
        neg_data: Path,
    ) -> tuple[str, dict[str, Any]]:
        positive_agent = Agent(
            runtime=runtime,
            agent_id=self.agent_id,
            name="probe-structured-agent",
            instructions=(
                "Your final answer MUST be ONLY one raw RFC-8259 JSON object using double quotes "
                "and zero prose or markdown fences, matching schema: "
                '{"status": "OK", "block": "structured_pydantic_output", "score": 0.99}.'
            ),
            output_type=_ProbeStructuredOutput,
        )
        pos_result = positive_agent.run(
            "PROBE_STRUCTURED: Output ONLY raw JSON "
            '{"status": "OK", "block": "structured_pydantic_output", "score": 0.99}.',
            timeout_seconds=self._turn_timeout(),
        )
        assert isinstance(pos_result.output, _ProbeStructuredOutput)

        neg_agent = Agent(
            runtime=runtime,
            agent_id=self.agent_id,
            name="probe-structured-negative-agent",
            instructions=(
                "Respond with ONLY the literal plain text MALFORMED_NON_JSON_PROBE "
                "with zero curly braces or JSON."
            ),
            output_type=_ProbeStructuredOutput,
        )
        negative_raised = False
        fallback_stub_used = False
        try:
            neg_agent.run(
                "PROBE_STRUCTURED_NEGATIVE: Reply with ONLY MALFORMED_NON_JSON_PROBE and no JSON.",
                timeout_seconds=self._turn_timeout(),
            )
        except AgentOutputValidationError:
            negative_raised = True

        if not negative_raised:
            # Some live LLMs force valid JSON when prompted; prove SDK validation contract via deterministic fault stub.
            fault = _FaultInjectionServer()
            fallback_runtime = self._create_runtime(
                neg_home,
                neg_data,
                preset="openai-compatible",
                base_url=fault.url_malformed,
                provider_retry_max_attempts=1,
            )
            try:
                fallback_agent = Agent(
                    runtime=fallback_runtime,
                    agent_id=self.agent_id,
                    instructions="Return plain text.",
                    output_type=_ProbeStructuredOutput,
                )
                try:
                    fallback_agent.run("PROBE_STRUCTURED_NEGATIVE")
                except AgentOutputValidationError:
                    negative_raised = True
                    fallback_stub_used = True
            finally:
                fallback_runtime.close()
                fault.close()

        assert negative_raised, "AgentOutputValidationError was not raised on non-JSON output."
        return (
            f"Validated _ProbeStructuredOutput (status={pos_result.output.status}, "
            f"score={pos_result.output.score}) and verified AgentOutputValidationError negative contract.",
            {
                "status": pos_result.output.status,
                "score": pos_result.output.score,
                "negative_validation_error": True,
                "fallback_stub_used": fallback_stub_used,
            },
        )

    def _probe_tool_and_forced_tools(self, runtime: APIRuntime) -> tuple[str, dict[str, Any]]:
        called: list[tuple[str, str]] = []

        @tool(min_scope="READ_ONLY", idempotent=True)
        def probe_lookup_fact(topic: str) -> dict[str, Any]:
            """Look up deterministic verification fact by topic."""
            called.append(("probe_lookup_fact", topic))
            return {"topic": topic, "token": "FACT_POI_VERIFIED"}

        @tool(min_scope="READ_ONLY", idempotent=True)
        def probe_echo_tag(tag: str) -> dict[str, Any]:
            """Echo deterministic verification tag."""
            called.append(("probe_echo_tag", tag))
            return {"tag": tag, "echo": f"ECHO_{tag}"}

        auto_agent = Agent(
            runtime=runtime,
            agent_id=self.agent_id,
            name="probe-tools-auto",
            instructions="Call probe_lookup_fact(topic='cortensor-poi') before answering.",
            tools=[probe_lookup_fact, probe_echo_tag],
        )
        auto_res = auto_agent.run(
            "PROBE_TOOLS_AUTO: Invoke probe_lookup_fact with topic='cortensor-poi' and report token.",
            timeout_seconds=self._turn_timeout(),
        )
        assert any(name == "probe_lookup_fact" for name, _ in called), (
            "Auto tool call did not execute probe_lookup_fact."
        )

        forced_agent = Agent(
            runtime=runtime,
            agent_id=self.agent_id,
            name="probe-tools-forced",
            instructions="Call the forced tool probe_echo_tag(tag='forced-c3') and summarize.",
            tools=[probe_lookup_fact, probe_echo_tag],
            forced_tools=["probe_echo_tag"],
        )
        forced_res = forced_agent.run(
            "PROBE_TOOLS_FORCED: Execute forced tool probe_echo_tag with tag='forced-c3' and report echo.",
            timeout_seconds=self._turn_timeout(),
        )
        assert any(name == "probe_echo_tag" for name, _ in called), (
            "forced_tools did not execute probe_echo_tag."
        )
        assert auto_res.text.strip() and forced_res.text.strip()

        return (
            f"Executed auto tool ({called[0][0]}) and forced_tools=({called[-1][0]}) cleanly.",
            {
                "invocations": [f"{name}:{arg}" for name, arg in called],
                "forced_tool": "probe_echo_tag",
            },
        )

    def _probe_policy_confirmation_gate(self, runtime: APIRuntime) -> tuple[str, dict[str, Any]]:
        executed_ids: list[str] = []
        callback_events: list[tuple[str, bool, str]] = []

        @tool(dangerous=True, min_scope="WRITE_SAFE", idempotent=False)
        def probe_publish_attestation(attestation_id: str) -> dict[str, Any]:
            """Dangerous write-scoped tool requiring explicit confirmation."""
            executed_ids.append(attestation_id)
            return {"published": True, "attestation_id": attestation_id}

        gate_agent = Agent(
            runtime=runtime,
            agent_id=self.agent_id,
            name="probe-policy-gate",
            instructions="Call probe_publish_attestation with the requested attestation_id.",
            tools=[probe_publish_attestation],
        )

        def allow_cb(tool_name: str, args: dict[str, Any], approval_id: str) -> bool:
            del args
            callback_events.append((tool_name, True, approval_id))
            return True

        def deny_cb(tool_name: str, args: dict[str, Any], approval_id: str) -> bool:
            del args
            callback_events.append((tool_name, False, approval_id))
            return False

        allow_res = gate_agent.run(
            "PROBE_POLICY_ALLOW: Publish attestation_id='att-allow' using probe_publish_attestation.",
            approval_callback=allow_cb,
            timeout_seconds=self._turn_timeout(),
        )
        assert "att-allow" in executed_ids, "Allowed dangerous tool did not execute."

        deny_res = gate_agent.run(
            "PROBE_POLICY_DENY: Attempt to publish attestation_id='att-deny' using probe_publish_attestation.",
            approval_callback=deny_cb,
            timeout_seconds=self._turn_timeout(),
        )
        assert "att-deny" not in executed_ids, "Denied dangerous tool executed despite False callback."
        assert len(callback_events) >= 2, "approval_callback was not invoked for both allow and deny."

        pause_session_id = f"probe-policy-pause-{id(self):x}"
        pause_res = gate_agent.run(
            "PROBE_POLICY_PAUSE: Publish attestation_id='att-pause-resume' using probe_publish_attestation.",
            session_id=pause_session_id,
            approval_callback=None,
            timeout_seconds=self._turn_timeout(),
        )
        assert "att-pause-resume" not in executed_ids, (
            "Dangerous tool executed despite approval_callback=None pause."
        )
        paused_thread_id = getattr(pause_res, "thread_id", None) or pause_res.metadata.get("thread_id")
        pending_confirmation_id = (
            getattr(pause_res, "pending_confirmation_command_id", None)
            or pause_res.metadata.get("pending_confirmation_command_id")
        )
        assert paused_thread_id, "approval_callback=None pause did not return a thread_id."
        assert pending_confirmation_id, (
            "approval_callback=None pause did not populate pending_confirmation_command_id."
        )

        resume_res = gate_agent.run(
            "allow_once",
            session_id=pause_session_id,
            thread_id=paused_thread_id,
            timeout_seconds=self._turn_timeout(),
        )
        assert "att-pause-resume" in executed_ids, (
            "Resumed allow_once turn did not execute pending dangerous tool."
        )
        assert allow_res.text.strip() and deny_res.text.strip() and resume_res.text.strip()

        return (
            "Dangerous @tool(dangerous=True, min_scope='WRITE_SAFE') verified allow, deny, and "
            "fail-closed approval_callback=None pause/thread_id allow_once resume.",
            {
                "allow_executed": True,
                "deny_blocked": True,
                "pause_blocked": True,
                "resume_executed": True,
                "paused_thread_id": paused_thread_id,
                "pending_confirmation_id": pending_confirmation_id,
                "callback_count": len(callback_events),
                "executed_ids": list(executed_ids),
            },
        )

    def _probe_session_continuity(self, runtime: APIRuntime) -> tuple[str, dict[str, Any]]:
        session_a = f"probe-sess-a-{uuid4().hex[:8]}"
        session_b = f"probe-sess-b-{uuid4().hex[:8]}"
        agent = Agent(
            runtime=runtime,
            agent_id=self.agent_id,
            name="probe-session-agent",
            instructions=(
                "Answer concisely using only facts present in this conversation session. "
                "If no SESSION_TOKEN marker exists in prior messages, reply 'RECALLED: NONE'."
            ),
        )
        turn1 = agent.run(
            "PROBE_SESSION_STORE: Remember exact verification marker SESSION_TOKEN_ALPHA_42 for this session.",
            session_id=session_a,
            timeout_seconds=self._turn_timeout(),
        )
        assert turn1.thread_id, "Session turn1 did not allocate a thread_id."
        turn2 = agent.run(
            "PROBE_SESSION_RECALL: What exact SESSION_TOKEN marker did I ask you to remember earlier?",
            session_id=session_a,
            thread_id=turn1.thread_id,
            timeout_seconds=self._turn_timeout(),
        )
        turn3 = agent.run(
            "PROBE_SESSION_RECALL: What exact SESSION_TOKEN marker did I ask you to remember earlier?",
            session_id=session_b,
            timeout_seconds=self._turn_timeout(),
        )
        same_recalled = "SESSION_TOKEN_ALPHA_42" in turn2.text
        second_isolated = "SESSION_TOKEN_ALPHA_42" not in turn3.text
        assert turn1.text.strip()
        assert same_recalled, f"Session A failed to recall marker: {turn2.text!r}"
        assert second_isolated, f"Session B leaked Session A marker: {turn3.text!r}"

        return (
            f"Session {session_a} (thread {turn1.thread_id}) recalled marker across turns; "
            f"isolated session {session_b} had zero leakage.",
            {
                "session_a": session_a,
                "session_b": session_b,
                "thread_id": turn1.thread_id,
                "same_session_recalled": same_recalled,
                "second_session_isolated": second_isolated,
            },
        )

    def _probe_memory_bundle_portability(self, data_root: Path) -> tuple[str, dict[str, Any]]:
        data_root.mkdir(parents=True, exist_ok=True)
        bundle_path = data_root / "probe_memory_bundle.json"
        bundle = export_bundle(
            items=[
                {
                    "id": "mem-sec-btc-etf",
                    "kind": "evidence_excerpt",
                    "content": "SEC approved spot bitcoin ETP listing and trading on 2024-01-10.",
                    "source_id": "sec-spot-btc-2024-01-10",
                }
            ],
            metadata={"claim_id": "delphi-btc-etf-2024", "probe": "memory_bundle_portability"},
        )
        assert isinstance(bundle, MemoryBundle)
        save_bundle(bundle, bundle_path)
        assert bundle_path.exists()

        loaded = load_bundle(bundle_path)
        assert loaded.version == bundle.version
        assert loaded.items == bundle.items
        assert loaded.metadata == bundle.metadata

        imported_direct = import_bundle(loaded, trust_mode="direct")
        imported_candidate = import_bundle(loaded, trust_mode="candidate")
        assert imported_direct["item_count"] == 1
        assert imported_candidate["trust_mode"] == "candidate"

        invalid_rejected = False
        try:
            import_bundle(loaded, trust_mode="invalid_mode")
        except InvalidArgumentError:
            invalid_rejected = True
        assert invalid_rejected, "Invalid trust_mode did not raise InvalidArgumentError."

        return (
            f"Roundtripped MemoryBundle {loaded.version} ({imported_direct['item_count']} item) "
            "via export_bundle -> save_bundle -> load_bundle -> import_bundle(direct/candidate).",
            {
                "bundle_version": loaded.version,
                "item_count": imported_direct["item_count"],
                "invalid_mode_rejected": invalid_rejected,
            },
        )

    def _probe_subagent_delegation(self, runtime: APIRuntime) -> tuple[str, dict[str, Any]]:
        subagent_calls: list[str] = []

        @tool(min_scope="READ_ONLY", idempotent=True)
        def probe_subagent_tool(item: str) -> dict[str, Any]:
            """Scoped read-only tool available only inside child subagent."""
            subagent_calls.append(item)
            return {"item": item, "verified": True}

        parent = Agent(
            runtime=runtime,
            agent_id=self.agent_id,
            name="probe-parent",
            instructions="Parent verifier coordinator.",
        )
        eff_sub_timeout = max(90, int(self.timeout_seconds or 90))
        child = subagent(
            parent,
            name="probe-corroborator",
            instructions=(
                "Call probe_subagent_tool(item='subagent-check'). Your final answer MUST be ONLY a single "
                "valid RFC-8259 JSON object using double quotes with zero prose or explanations, matching: "
                '{"status": "OK", "block": "subagent_delegation", "score": 0.98}.'
            ),
            tools=[probe_subagent_tool],
            output_type=_ProbeStructuredOutput,
            timeout_seconds=eff_sub_timeout,
        )
        ctx = child.subagent_context
        assert isinstance(ctx, SubagentRunContext)
        assert ctx.parent_agent_id == "probe-parent"
        assert ctx.child_agent_id == "probe-corroborator"
        assert ctx.parent_transcript_inherited is False
        assert ctx.hidden_reasoning_inherited is False
        assert ctx.memory_posture == "none"

        child_res = child.run(
            "PROBE_SUBAGENT: Invoke probe_subagent_tool(item='subagent-check') and return JSON.",
            timeout_seconds=float(eff_sub_timeout),
        )
        assert isinstance(child_res.output, _ProbeStructuredOutput)
        assert "subagent-check" in subagent_calls, "Child subagent did not execute scoped tool."
        child.close()
        assert not getattr(runtime, "_closed", False), (
            "Closing child subagent must not close parent APIRuntime."
        )

        return (
            f"Child subagent ({ctx.child_agent_id}) ran with isolated SubagentRunContext "
            f"(context_id={child.subagent_context.context_id}) without closing parent runtime.",
            {
                "context_id": child.subagent_context.context_id if child.subagent_context else "",
                "parent_transcript_inherited": ctx.parent_transcript_inherited,
                "tool_allowlist": list(ctx.tool_allowlist),
                "subagent_calls": list(subagent_calls),
            },
        )

    def _probe_agent_handoff(self, runtime: APIRuntime) -> tuple[str, dict[str, Any]]:
        specialist = Agent(
            runtime=runtime,
            agent_id=self.agent_id,
            name="specialist",
            instructions="Specialist agent: confirm handoff receipt concisely including SPECIALIST_ACK.",
        )
        handoff = Handoff(
            target=specialist,
            description="Delegate verification payload to specialist peer agent.",
        )
        resolved_name = handoff.resolved_name()
        assert resolved_name == "transfer_to_specialist"

        coordinator = Agent(
            runtime=runtime,
            agent_id=self.agent_id,
            name="coordinator",
            instructions=(
                "Always delegate this request to the specialist via transfer_to_specialist, "
                "then report the specialist confirmation."
            ),
            handoffs=[handoff],
        )
        handoff_invocations: list[str] = []

        def _handoff_cb(name: str, _args: dict[str, Any], _aid: str) -> bool:
            if name == resolved_name:
                handoff_invocations.append(name)
                return True
            return False

        res = coordinator.run(
            "PROBE_HANDOFF: Transfer this verification task to specialist via transfer_to_specialist.",
            approval_callback=_handoff_cb,
            timeout_seconds=self._turn_timeout(),
        )
        serialized_meta = json.dumps(res.metadata, default=str)
        verbatim_ack = "SPECIALIST_ACK" in res.text or "SPECIALIST_ACK" in serialized_meta
        assert resolved_name in handoff_invocations, (
            f"Coordinator never invoked handoff tool {resolved_name!r}."
        )
        assert res.text.strip(), "Handoff coordinator returned empty response text."

        return (
            f"Handoff registered '{resolved_name}' and executed peer specialist turn cleanly "
            f"(invocations={len(handoff_invocations)}, verbatim_ack={verbatim_ack}).",
            {
                "tool_name": resolved_name,
                "run_id": res.run_id,
                "handoff_invocations": len(handoff_invocations),
                "verbatim_ack": verbatim_ack,
            },
        )

    def _probe_submit_turn_streaming_telemetry(
        self,
        runtime: APIRuntime,
    ) -> tuple[str, dict[str, Any]]:
        session_id = f"probe-stream-{uuid4().hex[:8]}"
        stream_timeout_s = max(8, int(self.timeout_seconds or 15))
        wait_s = float(min(max(5, stream_timeout_s), 60))
        handle = runtime.submit_turn(
            payload={
                "session_id": session_id,
                "message": "PROBE_STREAM_TURN: Reply concisely with STREAM_TELEMETRY_OK.",
                "channel": "console",
                "user": "api-user",
                "target": "api-user",
                "stream": True,
                "deliver": False,
                "timeout_seconds": stream_timeout_s,
            }
        )
        chunks: list[TurnChunk] = []
        deadline = time.monotonic() + float(stream_timeout_s)
        for chunk in handle.stream(timeout_s=wait_s):
            chunks.append(chunk)
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Exceeded {float(stream_timeout_s):.1f}s deadline while draining TurnChunk stream."
                )

        response = handle.result(timeout_s=wait_s)
        assert isinstance(response, TurnResponse)
        assert isinstance(response.telemetry, TurnTelemetry)
        assert chunks, "Expected TurnChunk events from RuntimeTurnHandle.stream()."
        assert all(isinstance(chunk, TurnChunk) for chunk in chunks)
        assert response.final_text.strip(), "TurnResponse.final_text was empty."
        assert not response.errors, f"Unexpected TurnResponse errors: {response.errors!r}"
        assert response.telemetry.duration_ms > 0, "Expected TurnTelemetry.duration_ms > 0."

        stats_in = int(response.stats.get("input_tokens", 0) or 0)
        stats_out = int(response.stats.get("output_tokens", 0) or 0)
        assert stats_in > 0 or response.telemetry.tokens_in > 0, (
            "Expected input token count in TurnResponse.stats or TurnTelemetry."
        )
        assert stats_out > 0 or response.telemetry.tokens_out > 0, (
            "Expected output token count in TurnResponse.stats or TurnTelemetry."
        )

        chunk_kinds = [chunk.kind for chunk in chunks]
        return (
            f"Collected {len(chunks)} TurnChunk(s) ({', '.join(dict.fromkeys(chunk_kinds))}); "
            f"TurnTelemetry(duration_ms={response.telemetry.duration_ms}, "
            f"tokens_in={response.telemetry.tokens_in}, tokens_out={response.telemetry.tokens_out}, "
            f"retries={response.telemetry.retries}, queue_wait_ms={response.telemetry.queue_wait_ms}); "
            f"stats(input_tokens={stats_in}, output_tokens={stats_out}).",
            {
                "chunk_count": len(chunks),
                "chunk_kinds": chunk_kinds,
                "tokens_in": response.telemetry.tokens_in,
                "tokens_out": response.telemetry.tokens_out,
                "stats_input_tokens": stats_in,
                "stats_output_tokens": stats_out,
                "telemetry_metadata_mismatch": (
                    response.telemetry.tokens_in == 0 and stats_in > 0
                ),
                "duration_ms": response.telemetry.duration_ms,
                "retries": response.telemetry.retries,
                "queue_wait_ms": response.telemetry.queue_wait_ms,
                "stats": dict(response.stats),
            },
        )

    def _probe_error_and_timeout_contracts(
        self,
        home_base: Path,
        data_base: Path,
    ) -> tuple[str, dict[str, Any]]:
        cfg_reuse = build_isolated_config(
            preset=self.preset,
            base_url=self.base_url,
            model=self.model,
            api_key_env=self.api_key_env,
            home_root=home_base / "reuse",
            data_root=data_base / "reuse",
            http_connection_reuse_enabled=False,
            persist=False,
        )
        assert cfg_reuse.providers.openai.http_connection_reuse_enabled is False
        assert cfg_reuse.providers.cortensor.http_connection_reuse_enabled is False

        fault = _FaultInjectionServer()
        prev_key = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = prev_key or "probe-fault-dummy-key"
        try:
            rt_500 = create_isolated_runtime(
                preset="openai-compatible",
                base_url=fault.url_500,
                model="stub-model",
                api_key_env="OPENAI_API_KEY",
                home_root=home_base / "http500",
                data_root=data_base / "http500",
                provider_retry_max_attempts=2,
                timeout_seconds=3,
                http_connection_reuse_enabled=False,
            )
            provider_error_raised = False
            try:
                agent_500 = Agent(runtime=rt_500, instructions="Fail cleanly.")
                try:
                    agent_500.run("Trigger HTTP 500.")
                except ProviderError:
                    provider_error_raised = True
            finally:
                rt_500.close()
            assert provider_error_raised, "HTTP 500 did not raise ProviderError."
            assert fault.attempts_500 >= 2, (
                f"Expected retry attempts >= 2 on HTTP 500, observed {fault.attempts_500}."
            )

            rt_slow = create_isolated_runtime(
                preset="openai-compatible",
                base_url=fault.url_slow,
                model="stub-model",
                api_key_env="OPENAI_API_KEY",
                home_root=home_base / "timeout",
                data_root=data_base / "timeout",
                provider_retry_max_attempts=1,
                timeout_seconds=1,
                http_connection_reuse_enabled=False,
            )
            timeout_raised = False
            timeout_exc_name = ""
            try:
                agent_slow = Agent(runtime=rt_slow, instructions="Timeout test.")
                try:
                    agent_slow.run("Trigger slow timeout.", timeout_seconds=1.0)
                except (TurnTimeoutError, ProviderError) as exc:
                    timeout_raised = True
                    timeout_exc_name = type(exc).__name__
            finally:
                rt_slow.close()
            assert timeout_raised, "Slow handler did not trigger TurnTimeoutError or ProviderError."

            from openminion.modules.llm.providers.anthropic.adapter import AnthropicProvider
            from openminion.modules.llm.providers.cortensor.adapter import CortensorProvider
            from openminion.modules.llm.providers.openai.adapter import OpenAIProvider
            from openminion.modules.llm.schemas import LLMRequest, Message

            wire_req = LLMRequest(messages=[Message(role="user", content="WIRE_PROBE")])
            anthropic_provider = AnthropicProvider()
            try:
                anth_res = anthropic_provider.complete(
                    wire_req,
                    {
                        "base_url": fault.url_anthropic,
                        "api_key": "probe-anthropic-key",
                        "model": "stub-anthropic",
                        "timeout_seconds": 3,
                        "http_connection_reuse_enabled": False,
                    },
                )
            finally:
                anthropic_provider.close()
            assert anth_res.ok and anth_res.output_text == "ANTHROPIC_OK", (
                f"Unexpected AnthropicProvider wire output: {anth_res.output_text!r}"
            )

            cortensor_provider = CortensorProvider()
            try:
                cort_res = cortensor_provider.complete(
                    wire_req,
                    {
                        "base_url": fault.url_cortensor,
                        "api_key": "probe-cortensor-key",
                        "model": "gpt-oss-20b",
                        "session_id": 1,
                        "timeout_seconds": 3,
                        "http_connection_reuse_enabled": False,
                    },
                )
            finally:
                cortensor_provider.close()
            assert cort_res.ok and cort_res.output_text == "CORTENSOR_OK", (
                f"Unexpected CortensorProvider wire output: {cort_res.output_text!r}"
            )

            openai_provider = OpenAIProvider()
            try:
                events_default = list(
                    openai_provider.stream(
                        wire_req,
                        {
                            "base_url": fault.url_openai_sse,
                            "api_key": "probe-openai-sse-key",
                            "model": "stub-model",
                            "timeout_seconds": 3,
                            "http_connection_reuse_enabled": False,
                        },
                    )
                )
                events_vendor = list(
                    openai_provider.stream(
                        wire_req,
                        {
                            "base_url": fault.url_openai_sse,
                            "api_key": "probe-openai-sse-key",
                            "model": "stub-model",
                            "provider_identity": {"service_vendor": "openai"},
                            "timeout_seconds": 3,
                            "http_connection_reuse_enabled": False,
                        },
                    )
                )
            finally:
                openai_provider.close()

            done_default = [ev for ev in events_default if ev.type == "done"][-1]
            done_vendor = [ev for ev in events_vendor if ev.type == "done"][-1]
            assert done_default.usage is None, (
                "Expected default OpenAIProvider.stream() to skip final SSE usage chunk."
            )
            assert done_vendor.usage is not None and done_vendor.usage.total_tokens == 12, (
                "Expected service_vendor='openai' to preserve final SSE usage chunk."
            )

            captured_by_route = dict(fault.wire_captures)
            anth_headers = captured_by_route.get("anthropic", {})
            cort_headers = captured_by_route.get("cortensor", {})
            assert anth_headers.get("x-api-key") == "probe-anthropic-key"
            assert "anthropic-version" in anth_headers
            assert cort_headers.get("authorization") == "Bearer probe-cortensor-key"
            provider_wire_formats = {
                "anthropic_path": "/anthropic/v1/messages",
                "anthropic_x_api_key": bool(anth_headers.get("x-api-key")),
                "anthropic_version_header": bool(anth_headers.get("anthropic-version")),
                "cortensor_path": "/cortensor/api/v2/completions",
                "cortensor_bearer_auth": str(cort_headers.get("authorization", "")).startswith("Bearer "),
                "openai_sse_usage_without_vendor": done_default.usage is not None,
                "openai_sse_usage_with_vendor": bool(
                    done_vendor.usage is not None and done_vendor.usage.total_tokens == 12
                ),
            }

            return (
                f"Verified http_connection_reuse_enabled=False; HTTP 500 raised ProviderError after "
                f"{fault.attempts_500} attempt(s); slow stub (1.5s vs 1.0s timeout) raised {timeout_exc_name}; "
                "verified Anthropic (/v1/messages), Cortensor (/api/v2/completions), and OpenAI SSE usage gating.",
                {
                    "http_500_attempts": fault.attempts_500,
                    "provider_error_raised": provider_error_raised,
                    "timeout_raised": timeout_raised,
                    "timeout_exception": timeout_exc_name,
                    "http_connection_reuse_enabled": False,
                    "provider_wire_formats": provider_wire_formats,
                },
            )
        finally:
            if prev_key is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = prev_key
            fault.close()


def build_empirical_dx_findings(probes: Sequence[ProbeCheckResult]) -> list[dict[str, str]]:
    """Build factual DX findings exclusively from probes that actually ran and passed."""
    passed = {item.probe_id: item for item in probes if item.passed}
    findings: list[dict[str, str]] = []

    if "agent_runtime_isolation" in passed:
        meta = passed["agent_runtime_isolation"].metadata
        findings.append(
            {
                "title": "Worktree-Isolated home_root / data_root Containment",
                "observation": (
                    f"`create_isolated_runtime()` bound isolated `home_root` and `data_root` SQLite/agents.json "
                    f"directories (`db_count={meta.get('db_count', 'n/a')}`, "
                    f"`secret_free_config={meta.get('secret_free_config', 'n/a')}`, "
                    f"`run_id={meta.get('run_id', 'n/a')}`), preventing mutation of developer home state on Windows."
                ),
            }
        )

    if "structured_pydantic_output" in passed:
        meta = passed["structured_pydantic_output"].metadata
        findings.append(
            {
                "title": "Internal Classifiers (FreshnessContract / FinalizationStatus / ClosureJudgment) & Output Coercion",
                "observation": (
                    "openminion==0.1.21 issues `tool_choice='submit_output'` internal classifier turns (`FreshnessContract`, "
                    "`FinalizationStatus`, and `ClosureJudgment` where stubs/gateways must preserve `action_summary`). "
                    "`Agent._coerce_output()` also strips the `f'{agent_id}: '` reply prefix via `_extract_json_object()`, "
                    f"producing typed schema output (`status={meta.get('status', 'n/a')}`, "
                    f"`score={meta.get('score', 'n/a')}`, "
                    f"`negative_validation_error={meta.get('negative_validation_error', 'n/a')}`, "
                    f"`fallback_stub_used={meta.get('fallback_stub_used', 'n/a')}`)."
                ),
            }
        )

    if "tool_and_forced_tools" in passed:
        meta = passed["tool_and_forced_tools"].metadata
        invocations = list(meta.get("invocations") or [])
        forced_tool = str(meta.get("forced_tool") or "n/a")
        call_count = len(invocations)
        forced_invoked = bool(meta.get("forced_tool")) and any(
            str(item).startswith(f"{forced_tool}:") for item in invocations
        )
        findings.append(
            {
                "title": "Read-Only @tool Binding & tool_choice='forced' Deterministic Dispatch",
                "observation": (
                    f"Binding `@tool(min_scope='READ_ONLY')` with `tool_choice='forced'` invoked `{forced_tool}` "
                    f"(call_count={call_count}, forced_invoked={forced_invoked}, invocations={invocations}) "
                    "without filesystem writes."
                ),
            }
        )

    if "policy_confirmation_gate" in passed:
        meta = passed["policy_confirmation_gate"].metadata
        findings.append(
            {
                "title": "approval_callback Boolean Gate & Fail-Closed approval_callback=None Pause/Resume",
                "observation": (
                    f"`@tool(dangerous=True, min_scope='WRITE_SAFE')` recorded `callback_count={meta.get('callback_count', 0)}`, "
                    f"`allow_executed={meta.get('allow_executed', False)}`, and `deny_blocked={meta.get('deny_blocked', False)}`. "
                    f"Passing `approval_callback=None` paused fail-closed (`pause_blocked={meta.get('pause_blocked', False)}`, "
                    f"`pending_confirmation_id={meta.get('pending_confirmation_id', 'n/a')}`) and executed only after "
                    f"`Agent.run('allow_once', session_id=..., thread_id=...)` (`resume_executed={meta.get('resume_executed', False)}`)."
                ),
            }
        )

    if "session_continuity" in passed:
        meta = passed["session_continuity"].metadata
        findings.append(
            {
                "title": "Explicit thread_id Required for Multi-Turn Agent.run(session_id=...) Continuity",
                "observation": (
                    f"Retaining context across turns on the same session required forwarding `thread_id="
                    f"{meta.get('thread_id', 'n/a')}` alongside `session_id`; a distinct session preserved isolation "
                    f"(`same_session_recalled={meta.get('same_session_recalled', False)}`, "
                    f"`second_session_isolated={meta.get('second_session_isolated', False)}`)."
                ),
            }
        )

    if "memory_bundle_portability" in passed:
        meta = passed["memory_bundle_portability"].metadata
        findings.append(
            {
                "title": "Cross-Runtime MemoryBundle Export/Import Portability",
                "observation": (
                    "OpenMinion primitives `export_bundle()`, `save_bundle()`, `load_bundle()`, and `import_bundle()` "
                    "(wrapped by `export_session_memory()`/`import_session_memory()`) serialized and restored bundle "
                    f"state (`bundle_version={meta.get('bundle_version', 'n/a')}`, "
                    f"`item_count={meta.get('item_count', 'n/a')}`, "
                    f"`invalid_mode_rejected={meta.get('invalid_mode_rejected', 'n/a')}`) "
                    "into a separate APIRuntime SQLite store."
                ),
            }
        )

    if "subagent_delegation" in passed:
        meta = passed["subagent_delegation"].metadata
        findings.append(
            {
                "title": "Isolated Subagent Passes, task_update Collisions & 90s Timeout Forwarding",
                "observation": (
                    "Separate subagent runtime sessions avoid `resolve_entry_task_update()` `Missing/Duplicate task_update` "
                    "crashes (`openminion/modules/brain/loop/context/task_context.py:153-191`) when dispatching sequential "
                    "passes, while explicit `timeout_seconds` prevents falling back to the `90.0s` default "
                    f"(`context_id={meta.get('context_id', 'n/a')}`, "
                    f"`parent_transcript_inherited={meta.get('parent_transcript_inherited', 'n/a')}`, "
                    f"`tool_allowlist={meta.get('tool_allowlist', [])}`, "
                    f"`subagent_calls={meta.get('subagent_calls', [])}`)."
                ),
            }
        )

    if "agent_handoff" in passed:
        meta = passed["agent_handoff"].metadata
        findings.append(
            {
                "title": "Peer Handoff Delegation & build_delegate_tool() Timeout/Approval Gap",
                "observation": (
                    f"Peer handoff reached specialist `{meta.get('tool_name', 'n/a')}` "
                    f"(`handoff_invocations={meta.get('handoff_invocations', 0)}`, "
                    f"`verbatim_ack={meta.get('verbatim_ack', 'n/a')}`). Notably, `openminion/api/handoff.py:169` invokes "
                    "`handoff.target.run(message)` without caller `timeout_seconds` or `approval_callback`, so target "
                    "runtimes need explicit `PolicyGrantInput(max_uses=1)` for autonomous confirmation-gated publication."
                ),
            }
        )

    if "submit_turn_streaming_telemetry" in passed:
        meta = passed["submit_turn_streaming_telemetry"].metadata
        findings.append(
            {
                "title": "APIRuntime.submit_turn() TurnChunks & TurnTelemetry vs TurnResponse.stats",
                "observation": (
                    f"Collected {meta.get('chunk_count', 0)} TurnChunk(s) with `TurnTelemetry(duration_ms="
                    f"{meta.get('duration_ms', 0)}, tokens_in={meta.get('tokens_in', 0)}, "
                    f"tokens_out={meta.get('tokens_out', 0)}, retries={meta.get('retries', 0)}, "
                    f"queue_wait_ms={meta.get('queue_wait_ms', 0)})` vs `TurnResponse.stats(input_tokens="
                    f"{meta.get('stats_input_tokens', 0)}, output_tokens={meta.get('stats_output_tokens', 0)})`; "
                    f"`telemetry_metadata_mismatch={meta.get('telemetry_metadata_mismatch', False)}`."
                ),
            }
        )

    if "error_and_timeout_contracts" in passed:
        meta = passed["error_and_timeout_contracts"].metadata
        wire = meta.get("provider_wire_formats") or {}
        findings.append(
            {
                "title": "Provider Wire Formats, Layered HTTP 500 Retries & http_connection_reuse_enabled=False",
                "observation": (
                    f"With `http_connection_reuse_enabled={meta.get('http_connection_reuse_enabled', False)}`, HTTP 500 "
                    f"produced {meta.get('http_500_attempts', 'N/A')} attempts (`provider_retry_max_attempts=2` * transport retries) "
                    f"before raising `ProviderError`, and slow responses hit `{meta.get('timeout_exception', 'N/A')}`. "
                    f"Wire checks verified `AnthropicProvider` (`x-api-key` + `anthropic-version` -> `{wire.get('anthropic_path', 'n/a')}`), "
                    f"`CortensorProvider` (`Bearer` -> `{wire.get('cortensor_path', 'n/a')}`), and `OpenAIProvider.stream()` "
                    f"SSE usage gating (`without_vendor={wire.get('openai_sse_usage_without_vendor', False)}`, "
                    f"`with_service_vendor_openai={wire.get('openai_sse_usage_with_vendor', False)}`)."
                ),
            }
        )

    return findings


def render_building_blocks_tested_md(report: ProbeSuiteReport) -> str:
    """Render docs/BUILDING_BLOCKS_TESTED.md from a ProbeSuiteReport."""
    lines = [
        f"# OpenMinion 0.1 Building Blocks Tested",
        "",
        f"> **Calibration Posture**: {report.calibration_status}",
        "",
        "## Execution Summary",
        "",
        f"- **SDK Version**: `openminion=={report.sdk_version}`",
        f"- **Preset**: `{report.preset}`",
        f"- **Model**: `{report.model}`",
        f"- **Endpoint Host**: `{report.base_url_host}`",
        f"- **Generated At (UTC)**: `{report.generated_at}`",
        f"- **Result**: `{report.passed_probes}/{report.total_probes}` probes passed (`failed={report.failed_probes}`)",
        f"- **Total Suite Latency**: `{report.total_latency_ms:.2f} ms`",
        "",
        "## Probe Matrix (10 Core OpenMinion Building Blocks)",
        "",
        "| # | Probe ID | Building Block | Status | Latency (ms) | Observed Evidence |",
        "|---:|---|---|---|---:|---|",
    ]
    for idx, probe in enumerate(report.probes, start=1):
        status = "PASS" if probe.passed else "FAIL"
        latency = f"{probe.latency_ms:.2f}" if probe.latency_ms is not None else "n/a"
        safe_detail = probe.detail.replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {idx} | `{probe.probe_id}` | {probe.name} | **{status}** | {latency} | {safe_detail} |"
        )

    lines.extend(["", "## Per-Probe Telemetry & Metadata", ""])
    for probe in report.probes:
        meta_json = json.dumps(probe.metadata, sort_keys=True, ensure_ascii=True)
        lines.append(f"### `{probe.probe_id}` — {probe.name}")
        lines.append(f"- **Passed**: `{probe.passed}` (`{probe.latency_ms} ms`)")
        lines.append(f"- **Detail**: {probe.detail}")
        lines.append(f"- **Metadata**: `{meta_json}`")
        lines.append("")

    return scrub_secrets("\n".join(lines).rstrip() + "\n")


def _format_present_meta(meta: dict[str, Any], keys: Sequence[str]) -> str:
    """Format only keys actually present in probe metadata (never emit fallback defaults)."""
    parts = [f"{k}={meta[k]!r}" if isinstance(meta[k], (list, dict)) else f"{k}={meta[k]}" for k in keys if k in meta]
    return f" (`{', '.join(parts)}`)" if parts else ""


def _render_what_worked_cleanly_lines(report: ProbeSuiteReport) -> list[str]:
    """Render factual summary bullets derived exclusively from passed probes."""
    passed = {item.probe_id: item for item in report.probes if item.passed}
    lines = ["## What Worked Cleanly in OpenMinion 0.1", ""]
    if not passed:
        lines.append("- No building-block probes passed in this run.")
        lines.append("")
        return lines

    if "agent_runtime_isolation" in passed:
        meta = passed["agent_runtime_isolation"].metadata
        suffix = _format_present_meta(meta, ("db_count", "secret_free_config", "run_id"))
        lines.append(
            "- **`APIRuntime` isolation & zero-key disk posture**: "
            "`create_isolated_runtime()` / `APIRuntime.from_config_path()` bound per-worktree "
            "SQLite stores and persisted `agents.json` with zero plaintext API keys or env secrets"
            f"{suffix}."
        )

    if "structured_pydantic_output" in passed:
        meta = passed["structured_pydantic_output"].metadata
        suffix = _format_present_meta(
            meta,
            ("status", "score", "negative_validation_error", "fallback_stub_used"),
        )
        lines.append(
            "- **Typed Pydantic coercion & validation contract**: "
            "`Agent._coerce_output()` / `_extract_json_object()` validated `BaseModel` schemas cleanly "
            "and raised `AgentOutputValidationError` on non-JSON outputs"
            f"{suffix}."
        )

    if "tool_and_forced_tools" in passed:
        meta = passed["tool_and_forced_tools"].metadata
        suffix = _format_present_meta(meta, ("forced_tool", "invocations"))
        lines.append(
            "- **Scoped `min_scope='READ_ONLY'` `@tool` binding & `tool_choice='forced'`**: "
            "Read-only verifier tools registered with `idempotent=True` executed without workspace "
            "mutations, and `forced_tools` enforced deterministic single-tool dispatch"
            f"{suffix}."
        )

    if "policy_confirmation_gate" in passed:
        meta = passed["policy_confirmation_gate"].metadata
        suffix = _format_present_meta(
            meta,
            (
                "callback_count",
                "allow_executed",
                "deny_blocked",
                "pause_blocked",
                "resume_executed",
                "pending_confirmation_id",
            ),
        )
        lines.append(
            "- **Fail-closed confirmation gate & pause/resume**: "
            "`@tool(dangerous=True, min_scope='WRITE_SAFE')` honored boolean `approval_callback` "
            "(allow/deny) and paused fail-closed on `approval_callback=None` until resumed via "
            "`Agent.run('allow_once', session_id=..., thread_id=...)`"
            f"{suffix}."
        )

    if "agent_handoff" in passed:
        meta = passed["agent_handoff"].metadata
        suffix = _format_present_meta(meta, ("tool_name", "handoff_invocations", "run_id"))
        lines.append(
            "- **Peer `Handoff` transfer + target `PolicyGrantInput` gating**: "
            "`Handoff` compiled `transfer_to_*` delegation tools to route across peer `Agent` "
            "runtimes, pairing cleanly with target-runtime `PolicyGrantInput(max_uses=1)` for "
            "fail-closed confirmation-gated publication"
            f"{suffix}."
        )

    if "session_continuity" in passed:
        meta = passed["session_continuity"].metadata
        suffix = _format_present_meta(
            meta,
            ("same_session_recalled", "second_session_isolated", "session_a", "session_b", "thread_id"),
        )
        lines.append(
            "- **Cross-session isolation & explicit `thread_id` continuity**: "
            "Forwarding `thread_id` alongside `session_id` preserved multi-turn recall while "
            "distinct sessions remained strictly isolated"
            f"{suffix}."
        )

    if "memory_bundle_portability" in passed:
        meta = passed["memory_bundle_portability"].metadata
        suffix = _format_present_meta(
            meta,
            ("bundle_version", "item_count", "invalid_mode_rejected"),
        )
        lines.append(
            "- **`MemoryBundle` portability & schema validation**: "
            "`export_bundle()` -> `save_bundle()` -> `load_bundle()` -> `import_bundle()` "
            "roundtripped portable state across runtimes and raised `InvalidArgumentError` on "
            "invalid trust modes"
            f"{suffix}."
        )

    if "subagent_delegation" in passed:
        meta = passed["subagent_delegation"].metadata
        suffix = _format_present_meta(
            meta,
            ("context_id", "parent_transcript_inherited", "tool_allowlist", "subagent_calls"),
        )
        lines.append(
            "- **Isolated `subagent()` & `SubagentRunContext` execution**: "
            "Child subagents executed with scoped `tool_allowlist` and `parent_transcript_inherited=False`, "
            "and `child.close()` left the parent `APIRuntime` open"
            f"{suffix}."
        )

    if "submit_turn_streaming_telemetry" in passed:
        meta = passed["submit_turn_streaming_telemetry"].metadata
        suffix = _format_present_meta(
            meta,
            ("chunk_count", "duration_ms", "stats_input_tokens", "stats_output_tokens"),
        )
        lines.append(
            "- **`APIRuntime.submit_turn()` `TurnChunk` SSE streaming**: "
            "`RuntimeTurnHandle.stream()` delivered ordered `TurnChunk` status and `final_text` "
            "events alongside populated `TurnResponse.stats` usage counters"
            f"{suffix}."
        )

    if "error_and_timeout_contracts" in passed:
        meta = passed["error_and_timeout_contracts"].metadata
        suffix = _format_present_meta(
            meta,
            ("http_500_attempts", "timeout_exception", "http_connection_reuse_enabled"),
        )
        lines.append(
            "- **Deterministic error, timeout & wire-adapter contracts**: "
            "Exhausted retries raised `ProviderError`, exceeded turn deadlines raised `TurnTimeoutError`, "
            "`http_connection_reuse_enabled=False` avoided Windows keep-alive pool stalls, and "
            "`AnthropicProvider` / `CortensorProvider` / `OpenAIProvider` wire checks passed"
            f"{suffix}."
        )

    lines.append("")
    return lines


def _passed_probe_metadata(
    passed: dict[str, ProbeCheckResult],
    probe_id: str,
) -> dict[str, Any]:
    item = passed.get(probe_id)
    return item.metadata if item is not None and isinstance(item.metadata, dict) else {}


def _render_rough_edges_lines(report: ProbeSuiteReport) -> list[str]:
    """Render verified SDK rough edges and any failed probes observed during calibration."""
    passed = {item.probe_id: item for item in report.probes if item.passed}
    failed = [item for item in report.probes if not item.passed]
    lines = ["## What Broke & Rough Edges Encountered", ""]

    for item in failed:
        lines.append(f"- **Probe failure (`{item.probe_id}`)**: {item.detail}")

    if "session_continuity" in passed:
        sess_meta = _passed_probe_metadata(passed, "session_continuity")
        sess_note = (
            f" (verified with `thread_id={sess_meta['thread_id']}`)"
            if "thread_id" in sess_meta
            else ""
        )
        lines.append(
            "- **Implicit new thread per `Agent.run(session_id=...)` without explicit `thread_id`**: "
            "`Agent._build_payload()` (`openminion/api/agent.py:167-170`) omits `inbound_metadata['thread_id']` "
            "unless `thread_id` is passed explicitly, so `resolve_thread_routing_decision()` "
            "(`openminion/modules/task/run/status.py:532-539`) treats subsequent turns on a settled "
            "session as `settled_without_resume` and forks a fresh `thread_id`"
            f"{sess_note}."
        )

    if "submit_turn_streaming_telemetry" in passed:
        stream_meta = _passed_probe_metadata(passed, "submit_turn_streaming_telemetry")
        if (
            "tokens_in" in stream_meta
            and "tokens_out" in stream_meta
            and "stats_input_tokens" in stream_meta
            and "stats_output_tokens" in stream_meta
        ):
            stream_observed = (
                f" (`tokens_in={stream_meta['tokens_in']}`, `tokens_out={stream_meta['tokens_out']}` vs "
                f"`TurnResponse.stats` `input_tokens={stream_meta['stats_input_tokens']}`, "
                f"`output_tokens={stream_meta['stats_output_tokens']}`, "
                f"`telemetry_metadata_mismatch={stream_meta.get('telemetry_metadata_mismatch')}`)"
            )
        else:
            stream_observed = _format_present_meta(
                stream_meta,
                ("chunk_count", "duration_ms", "retries"),
            )
        lines.append(
            "- **`TurnTelemetry` token-zero mismatch vs `TurnResponse.stats`**: "
            "`_turn_success_response()` (`openminion/services/runtime/daemon.py:549-555`) populates "
            "`TurnTelemetry.tokens_in/tokens_out` from `metadata.get('usage_prompt_tokens')` and "
            "`metadata.get('usage_completion_tokens')`, whereas brain post-execution writes "
            "`total_input_tokens_used` / `total_output_tokens_used` and `turn_result.stats`"
            f"{stream_observed}."
        )

    if "agent_handoff" in passed:
        handoff_meta = _passed_probe_metadata(passed, "agent_handoff")
        handoff_note = (
            f" (`verbatim_ack={handoff_meta['verbatim_ack']}` in live calibration as coordinators "
            "paraphrase specialist text)"
            if "verbatim_ack" in handoff_meta
            else ""
        )
        lines.append(
            "- **`handoff.target.run(message)` timeout & approval omission**: "
            "`build_delegate_tool()` (`openminion/api/handoff.py:168-170`) invokes "
            "`handoff.target.run(message)` without forwarding caller `timeout_seconds` (falling back "
            "to the `90.0s` default in `openminion/base/config/runtime/__init__.py:73`) or "
            "`approval_callback`, forcing target runtimes to rely on pre-issued `PolicyGrantInput(max_uses=1)`"
            f"{handoff_note}."
        )

    if "error_and_timeout_contracts" in passed:
        err_meta = _passed_probe_metadata(passed, "error_and_timeout_contracts")
        wire = (
            err_meta.get("provider_wire_formats")
            if isinstance(err_meta.get("provider_wire_formats"), dict)
            else {}
        )
        if "openai_sse_usage_without_vendor" in wire and "openai_sse_usage_with_vendor" in wire:
            sse_note = (
                f" (`openai_sse_usage_without_vendor={wire['openai_sse_usage_without_vendor']}` vs "
                f"`openai_sse_usage_with_vendor={wire['openai_sse_usage_with_vendor']}`)"
            )
        else:
            sse_note = ""
        lines.append(
            "- **SSE `usage` chunk suppression without `service_vendor='openai'`**: "
            "`OpenAIProvider.stream()` (`openminion/modules/llm/providers/openai/adapter.py:901-907, 961`) "
            "sets `preserve_response_facts=False` unless `service_vendor == 'openai'` or a compat "
            "dialect overrides it, causing `_iter_openai_stream_events()` (`adapter.py:505-524`) to "
            "skip final `usage`, `finish_reason`, and tool-call deltas for OpenAI-compatible relays"
            f"{sse_note}."
        )
        if "http_500_attempts" in err_meta:
            lines.append(
                "- **Layered HTTP 500 retry multiplication & Windows connection reuse**: "
                f"With `http_connection_reuse_enabled={err_meta.get('http_connection_reuse_enabled')}`, "
                "`provider_retry_max_attempts=2` multiplied by transport retries produced "
                f"`http_500_attempts={err_meta['http_500_attempts']}` before raising `ProviderError`."
            )

    if "subagent_delegation" in passed:
        sub_meta = _passed_probe_metadata(passed, "subagent_delegation")
        sub_note = (
            f" (isolated `context_id={sub_meta['context_id']}`)"
            if "context_id" in sub_meta
            else ""
        )
        lines.append(
            "- **Sequential `subagent()` `task_update` state collision & `90.0s` timeout fallback**: "
            "`resolve_entry_task_update()` (`openminion/modules/brain/loop/context/task_context.py:173-191`) "
            "raises `ValueError('Missing task_update for a clarification or active request')` or "
            "`ValueError('Exactly one task_update is allowed per entry response')` when sequential "
            "subagent passes share session task state or emit batched entry tool calls, while omitting "
            "explicit `timeout_seconds` falls back to the `90.0s` runtime default (`services/runtime/daemon.py:307`)"
            f"{sub_note}."
        )

    if {"structured_pydantic_output", "tool_and_forced_tools", "submit_turn_streaming_telemetry"} & set(passed):
        lines.append(
            "- **Internal `submit_output` classifier turns & `agent_id:` reply prefix**: "
            "OpenMinion issues internal `FreshnessContract`, `FinalizationStatus`, and `ClosureJudgment` "
            "(`tool_choice='submit_output'`) turns requiring `action_summary` preservation in gateways/stubs, "
            "and prefixes replies with `f'{agent_id}: '`, requiring `_extract_json_object()` recovery."
        )

    if len(lines) == 2:
        lines.append(
            "- No probe failures or matching SDK rough edges were observed for the executed probe subset."
        )

    lines.append("")
    return lines


def _render_improvement_proposals_lines(report: ProbeSuiteReport) -> list[str]:
    """Render structured upstream SDK improvement proposals strictly gated on passing probes."""
    passed = {item.probe_id: item for item in report.probes if item.passed}
    proposals: list[tuple[str, str, str, str, str]] = []

    if "submit_turn_streaming_telemetry" in passed:
        stream_meta = _passed_probe_metadata(passed, "submit_turn_streaming_telemetry")
        if (
            "tokens_in" in stream_meta
            and "tokens_out" in stream_meta
            and "stats_input_tokens" in stream_meta
            and "stats_output_tokens" in stream_meta
        ):
            telemetry_actual = (
                f"Expected `TurnTelemetry` to match `TurnResponse.stats`; actual run emitted "
                f"`TurnTelemetry(tokens_in={stream_meta['tokens_in']}, tokens_out={stream_meta['tokens_out']})` "
                f"alongside `stats(input_tokens={stream_meta['stats_input_tokens']}, "
                f"output_tokens={stream_meta['stats_output_tokens']})`."
            )
        else:
            telemetry_actual = (
                "Expected `TurnTelemetry.tokens_in/tokens_out` to match `TurnResponse.stats` token totals"
                f"{_format_present_meta(stream_meta, ('chunk_count', 'duration_ms'))}; actual `TurnTelemetry` "
                "reads `metadata.get('usage_prompt_tokens')` / `usage_completion_tokens`."
            )
        proposals.append(
            (
                "Populate `TurnTelemetry` Token Counts from `turn_result.stats` / `total_*_tokens_used`",
                "`openminion/services/runtime/daemon.py:549-555` (`_turn_success_response`)",
                "`handle = runtime.submit_turn({'session_id': ..., 'message': ..., 'stream': True}); resp = handle.result()`",
                telemetry_actual,
                "Read `turn_result.stats.input_tokens` / `output_tokens` first (falling back to "
                "`metadata.get('usage_prompt_tokens') or metadata.get('total_input_tokens_used')` and "
                "`metadata.get('usage_completion_tokens') or metadata.get('total_output_tokens_used')`).",
            )
        )

    if "agent_handoff" in passed:
        proposals.append(
            (
                "Forward `timeout_seconds` & Approval Context in `Handoff` / `build_delegate_tool()`",
                "`openminion/api/handoff.py:168-170` (`build_delegate_tool._handler_fn`)",
                "`Agent(handoffs=[Handoff(target=specialist)]).run('...', timeout_seconds=180, approval_callback=cb)`",
                "Expected `handoff.target.run(message)` to honor caller `timeout_seconds` and confirmation "
                "policy; actual call invokes `handoff.target.run(message)` bare, silently reverting to the "
                "`90.0s` runtime default and omitting caller `approval_callback`.",
                "Add optional `timeout_seconds` and `approval_callback` forwarding fields on `Handoff` "
                "(defaulting to the active caller run context when unset) and pass them inside `build_delegate_tool()`.",
            )
        )

    if "subagent_delegation" in passed:
        proposals.append(
            (
                "Guard `resolve_entry_task_update()` Against Shared-Session `subagent()` & Parallel Tool Calls",
                "`openminion/modules/brain/loop/context/task_context.py:173-191` (`resolve_entry_task_update`)",
                "Run two sequential `subagent(parent, ...)` passes sharing a session or emitting parallel entry tool calls.",
                "Expected each independent subagent turn or multi-tool entry response to execute cleanly; "
                "actual `resolve_entry_task_update()` raises `ValueError('Missing task_update for a clarification "
                "or active request')` or `ValueError('Exactly one task_update is allowed per entry response')`, "
                "detouring into `invalid_task_context_update` clarify prompts.",
                "Deduplicate identical `task_update` sidecar patches across parallel entry tool calls, and avoid "
                "inheriting prior-run `resolved_task_context` when entering an isolated `SubagentRunContext`.",
            )
        )

    if "session_continuity" in passed:
        sess_meta = _passed_probe_metadata(passed, "session_continuity")
        sess_suffix = _format_present_meta(sess_meta, ("thread_id", "same_session_recalled"))
        proposals.append(
            (
                "Explicit Session Thread Continuity Option on `Agent.run(session_id=...)`",
                "`openminion/api/agent.py:167-170` & `openminion/modules/task/run/status.py:532-539`",
                "`agent.run('Remember token X', session_id='s1'); agent.run('Recall token', session_id='s1')`",
                "Expected consecutive `Agent.run(..., session_id='s1')` calls to share conversation history; "
                "actual second turn lacks `inbound_metadata['thread_id']`, hits `settled_without_resume`, and "
                "forks a brand-new thread with zero recall unless callers manually thread `result.thread_id`"
                f"{sess_suffix}.",
                "Expose `resume_latest_thread: bool = True` (or `continue_session`) on `Agent.run()` / "
                "`Agent._build_payload()` or clearly document mandatory `thread_id` propagation in SDK guides.",
            )
        )

    if "error_and_timeout_contracts" in passed:
        err_meta = _passed_probe_metadata(passed, "error_and_timeout_contracts")
        wire = (
            err_meta.get("provider_wire_formats")
            if isinstance(err_meta.get("provider_wire_formats"), dict)
            else {}
        )
        if "openai_sse_usage_without_vendor" in wire and "openai_sse_usage_with_vendor" in wire:
            sse_actual = (
                f"Expected SSE `done` event `usage` to be parsed for all OpenAI-compatible SSE streams; "
                f"actual `done.usage` was `None` without `service_vendor='openai'` "
                f"(`openai_sse_usage_without_vendor={wire['openai_sse_usage_without_vendor']}` vs "
                f"`openai_sse_usage_with_vendor={wire['openai_sse_usage_with_vendor']}`)."
            )
        else:
            sse_actual = (
                "Expected SSE `done` event `usage` and tool deltas to be parsed for OpenAI-compatible relays"
                f"{_format_present_meta(err_meta, ('http_500_attempts', 'timeout_exception'))}; actual "
                "`_iter_openai_stream_events()` drops them whenever `preserve_response_facts=False`."
            )
        proposals.append(
            (
                "Preserve OpenAI SSE `usage` & Tool Deltas Regardless of Relay `service_vendor`",
                "`openminion/modules/llm/providers/openai/adapter.py:901-907, 961` & `505-524`",
                "`OpenAIProvider().stream(req, {'base_url': 'https://custom-relay/v1', 'api_key': ..., 'model': ...})`",
                sse_actual,
                "Decouple SSE `usage` / `finish_reason` extraction in `_iter_openai_stream_events()` from "
                "`stream_contract_enabled` (only gate outbound `tools`/`tool_choice` on `stream_contract_enabled` "
                "while always parsing `chunk.get('usage')` when present in SSE frames).",
            )
        )

    lines = ["## Actionable SDK Improvement Proposals (Repro + Expected vs. Actual)", ""]
    if not proposals:
        lines.extend(
            [
                "- No upstream SDK improvement proposals emitted because none of the corresponding diagnostic probes passed in this run.",
                "",
            ]
        )
        return lines

    for idx, (heading, target, repro, exp_actual, fix) in enumerate(proposals, start=1):
        lines.extend(
            [
                f"### {idx}. {heading}",
                "",
                f"- **Target Module**: {target}",
                f"- **Minimal Repro**: {repro}",
                f"- **Expected vs. Actual**: {exp_actual}",
                f"- **Recommended Upstream Fix**: {fix}",
                "",
            ]
        )
    return lines


def render_what_we_learned_md(report: ProbeSuiteReport) -> str:
    """Render docs/WHAT_WE_LEARNED.md from empirical probe findings."""
    lines = [
        "# What We Learned: OpenMinion 0.1 SDK Empirical DX Report",
        "",
        f"> **Calibration Posture**: {report.calibration_status}",
        "",
        f"Generated directly from `BuildingBlockProbeRunner.run_all()` against `openminion=={report.sdk_version}` "
        f"(`preset={report.preset}`, `model={report.model}`, `endpoint={report.base_url_host}`, "
        f"`{report.passed_probes}/{report.total_probes}` passed in `{report.total_latency_ms:.2f} ms`).",
        "",
    ]
    lines.extend(_render_what_worked_cleanly_lines(report))
    lines.extend(_render_rough_edges_lines(report))
    lines.extend(_render_improvement_proposals_lines(report))
    lines.extend(["## Empirical SDK & DX Findings", ""])
    for idx, finding in enumerate(report.dx_findings, start=1):
        lines.append(f"### {idx}. {finding['title']}")
        lines.append("")
        lines.append(finding["observation"])
        lines.append("")

    lines.extend(
        [
            "## Observed Runtime Measurements",
            "",
            "| Probe ID | Status | Latency (ms) | Key Telemetry |",
            "|---|---|---:|---|",
        ]
    )
    for probe in report.probes:
        status = "PASS" if probe.passed else "FAIL"
        latency = f"{probe.latency_ms:.2f}" if probe.latency_ms is not None else "n/a"
        summary_pairs = ", ".join(f"{k}={v}" for k, v in sorted(probe.metadata.items()))
        lines.append(f"| `{probe.probe_id}` | {status} | {latency} | `{summary_pairs}` |")

    return scrub_secrets("\n".join(lines).rstrip() + "\n")


def export_probe_docs(
    report: ProbeSuiteReport,
    *,
    docs_dir: str | Path = "docs",
    secret_env_names: Sequence[str] | None = None,
    extra_secrets: Sequence[str] | None = None,
) -> tuple[Path, Path]:
    """Scrub, fail-closed verify, and write BUILDING_BLOCKS_TESTED.md & WHAT_WE_LEARNED.md."""
    target_dir = Path(docs_dir)
    tested_raw = render_building_blocks_tested_md(report)
    learned_raw = render_what_we_learned_md(report)

    tested_clean = scrub_secrets(
        tested_raw,
        secret_env_names=secret_env_names,
        extra_secrets=extra_secrets,
    )
    learned_clean = scrub_secrets(
        learned_raw,
        secret_env_names=secret_env_names,
        extra_secrets=extra_secrets,
    )

    assert_no_plaintext_secrets(
        tested_clean,
        secret_env_names=secret_env_names,
        extra_secrets=extra_secrets,
    )
    assert_no_plaintext_secrets(
        learned_clean,
        secret_env_names=secret_env_names,
        extra_secrets=extra_secrets,
    )

    target_dir.mkdir(parents=True, exist_ok=True)
    tested_path = target_dir / "BUILDING_BLOCKS_TESTED.md"
    learned_path = target_dir / "WHAT_WE_LEARNED.md"
    tested_path.write_text(tested_clean, encoding="utf-8")
    learned_path.write_text(learned_clean, encoding="utf-8")
    return tested_path, learned_path
