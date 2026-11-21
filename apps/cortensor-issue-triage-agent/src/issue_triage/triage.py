"""Single-issue deep triage orchestrator.

Two isolated subagent calls, each exactly one model call:

1. **classifier** — issue title + body + a few comments + linked PRs +
   repo labels + CODEOWNERS hints + past decisions for this repo ->
   :class:`TriageVerdict` (type, severity, component, assignee, route,
   confidence + rationale). Input is kept small on purpose so a free
   model can handle it.
2. **drafter** — verdict + issue summary -> :class:`TriageDraft`, a reply
   draft for the maintainer. Never sent automatically.

The two calls share no transcript (isolated contexts, mirroring the
SDK's ``parent_transcript_inherited=False`` rule); the only thing passed
forward is the typed verdict.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from .config import ProviderSettings
from .github_client import GitHubClient, label_names, linked_pr_numbers
from .llm_client import DirectClient, VerdictParseError
from .memory import RepoMemory
from .models import TriageDecision, TriageDraft, TriageVerdict, utcnow_iso

MAX_BODY_CHARS = 3000
MAX_COMMENT_CHARS = 800
MAX_COMMENTS = 5

CLASSIFIER_SYSTEM = (
    "You are an issue triage classifier for an open-source repository. "
    "Read the issue and reply with exactly one JSON object matching the given schema. "
    "Do not invent labels, people, or components that are not in the provided lists. "
    "If the evidence is thin, lower the confidence and say so in the rationale; "
    "never guess a confident answer from nothing. "
    "suggested_labels must only use labels from the repository label list. "
    "assignee must only be a login from the contributor / CODEOWNERS lists, or null."
)

DRAFTER_SYSTEM = (
    "You are a triage assistant drafting a first reply for a repository maintainer. "
    "Write a short, friendly Markdown reply: acknowledge the issue, state the "
    "classification and routing in one line, and ask exactly the follow-up question "
    "the verdict needs (or say what happens next). No promises the project cannot keep. "
    "Reply with exactly one JSON object matching the given schema."
)


def verdict_tool_schema() -> dict[str, Any]:
    """OpenAI function schema for TriageVerdict (also the Pydantic contract)."""
    return {
        "type": "function",
        "function": {
            "name": "submit_triage_verdict",
            "description": "Submit the triage verdict for one GitHub issue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_type": {
                        "type": "string",
                        "enum": ["bug", "feature", "question", "docs", "chore", "duplicate"],
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low"],
                    },
                    "component": {"type": "string"},
                    "suggested_labels": {"type": "array", "items": {"type": "string"}},
                    "assignee": {"type": ["string", "null"]},
                    "route": {
                        "type": "string",
                        "enum": [
                            "needs-maintainer",
                            "needs-info",
                            "good-first-issue",
                            "ready-to-fix",
                            "docs-queue",
                            "close-as-duplicate",
                            "needs-discussion",
                        ],
                    },
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "rationale": {"type": "string"},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                    "duplicate_of": {"type": ["integer", "null"]},
                },
                "required": [
                    "issue_type",
                    "severity",
                    "component",
                    "route",
                    "confidence",
                    "rationale",
                ],
                "additionalProperties": False,
            },
        },
    }


def draft_tool_schema() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "submit_triage_draft",
            "description": "Submit the draft triage reply.",
            "parameters": {
                "type": "object",
                "properties": {
                    "draft": {"type": "string"},
                    "tone": {"type": "string"},
                },
                "required": ["draft"],
                "additionalProperties": False,
            },
        },
    }


def truncate(text: str | None, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n…[truncated, {len(text) - limit} chars omitted]"


@dataclass
class IssueContext:
    repo: str
    number: int
    title: str
    body: str
    author: str
    state: str
    existing_labels: list[str] = field(default_factory=list)
    comments: list[dict[str, str]] = field(default_factory=list)
    linked_prs: list[int] = field(default_factory=list)
    # Fetched PR summaries (number/title/body/state) — empty when the PRs
    # were not fetched (eval mode, or no linked PRs). Numbers alone are in
    # linked_prs; details are real evidence for the classifier.
    linked_pr_details: list[dict[str, Any]] = field(default_factory=list)
    repo_labels: list[str] = field(default_factory=list)
    codeowners: list[tuple[str, list[str]]] = field(default_factory=list)
    contributors: list[str] = field(default_factory=list)
    history: list[TriageDecision] = field(default_factory=list)


def validate_labels(proposed: list[str], repo_labels: list[str]) -> tuple[list[str], list[str]]:
    """Keep only labels that exist in the repo. Returns (kept, dropped).

    A free model invents labels freely; the closed vocabulary is enforced
    here, deterministically, not by hoping the model behaves.
    """
    known = set(repo_labels)
    kept = [label for label in proposed if label in known]
    dropped = [label for label in proposed if label not in known]
    # de-duplicate while preserving order
    kept = list(dict.fromkeys(kept))
    return kept, dropped


def validate_assignee(assignee: str | None, allowed: list[str]) -> str | None:
    if assignee and assignee.lstrip("@") in {a.lstrip("@") for a in allowed}:
        return assignee.lstrip("@")
    return None


class TriageEngine:
    def __init__(
        self,
        llm: DirectClient,
        github: GitHubClient,
        memory: RepoMemory | None = None,
    ):
        self.llm = llm
        self.github = github
        self.memory = memory or RepoMemory()

    # -- context --------------------------------------------------------
    def fetch_repo_cache(self, repo: str) -> dict[str, Any]:
        """Repo-level data fetched once and reused across issues in a run
        (keeps unauthenticated GitHub API use inside the 60 req/hour cap)."""
        cache: dict[str, Any] = {}
        try:
            cache["repo_labels"] = self.github.list_labels(repo)
        except Exception:
            cache["repo_labels"] = []
        try:
            cache["codeowners"] = self.github.get_codeowners(repo)
        except Exception:
            cache["codeowners"] = []
        try:
            cache["contributors"] = [
                c.get("login") for c in self.github.list_contributors(repo) if c.get("login")
            ]
        except Exception:
            cache["contributors"] = []
        return cache

    def fetch_context(
        self, repo: str, number: int, repo_cache: dict[str, Any] | None = None,
        fetch_linked_prs: bool = True,
    ) -> IssueContext:
        issue = self.github.get_issue(repo, number)
        comments_raw = self.github.list_comments(repo, number, per_page=MAX_COMMENTS)
        timeline = self.github.list_timeline(repo, number)
        if repo_cache is None:
            repo_cache = self.fetch_repo_cache(repo)
        history = self.memory.lookup(repo, limit=5)
        linked = linked_pr_numbers(timeline)
        # Linked PR titles/bodies are real evidence for the classifier;
        # numbers alone say nothing. Capped at 2 (unauthenticated GitHub
        # allows 60 req/hour; a triage already uses ~6). Eval passes False
        # to keep its prompt identical to the baseline run.
        linked_details: list[dict[str, Any]] = []
        if fetch_linked_prs:
            for pr_number in linked[:2]:
                try:
                    summary = self.github.get_pull_summary(repo, pr_number)
                except Exception:
                    summary = None
                if summary:
                    linked_details.append(summary)
        return IssueContext(
            repo=repo,
            number=number,
            title=issue.get("title") or "",
            body=issue.get("body") or "",
            author=(issue.get("user") or {}).get("login") or "",
            state=issue.get("state") or "open",
            existing_labels=label_names(issue),
            comments=[
                {
                    "author": (c.get("user") or {}).get("login") or "",
                    "body": truncate(c.get("body"), MAX_COMMENT_CHARS),
                }
                for c in comments_raw
            ],
            linked_prs=linked,
            linked_pr_details=linked_details,
            repo_labels=repo_cache.get("repo_labels") or [],
            codeowners=repo_cache.get("codeowners") or [],
            contributors=repo_cache.get("contributors") or [],
            history=history,
        )

    @staticmethod
    def context_from_fixture(repo: str, issue: dict[str, Any]) -> IssueContext:
        """Build context from a saved raw issue JSON (demo / offline use)."""
        return IssueContext(
            repo=repo,
            number=issue.get("number", 0),
            title=issue.get("title") or "",
            body=issue.get("body") or "",
            author=(issue.get("user") or {}).get("login") or "",
            state=issue.get("state") or "open",
            existing_labels=label_names(issue),
            comments=[
                {
                    "author": (c.get("user") or {}).get("login") or "",
                    "body": truncate(c.get("body"), MAX_COMMENT_CHARS),
                }
                for c in (issue.get("_comments") or [])
            ],
            linked_prs=[],
            repo_labels=issue.get("_repo_labels") or [],
            codeowners=[],
            contributors=issue.get("_contributors") or [],
            history=[],
        )

    # -- prompts --------------------------------------------------------
    def _classifier_messages(
        self, ctx: IssueContext, slim: bool = False, hide_existing_labels: bool = False
    ) -> list[dict[str, str]]:
        history_lines = []
        for d in ctx.history:
            history_lines.append(
                f"- #{d.issue_number} [{d.component}] {d.issue_type}/{d.severity} "
                f"route={d.route} labels={','.join(d.labels)}"
                + (f" assignee={d.assignee}" if d.assignee else "")
            )
        codeowner_lines = [
            f"- {pattern}: {', '.join(owners)}" for pattern, owners in ctx.codeowners[:10]
        ]
        comments = "\n".join(
            f"- @{c['author']}: {c['body']}" for c in ctx.comments
        ) or "(no comments)"
        # Label-blind mode (evaluation): the issue's existing maintainer
        # labels are the ground truth being scored, so they must not reach
        # the model — otherwise the accuracy measures label-copying, not
        # classification. The repo label list stays: it is the closed
        # vocabulary the model must choose from, not the answer.
        if hide_existing_labels:
            existing_line = (
                "Existing labels: (hidden — evaluation mode; "
                "classify from the issue text only)"
            )
        else:
            existing_line = (
                f"Existing labels: {', '.join(ctx.existing_labels) or '(none)'}"
            )
        if ctx.linked_pr_details:
            linked_prs_text = "\n".join(
                f"- #{p['number']} [{p.get('state', '')}]: {p.get('title', '')} — "
                f"{truncate(p.get('body') or '', 400)}"
                for p in ctx.linked_pr_details
            )
        else:
            linked_prs_text = (
                ', '.join(f'#{n}' for n in ctx.linked_prs) or '(none)'
            )
        if slim:
            # minimal prompt for the retry after an output_token_limit error:
            # short body, no comments / history / CODEOWNERS
            user = (
                f"Repository: {ctx.repo}\n"
                f"Issue #{ctx.number} [{ctx.state}] by @{ctx.author}\n"
                f"Title: {ctx.title}\n"
                f"Body:\n{truncate(ctx.body, 1200)}\n\n"
                f"{existing_line}\n"
                f"Repository labels (only these may be suggested): "
                f"{', '.join(ctx.repo_labels[:80]) or '(unknown — suggest none)'}\n\n"
                "Classify this issue. Reply with exactly one short JSON object."
            )
            return [
                {"role": "system", "content": CLASSIFIER_SYSTEM},
                {"role": "user", "content": user},
            ]
        user = (
            f"Repository: {ctx.repo}\n"
            f"Issue #{ctx.number} [{ctx.state}] by @{ctx.author}\n"
            f"Title: {ctx.title}\n"
            f"Body:\n{truncate(ctx.body, MAX_BODY_CHARS)}\n\n"
            f"{existing_line}\n"
            f"Repository labels (only these may be suggested): "
            f"{', '.join(ctx.repo_labels[:80]) or '(unknown — suggest none)'}\n"
            f"Linked PRs:\n{linked_prs_text}\n"
            f"Comments:\n{comments}\n\n"
            f"CODEOWNERS (component -> owners):\n"
            + ("\n".join(codeowner_lines) or "(none)")
            + "\n\nContributors (possible assignees): "
            + (", ".join(ctx.contributors[:15]) or "(unknown)")
            + "\n\nPast triage decisions in this repo (for label/route consistency):\n"
            + ("\n".join(history_lines) or "(none yet)")
            + "\n\nClassify this issue. Reply with exactly one JSON object."
        )
        return [
            {"role": "system", "content": CLASSIFIER_SYSTEM},
            {"role": "user", "content": user},
        ]

    def _drafter_messages(self, ctx: IssueContext, verdict: TriageVerdict) -> list[dict[str, str]]:
        user = (
            f"Repository: {ctx.repo}\n"
            f"Issue #{ctx.number} by @{ctx.author}: {ctx.title}\n"
            f"Issue body (truncated):\n{truncate(ctx.body, 1200)}\n\n"
            f"Verdict: type={verdict.issue_type}, severity={verdict.severity}, "
            f"component={verdict.component}, route={verdict.route}, "
            f"confidence={verdict.confidence:.2f}\n"
            f"Rationale: {verdict.rationale}\n"
            f"Suggested labels: {', '.join(verdict.suggested_labels) or '(none)'}\n"
            f"Suggested assignee: {verdict.assignee or '(none)'}\n\n"
            "Draft the first triage reply. Reply with exactly one JSON object."
        )
        return [
            {"role": "system", "content": DRAFTER_SYSTEM},
            {"role": "user", "content": user},
        ]

    # -- steps ----------------------------------------------------------
    def classify(
        self, ctx: IssueContext, hide_existing_labels: bool = False
    ) -> tuple[TriageVerdict, dict[str, Any]]:
        """One model call (tool_calls channel preferred, text JSON fallback).
        On a validation failure, one correction retry with the error quoted.
        On a provider error (e.g. 400 output_token_limit_exceeded — the free
        model sometimes burns its output budget on reasoning — or the
        `<|constrain|>commentary` 400), one retry with a slimmed prompt in
        a *different request shape* (plain text, no tools, no json_object):
        the upstream caches the constrained-decoding 400 verbatim, so
        re-sending the same shape cannot recover. ``hide_existing_labels``
        is the evaluation mode: the issue's maintainer labels (the ground
        truth) are kept out of the prompt; it changes nothing else."""
        messages = self._classifier_messages(ctx, hide_existing_labels=hide_existing_labels)
        tools = [verdict_tool_schema()]
        try:
            verdict, result = self.llm.chat_typed(
                messages, TriageVerdict, tools=tools, response_format_json=True
            )
        except VerdictParseError as exc:
            correction = messages + [
                {
                    "role": "user",
                    "content": (
                        "Your previous reply could not be validated as a TriageVerdict. "
                        f"Error: {exc}. Reply again with exactly one JSON object "
                        "matching the schema, using only the listed enum values and "
                        "only labels from the repository label list."
                    ),
                }
            ]
            verdict, result = self.llm.chat_typed(
                correction, TriageVerdict, tools=tools, response_format_json=True
            )
        except RuntimeError:
            # provider-side failure: retry once with a *different request
            # shape* (slim prompt, plain text, no tools, no json_object).
            # The `<|constrain|>commentary` HTTP 400 is a constrained-
            # decoding upstream glitch: the upstream caches that exact 400
            # for minutes, so re-sending the identical constrained request
            # cannot recover — verified on #777/#773 in the 2026-11-16
            # eval, where the slim-prompt retry with the same shape failed
            # too. Changing the shape gets a fresh cache key and bypasses
            # constrained decoding entirely; the draft step already uses
            # this fallback for the same error class. The JSON shape is
            # spelled out in the message because, without a tool schema,
            # the model invents key names.
            retry_messages = self._classifier_messages(
                ctx, slim=True, hide_existing_labels=hide_existing_labels
            ) + [
                {
                    "role": "user",
                    "content": (
                        "Your previous reply could not be delivered. Reply "
                        "again with exactly one JSON object and no other "
                        "text, using exactly these keys: issue_type (one "
                        "of bug, feature, question, docs, chore, "
                        "duplicate), severity (one of critical, high, "
                        "medium, low), component (string), suggested_labels "
                        "(array of strings, only from the repository label "
                        "list), assignee (a login or null), route (one of "
                        "needs-maintainer, needs-info, good-first-issue, "
                        "ready-to-fix, docs-queue, close-as-duplicate, "
                        "needs-discussion), confidence (number 0-1), "
                        "rationale (string), evidence (array of strings), "
                        "duplicate_of (an issue number or null)."
                    ),
                }
            ]
            verdict, result = self.llm.chat_typed(
                retry_messages, TriageVerdict, tools=None, response_format_json=False
            )
            return self._finalise_verdict(ctx, verdict, result, slim_retry=True)
        return self._finalise_verdict(ctx, verdict, result)

    def _finalise_verdict(
        self, ctx: IssueContext, verdict: TriageVerdict, result, slim_retry: bool = False
    ) -> tuple[TriageVerdict, dict[str, Any]]:
        kept, dropped = validate_labels(verdict.suggested_labels, ctx.repo_labels)
        if dropped:
            verdict = verdict.model_copy(update={"suggested_labels": kept})
        allowed_people = list(ctx.contributors) + [
            owner for _, owners in ctx.codeowners for owner in owners
        ]
        assignee = validate_assignee(verdict.assignee, allowed_people)
        if assignee != verdict.assignee:
            verdict = verdict.model_copy(update={"assignee": assignee})
        meta = {
            "latency_ms": result.latency_ms,
            "channel": result.channel,
            "model": result.model,
            "usage": result.usage,
            "dropped_labels": dropped,
            "slim_retry": slim_retry,
        }
        return verdict, meta

    def draft(self, ctx: IssueContext, verdict: TriageVerdict) -> tuple[TriageDraft, dict[str, Any]]:
        """One model call, isolated context: only verdict + issue summary.

        On a provider error, retry once with a *different request shape*
        (plain text, no tools, no json_object). The free tier's upstream
        caches some 400s verbatim for minutes (the `<|constrain|>commentary`
        400 returned a byte-identical body — same timestamp — on two
        attempts 45 s apart), so re-sending the identical constrained
        request cannot recover; changing the shape gets a fresh cache key
        and bypasses the constrained-decoding path entirely.
        """
        messages = self._drafter_messages(ctx, verdict)
        try:
            draft_obj, result = self.llm.chat_typed(
                messages,
                TriageDraft,
                tools=[draft_tool_schema()],
                response_format_json=True,
            )
        except RuntimeError:
            # Plain-text retry, with the JSON shape spelled out in the
            # message: without a tool schema the model invents key names
            # (observed: {"message": ...} instead of {"draft": ...}).
            retry_messages = messages + [
                {
                    "role": "user",
                    "content": (
                        "Your previous reply could not be delivered. Reply again "
                        "with exactly one JSON object and no other text, using "
                        'exactly this shape: {"draft": "<markdown reply>", '
                        '"tone": "neutral"}'
                    ),
                }
            ]
            draft_obj, result = self.llm.chat_typed(
                retry_messages,
                TriageDraft,
                tools=None,
                response_format_json=False,
            )
        return draft_obj, {
            "latency_ms": result.latency_ms,
            "channel": result.channel,
            "model": result.model,
            "usage": result.usage,
        }

    def run(
        self,
        ctx: IssueContext,
        via_sdk: bool = False,
        provider: ProviderSettings | None = None,
    ) -> dict[str, Any]:
        """Full single-issue deep triage: classify + draft + record (proposed).

        Classify always uses the paced DirectClient: the SDK has no
        ``response_format`` support, so the free model free-forms its
        classify JSON (invented field names, all-null follow-ups — measured
        2026-11-17, see :mod:`issue_triage.sdk_triage`). With ``via_sdk``
        the *draft* step runs through a real OpenMinion ``Agent.run`` turn;
        if that turn yields no usable draft, fall back to the DirectClient
        draft and record the fallback in ``draft_via`` / ``draft_meta``.
        """
        started = time.monotonic()
        verdict, classify_meta = self.classify(ctx)
        draft_via = "direct"
        if via_sdk and provider is not None:
            from .sdk_triage import run_sdk_draft

            # The SDK turn fires several consecutive provider calls inside
            # a 45 s free-tier window: starting it right after classify
            # means its first internal call lands inside classify's
            # window and 402s (CLI runs 2026-11-17: first call 200, then
            # 9x 402). Wait out the pacing interval first so the turn
            # starts in a fresh window. Best-effort only: the turn still
            # needs more than one 200 inside the window, which the free
            # tier does not allow — see docs/WHAT_WE_LEARNED.md §15.
            # The fallback below still applies if the turn fails.
            self.llm.wait_pacing()
            messages = self._drafter_messages(ctx, verdict)
            sdk_draft, sdk_meta = run_sdk_draft(
                messages[0]["content"], messages[1]["content"], provider
            )
            if sdk_draft is not None:
                draft_obj, draft_meta = sdk_draft, sdk_meta
                draft_via = "sdk-native"
            else:
                draft_obj, draft_meta = self.draft(ctx, verdict)
                draft_meta = {**draft_meta, "sdk_error": sdk_meta.get("error")}
                draft_via = "direct (sdk fallback)"
        else:
            draft_obj, draft_meta = self.draft(ctx, verdict)
        self.memory.record(
            TriageDecision(
                repo=ctx.repo,
                issue_number=ctx.number,
                issue_type=verdict.issue_type,
                severity=verdict.severity,
                component=verdict.component,
                labels=verdict.suggested_labels,
                route=verdict.route,
                assignee=verdict.assignee,
                confidence=verdict.confidence,
                status="proposed",
                decided_at=utcnow_iso(),
            )
        )
        return {
            "repo": ctx.repo,
            "issue_number": ctx.number,
            "title": ctx.title,
            "verdict": verdict,
            "draft": draft_obj,
            "classify_meta": classify_meta,
            "draft_meta": draft_meta,
            "classify_via": "direct",
            "draft_via": draft_via,
            "total_ms": int((time.monotonic() - started) * 1000),
            "llm_calls": self.llm.calls_made,
        }


def snapshot_id_for(repo: str, number: int) -> str:
    import hashlib

    digest = hashlib.sha1(f"{repo}#{number}#{utcnow_iso()}".encode()).hexdigest()[:8]
    return f"{repo.replace('/', '-')}-{number}-{digest}"
