"""Check orchestration: fetch -> diff vs memory -> screen -> alert.

Deterministic work (fetch, parse, normalise, dedupe, rule screen) never
touches the model. The model is only called for entries the rule screen
left ``unsure`` (or, with --model-all, for every new entry), at most
``max_model_calls`` per run, one short call each. First run with empty
memory seeds memory from the baseline so the 171 known entries are not
all reported as "new" at once.
"""

from __future__ import annotations

from pathlib import Path

from . import suitability
from .baseline import dedupe_key, load_baseline
from .llm_client import DirectClient, RateLimitedError, VerdictParseError
from .memory import WatchMemory
from .models import CheckReport, HackathonEntry, SourceFetchResult, SuitabilityVerdict, utcnow_iso
from .normalize import entry_key
from .sources import SOURCES, SourceUnavailable, fetch_source


def seed_memory_from_baseline(memory: WatchMemory,
                              baseline_dir: str | Path) -> int:
    entries, _stats = load_baseline(baseline_dir)
    count = 0
    seen_urls: dict[str, str] = {}
    for entry in entries:
        key = dedupe_key(entry, seen_urls)
        if not memory.known(key):
            memory.record(key, entry.name, entry.url, source="baseline",
                          first_seen="2026-11-16T00:00:00+00:00")
            count += 1
    return count


def run_check(sources: list[str], memory: WatchMemory,
              baseline_dir: str | Path | None = None,
              live_classify: bool = False,
              max_model_calls: int = 5,
              client: DirectClient | None = None,
              html_overrides: dict[str, str] | None = None) -> CheckReport:
    report = CheckReport(checked_at=utcnow_iso())
    if baseline_dir is not None and len(memory) == 0:
        seeded = seed_memory_from_baseline(memory, baseline_dir)
        report.seeded_from_baseline = True
        report.note = (f"Memory was empty; seeded {seeded} known entries "
                       "from the 2026-11-16 baseline so they are not "
                       "reported as new.")

    html_overrides = html_overrides or {}
    fetched: list[HackathonEntry] = []
    for source in sources:
        if source not in SOURCES:
            report.sources.append(SourceFetchResult(
                source=source, url="", status="error",
                detail=f"unknown source {source!r}"))
            continue
        try:
            outcome = fetch_source(
                source, html_override=html_overrides.get(source))
        except SourceUnavailable as exc:
            report.sources.append(SourceFetchResult(
                source=source, url=SOURCES[source]["list_url"],
                status="unavailable", detail=str(exc),
                fetched_at=utcnow_iso()))
            continue
        except Exception as exc:  # network error etc. — record, don't crash
            report.sources.append(SourceFetchResult(
                source=source, url=SOURCES[source]["list_url"],
                status="error", detail=f"{type(exc).__name__}: {exc}",
                fetched_at=utcnow_iso()))
            continue
        report.sources.append(SourceFetchResult(
            source=source, url=outcome.url, status="ok",
            entries_found=len(outcome.entries), detail=outcome.detail,
            fetched_at=utcnow_iso()))
        fetched.extend(outcome.entries)

    # Dedupe across sources by key; new = key absent from memory.
    seen_keys: set[str] = set()
    for entry in fetched:
        key = entry_key(entry.url, entry.name)
        if key in seen_keys or memory.known(key):
            continue
        seen_keys.add(key)
        report.new_entries.append(entry)

    model_budget = max_model_calls if live_classify and client is not None else 0
    if model_budget > 0:
        # Spend the scarce model budget first on entries whose names hint
        # at the direction (Agent/LLM/AI); the rest keep the rule verdict.
        hints = ("agent", "llm", "legal")
        report.new_entries.sort(
            key=lambda e: 0 if any(h in e.name.lower() for h in hints) else 1)
    for entry in report.new_entries:
        key = entry_key(entry.url, entry.name)
        rule_verdict = suitability.rule_screen(entry)
        verdict = rule_verdict
        if model_budget > 0 and rule_verdict.label == "unsure":
            # Model only for entries the rule screen could not decide;
            # a model failure falls back to the rule verdict, never to
            # an invented label.
            try:
                verdict = client.classify(
                    SuitabilityVerdict,
                    suitability.build_classify_messages(entry),
                    tools=suitability.verdict_tool_schema())
                model_budget -= 1
                report.model_calls = client.calls_made
                report.model_tokens = client.tokens_used
            except (RateLimitedError, VerdictParseError, RuntimeError):
                verdict = rule_verdict
        report.verdicts[key] = verdict
        memory.record(key, entry.name, entry.url, source=entry.source,
                      first_seen=report.checked_at,
                      verdict=verdict.label,
                      reminded=verdict.label == "preliminary")
        if verdict.label == "preliminary":
            report.alerts.append(entry)
            memory.mark_reminded(key)
    return report


def format_report(report: CheckReport) -> str:
    lines = [f"Hackathon Watch check — {report.checked_at}",
             f"Model calls: {report.model_calls}  tokens: {report.model_tokens}"]
    if report.note:
        lines.append(report.note)
    for src in report.sources:
        lines.append(f"{src.source}: {src.status}: {src.detail}")
    lines.append(f"New entries: {len(report.new_entries)}")
    if report.alerts:
        lines.append("")
        lines.append("NEW AND PRELIMINARY-SUITABLE (verify on the official "
                     "page before registering):")
        for entry in report.alerts:
            verdict = report.verdicts.get(entry_key(entry.url, entry.name))
            reason = verdict.reason if verdict else ""
            lines.append(f"- {entry.name} ({entry.source})")
            lines.append(f"  {entry.url}")
            if entry.deadline:
                lines.append(f"  deadline: {entry.deadline}")
            if entry.prize:
                lines.append(f"  prize: {entry.prize}")
            lines.append(f"  preliminary reason: {reason}")
    elif report.new_entries:
        lines.append("No new entry passed the preliminary screen; all new "
                     "entries are unsure / not-suitable — see verdicts.")
    else:
        lines.append("No new hackathons found on the checked sources.")
    return "\n".join(lines)
