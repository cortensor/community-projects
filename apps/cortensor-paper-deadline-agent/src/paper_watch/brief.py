"""Deterministic brief construction + honesty-checked rendering.

The brief has two layers, kept visibly separate:
1. **Deterministic layer** (always present, never model-written): the
   citation table — venue, CCF grade, deadline, verification status,
   source URL — built straight from the CSVs.
2. **Synthesis layer** (2–3 short paragraphs): either model-written via
   the OpenMinion agent (``agent.py``) or the deterministic template below
   when the model is unavailable. The template is labelled as a template.

Honesty rule, enforced by :func:`render_brief` and unit-tested: every
deadline line carries its verification status, and the word "verified"
appears *only* next to rows whose status really is ``verified``. A
``date_unclear`` row never appears as a dated deadline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .store import DATE_UNCLEAR, Deadline

__all__ = ["Brief", "build_template_brief", "render_brief", "check_honesty"]


@dataclass
class Brief:
    topic: str
    deadlines: list[Deadline] = field(default_factory=list)
    paragraphs: list[str] = field(default_factory=list)
    synthesis_source: str = "template"  # template | model
    model_name: str = ""
    total_matching: int = 0
    unclear_count: int = 0

    @property
    def nearest(self) -> Deadline | None:
        dated = [d for d in self.deadlines if d.deadline_date is not None]
        return min(dated, key=lambda d: d.deadline_date) if dated else None

    @property
    def a_level(self) -> list[Deadline]:
        return [d for d in self.deadlines if d.ccf_grade == "A"]


def build_template_brief(topic: str, deadlines: list[Deadline], unclear_count: int = 0) -> Brief:
    """Deterministic 2–3 paragraph synthesis from the citation table."""
    dated = [d for d in deadlines if d.deadline_date is not None]
    paragraphs: list[str] = []
    if not dated:
        paragraphs.append(
            f'No upcoming submission deadline was found for topic "{topic}" '
            "in the verified venue tables. Nothing was invented to fill the gap."
        )
        return Brief(
            topic=topic, deadlines=[], paragraphs=paragraphs,
            synthesis_source="template", total_matching=0, unclear_count=unclear_count,
        )
    nearest = min(dated, key=lambda d: d.deadline_date)
    paragraphs.append(
        f'The nearest deadline for "{topic}" is {nearest.abbreviation} '
        f"({nearest.full_name}), {nearest.deadline_kind} deadline "
        f"{nearest.deadline_date.isoformat()}"
        + (f" ({nearest.track})" if nearest.track else "")
        + f", CCF grade {nearest.ccf_grade or 'ungraded'} "
        f"[verification: {nearest.status}]."
    )
    a_level = [d for d in dated if d.ccf_grade == "A"]
    if a_level:
        names = ", ".join(
            f"{d.abbreviation} ({d.deadline_date.isoformat()})" for d in a_level
        )
        paragraphs.append(f"A-level venues in scope: {names}.")
    else:
        paragraphs.append("No A-level venue is in scope for this topic.")
    watch = [d for d in dated if d.status != "verified"]
    if watch:
        paragraphs.append(
            "Watch out: the following venue(s) carry dates that have NOT "
            "been re-verified against the official site (see the status "
            "column) — confirm on the official page before planning around "
            "them: " + ", ".join(f"{d.abbreviation}" for d in watch) + "."
        )
    else:
        paragraphs.append(
            "All dates in this brief were verified against the venues' "
            "official pages on 2026-11-16."
        )
    return Brief(
        topic=topic, deadlines=dated, paragraphs=paragraphs,
        synthesis_source="template", total_matching=len(dated),
        unclear_count=unclear_count,
    )


def render_brief(brief: Brief) -> str:
    """Render the full brief text (citation table + synthesis)."""
    lines = [f"# Research brief: {brief.topic}", ""]
    tag = "model synthesis" if brief.synthesis_source == "model" else "template synthesis (no model used)"
    lines.append(f"Synthesis: {tag}" + (f" — model {brief.model_name}" if brief.model_name else ""))
    lines.append("")
    for para in brief.paragraphs:
        lines.append(para)
        lines.append("")
    lines.append("## Deadlines (deterministic, from the verified CSVs)")
    lines.append("")
    if not brief.deadlines:
        lines.append("No matching upcoming deadlines.")
    for d in brief.deadlines:
        lines.append(f"- {d.one_line()}")
    if brief.unclear_count:
        lines.append("")
        lines.append(
            f"Note: {brief.unclear_count} matching venue(s) have no future "
            "date in the table (date_unclear) and are not listed above."
        )
    lines.append("")
    lines.append(
        "Verification key: [verified] = date checked against the official "
        "page 2026-11-16; [cycle_not_announced] = next cycle not yet "
        "announced, date is from the last known cycle; [not_found] = no "
        "authoritative date found; [date_unclear] = no future date parsable."
    )
    return "\n".join(lines)


def _line_abbreviation(line: str) -> str:
    """Abbreviation of a rendered deadline line (``- ABBR [...]``).

    Matched as the first token only: substring search would false-positive
    on venues whose *full name* contains another venue's abbreviation
    (e.g. ICWSM's full name contains "AAAI").
    """
    if not line.startswith("- "):
        return ""
    parts = line[2:].split(" ", 1)
    return parts[0] if parts else ""


def _line_identity(line: str) -> tuple[str, str]:
    """(abbreviation, full_name) of a rendered deadline line.

    Identity needs the full name too: two different venues can share an
    abbreviation (FSE = Foundations of Software Engineering vs Fast
    Software Encryption), and one of them may be dated while the other
    is unclear.
    """
    abbr = _line_abbreviation(line)
    if not abbr:
        return ("", "")
    rest = line[2 + len(abbr):].strip()
    # rest is "[GRADE] Full Name — kind deadline ..."
    if rest.startswith("["):
        close = rest.find("]")
        if close >= 0:
            rest = rest[close + 1:].strip()
    name = rest.split(" — ", 1)[0].strip()
    return (abbr, name)


def check_honesty(text: str, deadlines: list[Deadline]) -> list[str]:
    """Return a list of honesty violations in a rendered brief.

    Violations: a deadline line without a status tag; the word "verified"
    describing a row whose status is not ``verified``; a ``date_unclear``
    row rendered with a date.
    """
    problems: list[str] = []
    by_identity = {(d.abbreviation, d.full_name): d for d in deadlines}
    for line in text.splitlines():
        if not line.startswith("- "):
            continue
        if "[" not in line or "]" not in line:
            problems.append(f"deadline line without status tag: {line}")
            continue
        d = by_identity.get(_line_identity(line))
        if d is not None and d.deadline_date is None and "date unclear" not in line:
            problems.append(f"unclear row rendered with a date: {line}")
        if d is not None and d.status != "verified" and "[verified]" in line:
            problems.append(f"unverified venue labelled verified: {line}")
    return problems
