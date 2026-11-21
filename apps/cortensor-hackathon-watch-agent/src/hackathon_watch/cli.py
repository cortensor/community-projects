"""CLI: hackathon-watch check | list | memory | probe."""

from __future__ import annotations

from pathlib import Path

import typer
from rich import print as rprint

from .baseline import load_baseline
from .check import format_report, run_check
from .config import fix_proxy_env, resolve_provider
from .llm_client import DirectClient
from .memory import WatchMemory
from .probe import render_building_blocks_doc, run_probes
from .sources import SOURCES

app = typer.Typer(help="Hackathon Watch — spot newly listed hackathons "
                       "and give a preliminary suitability call.")

DEFAULT_SOURCES = "dorahacks,devfolio,kaggle"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _memory_path(state_dir: str | None) -> Path:
    if state_dir:
        return Path(state_dir) / "memory.json"
    return _repo_root() / "state" / "memory.json"


def _baseline_dir(baseline_dir: str | None) -> Path:
    if baseline_dir:
        return Path(baseline_dir)
    return _repo_root() / "data"


@app.command()
def check(
    sources: str = typer.Option(DEFAULT_SOURCES, "--sources",
                                help="Comma-separated: dorahacks,devfolio,kaggle"),
    state_dir: str | None = typer.Option(None, "--state-dir"),
    baseline_dir: str | None = typer.Option(None, "--baseline-dir"),
    preset: str = typer.Option("openai-compatible", "--preset"),
    live_classify: bool = typer.Option(
        False, "--live-classify",
        help="Call the model for new entries the rule screen left unsure "
             "(max --max-model-calls, one short call each). Off = rules only."),
    max_model_calls: int = typer.Option(5, "--max-model-calls"),
    no_seed: bool = typer.Option(False, "--no-seed",
                                 help="Do not seed empty memory from baseline."),
) -> None:
    """Fetch the public list pages, diff vs memory, print new + suitable."""
    fix_proxy_env()
    memory = WatchMemory(_memory_path(state_dir))
    baseline = None if no_seed else _baseline_dir(baseline_dir)
    client = None
    if live_classify:
        client = DirectClient(resolve_provider(preset))
    report = run_check(
        [s.strip() for s in sources.split(",") if s.strip()],
        memory, baseline_dir=baseline, live_classify=live_classify,
        max_model_calls=max_model_calls, client=client)
    rprint(format_report(report))
    rprint(f"\nMemory now holds {len(memory)} known entries "
           f"({_memory_path(state_dir)}).")


@app.command(name="list")
def list_baseline(
    baseline_dir: str | None = typer.Option(None, "--baseline-dir"),
    limit: int = typer.Option(0, "--limit", help="0 = all"),
) -> None:
    """List the baseline's currently-open entries (reads baseline files)."""
    entries, stats = load_baseline(_baseline_dir(baseline_dir))
    rprint(f"Baseline: {stats['deduped']} open entries "
           f"(from {stats['files']} files, {stats['parsed']} parsed lines).")
    shown = entries if limit <= 0 else entries[:limit]
    for entry in shown:
        line = f"- {entry.name}"
        if entry.url:
            line += f" — {entry.url}"
        rprint(line)
    if limit > 0 and len(entries) > limit:
        rprint(f"... and {len(entries) - limit} more (use --limit 0 for all).")


@app.command()
def probe(
    preset: str = typer.Option("openai-compatible", "--preset"),
    offline: bool = typer.Option(False, "--offline",
                                 help="Skip live model calls (CI-safe)."),
    export_docs: bool = typer.Option(True, "--export-docs/--no-export-docs"),
) -> None:
    """Run the building-block probes and regenerate docs/BUILDING_BLOCKS_TESTED.md."""
    fix_proxy_env()
    provider = resolve_provider(preset)
    results, live_calls, live_tokens = run_probes(provider, offline=offline)
    passed = sum(1 for r in results if r.status == "pass")
    partial = sum(1 for r in results if r.status == "partial")
    failed = sum(1 for r in results if r.status == "fail")
    for r in results:
        rprint(f"[{r.status.upper():7}] {r.name} ({r.duration_ms} ms): {r.evidence}")
    rprint(f"\n{passed} pass / {partial} partial / {failed} fail "
           f"out of {len(results)} probes.")
    if export_docs:
        doc = render_building_blocks_doc(results, provider,
                                         live_calls=live_calls,
                                         live_tokens=live_tokens)
        out = _repo_root() / "docs" / "BUILDING_BLOCKS_TESTED.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(doc, encoding="utf-8")
        rprint(f"Wrote {out}")


_memory_app = typer.Typer(help="Memory export / import.")
app.add_typer(_memory_app, name="memory")


@_memory_app.command("export")
def memory_export(
    dest: str = typer.Option("state/memory-export.json", "--dest"),
    bundle: bool = typer.Option(False, "--bundle",
                                help="Export as an OpenMinion MemoryBundle."),
    state_dir: str | None = typer.Option(None, "--state-dir"),
) -> None:
    """Export memory to a JSON file (or a MemoryBundle with --bundle)."""
    memory = WatchMemory(_memory_path(state_dir))
    if bundle:
        path = memory.export_bundle(dest)
    else:
        path = memory.export_json(dest)
    rprint(f"Exported {len(memory)} entries to {path}")


@_memory_app.command("import")
def memory_import(
    src: str = typer.Argument(...),
    bundle: bool = typer.Option(False, "--bundle",
                                help="Import an OpenMinion MemoryBundle file."),
    state_dir: str | None = typer.Option(None, "--state-dir"),
) -> None:
    """Import memory from a JSON file (or a MemoryBundle with --bundle)."""
    memory = WatchMemory(_memory_path(state_dir))
    if bundle:
        count = memory.import_bundle_file(src)
    else:
        count = memory.import_json(src)
    rprint(f"Imported {count} entries; memory now holds {len(memory)}.")


if __name__ == "__main__":
    app()
