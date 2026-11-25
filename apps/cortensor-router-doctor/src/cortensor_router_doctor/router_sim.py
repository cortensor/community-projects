"""Lightweight local Cortensor Router v2 HTTP simulator for deterministic testing and demos."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time
from typing import Any, Literal

RouterProfileName = Literal["healthy", "poi_drift", "sla_degraded"]


@dataclass(frozen=True)
class RouterNodeProfile:
    """Configuration for a simulated Cortensor Router node."""

    profile: RouterProfileName = "healthy"
    node_id: str = "cortensor-sim-node-01"
    model: str = "gpt-oss-20b"
    base_latency_ms: float | None = None
    fail_every_n: int = 2

    def effective_latency_ms(self) -> float:
        if self.base_latency_ms is not None:
            return max(0.0, float(self.base_latency_ms))
        if self.profile == "sla_degraded":
            return 650.0
        if self.profile == "poi_drift":
            return 30.0
        return 20.0


_DRIFT_ANSWERS: tuple[str, ...] = (
    "Consensus state: FINALIZED_EPOCH_4092 on Arbitrum Sepolia with quorum 5/5.",
    "Consensus state: REORG_DETECTED_EPOCH_9911 on Ethereum Mainnet with slashed validator 0xdead.",
    "Consensus state: HALTED_MEMPOOL_OVERFLOW on Polygon Amoy with zero active miners.",
    "Consensus state: UNKNOWN_FORK_7710 on Optimism Goerli with unverified witness root.",
)


class SimulatedCortensorRouter:
    """Thread-safe local HTTP server emulating Cortensor `/api/v2/completions` and `/health`."""

    def __init__(
        self,
        profile: RouterProfileName | RouterNodeProfile = "healthy",
        *,
        host: str = "127.0.0.1",
        port: int = 0,
    ) -> None:
        self.node_profile = (
            profile
            if isinstance(profile, RouterNodeProfile)
            else RouterNodeProfile(profile=profile, node_id=f"cortensor-sim-{profile}")
        )
        self._host = host
        self._port = port
        self._lock = threading.Lock()
        self._request_count = 0
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def request_count(self) -> int:
        with self._lock:
            return self._request_count

    @property
    def base_url(self) -> str:
        if self._server is None:
            raise RuntimeError("SimulatedCortensorRouter has not been started")
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    @property
    def completions_url(self) -> str:
        return f"{self.base_url}/api/v2/completions"

    @property
    def chat_completions_url(self) -> str:
        return f"{self.base_url}/v1/chat/completions"

    @property
    def health_url(self) -> str:
        return f"{self.base_url}/health"

    def _next_request_index(self) -> int:
        with self._lock:
            self._request_count += 1
            return self._request_count

    def _build_completion_response(
        self, payload: dict[str, Any], req_index: int
    ) -> tuple[int, dict[str, Any]]:
        latency_ms = self.node_profile.effective_latency_ms()
        if latency_ms > 0:
            time.sleep(latency_ms / 1000.0)

        profile = self.node_profile.profile
        if profile == "sla_degraded":
            fail_every = max(1, self.node_profile.fail_every_n)
            if req_index % fail_every == 0:
                return 503, {
                    "error": {
                        "code": "MINER_POOL_OVERLOADED",
                        "message": "Cortensor router backend temporarily unavailable (HTTP 503)",
                    },
                    "node_id": self.node_profile.node_id,
                    "request_index": req_index,
                }

        prompt = str(payload.get("prompt") or "")
        if not prompt and isinstance(payload.get("messages"), list):
            parts = [
                str(msg.get("content", ""))
                for msg in payload["messages"]
                if isinstance(msg, dict)
            ]
            prompt = "\n".join(parts)

        session_id = int(payload.get("session_id") or 1)
        model = str(payload.get("model") or self.node_profile.model)
        prompt_digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]

        if profile == "poi_drift":
            variant = _DRIFT_ANSWERS[(req_index - 1) % len(_DRIFT_ANSWERS)]
            text = f"{variant} (miner_round={req_index}, prompt_ref={prompt_digest})"
            miner_id = f"miner-drift-{(req_index - 1) % len(_DRIFT_ANSWERS) + 1:02d}"
        elif profile == "sla_degraded":
            text = (
                f"CORTENSOR_POI_DEGRADED_OK prompt_ref={prompt_digest} "
                f"session={session_id} consensus=stable"
            )
            miner_id = "miner-slow-01"
        else:
            text = (
                f"CORTENSOR_POI_VERIFIED prompt_ref={prompt_digest} "
                f"session={session_id} consensus=deterministic_ok"
            )
            miner_id = "miner-healthy-quorum"

        body: dict[str, Any] = {
            "id": f"cmpl-sim-{req_index:04d}",
            "object": "text_completion",
            "model": model,
            "session_id": session_id,
            "choices": [
                {
                    "index": 0,
                    "text": text,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": max(1, len(prompt.split())),
                "completion_tokens": max(1, len(text.split())),
                "total_tokens": max(2, len(prompt.split()) + len(text.split())),
            },
            "cortensor_poi": {
                "node_id": self.node_profile.node_id,
                "miner_id": miner_id,
                "profile": profile,
                "round_index": req_index,
                "latency_ms": round(latency_ms, 2),
            },
        }
        return 200, body

    def start(self) -> "SimulatedCortensorRouter":
        if self._server is not None:
            return self
        router = self

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                del format, args

            def _send_json(self, status_code: int, data: dict[str, Any]) -> None:
                raw = json.dumps(data, ensure_ascii=True).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self) -> None:  # noqa: N802
                if self.path.rstrip("/") == "/health":
                    self._send_json(
                        200,
                        {
                            "status": "ok",
                            "profile": router.node_profile.profile,
                            "node_id": router.node_profile.node_id,
                            "requests_served": router.request_count,
                        },
                    )
                    return
                self._send_json(404, {"error": f"Unknown path: {self.path}"})

            def do_POST(self) -> None:  # noqa: N802
                path = self.path.split("?", 1)[0].rstrip("/")
                if path not in {"/api/v2/completions", "/v1/chat/completions"}:
                    self._send_json(404, {"error": f"Unknown endpoint: {self.path}"})
                    return
                length = int(self.headers.get("Content-Length", "0") or "0")
                raw_body = self.rfile.read(length) if length > 0 else b"{}"
                try:
                    payload = json.loads(raw_body.decode("utf-8"))
                    if not isinstance(payload, dict):
                        payload = {}
                except json.JSONDecodeError:
                    self._send_json(400, {"error": "Invalid JSON body"})
                    return
                req_index = router._next_request_index()
                status_code, response_body = router._build_completion_response(
                    payload, req_index
                )
                self._send_json(status_code, response_body)

        self._server = ThreadingHTTPServer((self._host, self._port), _Handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name=f"cortensor-sim-{self.node_profile.profile}",
            daemon=True,
        )
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def __enter__(self) -> "SimulatedCortensorRouter":
        return self.start()

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        del exc_type, exc_val, exc_tb
        self.stop()
