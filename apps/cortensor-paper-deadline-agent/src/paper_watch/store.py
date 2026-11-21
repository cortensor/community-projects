"""Load the verified venue tables and build one unified deadline list.

Sources (copied verbatim into ``data/``, see ``data/README.md``):
- ``deadlines-all-conferences.csv`` — 390 CCF conferences, one row each.
- ``journals-submission.csv`` — 295 CCF journals.
- ``law-submission.csv`` — 24 law venues (21 + 3 SSCI, mostly non-CCF).

Verification status is carried verbatim from the CSV ``status`` column
(``verified`` / ``cycle_not_announced`` / ``not_found``) and is *never*
upgraded by this module. A row with no future date at all becomes a
``date_unclear`` record: it is counted and reported, but it never enters
an upcoming-deadline list.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from .dates import earliest_future

__all__ = ["Deadline", "VenueStore", "VERIFIED", "CYCLE_NOT_ANNOUNCED", "NOT_FOUND", "DATE_UNCLEAR"]

VERIFIED = "verified"
CYCLE_NOT_ANNOUNCED = "cycle_not_announced"
NOT_FOUND = "not_found"
DATE_UNCLEAR = "date_unclear"

_KNOWN_STATUSES = {VERIFIED, CYCLE_NOT_ANNOUNCED, NOT_FOUND}


@dataclass(frozen=True)
class Deadline:
    """One venue + one (earliest future) submission deadline."""

    abbreviation: str
    full_name: str
    kind: str  # conference | journal | law
    ccf_grade: str
    field: str
    deadline_date: date | None  # None -> date_unclear
    deadline_kind: str  # full | abstract | fixed | unclear
    track: str
    timezone: str
    status: str  # verified | cycle_not_announced | not_found | date_unclear
    source_url: str
    website: str
    raw_text: str = ""

    @property
    def memory_key(self) -> str:
        """Dedup key for the reminded-set: venue + date + deadline kind."""
        d = self.deadline_date.isoformat() if self.deadline_date else "no-date"
        return f"{self.abbreviation}|{d}|{self.deadline_kind}"

    def one_line(self) -> str:
        """Render with verification status always attached (honesty rule)."""
        if self.deadline_date is None:
            when = "date unclear — no future date in the table"
        else:
            when = self.deadline_date.isoformat()
            if self.track:
                when += f" ({self.track})"
        grade = self.ccf_grade or "ungraded"
        return (
            f"{self.abbreviation} [{grade}] {self.full_name} — "
            f"{self.deadline_kind} deadline {when} "
            f"[{self.status}] {self.source_url or self.website}"
        )


@dataclass
class VenueStore:
    """All deadlines from the three CSVs, plus the unclear ones."""

    deadlines: list[Deadline] = field(default_factory=list)
    unclear: list[Deadline] = field(default_factory=list)

    @classmethod
    def load(cls, data_dir: str | Path, today: date | None = None) -> "VenueStore":
        data_dir = Path(data_dir)
        today = today or date.today()
        store = cls()
        store._load_conferences(data_dir / "deadlines-all-conferences.csv", today)
        store._load_fixed(data_dir / "journals-submission.csv", kind="journal", today=today)
        store._load_fixed(data_dir / "law-submission.csv", kind="law", today=today)
        store._dedupe()
        return store

    def _dedupe(self) -> None:
        """Drop exact cross-file duplicates (same venue + same date).

        CLSR appears in both the journals and the law table with the
        identical name and fixed deadline; it is one venue, not two.
        Same-abbreviation *different* venues (FSE, SEC) are NOT deduped:
        the full name is part of the key.
        """
        seen: set[tuple[str, str, str, str]] = set()
        kept: list[Deadline] = []
        for d in self.deadlines:
            key = (
                d.abbreviation,
                d.full_name,
                d.deadline_date.isoformat() if d.deadline_date else "",
                d.deadline_kind,
            )
            if key in seen:
                continue
            seen.add(key)
            kept.append(d)
        self.deadlines = kept

    # -- loaders ---------------------------------------------------------
    def _load_conferences(self, path: Path, today: date) -> None:
        with open(path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                abbr = (row.get("abbreviation") or "").strip()
                # 18 journal rows have no abbreviation; fall back to the
                # full name so the venue is not silently dropped.
                ident = abbr or (row.get("full_name") or "").strip()
                if not ident:
                    continue
                status = (row.get("status") or "").strip() or NOT_FOUND
                full = earliest_future(row.get("full_deadline"), today)
                if full is not None:
                    self.deadlines.append(self._conf_row(row, full, "full", status))
                    continue
                abstract = earliest_future(row.get("abstract_deadline"), today)
                if abstract is not None:
                    self.deadlines.append(self._conf_row(row, abstract, "abstract", status))
                    continue
                self.unclear.append(
                    self._conf_row(row, None, "unclear", DATE_UNCLEAR)
                )

    def _conf_row(self, row, entry, deadline_kind, status) -> Deadline:
        abbr = (row.get("abbreviation") or "").strip()
        return Deadline(
            abbreviation=abbr or (row.get("full_name") or "").strip(),
            full_name=(row.get("full_name") or "").strip(),
            kind="conference",
            ccf_grade=(row.get("ccf_grade") or "").strip(),
            field=(row.get("field") or "").strip(),
            deadline_date=entry.date if entry else None,
            deadline_kind=deadline_kind,
            track=entry.track if entry else "",
            timezone=(row.get("deadline_timezone") or "").strip(),
            status=status if status in _KNOWN_STATUSES or status == DATE_UNCLEAR else NOT_FOUND,
            source_url=(row.get("source_url") or "").strip(),
            website=(row.get("website") or "").strip(),
            raw_text=(row.get("full_deadline") or "").strip(),
        )

    def _load_fixed(self, path: Path, kind: str, today: date) -> None:
        with open(path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                abbr = (row.get("abbreviation") or "").strip()
                ident = abbr or (row.get("full_name") or "").strip()
                if not ident:
                    continue
                status = (row.get("status") or "").strip() or NOT_FOUND
                fixed = earliest_future(row.get("fixed_deadline"), today)
                if fixed is None:
                    self.unclear.append(
                        Deadline(
                            abbreviation=ident,
                            full_name=(row.get("full_name") or "").strip(),
                            kind=kind,
                            ccf_grade=(row.get("ccf_grade") or "").strip(),
                            field=(row.get("field") or "").strip(),
                            deadline_date=None,
                            deadline_kind="unclear",
                            track="",
                            timezone="",
                            status=DATE_UNCLEAR,
                            source_url=(row.get("source_url") or "").strip(),
                            website=(row.get("website") or "").strip(),
                            raw_text=(row.get("fixed_deadline") or "").strip(),
                        )
                    )
                    continue
                self.deadlines.append(
                    Deadline(
                        abbreviation=ident,
                        full_name=(row.get("full_name") or "").strip(),
                        kind=kind,
                        ccf_grade=(row.get("ccf_grade") or "").strip(),
                        field=(row.get("field") or "").strip(),
                        deadline_date=fixed.date,
                        deadline_kind="fixed",
                        track=fixed.track,
                        timezone="",
                        status=status if status in _KNOWN_STATUSES else NOT_FOUND,
                        source_url=(row.get("source_url") or "").strip(),
                        website=(row.get("website") or "").strip(),
                        raw_text=(row.get("fixed_deadline") or "").strip(),
                    )
                )

    # -- queries ---------------------------------------------------------
    def upcoming(self, within_days: int, today: date | None = None) -> list[Deadline]:
        """Deadlines in [today, today + within_days], earliest first."""
        today = today or date.today()
        end = today + timedelta(days=within_days)
        rows = [
            d for d in self.deadlines
            if d.deadline_date is not None and today <= d.deadline_date <= end
        ]
        return sorted(rows, key=lambda d: (d.deadline_date, d.abbreviation))

    def by_abbreviation(self, abbr: str) -> Deadline | None:
        want = abbr.strip().upper()
        for d in self.deadlines:
            if d.abbreviation.upper() == want:
                return d
        for d in self.unclear:
            if d.abbreviation.upper() == want:
                return d
        return None

    def counts(self) -> dict[str, int]:
        from collections import Counter

        c = Counter(d.status for d in self.deadlines)
        c[DATE_UNCLEAR] += len(self.unclear)
        return dict(c)
