"""Data models for Hackathon Watch.

Everything the agent moves around is a typed Pydantic model so a bad
model reply fails loudly at the parse step instead of silently entering
the alert list.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class HackathonEntry(BaseModel):
    """One hackathon / competition as seen on a public list page."""

    name: str
    url: str
    source: str = ""  # dorahacks | devfolio | kaggle | baseline
    deadline: str | None = None
    prize: str | None = None
    name_source: str = "page"  # "page" = name read off the page; "slug" = derived from URL slug
    notes: str = ""


class SuitabilityVerdict(BaseModel):
    """Preliminary suitability call. NEVER an official conclusion.

    Allen's profile (see README / suitability.py):
    free-only, online-first, non-student adults, LLM / Agent / AI-app /
    legal-AI direction, resident in Singapore / US.
    """

    label: Literal["preliminary", "unsure", "not-suitable"]
    reason: str = Field(max_length=280)
    needs_human_confirmation: bool = True


class KnownEntry(BaseModel):
    """One entry remembered in local memory."""

    key: str
    name: str
    url: str
    source: str = ""
    first_seen: str = ""
    reminded: bool = False
    verdict: str | None = None  # preliminary | unsure | not-suitable | None


class SourceFetchResult(BaseModel):
    source: str
    url: str
    status: str  # ok | unavailable | error
    entries_found: int = 0
    detail: str = ""
    fetched_at: str = ""


class CheckReport(BaseModel):
    checked_at: str = ""
    sources: list[SourceFetchResult] = []
    new_entries: list[HackathonEntry] = []
    alerts: list[HackathonEntry] = []  # new AND preliminary-suitable
    verdicts: dict[str, SuitabilityVerdict] = {}
    model_calls: int = 0
    model_tokens: int = 0
    seeded_from_baseline: bool = False
    note: str = ""
