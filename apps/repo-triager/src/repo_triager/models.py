"""Typed records shared by the CLI, the tools, and the agent output."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Severity = Literal["S1", "S2", "S3", "S4"]
IssueType = Literal["bug", "enhancement", "question", "documentation", "other"]
NextAction = Literal["ready-to-label", "needs-maintainer-input", "defer"]


class Issue(BaseModel):
    """One GitHub issue, trimmed to what triage needs."""

    model_config = ConfigDict(extra="ignore")

    number: int
    title: str
    body: str = ""
    labels: list[str] = Field(default_factory=list)
    comments: int = 0
    state: str = "open"
    url: str = ""
    created_at: str = ""
    updated_at: str = ""

    @property
    def search_text(self) -> str:
        return f"{self.title}\n{self.body}"


class LabelSpec(BaseModel):
    name: str
    description: str = ""


class RepoSnapshot(BaseModel):
    """A read-only view of one repository, from the API or the offline fixture."""

    repo: str
    captured_at: str = ""
    source: str = ""
    labels: list[LabelSpec] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)

    def issue(self, number: int) -> Issue | None:
        for item in self.issues:
            if item.number == number:
                return item
        return None

    @property
    def label_names(self) -> set[str]:
        return {label.name for label in self.labels}


class DuplicateCandidate(BaseModel):
    number: int
    title: str
    score: float
    reason: str = ""


class TriageDecision(BaseModel):
    """The structured answer the model must produce for one issue."""

    model_config = ConfigDict(extra="ignore")

    issue_number: int
    severity: Severity
    severity_reason: str = ""
    component: str = ""
    issue_type: IssueType = "other"
    duplicate_of: list[int] = Field(default_factory=list)
    duplicate_reason: str = ""
    confidence: float = 0.5
    labels: list[str] = Field(default_factory=list)
    reply_draft: str = ""
    next_action: NextAction = "ready-to-label"
    source: Literal["model", "heuristic-fallback", "heuristic", "cache"] = "model"

    @field_validator("confidence")
    @classmethod
    def _clamp(cls, value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @field_validator("duplicate_of")
    @classmethod
    def _dedupe(cls, value: list[int]) -> list[int]:
        seen: list[int] = []
        for item in value:
            number = int(item)
            if number not in seen:
                seen.append(number)
        return seen


class ValidationProblem(BaseModel):
    field: str
    message: str


class TriageRecord(BaseModel):
    """A decision plus the evidence that produced it, stored per run."""

    decision: TriageDecision
    issue_title: str
    issue_url: str = ""
    validation: list[ValidationProblem] = Field(default_factory=list)
    policy: list[dict] = Field(default_factory=list)
    applied: bool = False
    outbox: list[str] = Field(default_factory=list)
    run_id: str | None = None
    session_id: str | None = None
    llm_calls: int = 0
    tool_calls: int = 0
    elapsed_ms: int = 0


class RunReport(BaseModel):
    run_id: str
    repo: str
    started_at: str
    finished_at: str = ""
    provider: str = ""
    model: str = ""
    source: str = ""
    session_id: str = ""
    records: list[TriageRecord] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @property
    def issues_seen(self) -> int:
        return len(self.records)

    def summary_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in self.records:
            key = record.decision.severity
            counts[key] = counts.get(key, 0) + 1
        return counts
