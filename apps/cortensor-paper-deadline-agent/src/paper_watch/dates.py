"""Robust parsing of the dirty deadline text in the verified CSVs.

The source cells are free text, e.g.::

    "2026-10-25 (Long); 2026-11-16 (Short)"
    "ARR submission deadline: 2027-01-04; ACL commitment deadline: TBD"
    "Mar 30, 2026 (AoE, firm)"
    "rolling - no fixed deadline (journal submissions)"

Rules (no invented dates, ever):
- A cell is split on ';' into segments; each segment may hold one date
  plus an optional track label in parentheses.
- ISO dates (YYYY-MM-DD) and English month names ("Mar 30, 2026",
  "30 Mar 2026") are recognised.
- Only dates >= ``today`` count as future. A row with no future date
  yields ``None`` and is reported as ``date_unclear`` upstream.
- When several future dates exist, the earliest wins and the track label
  of its segment is kept, so the caller can say "(Short track)".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

__all__ = ["DatedEntry", "parse_deadline_cell", "earliest_future"]

_ISO_RE = re.compile(r"(20\d\d)-(\d\d)-(\d\d)")
_MONTHS = (
    "jan", "feb", "mar", "apr", "may", "jun",
    "jul", "aug", "sep", "oct", "nov", "dec",
)
_MONTH_RE = re.compile(
    r"(?P<m1>Jan[a-z]*|Feb[a-z]*|Mar[a-z]*|Apr[a-z]*|May|Jun[a-z]*|Jul[a-z]*|"
    r"Aug[a-z]*|Sep[a-z]*|Oct[a-z]*|Nov[a-z]*|Dec[a-z]*)\s+"
    r"(?P<d1>\d{1,2}),\s*(?P<y1>20\d\d)"
    r"|(?P<d2>\d{1,2})\s+"
    r"(?P<m2>Jan[a-z]*|Feb[a-z]*|Mar[a-z]*|Apr[a-z]*|May|Jun[a-z]*|Jul[a-z]*|"
    r"Aug[a-z]*|Sep[a-z]*|Oct[a-z]*|Nov[a-z]*|Dec[a-z]*)\s+"
    r"(?P<y2>20\d\d)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DatedEntry:
    """One parsed date plus the track label of its ';' segment."""

    date: date
    track: str = ""
    raw_segment: str = ""


def _month_number(name: str) -> int:
    return _MONTHS.index(name[:3].lower()) + 1


def _dates_in_segment(segment: str) -> list[date]:
    found: list[date] = []
    for m in _ISO_RE.finditer(segment):
        try:
            found.append(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        except ValueError:
            continue  # e.g. 2026-02-30: skip, never invent a corrected date
    for m in _MONTH_RE.finditer(segment):
        try:
            if m.group("m1"):
                found.append(
                    date(int(m.group("y1")), _month_number(m.group("m1")), int(m.group("d1")))
                )
            else:
                found.append(
                    date(int(m.group("y2")), _month_number(m.group("m2")), int(m.group("d2")))
                )
        except ValueError:
            continue
    return found


def _track_of(segment: str) -> str:
    """Parenthetical label of a segment, minus the date itself."""
    labels = re.findall(r"\(([^()]*)\)", segment)
    cleaned = []
    for lab in labels:
        lab = lab.strip()
        if not lab:
            continue
        if _ISO_RE.search(lab) or _MONTH_RE.search(lab):
            continue
        cleaned.append(lab)
    return "; ".join(cleaned)


def parse_deadline_cell(cell: str | None) -> list[DatedEntry]:
    """Parse every date in a free-text deadline cell, in cell order."""
    if not cell or not cell.strip():
        return []
    entries: list[DatedEntry] = []
    for segment in str(cell).split(";"):
        segment = segment.strip()
        if not segment:
            continue
        track = _track_of(segment)
        for d in _dates_in_segment(segment):
            entries.append(DatedEntry(date=d, track=track, raw_segment=segment))
    return entries


def earliest_future(cell: str | None, today: date) -> DatedEntry | None:
    """Earliest date >= today in the cell, or None if there is none."""
    future = [e for e in parse_deadline_cell(cell) if e.date >= today]
    if not future:
        return None
    return min(future, key=lambda e: e.date)
