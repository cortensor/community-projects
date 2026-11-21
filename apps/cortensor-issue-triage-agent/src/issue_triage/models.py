"""Typed models for the issue-triage agent.

Every label-like field is locked with ``Literal`` enums so a free model
cannot invent a value (Pollinations' gpt-oss-20b was observed returning
``"failure"`` for a label that was never in the candidate list).
Suggested GitHub labels are repo-specific, so they stay free strings and
are validated against the repo's real label set in :mod:`issue_triage.triage`.
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

IssueType = Literal["bug", "feature", "question", "docs", "chore", "duplicate"]
Severity = Literal["critical", "high", "medium", "low"]
Route = Literal[
    "needs-maintainer",  # needs a maintainer decision, cannot be auto-routed
    "needs-info",        # ask the reporter for a repro / details first
    "good-first-issue",  # small, well-scoped, safe for a newcomer
    "ready-to-fix",      # clear bug, component + owner known, can start now
    "docs-queue",        # documentation work, docs queue
    "close-as-duplicate",  # duplicate of another issue
    "needs-discussion",  # design / product question, needs discussion first
]

ISSUE_TYPES: tuple[str, ...] = ("bug", "feature", "question", "docs", "chore", "duplicate")
SEVERITIES: tuple[str, ...] = ("critical", "high", "medium", "low")
ROUTES: tuple[str, ...] = (
    "needs-maintainer",
    "needs-info",
    "good-first-issue",
    "ready-to-fix",
    "docs-queue",
    "close-as-duplicate",
    "needs-discussion",
)

# Synonyms the free model returns for the closed enum values, keyed by the
# normalised form (lowercase, spaces/underscores collapsed to "-").
# The model answers "enhancement" for a feature request — a real GitHub
# label — and "documentation" for docs; rejecting those loses the whole
# verdict, while the mapping is unambiguous. Anything not in the map and
# not a valid value still fails validation loudly (see test_models.py).
ENUM_SYNONYMS: dict[str, dict[str, str]] = {
    "issue_type": {
        "enhancement": "feature",
        "feature-request": "feature",
        "new-feature": "feature",
        "bug-report": "bug",
        "defect": "bug",
        "documentation": "docs",
        "doc": "docs",
        "help": "question",
        "support": "question",
    },
    "severity": {
        "blocker": "critical",
        "major": "high",
        "high-priority": "high",
        "minor": "low",
        "trivial": "low",
        "low-priority": "low",
    },
    "route": {},
}


def normalize_enum_value(value: Any, field: str) -> Any:
    """Normalise one enum-like value: lowercase, collapse spaces and
    underscores to "-", then apply the synonym map for that field.
    Non-strings pass through untouched (Pydantic reports them)."""
    if not isinstance(value, str):
        return value
    key = re.sub(r"[\s_]+", "-", value.strip().lower())
    return ENUM_SYNONYMS.get(field, {}).get(key, key)


def normalize_verdict_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalise the enum fields of a raw verdict payload before
    Pydantic validation. Returns a copy; unknown values are left alone
    so validation still rejects them."""
    out = dict(payload)
    for field in ("issue_type", "severity", "route"):
        if field in out:
            out[field] = normalize_enum_value(out[field], field)
    return out


class TriageVerdict(BaseModel):
    """The single-issue deep-triage verdict. Produced by the classifier call."""

    @model_validator(mode="before")
    @classmethod
    def _normalize_enums(cls, data: Any) -> Any:
        # The free model returns maintainer-label synonyms ("enhancement")
        # and formatting variants ("needs_info", "Bug Report"); map them
        # to the closed enums before validation so one synonym does not
        # lose the whole verdict. Unknown values still fail loudly.
        if isinstance(data, dict):
            return normalize_verdict_payload(data)
        return data

    issue_type: IssueType
    severity: Severity
    component: str = Field(
        description="Component / area, e.g. 'area:brain' or a repo path. 'unknown' if unclear."
    )
    suggested_labels: list[str] = Field(default_factory=list)
    assignee: str | None = Field(
        default=None,
        description="Suggested GitHub login to own this issue, or null if no one fits.",
    )
    route: Route
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(description="One or two sentences: why this verdict.")
    evidence: list[str] = Field(
        default_factory=list,
        description="Short quotes / pointers from the issue that support the verdict.",
    )
    duplicate_of: int | None = Field(default=None, description="Issue number if duplicate.")


class TriageDraft(BaseModel):
    """Draft triage reply produced by the drafter call. Never sent automatically."""

    draft: str = Field(description="Markdown reply draft for the maintainer to review.")
    tone: str = "neutral"


class TriageDecision(BaseModel):
    """One past triage decision remembered per repo (see memory.py)."""

    repo: str
    issue_number: int
    issue_type: IssueType
    severity: Severity
    component: str
    labels: list[str] = Field(default_factory=list)
    route: Route
    assignee: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    status: Literal["proposed", "decided"] = "proposed"
    decided_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Snapshot(BaseModel):
    """A pending triage snapshot awaiting human approval (fail-closed gate)."""

    id: str
    repo: str
    issue_number: int
    issue_title: str
    verdict: TriageVerdict
    draft: TriageDraft
    status: Literal["pending", "approved", "rejected", "consumed"] = "pending"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    decided_at: str | None = None
    note: str = ""


class EvalRecord(BaseModel):
    """One eval row: model prediction vs maintainer ground truth."""

    repo: str
    issue_number: int
    title: str
    ground_truth: IssueType
    predicted: IssueType
    severity: Severity
    confidence: float
    correct: bool
    maintainer_labels: list[str] = Field(default_factory=list)
    latency_ms: int = 0


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
