"""OpenMinion 0.1 SDK Integration for Cortensor Subnet Verification.
==================================================================
Implements a simple, reliable Subnet Task Verification Agent using the official
OpenMinion 0.1 SDK (`openminion.Agent` and `openminion.tool`).
"""

from __future__ import annotations

import json
import os
import math
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from openminion import Agent, tool

from cortensor_validator.attestation import AttestationReceipt, AttestationSigner
from cortensor_validator.verifier import verify_code_safety


# ---------------------------------------------------------------------------
# OpenMinion Tools
# ---------------------------------------------------------------------------

# Every tool appends (tool_name, result) here, so a live run can report exactly
# which tools the model called and what they returned. Results of code tools carry
# the code they were called with under "_code": the model chooses tool arguments,
# so the verdict must check that it tested the submission and not a rewrite of it.
TOOL_LOG: list[tuple[str, dict[str, Any]]] = []
TOOL_PROGRESS_CALLBACK: Callable[[str, dict[str, Any]], None] | None = None


def _record_tool_result(
    tool_name: str,
    out: dict[str, Any],
    code: str | None = None,
) -> None:
    """Append tool output to TOOL_LOG and notify any live progress hook."""
    entry = {**out, "_code": code} if code is not None else out
    TOOL_LOG.append((tool_name, entry))
    if TOOL_PROGRESS_CALLBACK is not None:
        TOOL_PROGRESS_CALLBACK(tool_name, out)


@tool(min_scope="READ_ONLY", idempotent=True)
def audit_code_safety(code: str) -> dict[str, Any]:
    """Inspect Python code for unsafe primitives and syntax errors before execution.

    Parameters
    ----------
    code : str
        Source code submitted by a subnet miner.

    Returns
    -------
    dict[str, Any]
        Audit outcome including valid flag, violations list, and latency.
    """
    res = verify_code_safety(code)
    out = {
        "valid": res.valid,
        "violations": list(res.violations),
        "nodes_scanned": res.ast_nodes_scanned,
        "latency_ms": res.latency_ms,
    }
    _record_tool_result("audit_code_safety", out, code=code)
    return out


SAFE_BUILTINS = {
    "range": range,
    "len": len,
    "min": min,
    "max": max,
    "abs": abs,
    "sum": sum,
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    "list": list,
    "dict": dict,
    "set": set,
    "tuple": tuple,
    "enumerate": enumerate,
    "zip": zip,
}


# Miner code runs in a child interpreter. The parent enforces a hard wall clock
# kill, and the child sets address space and CPU limits on itself before running
# anything. A timer inside the same process is not enough, because miner code can
# swallow the timer exception with a bare except and loop forever.
MEMORY_LIMIT_BYTES = 512 * 1024 * 1024
STARTUP_GRACE_SECONDS = 1.0

_WORKER = """
import builtins, json, resource, sys
req = json.loads(sys.stdin.read())
resource.setrlimit(resource.RLIMIT_AS, (req["mem"], req["mem"]))
resource.setrlimit(resource.RLIMIT_CPU, (req["cpu"], req["cpu"] + 1))
safe = {n: getattr(builtins, n) for n in req["builtins"]}
ns = {}
try:
    exec(req["code"], {"__builtins__": safe}, ns)
    fn = ns.get("solution")
    if not callable(fn):
        out = {"passed": False, "error": "No callable 'solution' defined in code."}
    else:
        actual = fn(req["input"])
        out = {"passed": actual == req["expected"], "actual_output": actual}
    line = json.dumps(out, default=repr)
except BaseException as exc:
    line = json.dumps({"passed": False, "error": type(exc).__name__ + ": " + str(exc)})
sys.stdout.write("\\n@@RESULT@@" + line)
"""


@tool(min_scope="READ_ONLY", idempotent=True)
def execute_test_case(
    code: str,
    test_input: int,
    expected_output: int,
    timeout_seconds: float = 1.0,
) -> dict[str, Any]:
    """Execute a safe pure function against an input-output test case with timeout defense.

    Parameters
    ----------
    code : str
        Verified Python code defining a function named 'solution'.
    test_input : int
        Input integer to test.
    expected_output : int
        Expected output integer.
    timeout_seconds : float, optional
        Maximum CPU execution time allowed in seconds (default: 1.0).

    Returns
    -------
    dict[str, Any]
        Test outcome including pass flag, actual output, and latency.
    """
    out = _run_test_case(code, test_input, expected_output, timeout_seconds)
    _record_tool_result("execute_test_case", out, code=code)
    return out


def _run_test_case(
    code: str,
    test_input: int,
    expected_output: int,
    timeout_seconds: float,
) -> dict[str, Any]:
    safety = verify_code_safety(code)
    if not safety.valid:
        return {
            "passed": False,
            "error": "Safety check failed; execution blocked.",
            "violations": list(safety.violations),
        }

    t0 = time.perf_counter()
    request = json.dumps({
        "code": code,
        "input": test_input,
        "expected": expected_output,
        "builtins": sorted(SAFE_BUILTINS),
        "mem": MEMORY_LIMIT_BYTES,
        "cpu": max(1, math.ceil(timeout_seconds)),
    })
    try:
        proc = subprocess.run(  # noqa: S603
            [sys.executable, "-I", "-S", "-c", _WORKER],
            input=request,
            capture_output=True,
            text=True,
            timeout=timeout_seconds + STARTUP_GRACE_SECONDS,
        )
    except subprocess.TimeoutExpired:
        dt_ms = (time.perf_counter() - t0) * 1000.0
        return {"passed": False, "error": "Execution timed out (wall clock budget exceeded, child killed).", "latency_ms": dt_ms}

    dt_ms = (time.perf_counter() - t0) * 1000.0
    marker = proc.stdout.rfind("@@RESULT@@")
    if marker < 0:
        return {
            "passed": False,
            "error": f"Execution killed (exit code {proc.returncode}, CPU or memory limit exceeded).",
            "latency_ms": dt_ms,
        }
    try:
        out = json.loads(proc.stdout[marker + len("@@RESULT@@"):])
    except ValueError:
        return {"passed": False, "error": "Execution produced no valid result.", "latency_ms": dt_ms}
    out["latency_ms"] = dt_ms
    if "actual_output" in out:
        out["expected_output"] = expected_output
    return out


@tool(min_scope="READ_ONLY", idempotent=True)
def create_attestation_receipt(
    task_id: str,
    passed: bool,
    validator_id: str | None = None,
) -> dict[str, Any]:
    """Generate an HMAC-SHA256 cryptographic attestation receipt for a task outcome.

    Parameters
    ----------
    task_id : str
        Subnet task identifier.
    passed : bool
        Whether the task verification passed.
    validator_id : str, optional
        Validator node identifier (defaults to CORTENSOR_VALIDATOR_ID env var).

    Returns
    -------
    dict[str, Any]
        Signed attestation receipt data.
    """
    effective_id = validator_id or os.getenv("CORTENSOR_VALIDATOR_ID", "val-cortensor-01")
    signer = AttestationSigner(validator_id=effective_id)
    receipt = signer.sign(task_id=task_id, passed=passed)
    out = {
        "task_id": receipt.task_id,
        "validator_id": receipt.validator_id,
        "epoch": receipt.epoch,
        "passed": receipt.passed,
        "signature": receipt.signature,
        "timestamp_ns": receipt.timestamp_ns,
    }
    _record_tool_result("create_attestation_receipt", out)
    return out


def query_hosted_portal(
    api_key: str | None = None,
    base_url: str | None = None,
    timeout_seconds: float = 5.0,
) -> dict[str, Any]:
    """Check whether the Cortensor Portal API is reachable with the given key.

    Portal is an OpenAI-compatible model endpoint. A 200 from ``/v1/models``
    means the key works and lists the models; it says nothing about whether a
    miner's code is correct, so this function never returns a verdict.
    """
    key = api_key or os.getenv("CORTENSOR_API_KEY")
    if not key:
        return {"connected": False, "reason": "No CORTENSOR_API_KEY provided"}

    base = (base_url or os.getenv("CORTENSOR_BASE_URL", "https://api.cortensor.app")).rstrip("/")
    models_url = f"{base}/v1/models"
    try:
        req = urllib.request.Request(
            models_url,
            headers={
                "Authorization": f"Bearer {key}",
                "User-Agent": "CortensorSentinel-OpenMinion/0.1",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            if response.status != 200:
                return {"connected": False, "status_code": response.status}
            body = json.loads(response.read().decode("utf-8"))
            items = body.get("data", body) if isinstance(body, dict) else body
            models = [m.get("id") or m.get("name") for m in items if isinstance(m, dict)]
            return {"connected": True, "endpoint": base, "models": models}
    except Exception as exc:
        return {"connected": False, "error": str(exc)}


@tool(min_scope="READ_ONLY", idempotent=True)
def verify_via_hosted_portal(
    code: str,
    test_input: int,
    expected_output: int,
) -> dict[str, Any]:
    """Report Cortensor Portal reachability and run the test case locally.

    Parameters
    ----------
    code : str
        Source code to verify.
    test_input : int
        Test input integer.
    expected_output : int
        Expected output integer.

    Returns
    -------
    dict[str, Any]
        Portal reachability plus the local test result. The verdict always
        comes from the local test, never from the Portal probe.
    """
    portal = query_hosted_portal()
    local_test = _run_test_case(code, test_input, expected_output, 1.0)
    out = {"portal": portal, "result": local_test}
    TOOL_LOG.append(("verify_via_hosted_portal", out))
    return out


# ---------------------------------------------------------------------------
# Cortensor Sentinel Facade
# ---------------------------------------------------------------------------


class CortensorSentinel:
    """Manages OpenMinion-powered task verification for Cortensor Subnet nodes."""

    def __init__(
        self,
        validator_id: str | None = None,
        epoch: int | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.validator_id = validator_id or os.getenv("CORTENSOR_VALIDATOR_ID", "val-cortensor-01")
        self.epoch = epoch if epoch is not None else int(os.getenv("CORTENSOR_EPOCH", "1"))
        self.signer = AttestationSigner(validator_id=self.validator_id, current_epoch=self.epoch)
        self.api_key = api_key or os.getenv("CORTENSOR_API_KEY")
        self.base_url = base_url or os.getenv("CORTENSOR_BASE_URL", "https://api.cortensor.app")
        self.last_mode: str = "local"

    def create_agent(self, model: str | None = None) -> Agent:
        """Create an official OpenMinion Agent equipped with verification tools."""
        instructions = (
            "You are a Cortensor Subnet Task Verification Agent built with OpenMinion 0.1. "
            "Use audit_code_safety to inspect code proposals for dangerous primitives. "
            "Use execute_test_case to test verified logic against expected outputs. "
            "Use verify_via_hosted_portal to verify tasks via Cortensor hosted portal. "
            "Use create_attestation_receipt to produce cryptographic verification receipts."
        )
        return Agent(
            name=f"CortensorSentinel-{self.validator_id}",
            instructions=instructions,
            model=model,
            tools=[
                audit_code_safety,
                execute_test_case,
                verify_via_hosted_portal,
                create_attestation_receipt,
            ],
        )

    def verify_submission(
        self,
        task_id: str,
        code: str,
        test_input: int,
        expected_output: int,
        use_hosted: bool = False,
    ) -> tuple[bool, AttestationReceipt]:
        """Perform a complete, deterministic verification cycle on a miner submission."""
        # 1. Audit code safety locally first (defense-in-depth)
        safety = verify_code_safety(code)
        if not safety.valid:
            self.last_mode = "local_rejected"
            receipt = self.signer.sign(task_id=task_id, passed=False)
            return False, receipt

        # 2. Optionally record Portal reachability. It never decides the verdict.
        if use_hosted or self.api_key:
            portal = query_hosted_portal(api_key=self.api_key, base_url=self.base_url)
            self.last_mode = "local, portal reachable" if portal.get("connected") else "local, portal unreachable"
        else:
            self.last_mode = "local"

        # 3. Test correctness locally
        test_res = _run_test_case(code, test_input, expected_output, 1.0)
        passed = bool(test_res.get("passed", False))

        # 4. Sign attestation
        receipt = self.signer.sign(task_id=task_id, passed=passed)
        return passed, receipt
