"""CLI entrypoint for Cortensor Agent Eval."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cortensor_agent_eval.runner import run_eval_suite


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cortensor-eval",
        description="Run deterministic OpenMinion 0.1.24 benchmark evaluations.",
    )
    parser.add_argument(
        "--suite",
        default="openminion-core-v1",
        help="Suite identifier recorded in outputs.",
    )
    parser.add_argument(
        "--provider",
        default="openai",
        choices=[
            "openai",
            "openrouter",
            "cortensor-portal",
            "cortensor-router",
            "groq",
            "ollama",
        ],
        help="OpenMinion ProviderSetupRequest preset.",
    )
    parser.add_argument("--model", default=None, help="Model ID override.")
    parser.add_argument("--base-url", default=None, help="Endpoint base URL override.")
    parser.add_argument("--api-key", default=None, help="Optional API key.")
    parser.add_argument(
        "--out-dir",
        default="eval-out",
        help="Output directory for facts.json, report.md, and memory_bundle.json.",
    )
    parser.add_argument("--session-id", default=None, help="Explicit session ID.")
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Fail fast on ProviderError/TurnTimeoutError instead of offline fallback.",
    )
    parser.add_argument(
        "--allow-private-probe",
        action="store_true",
        help="Allow probing private/loopback endpoints such as local Cortensor Router.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    outcome = run_eval_suite(
        suite_name=args.suite,
        provider=args.provider,
        model=args.model,
        base_url=args.base_url,
        api_key=args.api_key,
        out_dir=Path(args.out_dir),
        session_id=args.session_id,
        allow_offline_fallback=not args.no_fallback,
        allow_private_probe=args.allow_private_probe,
    )
    if args.json:
        print(
            json.dumps(
                {
                    "summary": outcome.summary.model_dump(),
                    "report": outcome.report.model_dump(),
                    "probe": outcome.probe.model_dump(),
                    "used_offline_fallback": outcome.used_offline_fallback,
                },
                indent=2,
            )
        )
    else:
        print(
            f"[{outcome.report.verdict}] {outcome.summary.suite_name}: "
            f"{outcome.summary.passed_cases}/{outcome.summary.total_cases} passed "
            f"(score={outcome.report.score}, report={outcome.report_path})"
        )
    return 0 if outcome.report.verdict != "FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
