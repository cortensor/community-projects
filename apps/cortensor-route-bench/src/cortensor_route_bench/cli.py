"""Command-line entry point for Cortensor Route Bench."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from .config import (
    ensure_openminion_config,
    load_dotenv_file,
    resolve_model,
    resolve_provider_profile,
    run_preflight,
)
from .models import ProbeMatrixReport, RouteBenchSummary
from .probes import run_building_block_probes
from .reporter import write_all_artifacts
from .workflow import run_consensus_benchmark

DEFAULT_TASK = (
    "Verify OpenMinion 0.1.23 SDK readiness, Cortensor Portal compatibility posture, "
    "and rate-limit resilience for autonomous builder workflows."
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cortensor-route-bench",
        description="OpenMinion 0.1 SDK building-block probe suite & multi-agent route consensus verifier.",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="Provider preset ID (gemini, cortensor-portal, cortensor-router, openrouter, groq, ollama).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model ID override for preflight/probes (defaults to provider's recommended live model).",
    )
    parser.add_argument(
        "--bench-model",
        default=None,
        help="Optional separate model ID for multi-agent consensus bench (helps spread free-tier RPD quotas).",
    )
    parser.add_argument(
        "--config-path",
        type=Path,
        default=Path(".openminion") / "config.yaml",
        help="Path to OpenMinion YAML config.",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=Path("artifacts"),
        help="Directory for JSON & Markdown execution artifacts.",
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path("docs"),
        help="Directory for generated BUILDING_BLOCKS_TESTED.md and WHAT_WE_LEARNED.md.",
    )
    parser.add_argument(
        "--pace-seconds",
        type=float,
        default=1.5,
        help="Cooldown seconds between sequential live model requests.",
    )

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("preflight", help="Run deterministic provider & SDK preflight checks.")
    sub.add_parser("probe", help="Run all 10 live OpenMinion 0.1 SDK building-block probes.")

    bench_p = sub.add_parser("bench", help="Run the multi-agent PoI-style consensus benchmark.")
    bench_p.add_argument("--task", default=DEFAULT_TASK, help="Verification task prompt.")

    all_p = sub.add_parser("run-all", help="Run preflight, 10 SDK probes, consensus benchmark, and export artifacts.")
    all_p.add_argument("--task", default=DEFAULT_TASK, help="Verification task prompt.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Execute the requested Cortensor Route Bench CLI subcommand."""
    load_dotenv_file()
    parser = _build_parser()
    args = parser.parse_args(argv)

    profile = resolve_provider_profile(args.provider)
    model = resolve_model(profile, args.model)

    if args.command == "preflight":
        report = run_preflight(provider=profile.provider_id, model=model, config_path=args.config_path)
        print(json.dumps(report.model_dump(mode="json"), indent=2))
        return 0 if report.overall_status != "blocked" else 2

    preflight = run_preflight(provider=profile.provider_id, model=model, config_path=args.config_path)
    if preflight.overall_status == "blocked":
        print(json.dumps(preflight.model_dump(mode="json"), indent=2), file=sys.stderr)
        return 2

    ensure_openminion_config(args.config_path, profile, model)
    preflight = run_preflight(provider=profile.provider_id, model=model, config_path=args.config_path)

    probe_matrix = None
    consensus = None
    consensus_telemetry = None
    bench_model = (args.bench_model or "").strip() or model

    if args.command in {"probe", "run-all"}:
        print(f"[cortensor-route-bench] Running 10 OpenMinion SDK probes ({profile.provider_id} / {model})...")
        probe_matrix = run_building_block_probes(
            config_path=str(args.config_path),
            provider=profile.provider_id,
            model=model,
            pace_seconds=args.pace_seconds,
        )
        print(
            f"[cortensor-route-bench] Probes finished: {probe_matrix.passed_probes}/{probe_matrix.total_probes} "
            f"passed in {probe_matrix.total_elapsed_ms:.2f} ms."
        )
        # Flush probe artifacts immediately before running multi-agent consensus.
        partial_summary = RouteBenchSummary(
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            provider=profile.provider_id,
            model=model,
            openminion_version=preflight.openminion_version,
            preflight=preflight,
            probe_matrix=probe_matrix,
        )
        write_all_artifacts(
            partial_summary,
            artifacts_dir=args.artifacts_dir,
            docs_dir=args.docs_dir,
        )

    if args.command in {"bench", "run-all"}:
        if probe_matrix is None:
            existing_matrix = args.artifacts_dir / "probe_matrix.json"
            if existing_matrix.is_file():
                probe_matrix = ProbeMatrixReport.model_validate_json(
                    existing_matrix.read_text(encoding="utf-8")
                )
        task_prompt = getattr(args, "task", DEFAULT_TASK)
        print(f"[cortensor-route-bench] Running multi-agent consensus benchmark ({profile.provider_id} / {bench_model})...")
        consensus, consensus_telemetry = run_consensus_benchmark(
            config_path=str(args.config_path),
            provider=profile.provider_id,
            model=bench_model,
            task=task_prompt,
            pace_seconds=args.pace_seconds,
        )
        print(
            f"[cortensor-route-bench] Consensus decision: {consensus.decision} "
            f"(agreement={consensus.agreement_score:.2f})."
        )

    summary = RouteBenchSummary(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        provider=profile.provider_id,
        model=model,
        openminion_version=preflight.openminion_version,
        preflight=preflight,
        probe_matrix=probe_matrix,
        consensus_verdict=consensus,
        telemetry=consensus_telemetry or {},
    )
    written = write_all_artifacts(
        summary,
        artifacts_dir=args.artifacts_dir,
        docs_dir=args.docs_dir,
        consensus_telemetry=consensus_telemetry,
    )
    print("[cortensor-route-bench] Exported artifacts:")
    for label, path in written.items():
        print(f"  - {label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
