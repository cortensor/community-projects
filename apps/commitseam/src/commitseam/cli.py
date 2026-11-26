from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from commitseam.junit_parser import parse_junit_failures
from commitseam.minion_adapter import (
    MissingCredentialsError,
    default_fixture_path,
    diagnose_run,
    resolve_provider_settings,
    run_demo,
)

app = typer.Typer(
    help="CommitSeam CLI — exactly-once local SQLite rerun queue across OpenMinion 0.1.24 crash seams."
)


@app.command()
def demo(
    run_dir: Path = typer.Option(
        Path(".commitseam-run"),
        "--run-dir",
        help="Directory for isolated SQLite queue DB, OpenMinion session store, and audit bundles.",
    ),
    request_id: str = typer.Option(
        "demo-run",
        "--request-id",
        help="Base business request_id shared across crash recovery attempts.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Explicitly approve SQLite rerun queue writes in non-interactive runs.",
    ),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        help="LLM provider: groq, openai (OpenAI/Cortensor/Ollama compatible), or offline.",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help="Override provider model ID.",
    ),
    base_url: Optional[str] = typer.Option(
        None,
        "--base-url",
        help="Override OpenAI-compatible base URL (e.g. Cortensor Portal or local vLLM/Ollama).",
    ),
    receipt_out: Optional[Path] = typer.Option(
        None,
        "--receipt-out",
        help="Optional path to atomically copy the redacted receipt JSON.",
    ),
) -> None:
    """Run approval denial, pre-commit crash (0->1), and post-commit crash (1->1) on sample_junit.xml."""
    resolved_fixture = default_fixture_path()
    try:
        items = parse_junit_failures(resolved_fixture)
    except (FileNotFoundError, OSError, ValueError) as exc:
        typer.echo(f"Fixture error: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    queue_path = run_dir / "queue.sqlite"

    if not yes:
        if not sys.stdin.isatty():
            typer.echo(
                "Refusing to prompt for write approval in a non-TTY session.\n"
                f"Target queue: {queue_path} ({len(items)} failed items from {resolved_fixture.name}).\n"
                "Re-run interactively in a terminal or pass --yes to explicitly approve enqueue writes.",
                err=True,
            )
            raise typer.Exit(code=2)

        typer.echo(f"Approve SQLite rerun enqueue for request_id={request_id}?")
        typer.echo(f"  Target queue: {queue_path}")
        typer.echo(f"  Items ({len(items)}): {', '.join(it.item_id for it in items)}")
        answer = input("Proceed? [y/N]: ").strip().lower()
        if answer not in {"y", "yes"}:
            typer.echo("Operator declined enqueue approval; exiting without writes.")
            raise typer.Exit(code=1)

    try:
        settings = resolve_provider_settings(
            provider=provider,
            model=model,
            base_url=base_url,
        )
        receipt = run_demo(
            run_dir=run_dir,
            fixture_path=resolved_fixture,
            items=items,
            request_id=request_id,
            provider_settings=settings,
            operator_approved=True,
            receipt_out=receipt_out,
        )
    except (MissingCredentialsError, ValueError, RuntimeError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    deny = receipt["scenarios"]["approval_denial"]
    pre = receipt["scenarios"]["pre_commit_crash"]
    post = receipt["scenarios"]["post_commit_crash"]

    typer.echo(f"MODE: {receipt['mode']} | provider={receipt['provider']} | model={receipt['model']}")
    typer.echo(
        f"  1) approval_denial   req={deny['request_id']} committed={deny['committed_enqueue_count']} "
        f"denied_events={deny['denied_events_count']}"
    )
    typer.echo(
        f"  2) pre_commit_crash  req={pre['request_id']} after_crash={pre['after_crash_committed_count']} -> "
        f"final={pre['committed_enqueue_count']} job_id={pre['job_id']} exact_once={pre['exact_once_ok']}"
    )
    typer.echo(
        f"  3) post_commit_crash req={post['request_id']} after_crash={post['after_crash_committed_count']} -> "
        f"final={post['committed_enqueue_count']} action={post['replay_action']} "
        f"job_id={post['initial_committed_job_id']} recovered={post['recovered_job_id']} "
        f"exact_once={post['exact_once_ok']}"
    )
    typer.echo(f"  receipt: {run_dir / 'receipts.json'}")


@app.command()
def diagnose(
    run_dir: Path = typer.Option(
        ...,
        "--run-dir",
        help="Run directory containing queue.sqlite, openminion.sqlite, and memory bundles.",
    ),
    request_id: Optional[str] = typer.Option(
        None,
        "--request-id",
        help="Specific request_id to reconcile (omit to summarize all requests in run_dir).",
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Emit machine-readable JSON reconciliation report.",
    ),
) -> None:
    """Reconcile SQLite queue rows alongside OpenMinion sessions, MemoryBundle, and context_traces."""
    try:
        report = diagnose_run(run_dir, request_id=request_id)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    if as_json:
        typer.echo(json.dumps(report, indent=2, sort_keys=True))
        return

    typer.echo(f"MODE: {report['mode']}")
    if request_id is not None:
        job_ids = [j["job_id"] for j in report["jobs"]]
        creators = [j["created_by_attempt_id"] for j in report["jobs"]]
        typer.echo(
            f"request_id={report['request_id']} expected={report['expected_count']} "
            f"committed={report['committed_enqueue_count']} exact_once={report['exact_once_ok']} "
            f"job_id={','.join(job_ids) or 'none'} created_by_attempt_id={','.join(creators) or 'none'} "
            f"action={report['action']} recovered_job_id={report['recovered_job_id']} "
            f"session_ids={','.join(report['session_ids']) or 'none'} "
            f"memory_bundle_verified={report['memory_bundle_verified']} "
            f"context_traces={report['context_traces']['available']} ({report['context_traces']['trace_count']})"
        )
        return

    for rid, item in report["requests"].items():
        typer.echo(
            f"  {rid}: expected={item['expected_count']} committed={item['committed_enqueue_count']} "
            f"exact_once={item['exact_once_ok']} recovered={item['recovered_job_id']} "
            f"bundle={item['memory_bundle_verified']} traces={item['context_traces']['trace_count']}"
        )


def main() -> None:
    app()
