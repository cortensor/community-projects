"""`paper-watch` CLI: deadlines / brief / probe / memory.

- ``deadlines``: list upcoming submission deadlines (default: new ones
  only, then mark them reminded; ``--include-reminded`` shows old ones too).
- ``brief``: multi-source research brief for a topic (model synthesis,
  deterministic template fallback).
- ``probe``: building-block probe suite -> docs/BUILDING_BLOCKS_TESTED.md.
- ``memory``: list / export / import the reminded-set.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import typer

from .agent import run_brief
from .brief import render_brief
from .config import resolve_preset
from .memory import RemindedMemory
from .probe import PROBE_NAMES, render_probes_doc, run_probes
from .store import Deadline, VenueStore
from .topics import match_topic

app = typer.Typer(help="Paper Deadline Watch: CCF venue deadlines + research briefs.")
memory_app = typer.Typer(help="Inspect, export and import the reminded-set.")
app.add_typer(memory_app, name="memory")


def _data_dir() -> Path:
    import os

    override = os.environ.get("PAPER_WATCH_DATA")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent.parent / "data"


def _today() -> date:
    return date.today()


@app.command()
def deadlines(
    within_days: int = typer.Option(120, "--within-days", help="Window in days from today."),
    verbose: bool = typer.Option(False, "--verbose", help="Also list date_unclear rows separately."),
    include_reminded: bool = typer.Option(False, "--include-reminded", help="Show already-reminded deadlines too."),
    no_mark: bool = typer.Option(False, "--no-mark", help="Do not mark shown deadlines as reminded."),
    preset: str = typer.Option(None, "--preset", help="Provider preset (unused by this deterministic command)."),
) -> None:
    """List submission deadlines in the next N days (default 120)."""
    today = _today()
    store = VenueStore.load(_data_dir(), today=today)
    rows = store.upcoming(within_days, today)
    memory = RemindedMemory()
    fresh = [d for d in rows if d.memory_key not in memory]
    shown = rows if include_reminded else fresh
    typer.echo(f"Paper deadlines, next {within_days} days from {today.isoformat()} "
               f"({len(rows)} upcoming, {len(fresh)} new, {len(store.unclear)} date_unclear in table)")
    typer.echo("")
    if not shown:
        typer.echo("No new reminders." if not include_reminded else "No upcoming deadlines in this window.")
    for d in shown:
        mark = " [already reminded]" if d.memory_key in memory else ""
        typer.echo(f"- {d.one_line()}{mark}")
    if verbose and store.unclear:
        typer.echo("")
        typer.echo(f"date_unclear rows ({len(store.unclear)}; no future date in the table, not listed above):")
        for d in store.unclear[:20]:
            typer.echo(f"- {d.abbreviation} [{d.kind}] {d.full_name} — date unclear [date_unclear]")
        if len(store.unclear) > 20:
            typer.echo(f"  ... and {len(store.unclear) - 20} more")
    if shown and not no_mark:
        new = memory.mark([d.memory_key for d in shown])
        typer.echo("")
        typer.echo(f"Marked {new} deadline(s) as reminded (memory: {memory.path}).")


@app.command()
def brief(
    topic: str = typer.Option(..., "--topic", help="Topic, Chinese or English, e.g. 人工智能 / vision."),
    within_days: int = typer.Option(120, "--within-days"),
    preset: str = typer.Option(None, "--preset", help="Provider preset: openai-compatible (default), cortensor-portal, cortensor-router."),
    no_model: bool = typer.Option(False, "--no-model", help="Skip the model; emit the deterministic template brief."),
    save_record: str = typer.Option("", "--save-record", help="Write the run record JSON to this path (fixtures/live_run_*.json)."),
) -> None:
    """Write a short research brief for a topic (model synthesis + citations)."""
    today = _today()
    store = VenueStore.load(_data_dir(), today=today)
    if no_model:
        from .brief import build_template_brief

        rows = store.upcoming(within_days, today)
        matched = match_topic(topic, rows)
        unclear = [d for d in store.unclear if match_topic(topic, [d])]
        result = build_template_brief(topic, matched, unclear_count=len(unclear))
        typer.echo(render_brief(result))
        return
    record: dict = {}
    result = run_brief(topic, store, within_days=within_days, preset=preset, today=today, record=record)
    typer.echo(render_brief(result))
    if record.get("reminder_text"):
        typer.echo("")
        typer.echo("--- reminder ---")
        typer.echo(record["reminder_text"])
    if save_record:
        dest = Path(save_record)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        typer.echo(f"\n[run record saved to {dest}]")
    elif record.get("path") == "template":
        typer.echo(f"\n[model unavailable — template brief shown; reason: {record.get('fallback_reason', '')}]")


@app.command()
def probe(
    preset: str = typer.Option(None, "--preset"),
    skip_model: bool = typer.Option(False, "--skip-model", help="Only run the model-free probes."),
    export_docs: str = typer.Option("", "--export-docs", help="Write docs/BUILDING_BLOCKS_TESTED.md to this path."),
) -> None:
    """Run the building-block probe suite (only blocks this agent uses)."""
    provider = resolve_preset(preset)
    typer.echo(f"Probing with preset {provider.preset} / model {provider.model} ...")
    results = run_probes(preset, skip_model=skip_model, data_dir=_data_dir())
    for r in results:
        typer.echo(f"[{r.status}] {r.name} ({r.duration_ms / 1000:.1f}s): {r.evidence}")
    passed = sum(1 for r in results if r.status == "pass")
    typer.echo(f"\n{passed}/{len(results)} pass.")
    if export_docs:
        dest = Path(export_docs)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(render_probes_doc(results, provider), encoding="utf-8")
        typer.echo(f"Wrote {dest}")
    if any(r.status == "fail" for r in results):
        raise typer.Exit(code=1)


@memory_app.command("list")
def memory_list() -> None:
    """List reminded deadline keys."""
    memory = RemindedMemory()
    typer.echo(f"Memory file: {memory.path} ({len(memory)} reminded)")
    for key in memory.keys():
        typer.echo(f"- {key}")


@memory_app.command("export")
def memory_export(to: str = typer.Option(..., "--to", help="Destination JSON path.")) -> None:
    """Export the reminded-set JSON."""
    dest = RemindedMemory().export_to(to)
    typer.echo(f"Exported to {dest}")


@memory_app.command("import")
def memory_import(from_path: str = typer.Option(..., "--from", help="Source JSON path.")) -> None:
    """Import (merge) a reminded-set JSON."""
    added = RemindedMemory().import_from(from_path)
    typer.echo(f"Imported; {added} new key(s) added.")


@app.command()
def version() -> None:
    """Print the version."""
    from . import __version__

    typer.echo(f"paper-watch {__version__}")


if __name__ == "__main__":
    app()
