"""CLI entry point for ProofAudit Minion."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from proof_audit.agent import run_proof_audit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proof-audit",
        description="Audit an OpenMinion / Cortensor repository for submission readiness.",
    )
    parser.add_argument(
        "repo_path",
        nargs="?",
        default=".",
        help="Path to the target repository directory (default: current directory).",
    )
    parser.add_argument(
        "--provider",
        default="openrouter",
        choices=["openrouter", "cortensor-portal", "cortensor-router", "custom-openai-compatible"],
        help="OpenMinion provider preset to use.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model ID override for the selected provider.",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Base URL for custom-openai-compatible or endpoint override.",
    )
    parser.add_argument(
        "--probe-url",
        default=None,
        help="Optional separate OpenAI-compatible URL to probe in Stage 1.",
    )
    parser.add_argument(
        "--out-dir",
        default="audit-out",
        help="Directory where facts.json, report.md, and run.txt are written.",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="Optional OpenMinion session ID for continuity.",
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Fail immediately on ProviderError instead of using deterministic offline fallback.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    outcome = run_proof_audit(
        args.repo_path,
        provider=args.provider,
        model=args.model,
        base_url=args.base_url,
        probe_url=args.probe_url,
        out_dir=Path(args.out_dir),
        session_id=args.session_id,
        allow_offline_fallback=not args.no_fallback,
    )

    print(f"Repo: {outcome.report.repo_name}")
    print(f"Verdict: {outcome.report.verdict} ({outcome.report.score}/100)")
    print(f"Session: {outcome.session_id}")
    print(f"Building blocks: {', '.join(outcome.report.building_blocks_detected) or 'none'}")
    print(f"Offline fallback: {outcome.used_offline_fallback}")
    if outcome.out_dir is not None:
        print(f"Artifacts written to: {outcome.out_dir}")
    return 0 if outcome.report.verdict != "BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
