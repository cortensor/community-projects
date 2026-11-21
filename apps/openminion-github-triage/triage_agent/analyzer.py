from __future__ import annotations

import re

from .models import (
    ChecklistItem,
    IssueAssessment,
    IssueInput,
    ReleaseAssessment,
    ReleaseInput,
    Severity,
)


_SEVERITY_ORDER: dict[Severity, int] = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}

_LABEL_SEVERITY: dict[str, Severity] = {
    "severity: critical": "critical",
    "priority: critical": "critical",
    "p0": "critical",
    "security": "critical",
    "data-loss": "critical",
    "severity: high": "high",
    "priority: high": "high",
    "p1": "high",
    "bug": "medium",
    "regression": "high",
    "severity: medium": "medium",
    "priority: medium": "medium",
    "p2": "medium",
    "severity: low": "low",
    "priority: low": "low",
    "p3": "low",
    "docs": "low",
}

_TEXT_SEVERITY: tuple[tuple[tuple[str, ...], Severity], ...] = (
    (("security", "vulnerability", "credential leak", "data loss", "corruption"), "critical"),
    (("crash", "traceback", "exception", "regression", "cannot start", "deadlock"), "high"),
    (("error", "broken", "fails", "failure", "timeout", "slow"), "medium"),
)

_CATEGORY_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("security", ("security", "vulnerability", "credential", "auth", "permission")),
    ("reliability", ("crash", "exception", "traceback", "deadlock", "hang", "timeout")),
    ("data", ("database", "migration", "corruption", "data loss", "sqlite")),
    ("install", ("install", "pip", "setup", "dependency", "import")),
    ("performance", ("slow", "memory", "cpu", "latency", "performance")),
    ("user-interface", ("button", "screen", "terminal", "display", "layout")),
    ("documentation", ("docs", "readme", "documentation", "typo")),
)

_REPRO_CHECKS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("steps", ("steps to reproduce", "reproduction", "reproduce", "how to reproduce")),
    ("expected", ("expected behavior", "expected result", "expected:")),
    ("actual", ("actual behavior", "actual result", "actual:", "what happened")),
    ("environment", ("environment", "os:", "python version", "version:", "platform")),
    ("logs", ("traceback", "stack trace", "error log", "logs:", "```")),
)


def _raise_severity(current: Severity, candidate: Severity) -> Severity:
    return candidate if _SEVERITY_ORDER[candidate] > _SEVERITY_ORDER[current] else current


def _normalized_labels(labels: list[str]) -> list[str]:
    return [label.strip().lower() for label in labels if label.strip()]


def assess_issue(issue: IssueInput) -> IssueAssessment:
    text = f"{issue.title}\n{issue.body}".lower()
    labels = _normalized_labels(issue.labels)
    severity: Severity = "low"
    rationale: list[str] = []
    risk_flags: list[str] = []
    categories: list[str] = []

    for label in labels:
        mapped = _LABEL_SEVERITY.get(label)
        if mapped is not None:
            severity = _raise_severity(severity, mapped)
            rationale.append(f"label {label!r} maps to {mapped} severity")
        if label.startswith(("area:", "component:")):
            categories.append(label.split(":", 1)[1].strip())

    for terms, mapped in _TEXT_SEVERITY:
        hits = [term for term in terms if term in text]
        if hits:
            severity = _raise_severity(severity, mapped)
            rationale.append(f"text contains {hits[0]!r}")

    for category, terms in _CATEGORY_TERMS:
        if any(term in text for term in terms) and category not in categories:
            categories.append(category)

    if "security" in categories:
        risk_flags.append("security-sensitive")
    if "data" in categories:
        risk_flags.append("data-integrity-sensitive")
    if "regression" in labels:
        risk_flags.append("regression")

    detected: list[str] = []
    for field, terms in _REPRO_CHECKS:
        if any(term in text for term in terms):
            detected.append(field)
    missing = [field for field, _ in _REPRO_CHECKS if field not in detected]
    repro_score = min(100, len(detected) * 20)
    if len(issue.body.strip()) >= 600:
        repro_score = min(100, repro_score + 10)

    if repro_score < 40:
        risk_flags.append("repro-incomplete")
    if not categories:
        categories.append("uncategorized")
    if not rationale:
        rationale.append("no severity labels or strong failure terms matched")

    confidence = min(0.98, 0.58 + len(rationale) * 0.08)
    return IssueAssessment(
        severity=severity,
        confidence=round(confidence, 2),
        categories=sorted(dict.fromkeys(categories)),
        repro_score=repro_score,
        missing_repro_fields=missing,
        risk_flags=sorted(dict.fromkeys(risk_flags)),
        rationale=rationale,
    )


_CHECKBOX_RE = re.compile(r"^\s*[-*]\s+\[([ xX])\]\s+(.+?)\s*$")
_SEMVER_RE = re.compile(
    r"^v?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<pre>[0-9A-Za-z.-]+))?$"
)


def _parse_checklist(body: str) -> list[ChecklistItem]:
    items: list[ChecklistItem] = []
    for line_number, line in enumerate(body.splitlines(), start=1):
        match = _CHECKBOX_RE.match(line)
        if match:
            items.append(
                ChecklistItem(
                    label=match.group(2).strip(),
                    checked=match.group(1).lower() == "x",
                    line_number=line_number,
                )
            )
    return items


def assess_release(release: ReleaseInput) -> ReleaseAssessment:
    blockers: list[str] = []
    warnings: list[str] = []
    tag = release.tag_name.strip()
    match = _SEMVER_RE.match(tag)

    if not tag:
        blockers.append("release tag is empty")
    elif match is None:
        blockers.append("release tag is not semantic versioning")
    if not release.name.strip():
        warnings.append("release name is empty")
    if not release.body.strip():
        warnings.append("release notes are empty")
    if release.draft:
        blockers.append("release is still a draft")
    if not release.assets:
        warnings.append("release has no assets")

    checklist = _parse_checklist(release.body)
    unchecked = [item for item in checklist if not item.checked]
    for item in unchecked:
        blockers.append(f"unchecked release item: {item.label}")
    if not checklist:
        warnings.append("release notes contain no checkbox checklist")

    lower_body = release.body.lower()
    is_major = bool(match and match.group("major") != "0")
    if is_major and "breaking" not in lower_body:
        warnings.append("major release notes do not mention breaking changes")
    if release.prerelease and not tag.lower().startswith(("rc", "beta", "alpha")) and "-" not in tag:
        warnings.append("prerelease flag is set but tag has no prerelease suffix")

    return ReleaseAssessment(
        verdict="hold" if blockers else "ship",
        version=tag,
        prerelease=release.prerelease,
        blockers=blockers,
        warnings=warnings,
        checklist=checklist,
        checked_count=len(checklist) - len(unchecked),
        unchecked_count=len(unchecked),
        asset_count=len(release.assets),
    )

