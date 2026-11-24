"""Scripts for the offline scripted model.

The scripted model is a **stand-in for the hosted model**, not a stub of the
runtime: every OpenMinion call (`Agent.run`, tool dispatch, the action policy,
the approval gate, session and memory services) still runs for real.  Only the
generated token stream is predetermined, which makes the demo and the test
suite reproducible without a credential.

Decisions here are authored per fixture issue to look like a careful
maintainer's answer; issues without an authored script fall back to the
deterministic heuristics so the pipeline always has an answer.
"""

from __future__ import annotations

import json
from typing import Any

from repo_triager.heuristics import (
    component_hint,
    heuristic_decision,
    issue_type_hint,
    labels_for_decision,
    severity_hint,
)
from repo_triager.models import Issue, RepoSnapshot, TriageDecision

#: Hand-authored decisions for the issues used by the demo.
AUTHORED: dict[int, dict[str, Any]] = {
    859: {
        "severity": "S2",
        "severity_reason": "A malformed plugin contract version is accepted instead of rejected, so a broken plugin loads and fails later.",
        "component": "area:tools",
        "issue_type": "bug",
        "duplicate_of": [],
        "duplicate_reason": "",
        "confidence": 0.78,
        "labels": ["bug", "area:tools"],
        "reply_draft": (
            "Thanks for the precise report — the contract-version check should reject "
            "an explicit but malformed version before any plugin module is imported, "
            "and right now it falls through to the lenient path.\n\n"
            "We are tracking this as an S2: a bad plugin can load successfully and "
            "then fail during the first tool call, which is much harder to diagnose. "
            "I have added `area:tools` and put it in front of the plugin loader work; "
            "no timeline yet, but I will comment here when a branch is up."
        ),
        "next_action": "ready-to-label",
    },
    853: {
        "severity": "S2",
        "severity_reason": "Structured output is unusable with any real provider because the schema never reaches the model.",
        "component": "area:sdk",
        "issue_type": "bug",
        "duplicate_of": [],
        "duplicate_reason": "",
        "confidence": 0.85,
        "labels": ["bug", "area:sdk"],
        "reply_draft": (
            "Confirmed on 0.1.24: `Agent(output_type=Model)` validates the reply but "
            "the turn never tells the model which schema to answer with, so a hosted "
            "model replies in prose and the client raises a validation error.\n\n"
            "Workaround for anyone hitting this today: put the JSON schema in the "
            "task message and keep `instructions` short. We are treating it as an S2 "
            "SDK defect and will link the fix here."
        ),
        "next_action": "ready-to-label",
    },
    857: {
        "severity": "S3",
        "severity_reason": "A temporary directory is leaked per in-memory session store, which only matters for long-running processes.",
        "component": "area:sessions",
        "issue_type": "bug",
        "duplicate_of": [],
        "duplicate_reason": "Session-storage reports exist (#797, #826) but neither describes this leak.",
        "confidence": 0.62,
        "labels": ["bug", "area:sessions"],
        "reply_draft": (
            "Thanks — `SQLiteSessionStore(':memory:')` does create a temporary "
            "directory that `close()` never removes, so a long-lived process leaks "
            "one directory per store.\n\n"
            "This looks related to the session-cleanup report in #797; I have linked "
            "them and labelled `area:sessions`. It is an S3 for single runs and worth "
            "fixing because our own worker creates a store per turn."
        ),
        "next_action": "needs-maintainer-input",
    },
    834: {
        "severity": "S2",
        "severity_reason": "The local Ollama provider cannot start at all when a proxy environment uses bracketed IPv6 no_proxy entries.",
        "component": "area:providers",
        "issue_type": "bug",
        "duplicate_of": [],
        "duplicate_reason": "",
        "confidence": 0.8,
        "labels": ["bug", "area:providers"],
        "reply_draft": (
            "Reproduced with a `no_proxy` value that contains `[::1]`: the port "
            "parser splits on the colon inside the bracket and raises "
            "`Invalid port: ':1]'` before the request is made.\n\n"
            "Localhost traffic should bypass the proxy entirely, so this is an S2 for "
            "anyone on a corporate network. Labelled `area:providers`."
        ),
        "next_action": "ready-to-label",
    },
    813: {
        "severity": "S4",
        "severity_reason": "A feature request for two convenience file tools with no defect attached.",
        "component": "area:tools",
        "issue_type": "enhancement",
        "duplicate_of": [],
        "duplicate_reason": "",
        "confidence": 0.7,
        "labels": ["enhancement", "area:tools"],
        "reply_draft": (
            "Makes sense — `file.mkdir` and `file.copy` are the two operations agents "
            "keep reimplementing through `exec`. Both fit the existing file family and "
            "would stay inside the same workspace root.\n\n"
            "Labelled `enhancement` + `area:tools`; I will scope it after the current "
            "file-family fixes land."
        ),
        "next_action": "ready-to-label",
    },
}


def _decision_for(issue: Issue, snapshot: RepoSnapshot) -> TriageDecision:
    authored = AUTHORED.get(issue.number)
    if authored:
        return TriageDecision(issue_number=issue.number, source="model", **authored)
    fallback, _ = heuristic_decision(issue, snapshot.labels, snapshot.issues)
    severity, _reasons = severity_hint(issue)
    component, _ranked = component_hint(
        issue, available={label.name for label in snapshot.labels}
    )
    issue_type = issue_type_hint(issue)
    labels = labels_for_decision(
        issue, severity, component, issue_type, snapshot.labels, fallback.duplicate_of
    )
    return fallback.model_copy(
        update={
            "issue_number": issue.number,
            "severity": severity,
            "component": component,
            "issue_type": issue_type,
            "labels": labels,
            "source": "model",
        }
    )


def scripts_for_issues(
    snapshot: RepoSnapshot,
    issues: list[Issue],
    *,
    apply: bool = True,
) -> dict[str, Any]:
    """Build one scripted conversation per issue."""

    scripts: dict[str, Any] = {}
    for issue in issues:
        decision = _decision_for(issue, snapshot)
        scenario = f"issue-{issue.number}"
        steps: list[dict[str, Any]] = [
            {"kind": "tool", "tool": "triage_precheck", "args": {"issue_number": issue.number}},
            {"kind": "tool", "tool": "get_issue", "args": {"issue_number": issue.number}},
            {
                "kind": "tool",
                "tool": "search_duplicate_issues",
                "args": {
                    "query": issue.title[:120],
                    "exclude_issue_number": issue.number,
                    "limit": 5,
                },
            },
            {"kind": "text", "content": json.dumps(decision.model_dump(), ensure_ascii=False)},
        ]
        scripts[scenario] = {
            "steps": steps,
            "fallback_text": json.dumps(decision.model_dump(), ensure_ascii=False),
        }
        stage_scenario = f"stage-{issue.number}"
        scripts[stage_scenario] = {
            "steps": [
                {
                    "kind": "tool",
                    "tool": "stage_triage",
                    "args": {
                        "issue_number": decision.issue_number,
                        "severity": decision.severity,
                        "component": decision.component,
                        "labels": decision.labels,
                        "reply_draft": decision.reply_draft,
                        "duplicate_of": decision.duplicate_of,
                        "next_action": decision.next_action,
                    },
                },
                {"kind": "text", "content": f"Staged the triage plan for #{issue.number}."},
            ]
        }
        scripts[f"remember-{issue.number}"] = {
            "steps": [
                {
                    "kind": "tool",
                    "tool": "memory_write",
                    "args": {
                        "record_type": "decision",
                        "key": f"triage:{snapshot.repo}:{issue.number}",
                        "title": f"Triage decision for #{issue.number}",
                        "content": {
                            "issue": issue.number,
                            "severity": decision.severity,
                            "component": decision.component,
                            "labels": decision.labels,
                        },
                        "tags": ["repo-triager", "triage"],
                    },
                },
                {"kind": "text", "content": f"Remembered the triage decision for #{issue.number}."},
            ]
        }
        scripts[f"dedupe-{issue.number}"] = {
            "steps": [
                {
                    "kind": "text",
                    "content": "\n".join(
                        [
                            f"NOTDUP {candidate.number} different failure mode reported"
                            if candidate.number not in decision.duplicate_of
                            else f"DUP {candidate.number} 0.7 {decision.duplicate_reason}"
                            for candidate in _candidates(snapshot, issue)
                        ]
                        or "NOTDUP 0 no candidate looked like a duplicate",
                    )
                }
            ]
        }
    return scripts


def _candidates(snapshot: RepoSnapshot, issue: Issue):
    from repo_triager.heuristics import similar_issues

    return similar_issues(issue, snapshot.issues, limit=4)
