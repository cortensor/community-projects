"""Risk-tiered @openminion.tool suite for endpoint probing and benchmark tasks."""

from __future__ import annotations

import ipaddress
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from openminion import tool


def _validate_probe_url(raw_url: str, *, allow_private: bool = False) -> str:
    """Validate scheme and block SSRF to private/loopback/link-local hosts unless opted in."""
    cleaned = str(raw_url or "").strip()
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("probe_inference_endpoint requires a valid http(s) URL")
    if parsed.username or parsed.password:
        raise ValueError("Credentials in URL are not permitted")

    host = (parsed.hostname or "").strip().lower()
    if not allow_private:
        if host in {"localhost", "127.0.0.1", "::1", "0.0.0.0"} or host.endswith(".local"):
            raise ValueError(f"Private/loopback probe host blocked: {host}")
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                raise ValueError(f"Non-public probe IP blocked: {host}")
        except ValueError as exc:
            if "blocked" in str(exc):
                raise

    target = cleaned.rstrip("/")
    if not target.endswith("/models") and "/completions" not in target:
        return f"{target}/models"
    return target


def build_eval_tools(
    *,
    workspace_dir: Path,
    counters: dict[str, int],
    allow_private_probe: bool = False,
):
    """Build scoped tools bound to an isolated output workspace."""
    resolved_workspace = workspace_dir.resolve()

    @tool(min_scope="READ_ONLY", idempotent=True)
    def probe_inference_endpoint(base_url: str, timeout_seconds: float = 5.0) -> str:
        """Probe an OpenAI-compatible or Cortensor endpoint without mutating state."""
        counters["probe_inference_endpoint"] = (
            counters.get("probe_inference_endpoint", 0) + 1
        )
        started = time.perf_counter()
        try:
            probe_url = _validate_probe_url(base_url, allow_private=allow_private_probe)
        except ValueError as exc:
            return json.dumps(
                {
                    "endpoint": str(base_url or "").strip(),
                    "reachable": False,
                    "status_code": None,
                    "latency_ms": 0.0,
                    "detail": f"Blocked: {exc}",
                },
                sort_keys=True,
            )

        bounded_timeout = min(30.0, max(0.5, float(timeout_seconds)))
        try:
            with httpx.Client(timeout=bounded_timeout, follow_redirects=False) as client:
                resp = client.get(probe_url)
            latency_ms = round((time.perf_counter() - started) * 1000.0, 2)
            reachable = resp.status_code < 500
            return json.dumps(
                {
                    "endpoint": probe_url,
                    "reachable": reachable,
                    "status_code": resp.status_code,
                    "latency_ms": latency_ms,
                    "detail": f"HTTP {resp.status_code}",
                },
                sort_keys=True,
            )
        except httpx.HTTPError as exc:
            latency_ms = round((time.perf_counter() - started) * 1000.0, 2)
            return json.dumps(
                {
                    "endpoint": probe_url,
                    "reachable": False,
                    "status_code": None,
                    "latency_ms": latency_ms,
                    "detail": type(exc).__name__,
                },
                sort_keys=True,
            )

    @tool(min_scope="READ_ONLY", idempotent=True)
    def score_case_output(case_id: str, observed: str, expected: str) -> str:
        """Compare observed output against expected substring deterministically."""
        counters["score_case_output"] = counters.get("score_case_output", 0) + 1
        passed = expected.strip().lower() in observed.strip().lower()
        return json.dumps(
            {
                "case_id": case_id,
                "passed": passed,
                "expected": expected,
                "observed_preview": observed[:120],
            },
            sort_keys=True,
        )

    @tool(idempotent=True)
    def write_eval_artifact(filename: str, content: str) -> str:
        """Write an evaluation report artifact inside the approved workspace."""
        counters["write_eval_artifact"] = counters.get("write_eval_artifact", 0) + 1
        if any(sep in str(filename or "") for sep in ("/", "\\", "\x00")) or ":" in str(filename or ""):
            raise ValueError("Path separators are not permitted in artifact filename")
        safe_name = Path(filename).name
        if not safe_name or safe_name in {".", ".."}:
            raise ValueError("Invalid artifact filename")
        resolved_workspace.mkdir(parents=True, exist_ok=True)
        out_path = (resolved_workspace / safe_name).resolve()
        if out_path.parent != resolved_workspace or out_path.is_symlink():
            raise ValueError("Path escapes approved workspace")
        encoded = content.encode("utf-8")
        if len(encoded) > 1_048_576:
            raise ValueError("Artifact exceeds 1 MiB size limit")
        tmp_path = resolved_workspace / f".{safe_name}.{os.getpid()}.tmp"
        tmp_path.write_bytes(encoded)
        os.replace(tmp_path, out_path)
        return json.dumps(
            {
                "written": True,
                "path": str(out_path),
                "bytes": len(encoded),
            },
            sort_keys=True,
        )

    @tool(dangerous=True)
    def purge_eval_history(confirm_phrase: str) -> str:
        """Destructive placeholder tool that should remain blocked fail-closed."""
        counters["purge_eval_history"] = counters.get("purge_eval_history", 0) + 1
        return json.dumps({"purged": False, "confirm_phrase": confirm_phrase})

    return {
        "probe_inference_endpoint": probe_inference_endpoint,
        "score_case_output": score_case_output,
        "write_eval_artifact": write_eval_artifact,
        "purge_eval_history": purge_eval_history,
    }
