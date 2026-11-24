"""Deterministic triage heuristics.

The agent is the part that reasons, writes, and decides.  These helpers give
it (and the operator) a grounded starting point: a severity pre-score, the
component candidates derived from the repository's own ``area:*`` labels, and
a similarity search over the open issue corpus.  Every helper is pure and
unit-tested, so a weak or unavailable model cannot turn the pipeline into
guesswork.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from repo_triager.models import (
    DuplicateCandidate,
    Issue,
    LabelSpec,
    Severity,
)

#: Words that raise or lower severity, with the weight applied per hit.
SEVERITY_SIGNALS: tuple[tuple[str, int, str], ...] = (
    (r"\bdata loss\b|\bcorrupt(?:s|ed|ion)?\b", 3, "data-loss wording"),
    (r"\bsecurity\b|\bcredential\b|\bsecret\b|\bleak(?:s|ed)?\b|\bexploit\b", 3, "security wording"),
    (r"\bsilently\b|\bsilent\b|\bno error\b|\bswallow(?:s|ed)?\b", 2, "silent failure wording"),
    (r"\bcrash(?:es|ed)?\b|\btraceback\b|\bexception\b|<Error>", 2, "crash wording"),
    (r"\bwrong\b|\bincorrect\b|\bmisclassif(?:y|ies|ied)\b|\bdrops?\b|\bignores?\b", 2, "incorrect-result wording"),
    (r"\bcannot\b|\bunable to\b|\bfails?\b|\bfailed\b|\bbroken\b|\bdoes not\b|\bdoesn't\b", 1, "feature-failure wording"),
    (r"\bhang(?:s|ing)?\b|\bdeadlock\b|\bwedge(?:s|d)?\b|\bleak(?:s|ed)? (?:memory|disk)\b", 2, "hang/resource wording"),
    (r"\bregression\b|\bwas working\b|\bused to\b", 1, "regression wording"),
    (r"\btypo\b|\bdocs?\b|\bdocumentation\b|\breadme\b", -2, "documentation wording"),
    (r"\bnit\b|\bcosmetic\b|\bminor\b", -1, "cosmetic wording"),
)

#: Component keywords per ``area:*`` label.  Extend from the repository's own
#: label descriptions with ``repo-triager labels --explain``.
AREA_KEYWORDS: dict[str, tuple[str, ...]] = {
    "area:approvals": ("approval", "approvals", "confirmation", "policy", "grant", "consent", "prompt"),
    "area:artifacts": ("artifact", "artifacts", "omx", "bundle", "storage bundle"),
    "area:brain": ("brain", "memory", "context", "planning", "completion", "freshness", "reflect", "judge"),
    "area:config": ("config", "configuration", "agents.json", "settings", "yaml", "provider config"),
    "area:identity": ("identity", "profile", "persona", "bundle import"),
    "area:mcp": ("mcp", "model context protocol", "server", "stdio", "sampling"),
    "area:providers": ("provider", "providers", "llm", "adapter", "openai", "anthropic", "ollama", "model"),
    "area:runtime": ("runtime", "turn", "lifecycle", "cancellation", "gateway", "replay", "checkpoint", "daemon"),
    "area:scheduling": ("schedule", "scheduler", "cron", "task", "tasks", "recurring"),
    "area:sdk": ("sdk", "agent(", "output_type", "approval_callback", "python api", "subagent", "handoff"),
    "area:sessions": ("session", "sessions", "thread", "continuity", "compact", "transcript"),
    "area:skills": ("skill", "skills", "skill.md", "ingest"),
    "area:tools": ("tool", "tools", "tool call", "registration", "schema", "ssm", "fetch url", "file."),
}

STOPWORDS = frozenset(
    """
    a an and are as at be been before by can does do for from has have how i if
    in into is it its may not of on or so than that the their them then there
    these they this to too was were what when which while who why will with
    without would you your
    """.split()
)

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_.:-]*")


def tokenize(text: str) -> set[str]:
    tokens = {match.group(0).strip("._:-") for match in TOKEN_RE.finditer(text.lower())}
    return {token for token in tokens if len(token) > 2 and token not in STOPWORDS}


def severity_score(issue: Issue) -> tuple[int, list[str]]:
    """Return a 0..10 severity score and the signals that produced it."""

    text = issue.search_text.lower()
    score = 3
    reasons: list[str] = []
    for pattern, weight, label in SEVERITY_SIGNALS:
        hits = len(re.findall(pattern, text, flags=re.IGNORECASE))
        if hits:
            score += weight if hits == 1 else weight + 1
            reasons.append(f"{label} x{hits}")
    lowered = {label.lower() for label in issue.labels}
    if "bug" in lowered:
        score += 1
        reasons.append("labelled bug")
    if "enhancement" in lowered:
        score -= 2
        reasons.append("labelled enhancement")
    if "documentation" in lowered:
        score -= 2
        reasons.append("labelled documentation")
    if any(label.startswith("status:awaiting-release") for label in lowered):
        score -= 1
        reasons.append("fix already merged")
    return max(0, min(10, score)), reasons


def severity_from_score(score: int) -> Severity:
    if score >= 8:
        return "S1"
    if score >= 6:
        return "S2"
    if score >= 3:
        return "S3"
    return "S4"


def severity_hint(issue: Issue) -> tuple[Severity, list[str]]:
    score, reasons = severity_score(issue)
    return severity_from_score(score), reasons


def component_scores(issue: Issue) -> list[tuple[str, int]]:
    """Rank ``area:*`` components by keyword overlap with the issue."""

    title = issue.title.lower()
    body = issue.body.lower()
    labels = {label.lower() for label in issue.labels}
    scores: list[tuple[str, int]] = []
    for area, keywords in AREA_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in title:
                score += 4
            hits = body.count(keyword)
            if hits:
                score += min(3, hits)
        if area in labels:
            score += 12
        if score:
            scores.append((area, score))
    scores.sort(key=lambda item: (-item[1], item[0]))
    return scores


def component_hint(issue: Issue, available: set[str] | None = None) -> tuple[str, list[tuple[str, int]]]:
    ranked = component_scores(issue)
    if available:
        ranked = [item for item in ranked if item[0] in available]
    return (ranked[0][0] if ranked else ""), ranked


def issue_type_hint(issue: Issue) -> str:
    lowered = {label.lower() for label in issue.labels}
    text = issue.search_text.lower()
    if "documentation" in lowered or re.search(r"\bdocs?\b|\breadme\b|\btypo\b", text):
        return "documentation"
    if "question" in lowered or text.strip().endswith("?"):
        return "question"
    if "enhancement" in lowered or text.startswith("feature") or "add " in text[:120]:
        return "enhancement"
    if "bug" in lowered or re.search(r"\bfail|\berror|\bcrash|\bbroken|\bwrong\b", text):
        return "bug"
    return "other"


def similarity(left: Issue | str, right: Issue | str) -> float:
    """Blend title edit distance, title token overlap, and body overlap.

    The score is a *candidate* generator, not a verdict: 0.5 to 0.7 usually
    means the same defect, 0.2 to 0.3 means the same area, and below 0.18 is
    noise.  Repo Triager reports candidates and lets the model (and then the
    maintainer) decide.
    """

    left_issue = left if isinstance(left, Issue) else Issue(number=-1, title=left, body=left)
    right_issue = (
        right if isinstance(right, Issue) else Issue(number=-2, title=right, body=right)
    )
    title_ratio = SequenceMatcher(
        None, left_issue.title.lower(), right_issue.title.lower()
    ).ratio()
    left_title = tokenize(left_issue.title)
    right_title = tokenize(right_issue.title)
    title_overlap = (
        len(left_title & right_title) / min(len(left_title), len(right_title))
        if left_title and right_title
        else 0.0
    )
    left_body = tokenize(left_issue.body[:400])
    right_body = tokenize(right_issue.body[:400])
    body_overlap = (
        len(left_body & right_body) / min(len(left_body), len(right_body))
        if left_body and right_body
        else 0.0
    )
    return round(0.5 * title_ratio + 0.35 * title_overlap + 0.15 * body_overlap, 4)


def similar_issues(
    issue: Issue,
    corpus: list[Issue],
    *,
    limit: int = 5,
    threshold: float = 0.18,
) -> list[DuplicateCandidate]:
    candidates: list[DuplicateCandidate] = []
    for other in corpus:
        if other.number == issue.number:
            continue
        score = similarity(issue, other)
        if score >= threshold:
            candidates.append(
                DuplicateCandidate(
                    number=other.number,
                    title=other.title,
                    score=score,
                    reason=f"token/sequence similarity {score:.2f}",
                )
            )
    candidates.sort(key=lambda item: (-item.score, item.number))
    return candidates[:limit]


def labels_for_decision(
    issue: Issue,
    severity: Severity,
    component: str,
    issue_type: str,
    taxonomy: list[LabelSpec],
    duplicates: list[int],
    *,
    max_labels: int = 4,
) -> list[str]:
    """Compose a label set restricted to the repository's own taxonomy."""

    known = {label.name for label in taxonomy}
    chosen: list[str] = []

    def add(name: str) -> None:
        if name and name in known and name not in chosen and len(chosen) < max_labels:
            chosen.append(name)

    type_label = {
        "bug": "bug",
        "enhancement": "enhancement",
        "question": "question",
        "documentation": "documentation",
    }.get(issue_type)
    add(type_label or "")
    if component:
        add(component)
    if duplicates:
        add("duplicate")
    if severity in {"S1", "S2"} and len(chosen) < max_labels:
        add("help wanted")
    return chosen


def heuristic_decision(
    issue: Issue,
    taxonomy: list[LabelSpec],
    corpus: list[Issue],
) -> tuple:
    """Build a deterministic fallback decision for one issue."""

    from repo_triager.models import TriageDecision  # local import keeps models import-light

    severity, reasons = severity_hint(issue)
    component, ranked = component_hint(issue, available={label.name for label in taxonomy})
    issue_type = issue_type_hint(issue)
    duplicates = [
        candidate.number
        for candidate in similar_issues(issue, corpus, limit=3)
        if candidate.score >= 0.45
    ]
    labels = labels_for_decision(issue, severity, component, issue_type, taxonomy, duplicates)
    confidence = 0.55 if component else 0.3
    decision = TriageDecision(
        issue_number=issue.number,
        severity=severity,
        severity_reason="; ".join(reasons) or "no strong signal",
        component=component,
        issue_type=issue_type,  # type: ignore[arg-type]
        duplicate_of=duplicates,
        duplicate_reason="; ".join(
            f"#{candidate.number} {candidate.score:.2f}"
            for candidate in similar_issues(issue, corpus, limit=3)
        ),
        confidence=confidence,
        labels=labels,
        reply_draft=(
            f"Thanks for the detailed report on #{issue.number}. "
            "We are classifying this as "
            f"{severity} in {component or 'unassigned area'}."
        ),
        next_action="needs-maintainer-input" if confidence < 0.4 else "ready-to-label",
        source="heuristic",
    )
    return decision, ranked
