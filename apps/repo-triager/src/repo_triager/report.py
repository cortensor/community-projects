"""Run reports: a machine-readable JSON file and a maintainer-facing Markdown file."""

from __future__ import annotations

import json
from pathlib import Path

from repo_triager.models import RunReport, TriageRecord


def _labels(record: TriageRecord) -> str:
    return ", ".join(f"`{label}`" for label in record.decision.labels) or "—"


def _duplicates(record: TriageRecord) -> str:
    return ", ".join(f"#{number}" for number in record.decision.duplicate_of) or "—"


def render_markdown(report: RunReport) -> str:
    counts = report.summary_counts()
    applied = sum(1 for record in report.records if record.applied)
    lines = [
        f"# Repo Triager report — {report.repo}",
        "",
        f"- Run: `{report.run_id}`",
        f"- Started: {report.started_at}  ·  Finished: {report.finished_at or '—'}",
        f"- Provider: {report.provider or '—'}  ·  Source: {report.source}",
        f"- Session: `{report.session_id}`",
        f"- Issues triaged: {report.issues_seen}  ·  staged plans: {applied}",
        "- Severity mix: " + (", ".join(f"{key} {value}" for key, value in sorted(counts.items())) or "—"),
        "",
        "| Issue | Severity | Component | Type | Labels | Duplicates | Conf. | Staged |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in report.records:
        decision = record.decision
        lines.append(
            "| #{number} {title} | {severity} | {component} | {itype} | {labels} | "
            "{dups} | {conf:.2f} | {staged} |".format(
                number=decision.issue_number,
                title=record.issue_title[:60].replace("|", "\\|"),
                severity=decision.severity,
                component=decision.component or "—",
                itype=decision.issue_type,
                labels=_labels(record),
                dups=_duplicates(record),
                conf=decision.confidence,
                staged="yes" if record.applied else "no",
            )
        )

    for record in report.records:
        decision = record.decision
        lines += [
            "",
            f"## #{decision.issue_number} — {record.issue_title}",
            "",
            f"- Severity **{decision.severity}** — {decision.severity_reason or '—'}",
            f"- Component `{decision.component or 'unassigned'}` · type `{decision.issue_type}`"
            f" · confidence {decision.confidence:.2f} · source `{decision.source}`",
            f"- Labels: {_labels(record)}",
            f"- Duplicates: {_duplicates(record)}"
            + (f" — {decision.duplicate_reason}" if decision.duplicate_reason else ""),
            f"- Next action: `{decision.next_action}`",
        ]
        if record.validation:
            lines.append("- Validation: " + "; ".join(
                f"{problem.field}: {problem.message}" for problem in record.validation
            ))
        if record.policy:
            lines.append(
                "- Policy: "
                + "; ".join(
                    f"{event.get('tool')} → {event.get('decision')} ({event.get('policy')})"
                    for event in record.policy
                )
            )
        if record.outbox:
            lines.append("- Staged files: " + ", ".join(f"`{path}`" for path in record.outbox))
        lines += [
            "",
            "### Reply draft",
            "",
            decision.reply_draft.strip() or "_no draft_",
        ]

    if report.notes:
        lines += ["", "## Notes", ""] + [f"- {note}" for note in report.notes]
    lines.append("")
    return "\n".join(lines)


def write_report(report: RunReport, directory: Path) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "report.json"
    markdown_path = directory / "report.md"
    json_path.write_text(
        json.dumps(report.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return markdown_path, json_path


def load_report(path: Path) -> RunReport:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return RunReport.model_validate(payload)
