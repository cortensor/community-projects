"""Deterministic tests for Markdown and JSON artifact rendering."""

from pathlib import Path

from cortensor_route_bench.models import (
    BuildingBlockProbeResult,
    ConsensusVerdict,
    PreflightCheck,
    PreflightReport,
    ProbeMatrixReport,
    RouteBenchSummary,
)
from cortensor_route_bench.reporter import write_all_artifacts


def test_write_all_artifacts_generates_required_files_and_redacts_secrets(tmp_path: Path) -> None:
    preflight = PreflightReport(
        generated_at_utc="2026-11-21T12:00:00+00:00",
        provider="gemini",
        model="gemini-2.5-flash-lite",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        supports_native_tool_calling=True,
        credential_configured=True,
        openminion_version="0.1.23",
        checks=[
            PreflightCheck(
                check_id="sdk.version",
                status="pass",
                summary="OpenMinion 0.1.23 OK Bearer secret_token_12345678",
            )
        ],
        overall_status="ready",
    )
    matrix = ProbeMatrixReport(
        generated_at_utc="2026-11-21T12:01:00+00:00",
        provider="gemini",
        model="gemini-2.5-flash-lite",
        openminion_version="0.1.23",
        total_probes=1,
        passed_probes=1,
        total_elapsed_ms=250.0,
        probes=[
            BuildingBlockProbeResult(
                probe_id="probe_01",
                building_block="APIRuntime Diagnostics",
                status="pass",
                elapsed_ms=250.0,
                summary="Runtime verified.",
            )
        ],
    )
    verdict = ConsensusVerdict(
        task="Verify route",
        decision="READY",
        agreement_score=0.95,
        worker_summaries=["transport_analyst: READY"],
        recommendations=["Keep prompt schema hint"],
        final_summary="Ready for deployment.",
    )
    summary = RouteBenchSummary(
        generated_at_utc="2026-11-21T12:02:00+00:00",
        provider="gemini",
        model="gemini-2.5-flash-lite",
        openminion_version="0.1.23",
        preflight=preflight,
        probe_matrix=matrix,
        consensus_verdict=verdict,
    )

    artifacts_dir = tmp_path / "artifacts"
    docs_dir = tmp_path / "docs"
    written = write_all_artifacts(summary, artifacts_dir=artifacts_dir, docs_dir=docs_dir)

    assert (artifacts_dir / "preflight.json").is_file()
    assert (artifacts_dir / "probe_matrix.json").is_file()
    assert (artifacts_dir / "live_consensus_run.json").is_file()
    assert (artifacts_dir / "BENCHMARK_REPORT.md").is_file()
    assert (docs_dir / "BUILDING_BLOCKS_TESTED.md").is_file()
    assert (docs_dir / "WHAT_WE_LEARNED.md").is_file()
    assert "secret_token_12345678" not in (artifacts_dir / "preflight.json").read_text(encoding="utf-8")
    assert len(written) == 7
