from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class IssueInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    number: int
    title: str
    body: str = ""
    state: str = "open"
    labels: list[str] = Field(default_factory=list)
    html_url: str = ""
    user: str = ""
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_github(cls, payload: dict[str, Any]) -> "IssueInput":
        labels = []
        for label in payload.get("labels") or []:
            if isinstance(label, str):
                labels.append(label)
            elif isinstance(label, dict) and label.get("name"):
                labels.append(str(label["name"]))
        user = payload.get("user")
        user_login = user.get("login", "") if isinstance(user, dict) else user
        return cls(
            number=int(payload.get("number") or 0),
            title=str(payload.get("title") or ""),
            body=str(payload.get("body") or ""),
            state=str(payload.get("state") or "open"),
            labels=labels,
            html_url=str(payload.get("html_url") or ""),
            user=str(user_login or ""),
            created_at=str(payload.get("created_at") or ""),
            updated_at=str(payload.get("updated_at") or ""),
        )


class ReleaseInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    tag_name: str
    name: str = ""
    body: str = ""
    draft: bool = False
    prerelease: bool = False
    target_commitish: str = ""
    html_url: str = ""
    assets: list[dict[str, Any]] = Field(default_factory=list)

    @classmethod
    def from_github(cls, payload: dict[str, Any]) -> "ReleaseInput":
        raw_assets = payload.get("assets") or []
        assets = [item for item in raw_assets if isinstance(item, dict)]
        return cls(
            tag_name=str(payload.get("tag_name") or ""),
            name=str(payload.get("name") or ""),
            body=str(payload.get("body") or ""),
            draft=bool(payload.get("draft", False)),
            prerelease=bool(payload.get("prerelease", False)),
            target_commitish=str(payload.get("target_commitish") or ""),
            html_url=str(payload.get("html_url") or ""),
            assets=assets,
        )


Severity = Literal["critical", "high", "medium", "low"]


class IssueAssessment(BaseModel):
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    categories: list[str] = Field(default_factory=list)
    repro_score: int = Field(ge=0, le=100)
    missing_repro_fields: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)


class ChecklistItem(BaseModel):
    label: str
    checked: bool
    line_number: int


class ReleaseAssessment(BaseModel):
    verdict: Literal["ship", "hold"]
    version: str
    prerelease: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checklist: list[ChecklistItem] = Field(default_factory=list)
    checked_count: int = 0
    unchecked_count: int = 0
    asset_count: int = 0


class TriageReport(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: str = "openminion-triage.v1"
    generated_at: str
    kind: Literal["issue", "release"]
    repo: str
    subject: str
    source_url: str = ""
    issue: IssueAssessment | None = None
    release: ReleaseAssessment | None = None
    model_notes: str | None = None
    diagnostics: dict[str, Any] = Field(default_factory=dict)

