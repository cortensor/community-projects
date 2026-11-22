"""Command-line entrypoint for Minionbench Ops."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from src.app import run_minionbench_pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Minionbench Ops OpenMinion 0.1.24 release triage and building-block diagnostics."
    )
    parser.add_argument(
        "--mode",
        choices=("live", "loopback"),
        default="live",
        help="Execution mode: 'live' runs a real neural model; 'loopback' uses deterministic 127.0.0.1 HTTP.",
    )
    parser.add_argument(
        "--workspace",
        default=str(Path(__file__).resolve().parents[1]),
        help="Target workspace root directory.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Verify pipeline in memory without writing output artifacts.",
    )
    args = parser.parse_args(argv)

    report, written = run_minionbench_pipeline(
        workspace_root=Path(args.workspace),
        mode=args.mode,
        write_artifacts=not args.no_write,
    )
    summary = {
        "project": report.target.project_slug,
        "openminion_version": report.openminion_version,
        "live_neural_model": report.live_receipt.live_neural_model,
        "model_id": report.live_receipt.model_id,
        "provider_transport": report.live_receipt.provider_transport,
        "session_id": report.live_receipt.session_id,
        "tool_invocations_count": len(report.live_receipt.tool_invocations),
        "probes_passed": f"{sum(1 for p in report.probes if p.passed)}/{len(report.probes)}",
        "artifacts": written,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
