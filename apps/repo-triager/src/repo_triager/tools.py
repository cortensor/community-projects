"""OpenMinion tools exposed to the triage agent.

Read tools are declared ``min_scope="READ_ONLY"`` so the default action policy
runs them without asking.  ``stage_triage`` is a bare ``@tool``: under
OpenMinion's default policy that is a local write with unknown reversibility,
so the runtime pauses for a policy confirmation and the operator decides.  That
confirmation *is* Repo Triager's human approval gate — there is no other path
that produces a staged plan.
"""

from __future__ import annotations

import contextlib
import contextvars
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from openminion import tool

from repo_triager.heuristics import (
    component_hint,
    issue_type_hint,
    similar_issues,
)
from repo_triager.models import DuplicateCandidate, Issue, RepoSnapshot, TriageDecision


@dataclass
class ToolContext:
    """Everything the tools may read or write for one triage run."""

    repo: str
    snapshot: RepoSnapshot
    outbox_dir: Path
    pending_decision: TriageDecision | None = None
    applied: bool = False
    outbox_paths: list[str] = field(default_factory=list)
    tool_events: list[dict] = field(default_factory=list)

    def issue(self, number: int) -> Issue | None:
        return self.snapshot.issue(number)

    def corpus(self) -> list[Issue]:
        return list(self.snapshot.issues)

    def record(self, name: str, **facts) -> None:
        self.tool_events.append(
            {
                "tool": name,
                "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                **facts,
            }
        )


_CURRENT: contextvars.ContextVar[ToolContext | None] = contextvars.ContextVar(
    "repo_triager_tool_context", default=None
)


def current() -> ToolContext:
    context = _CURRENT.get()
    if context is None:
        raise RuntimeError("no active Repo Triager tool context")
    return context


@contextlib.contextmanager
def use_context(context: ToolContext) -> Iterator[ToolContext]:
    token = _CURRENT.set(context)
    try:
        yield context
    finally:
        _CURRENT.reset(token)


def _trim(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit] + "\n…[trimmed]"


def _issue_payload(issue: Issue, *, body_limit: int = 1400) -> dict:
    return {
        "number": issue.number,
        "title": issue.title,
        "labels": issue.labels,
        "state": issue.state,
        "comments": issue.comments,
        "created_at": issue.created_at,
        "body": _trim(issue.body, body_limit),
    }


# ---------------------------------------------------------------- read tools
@tool(min_scope="READ_ONLY", idempotent=True)
def get_issue(issue_number: int) -> str:
    """Read one issue from the cached repository snapshot."""

    context = current()
    issue = context.issue(issue_number)
    context.record("get_issue", issue_number=issue_number, found=issue is not None)
    if issue is None:
        return json.dumps({"error": f"issue #{issue_number} is not in the snapshot"})
    return json.dumps(_issue_payload(issue), ensure_ascii=False)


@tool(min_scope="READ_ONLY", idempotent=True)
def list_open_issues(limit: int = 10) -> str:
    """List the newest open issues with their current labels."""

    context = current()
    issues = context.corpus()[: max(1, min(50, int(limit)))]
    context.record("list_open_issues", count=len(issues))
    return json.dumps(
        [
            {
                "number": issue.number,
                "title": issue.title,
                "labels": issue.labels,
                "comments": issue.comments,
            }
            for issue in issues
        ],
        ensure_ascii=False,
    )


@tool(min_scope="READ_ONLY", idempotent=True)
def search_duplicate_issues(
    query: str, exclude_issue_number: int = 0, limit: int = 5
) -> str:
    """Search the open issue corpus for textually similar issues."""

    context = current()
    probe = Issue(
        number=int(exclude_issue_number) or -1,
        title=query,
        body=query,
    )
    candidates: list[DuplicateCandidate] = similar_issues(
        probe, context.corpus(), limit=max(1, min(10, int(limit))), threshold=0.15
    )
    context.record(
        "search_duplicate_issues",
        query=query[:120],
        candidates=[candidate.number for candidate in candidates],
    )
    return json.dumps(
        [
            {
                "number": candidate.number,
                "title": candidate.title,
                "score": candidate.score,
                "labels": (context.issue(candidate.number).labels
                           if context.issue(candidate.number) else []),
            }
            for candidate in candidates
        ],
        ensure_ascii=False,
    )


@tool(min_scope="READ_ONLY", idempotent=True)
def label_taxonomy() -> str:
    """Return the repository's own label list and descriptions."""

    context = current()
    context.record("label_taxonomy", count=len(context.snapshot.labels))
    return json.dumps(
        [
            {"name": label.name, "description": _trim(label.description, 140)}
            for label in context.snapshot.labels
        ],
        ensure_ascii=False,
    )


@tool(min_scope="READ_ONLY", idempotent=True)
def triage_precheck(issue_number: int) -> str:
    """Return the deterministic severity and component pre-score for one issue."""

    context = current()
    issue = context.issue(issue_number)
    if issue is None:
        return json.dumps({"error": f"issue #{issue_number} is not in the snapshot"})
    from repo_triager.heuristics import severity_hint

    severity, reasons = severity_hint(issue)
    component, ranked = component_hint(
        issue, available={label.name for label in context.snapshot.labels}
    )
    context.record("triage_precheck", issue_number=issue_number, severity=severity)
    return json.dumps(
        {
            "issue_number": issue_number,
            "severity_suggestion": severity,
            "severity_signals": reasons,
            "component_suggestion": component,
            "component_ranking": [{"component": c, "score": s} for c, s in ranked[:4]],
            "issue_type_suggestion": issue_type_hint(issue),
            "nearest_issues": [
                {"number": candidate.number, "score": candidate.score}
                for candidate in similar_issues(issue, context.corpus(), limit=3)
            ],
        },
        ensure_ascii=False,
    )


# --------------------------------------------------------------- write tool
@tool
def stage_triage(
    issue_number: int,
    severity: str,
    component: str,
    labels: list[str],
    reply_draft: str,
    duplicate_of: list[int] | None = None,
    next_action: str = "ready-to-label",
) -> str:
    """Stage a triage plan for one issue in the local outbox (dry run).

    Nothing is sent to GitHub.  The plan is written to
    ``outbox/<repo>/<issue>.md`` and ``.json`` after the operator approves.
    """

    context = current()
    plan = context.pending_decision
    if plan is None:
        return json.dumps({"error": "no pending decision for this run"})
    if int(issue_number) != plan.issue_number:
        return json.dumps(
            {
                "error": "issue_number does not match the pending decision",
                "expected_issue_number": plan.issue_number,
            }
        )

    problems: list[str] = []
    unknown = [label for label in labels if label not in context.snapshot.label_names]
    if unknown:
        problems.append(f"labels not in the repository taxonomy: {unknown}")
    duplicates = list(duplicate_of or [])
    missing = [number for number in duplicates if context.issue(number) is None]
    if missing:
        problems.append(f"duplicate_of refers to unknown issues: {missing}")
    if problems:
        context.record("stage_triage", issue_number=issue_number, rejected=problems)
        return json.dumps({"error": "plan rejected", "problems": problems})

    issue = context.issue(plan.issue_number)
    assert issue is not None
    staged = plan.model_copy(
        update={
            "labels": list(labels),
            "severity": severity,  # type: ignore[arg-type]
            "component": component,
            "reply_draft": reply_draft,
            "duplicate_of": duplicates,
            "next_action": next_action,  # type: ignore[arg-type]
        }
    )
    repo_slug = context.repo.replace("/", "_")
    directory = context.outbox_dir / repo_slug
    directory.mkdir(parents=True, exist_ok=True)
    stem = f"{issue.number:04d}"
    markdown_path = directory / f"{stem}.md"
    json_path = directory / f"{stem}.json"

    markdown = render_plan_markdown(staged, issue)
    markdown_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(
        json.dumps(staged.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    context.applied = True
    context.outbox_paths = [str(markdown_path), str(json_path)]
    context.record(
        "stage_triage",
        issue_number=issue_number,
        labels=list(labels),
        outbox=context.outbox_paths,
    )
    return json.dumps(
        {
            "staged": True,
            "issue_number": issue.number,
            "labels": list(labels),
            "files": context.outbox_paths,
        },
        ensure_ascii=False,
    )


def render_plan_markdown(decision: TriageDecision, issue: Issue) -> str:
    labels = ", ".join(f"`{label}`" for label in decision.labels) or "—"
    duplicates = ", ".join(f"#{number}" for number in decision.duplicate_of) or "none"
    return "\n".join(
        [
            f"# Triage plan — #{issue.number} {issue.title}",
            "",
            f"- Repository issue: {issue.url or '(offline snapshot)'}",
            f"- Severity: **{decision.severity}** ({decision.severity_reason})",
            f"- Component: `{decision.component or 'unassigned'}`",
            f"- Type: `{decision.issue_type}`",
            f"- Labels to add: {labels}",
            f"- Possible duplicates: {duplicates}",
            f"- Confidence: {decision.confidence:.2f}",
            f"- Next action: `{decision.next_action}`",
            "- Mode: **dry run** — staged locally, nothing was written to GitHub",
            "",
            "## Reply draft",
            "",
            decision.reply_draft.strip() or "_no draft_",
            "",
        ]
    )


READ_TOOLS = [
    get_issue,
    list_open_issues,
    search_duplicate_issues,
    label_taxonomy,
    triage_precheck,
]

WRITE_TOOLS = [stage_triage]

TOOL_NAMES = [item.tool_decl.name for item in READ_TOOLS + WRITE_TOOLS]
