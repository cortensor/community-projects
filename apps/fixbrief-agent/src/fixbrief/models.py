"""Typed data contracts for FixBrief.

The brief schema is the contract between three layers:

1. deterministic Python tools that collect facts from sources,
2. the OpenMinion ``Agent`` (``output_type=RepairBrief``) that reasons
   over those facts with a real model, and
3. the CLI / SQLite store that render and persist the result.

Keeping one pydantic schema for all three means a brief produced by the
model path and a brief produced by the offline deterministic fallback are
validated identically.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Language(str, Enum):
    """Output languages supported by the brief workflow."""

    EN = "en"
    ES = "es"
    PT = "pt"
    AR = "ar"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    PROFESSIONAL = "professional"


class SourceRef(BaseModel):
    """One source the brief is grounded in."""

    title: str = Field(description="Short human-readable source title")
    locator: str = Field(
        description="URL for live sources, or sample filename for offline sources"
    )
    kind: str = Field(
        default="offline-sample",
        description="'live-url' or 'offline-sample'",
    )


class RepairBrief(BaseModel):
    """Structured troubleshooting brief for one device + symptom."""

    device: str = Field(description="Device model, e.g. 'Samsung Galaxy A54'")
    symptom: str = Field(description="Reported symptom, e.g. 'not charging'")
    language: Language = Field(
        default=Language.EN, description="Language of the brief text"
    )
    summary: str = Field(
        description="One or two sentence summary of the problem and likely fix path"
    )
    likely_causes: list[str] = Field(
        default_factory=list,
        description="Most likely root causes, most probable first",
    )
    diagnostic_steps: list[str] = Field(
        default_factory=list,
        description="Ordered checks to confirm the cause before opening the device",
    )
    repair_steps: list[str] = Field(
        default_factory=list,
        description="Ordered repair procedure once the cause is confirmed",
    )
    tools_needed: list[str] = Field(
        default_factory=list, description="Tools and parts required"
    )
    difficulty: Difficulty = Field(
        default=Difficulty.MEDIUM, description="Overall repair difficulty"
    )
    estimated_time_minutes: int = Field(
        default=30, ge=1, description="Estimated hands-on time in minutes"
    )
    safety_warnings: list[str] = Field(
        default_factory=list,
        description="Safety warnings (battery, ESD, data loss, warranty)",
    )
    sources: list[SourceRef] = Field(
        default_factory=list, description="Sources this brief is grounded in"
    )
    generated_by: str = Field(
        default="deterministic-fallback",
        description=(
            "Provenance label: 'openminion:<provider>/<model>' for a "
            "model-backed run, or 'deterministic-fallback' when no model "
            "was used. Never left ambiguous."
        ),
    )


class RepairFacts(BaseModel):
    """Deterministic facts extracted from source text by pure Python.

    This is what the tools hand to the model. The model never fetches or
    parses anything itself; it only reasons over this structure.
    """

    device_hints: list[str] = Field(default_factory=list)
    symptom_hints: list[str] = Field(default_factory=list)
    causes: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    difficulty_signals: list[str] = Field(default_factory=list)
    time_hints_minutes: list[int] = Field(default_factory=list)
    char_count: int = 0
