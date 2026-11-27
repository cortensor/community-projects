"""Cortensor Sentinel CLI Entrypoint.
==================================
Simple, reliable 1-command task verification agent for Cortensor Subnet nodes.

Supports:
  1. Automated dual test demo (Honest + Adversarial proposals)
  2. Dynamic file-based verification via CLI flags
  3. Environment-driven configuration (CORTENSOR_VALIDATOR_ID, CORTENSOR_EPOCH)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from cortensor_validator.openminion_agent import CortensorSentinel


def run_demo(verbose: bool = True, use_hosted: bool = False) -> int:
    """Run a deterministic Sentinel verification cycle."""
    t0 = time.perf_counter()
    validator_id = os.getenv("CORTENSOR_VALIDATOR_ID", "val-cortensor-node-01")

    if verbose:
        print("=" * 68)
        print("  CORTENSOR TASK SENTINEL (OpenMinion 0.1 SDK)")
        print("  DoraHacks Hackathon #5: Subnet Task Verification Agent")
        print("=" * 68)

    sentinel = CortensorSentinel(validator_id=validator_id)
    agent = sentinel.create_agent()

    if verbose:
        print(f"\n[1] Initialized OpenMinion Agent: '{agent.name}'")
        print(f"    - Tools registered: {', '.join(agent.tools)}")
        print(f"    - Session ID: {agent.session_id}")
        if use_hosted:
            print("    - Mode: Hosted Portal Verification enabled (with auto-fallback)")

    # Case A: Honest Miner Submission
    honest_task_id = "task-fibonacci-10"
    honest_code = (
        "def solution(n: int) -> int:\n"
        "    a, b = 0, 1\n"
        "    for _ in range(n):\n"
        "        a, b = b, a + b\n"
        "    return a\n"
    )

    if verbose:
        print(f"\n[2] Ingesting Subnet Task: '{honest_task_id}'")
        print("    - Solution Proposal: Pure iterative Fibonacci algorithm")
        print("    - Evaluating via OpenMinion verification pipeline...")

    passed, receipt = sentinel.verify_submission(
        task_id=honest_task_id,
        code=honest_code,
        test_input=10,
        expected_output=55,
        use_hosted=use_hosted,
    )

    if verbose:
        print(f"    Mode:            {sentinel.last_mode}")
        print(f"    Attestation sig: {receipt.signature[:24]}...")
        print(f"    Status:          {'CERTIFIED' if passed else 'REJECTED'}")

    # Case B: Malicious Miner Submission
    malicious_task_id = "task-exploit-attempt"
    malicious_code = (
        "import os\n"
        "def solution(n: int) -> int:\n"
        "    os.system('cat /etc/passwd')\n"
        "    return n\n"
    )

    if verbose:
        print(f"\n[3] Ingesting Adversarial Task: '{malicious_task_id}'")
        print("    - Solution Proposal: Contains unauthorized 'import os'")
        print("    - Evaluating via OpenMinion verification pipeline...")

    mal_passed, mal_receipt = sentinel.verify_submission(
        task_id=malicious_task_id,
        code=malicious_code,
        test_input=10,
        expected_output=10,
        use_hosted=use_hosted,
    )

    if verbose:
        print(f"    Mode:            {sentinel.last_mode}")
        print(f"    Attestation sig: {mal_receipt.signature[:24]}...")
        print(f"    Status:          {'CERTIFIED' if mal_passed else 'REJECTED'}")

    total_ms = (time.perf_counter() - t0) * 1000.0
    expected = passed and not mal_passed

    if verbose:
        print("\n" + "=" * 68)
        outcome = "both verdicts as expected" if expected else "UNEXPECTED VERDICT"
        print(f"  SENTINEL COMPLETE: {outcome} in {total_ms:.1f}ms")
        print("=" * 68 + "\n")

    return 0 if expected else 1


HONEST_CODE = (
    "def solution(n: int) -> int:\n"
    "    a, b = 0, 1\n"
    "    for _ in range(n):\n"
    "        a, b = b, a + b\n"
    "    return a\n"
)
MALICIOUS_CODE = (
    "import os\n"
    "def solution(n: int) -> int:\n"
    "    os.system('cat /etc/passwd')\n"
    "    return n\n"
)


def _brief_tool_output(out: dict[str, Any]) -> dict[str, Any]:
    """Extract compact display fields from a Sentinel tool result."""
    brief = {
        k: v
        for k, v in out.items()
        if k in ("valid", "violations", "passed", "actual_output", "error", "signature", "latency_ms")
    }
    if "signature" in brief:
        brief["signature"] = str(brief["signature"])[:16] + "..."
    if "latency_ms" in brief and isinstance(brief["latency_ms"], float):
        brief["latency_ms"] = round(brief["latency_ms"], 3)
    return brief


def _is_transient_portal_error(exc: Exception) -> bool:
    """Return True for decentralized router/HTTP failures worth retrying once."""
    if isinstance(exc, TimeoutError):
        return True
    haystack = f"{type(exc).__name__}: {exc}"
    return any(
        token in haystack
        for token in (
            "ProviderError",
            "TurnTimeoutError",
            "TimeoutError",
            "HTTP 500",
            "HTTP 502",
            "HTTP 503",
            "HTTP 504",
        )
    )


def _brief_exception(exc: Exception) -> str:
    first_line = str(exc).splitlines()[0] if str(exc) else ""
    summary = f"{type(exc).__name__}: {first_line}" if first_line else type(exc).__name__
    return summary[:100]


def _run_task_with_retries(
    *,
    run_live_task_fn,
    om_module,
    config_path: Path,
    task_id: str,
    code: str,
    test_input: int,
    expected_output: int,
    turn_timeout: float,
    provider: str,
) -> tuple[object, float]:
    """Run one live task with bounded retries on transient Cortensor Portal errors."""
    max_attempts = 3 if provider == "portal" else 1
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        t0 = time.perf_counter()

        def _on_tool_call(tool_name: str, out: dict[str, object], start: float = t0) -> None:
            elapsed = time.perf_counter() - start
            print(
                f"    [+{elapsed:5.1f}s] live tool  {tool_name} -> {json.dumps(_brief_tool_output(out))}",
                flush=True,
            )

        om_module.TOOL_PROGRESS_CALLBACK = _on_tool_call
        try:
            res = run_live_task_fn(
                config_path,
                task_id,
                code,
                test_input,
                expected_output,
                timeout_seconds=turn_timeout,
            )
        except Exception as exc:
            last_exc = exc
            if provider == "portal" and attempt < max_attempts and _is_transient_portal_error(exc):
                print(
                    f"    retry      attempt {attempt}/{max_attempts} ({_brief_exception(exc)}); retrying on Cortensor Portal...",
                    flush=True,
                )
                time.sleep(2)
                continue
            raise
        finally:
            om_module.TOOL_PROGRESS_CALLBACK = None

        dt = time.perf_counter() - t0
        if provider == "portal" and attempt < max_attempts and res.reason.startswith("model "):
            print(
                f"    retry      attempt {attempt}/{max_attempts} ({res.reason[:100]}); retrying on Cortensor Portal...",
                flush=True,
            )
            time.sleep(2)
            continue
        return res, dt

    assert last_exc is not None
    raise last_exc


def run_live_demo(provider: str) -> int:
    """Run the honest and the malicious task through a real model via OpenMinion."""
    from cortensor_validator import openminion_agent as om
    from cortensor_validator.live_agent import run_live_task, write_agent_config
    from cortensor_validator.openminion_agent import query_hosted_portal

    runtime_dir = Path(os.getenv("SENTINEL_RUNTIME_DIR", ".sentinel-runtime"))
    config_path = write_agent_config(provider, runtime_dir)
    cfg = json.loads(config_path.read_text())["providers"]["openai"]
    print("=" * 68, flush=True)
    print("  CORTENSOR TASK SENTINEL, live model run (OpenMinion 0.1 SDK)", flush=True)
    print(f"  provider={provider}  model={cfg['model']}  base_url={cfg['base_url']}", flush=True)
    if provider == "portal":
        probe = query_hosted_portal(base_url=cfg["base_url"].removesuffix("/v1"))
        if probe.get("connected"):
            print(f"  portal     connected=True  models={probe.get('models')}", flush=True)
        else:
            print(f"  portal     connected=False  detail={probe}", flush=True)
    print("=" * 68, flush=True)

    sentinel = CortensorSentinel()
    turn_timeout = 900.0 if provider == "portal" else 400.0
    tasks = [
        ("task-fibonacci-10", HONEST_CODE, 10, 55, True),
        ("task-exploit-attempt", MALICIOUS_CODE, 10, 10, False),
    ]
    all_as_expected = True
    for task_id, code, test_input, expected_output, want in tasks:
        print(f"\n>>> {task_id}: asking the model to verify it", flush=True)
        res, dt = _run_task_with_retries(
            run_live_task_fn=run_live_task,
            om_module=om,
            config_path=config_path,
            task_id=task_id,
            code=code,
            test_input=test_input,
            expected_output=expected_output,
            turn_timeout=turn_timeout,
            provider=provider,
        )
        for name, out in res.tool_calls:
            print(f"    tool call  {name}: {json.dumps(_brief_tool_output(out))}", flush=True)
        print(f"    model says {res.model_text.strip()}", flush=True)
        receipt = sentinel.signer.sign(task_id=task_id, passed=res.passed)
        model_receipts = [o for n, o in res.tool_calls if n == "create_attestation_receipt"]
        if model_receipts and bool(model_receipts[-1].get("passed")) != res.passed:
            print("    WARNING    the model's own receipt disagrees with the tool results; using the tool results", flush=True)
        print(f"    verdict    {'CERTIFIED' if res.passed else 'REJECTED'} ({res.reason})", flush=True)
        print(f"    receipt    {receipt.signature[:24]}...", flush=True)
        s = res.stats
        print(
            f"    cost       {s.get('llm_calls')} LLM calls {res.llm_calls_by_purpose}, "
            f"{s.get('input_tokens')} in / {s.get('output_tokens')} out tokens, {dt:.1f}s",
            flush=True,
        )
        # A rejection only counts if it came from the tools on the submission, not from
        # the model skipping or rewriting (those reasons start with "model ").
        handled = res.passed == want and not res.reason.startswith("model ")
        if not handled:
            print("    NOTE       agent did not complete the workflow on this task (fails closed)", flush=True)
        all_as_expected &= handled

    print("\n" + "=" * 68, flush=True)
    print(f"  LIVE RUN COMPLETE: {'both tasks verified by the agent' if all_as_expected else 'at least one task not completed by the agent'}", flush=True)
    print("=" * 68 + "\n", flush=True)
    return 0 if all_as_expected else 1


def verify_file(
    code_path: Path,
    task_id: str,
    test_input: int,
    expected_output: int,
    verbose: bool = True,
    json_mode: bool = False,
    use_hosted: bool = False,
) -> int:
    """Verify a miner code submission loaded dynamically from a file."""
    if not code_path.exists():
        err_msg = f"Error: File '{code_path}' does not exist."
        if json_mode:
            print(json.dumps({"error": err_msg, "passed": False}))
        else:
            print(err_msg, file=sys.stderr)
        return 1

    code = code_path.read_text(encoding="utf-8")
    sentinel = CortensorSentinel()
    passed, receipt = sentinel.verify_submission(
        task_id=task_id,
        code=code,
        test_input=test_input,
        expected_output=expected_output,
        use_hosted=use_hosted,
    )

    if json_mode:
        data = {
            "task_id": receipt.task_id,
            "status": "CERTIFIED" if passed else "REJECTED",
            "passed": passed,
            "validator_id": receipt.validator_id,
            "epoch": receipt.epoch,
            "signature": receipt.signature,
            "timestamp_ns": receipt.timestamp_ns,
            "verification_mode": sentinel.last_mode,
        }
        print(json.dumps(data, indent=2))
    elif verbose:
        status_str = "CERTIFIED" if passed else "REJECTED"
        print(f"Task: {task_id} | Status: {status_str} | Mode: {sentinel.last_mode} | Sig: {receipt.signature[:24]}...")

    return 0 if passed else 2


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Cortensor Subnet Task Sentinel")
    parser.add_argument("--code-file", type=Path, default=None, help="Path to code submission")
    parser.add_argument("--task-id", type=str, default="task-custom-01", help="Task identifier")
    parser.add_argument("--input", type=int, default=10, help="Test input integer")
    parser.add_argument("--expected", type=int, default=55, help="Expected output integer")
    parser.add_argument("--hosted", action="store_true", help="Route verification through hosted Cortensor API if CORTENSOR_API_KEY is present")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON receipt")
    parser.add_argument("--quiet", action="store_true", help="Quiet mode")
    parser.add_argument("--live", action="store_true", help="Run the demo tasks through a real model via the OpenMinion agent")
    parser.add_argument("--provider", choices=["local", "portal"], default="local", help="Model provider preset for --live")
    args = parser.parse_args()

    if args.live:
        sys.exit(run_live_demo(args.provider))

    if args.code_file is not None:
        sys.exit(
            verify_file(
                code_path=args.code_file,
                task_id=args.task_id,
                test_input=args.input,
                expected_output=args.expected,
                verbose=not args.quiet,
                json_mode=args.json,
                use_hosted=args.hosted,
            )
        )

    sys.exit(run_demo(verbose=not args.quiet, use_hosted=args.hosted))


if __name__ == "__main__":
    main()
