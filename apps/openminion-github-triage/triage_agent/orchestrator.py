from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from openminion.modules.brain.diagnostics.status import (
    PhaseStatus,
    coerce_phase_status,
    phase_status_payload,
)
from openminion.modules.brain.loop.recursive.schemas import TaskState
from openminion.modules.session.storage.store import SQLiteSessionStore
from openminion.modules.tool.base import ToolExecutionContext
from openminion.modules.tool.contracts.provider_types import ProviderToolCall
from openminion.modules.tool.framework import derive_tool_specs
from openminion.modules.tool.registry import ToolRegistry
from openminion.tools import tool

from .analyzer import assess_issue, assess_release
from .llm import ModelClient
from .models import IssueAssessment, IssueInput, ReleaseInput, TriageReport


@tool(name="triage.assess_issue", min_scope="READ_ONLY", idempotent=True)
def assess_issue_tool(issue_json: str) -> dict[str, Any]:
    """Classify issue severity and reproduction completeness."""

    issue = IssueInput.model_validate_json(issue_json)
    return assess_issue(issue).model_dump()


@tool(name="triage.assess_release", min_scope="READ_ONLY", idempotent=True)
def assess_release_tool(release_json: str) -> dict[str, Any]:
    """Validate a release payload and its checkbox checklist."""

    release = ReleaseInput.model_validate_json(release_json)
    return assess_release(release).model_dump()


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for declaration in (assess_issue_tool, assess_release_tool):
        for spec in derive_tool_specs(declaration.tool_family_spec()):
            registry.add(spec)
    return registry


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TriageAgent:
    def __init__(
        self,
        *,
        session_db: str | Path = ":memory:",
        registry: ToolRegistry | None = None,
        model_client: ModelClient | None = None,
    ) -> None:
        self.store = SQLiteSessionStore(session_db)
        self.registry = registry or build_registry()
        self.model_client = model_client

    def _run_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        session_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        call = ProviderToolCall(name=name, arguments=arguments, id=f"call-{uuid4().hex}")
        context = ToolExecutionContext(
            channel="cli",
            target="github-triage",
            session_id=session_id,
            metadata={"trace_id": trace_id},
        )
        batch = self.registry.execute_calls([call], context=context)
        if not batch.results:
            raise RuntimeError(f"tool {name} returned no result")
        result = batch.results[0]
        self.store.append_event(
            session_id,
            event_type="triage.tool.completed" if result.ok else "triage.tool.failed",
            payload={
                "tool": result.tool_name,
                "call_id": result.call_id or call.id,
                "duration_ms": result.duration_ms,
                "error": result.error,
            },
            actor_type="tool",
            actor_id=result.tool_name,
            trace_id=trace_id,
            status="ok" if result.ok else "error",
        )
        if not result.ok:
            raise RuntimeError(f"tool {name} failed: {result.error}")
        payload = json.loads(result.content)
        return payload.get("result", payload)

    def _base_diagnostics(
        self,
        *,
        session_id: str,
        trace_id: str,
        task_state: TaskState,
        phases: list[PhaseStatus],
    ) -> dict[str, Any]:
        events = self.store.list_events(session_id, limit=100)
        return {
            "session_id": session_id,
            "trace_id": trace_id,
            "task_state": task_state.model_dump(),
            "phase_statuses": [phase_status_payload(item) for item in phases],
            "event_count": len(events),
            "event_types": [str(item.get("type") or item.get("event_type")) for item in events],
        }

    def triage_issue(
        self,
        repo: str,
        issue_payload: dict[str, Any],
        *,
        model_client: ModelClient | None = None,
    ) -> TriageReport:
        issue = IssueInput.from_github(issue_payload)
        trace_id = f"issue-{issue.number}-{uuid4().hex[:10]}"
        session_id = self.store.create_session(
            title=f"Issue triage {repo}#{issue.number}",
            initial_agent_id="triage-agent",
            tags=["github", "issue-triage"],
            meta={"repo": repo, "kind": "issue", "number": issue.number},
        )
        self.store.append_event(
            session_id,
            event_type="triage.issue.loaded",
            payload={"repo": repo, "number": issue.number, "title": issue.title},
            actor_type="agent",
            actor_id="triage-agent",
            trace_id=trace_id,
            status="ok",
        )
        phases = [
            PhaseStatus(trace_id=trace_id, status_key="analyzing", label="Analyzing issue"),
        ]
        assessment_data = self._run_tool(
            "triage.assess_issue",
            {"issue_json": issue.model_dump_json()},
            session_id=session_id,
            trace_id=trace_id,
        )
        task_state = TaskState(
            plan_id=f"github-issue-{issue.number}",
            step_id="classify-and-check-reproduction",
            retry_count=0,
            verification_mode="rule_based",
            invariants=["severity is derived from visible facts", "report is valid JSON"],
        )
        phases.append(
            PhaseStatus(
                trace_id=trace_id,
                status_key="completed",
                label="Issue triage complete",
                terminal=True,
            )
        )
        model_notes = None
        client = model_client or self.model_client
        if client is not None:
            model_notes = client.review_issue(issue, IssueAssessment.model_validate(assessment_data))
        report = TriageReport(
            generated_at=_utc_now(),
            kind="issue",
            repo=repo,
            subject=f"#{issue.number} {issue.title}".strip(),
            source_url=issue.html_url,
            issue=assessment_data,
            model_notes=model_notes,
            diagnostics=self._base_diagnostics(
                session_id=session_id,
                trace_id=trace_id,
                task_state=task_state,
                phases=phases,
            ),
        )
        self.store.append_turn(
            session_id,
            "assistant",
            report.model_dump_json(),
            meta={"schema_version": report.schema_version, "kind": "issue"},
        )
        return report

    def triage_release(self, repo: str, release_payload: dict[str, Any]) -> TriageReport:
        release = ReleaseInput.from_github(release_payload)
        trace_id = f"release-{uuid4().hex[:10]}"
        session_id = self.store.create_session(
            title=f"Release validation {repo}@{release.tag_name}",
            initial_agent_id="triage-agent",
            tags=["github", "release-qa"],
            meta={"repo": repo, "kind": "release", "tag": release.tag_name},
        )
        self.store.append_event(
            session_id,
            event_type="triage.release.loaded",
            payload={"repo": repo, "tag": release.tag_name, "draft": release.draft},
            actor_type="agent",
            actor_id="triage-agent",
            trace_id=trace_id,
            status="ok",
        )
        phases = [
            PhaseStatus(trace_id=trace_id, status_key="verifying", label="Verifying release"),
        ]
        assessment_data = self._run_tool(
            "triage.assess_release",
            {"release_json": release.model_dump_json()},
            session_id=session_id,
            trace_id=trace_id,
        )
        task_state = TaskState(
            plan_id=f"github-release-{release.tag_name}",
            step_id="validate-version-checklist-and-assets",
            retry_count=0,
            verification_mode="rule_based",
            invariants=["unchecked checklist wins over release claims", "draft releases are blocked"],
        )
        terminal_status = coerce_phase_status(
            {"trace_id": trace_id, "status_key": "completed", "label": "Release QA complete", "terminal": True}
        )
        phases.append(terminal_status)
        report = TriageReport(
            generated_at=_utc_now(),
            kind="release",
            repo=repo,
            subject=release.tag_name,
            source_url=release.html_url,
            release=assessment_data,
            diagnostics=self._base_diagnostics(
                session_id=session_id,
                trace_id=trace_id,
                task_state=task_state,
                phases=phases,
            ),
        )
        self.store.append_turn(
            session_id,
            "assistant",
            report.model_dump_json(),
            meta={"schema_version": report.schema_version, "kind": "release"},
        )
        return report

