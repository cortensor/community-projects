"""ReleaseGuard Minion orchestrator backed by OpenMinion 0.1 APIRuntime & Agent."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openminion import APIRuntime, Agent, MemoryBundle, subagent
from openminion.modules.memory.portability import save_bundle

from .models import AuditRunEnvelope, ReleaseAuditReport
from .policy import ReleaseApprovalGate
from .tools import (
    create_release_tag,
    inspect_ci_and_tests,
    inspect_repo_manifest,
    scan_secret_hygiene,
    write_release_brief,
)

AUDITOR_INSTRUCTIONS = """You are ReleaseGuard Minion, a strict repository release-readiness auditor.
Use the provided read-only inspection tools to inspect the target repository's manifest, CI/tests, and secret hygiene.
Never fabricate file names or checks that were not returned by tools.
When asked to produce the final release audit report, respond with exact JSON matching the ReleaseAuditReport schema:
{"repo_name": "...", "verdict": "ready|needs_work|blocked", "score": 0-100, "rationale": "...", "checks": [{"category": "...", "passed": true/false, "evidence": "..."}], "blockers": [...], "recommendations": [...]}."""


def _repo_slug(repo_path: Path) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", repo_path.name.lower()).strip("-")
    return cleaned or "repo"


def render_release_brief_markdown(report: ReleaseAuditReport) -> str:
    """Render a deterministic Markdown brief from a validated ReleaseAuditReport."""

    lines = [
        f"# Release Readiness Brief: `{report.repo_name}`",
        "",
        f"- **Verdict**: `{report.verdict}`",
        f"- **Score**: `{report.score}/100`",
        f"- **Generated (UTC)**: `{datetime.now(timezone.utc).isoformat()}`",
        "",
        "## Rationale",
        "",
        report.rationale,
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        badge = "PASS" if check.passed else "FAIL"
        lines.append(f"- **[{badge}] {check.category}**: {check.evidence}")
    if report.blockers:
        lines.extend(["", "## Blockers", ""])
        lines.extend(f"- {item}" for item in report.blockers)
    if report.recommendations:
        lines.extend(["", "## Recommendations", ""])
        lines.extend(f"- {item}" for item in report.recommendations)
    lines.append("")
    return "\n".join(lines)


class ReleaseGuardMinion:
    """Application-owned OpenMinion runtime wrapper for repository release auditing."""

    def __init__(
        self,
        *,
        config_path: str | None = None,
        agent_id: str | None = None,
        runtime: APIRuntime | None = None,
    ) -> None:
        if runtime is not None and config_path is not None:
            raise ValueError("runtime and config_path cannot be used together")
        self._agent_id = (agent_id or "").strip() or None
        self._runtime = runtime or APIRuntime.from_config_path(
            config_path, logging_mode="interactive"
        )
        self._owns_runtime = runtime is None

    @property
    def runtime(self) -> APIRuntime:
        return self._runtime

    def close(self) -> None:
        if self._owns_runtime:
            self._runtime.close()

    def __enter__(self) -> ReleaseGuardMinion:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def diagnostics_snapshot(self) -> dict[str, Any]:
        """Collect OpenMinion's native posture, capability, self-model, and tool inventory."""

        return {
            "agent_id": self._agent_id,
            "runtime_posture": self._runtime.runtime_posture(agent_id=self._agent_id),
            "capability_report": self._runtime.capability_report(agent_id=self._agent_id),
            "runtime_self_model": self._runtime.runtime_self_model(agent_id=self._agent_id),
            "tool_count": len(self._runtime.tool_inventory_report()),
        }

    def audit_repository(
        self,
        repo_path: str | Path,
        *,
        session_id: str | None = None,
        output_brief_path: str | Path | None = None,
        memory_bundle_path: str | Path | None = None,
        allow_write_brief: bool = False,
        allow_release_tag: bool = False,
        include_tag_tool: bool = False,
        timeout_seconds: float = 120.0,
    ) -> AuditRunEnvelope:
        """Run a full inspectable release-readiness audit on ``repo_path``."""

        resolved_repo = Path(repo_path).expanduser().resolve()
        resolved_session = session_id or f"release-guard-{_repo_slug(resolved_repo)}"
        gate = ReleaseApprovalGate(
            allow_write_brief=allow_write_brief,
            allow_release_tag=allow_release_tag,
        )

        tools: list[Any] = [
            inspect_repo_manifest,
            inspect_ci_and_tests,
            scan_secret_hygiene,
        ]
        if output_brief_path is not None:
            tools.append(write_release_brief)
        if include_tag_tool:
            tools.append(create_release_tag)

        prompt_parts = [
            f"Audit the repository at `{resolved_repo}` for release readiness.",
            "Call `inspect_repo_manifest`, `inspect_ci_and_tests`, and `scan_secret_hygiene`.",
        ]
        if output_brief_path is not None:
            brief_target = Path(output_brief_path).expanduser().resolve()
            prompt_parts.append(
                f"After inspecting, call `write_release_brief` to save a Markdown brief at `{brief_target}`."
            )
        prompt_parts.append(
            "Finally, return ONLY a JSON object matching ReleaseAuditReport."
        )

        with Agent(
            name="release-guard",
            runtime=self._runtime,
            agent_id=self._agent_id,
            instructions=AUDITOR_INSTRUCTIONS,
            tools=tools,
            forced_tools=["inspect_repo_manifest"],
            output_type=ReleaseAuditReport,
            session_id=resolved_session,
        ) as agent:
            result = agent.run(
                " ".join(prompt_parts),
                timeout_seconds=timeout_seconds,
                approval_callback=gate,
            )

        report: ReleaseAuditReport = result.output
        saved_brief: str | None = None
        if output_brief_path is not None:
            brief_target = Path(output_brief_path).expanduser().resolve()
            if brief_target.is_file():
                saved_brief = str(brief_target)
            elif allow_write_brief:
                # Guarantee brief artifact exists if the model skipped calling write_release_brief
                brief_target.parent.mkdir(parents=True, exist_ok=True)
                brief_target.write_text(
                    render_release_brief_markdown(report), encoding="utf-8"
                )
                saved_brief = str(brief_target)

        saved_bundle: str | None = None
        if memory_bundle_path is not None:
            bundle = MemoryBundle(
                items=[
                    {
                        "kind": "release_audit",
                        "repo_name": report.repo_name,
                        "verdict": report.verdict,
                        "score": report.score,
                        "blockers": list(report.blockers),
                        "session_id": result.session_id,
                        "run_id": result.run_id,
                    }
                ],
                metadata={
                    "producer": "release-guard-minion",
                    "repo_path": str(resolved_repo),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            bundle_target = Path(memory_bundle_path).expanduser().resolve()
            bundle_target.parent.mkdir(parents=True, exist_ok=True)
            save_bundle(bundle, bundle_target)
            saved_bundle = str(bundle_target)

        return AuditRunEnvelope(
            report=report,
            session_id=result.session_id,
            run_id=result.run_id,
            run_state=result.run_state,
            thread_id=result.thread_id,
            approvals=list(gate.decisions),
            stats=dict(result.stats),
            memory_bundle_path=saved_bundle,
            brief_path=saved_brief,
        )

    def run_security_subagent(
        self,
        repo_path: str | Path,
        *,
        timeout_seconds: int = 60,
    ) -> str:
        """Delegate a bounded read-only secret-hygiene review to an OpenMinion subagent."""

        resolved_repo = Path(repo_path).expanduser().resolve()
        with Agent(
            name="release-guard-coordinator",
            runtime=self._runtime,
            agent_id=self._agent_id,
        ) as parent:
            reviewer = subagent(
                parent,
                name="secret-reviewer",
                instructions=(
                    "Run scan_secret_hygiene on the repository and summarize any "
                    "secret or .env hygiene risks in two concise sentences."
                ),
                tools=[scan_secret_hygiene],
                timeout_seconds=timeout_seconds,
            )
            # Workaround for OpenMinion 0.1.24 bug in openminion/api/handoff.py:299-307:
            # subagent() omits agent_id=parent.agent_id, causing non-default profiles to
            # silently fall back to default_agent.
            if reviewer.agent_id is None and parent.agent_id is not None:
                reviewer.agent_id = parent.agent_id
            result = reviewer.run(f"Check secret hygiene in `{resolved_repo}`.")
            return result.text
