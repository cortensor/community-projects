"""The triage agent: prompts, phases, and the OpenMinion building blocks.

Three phases, each its own ``Agent`` turn on one shared ``APIRuntime``:

1. **analyse** — read-only tools, ``output_type=TriageDecision``;
2. **stage**   — the only write tool, behind OpenMinion's policy confirmation;
3. **remember** — a built-in ``memory.write`` turn that keeps the next run
   consistent with this one.

The system prompt is deliberately short. OpenMinion 0.1.x truncates
``Agent(instructions=...)`` at roughly 860 characters without telling the
caller, so the rubric and the output schema travel in the task message
instead.  See ``BUILDING_BLOCKS_TESTED.md`` for the reproduction.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_triager.config import Settings
from repo_triager.heuristics import (
    component_hint,
    heuristic_decision,
    issue_type_hint,
    severity_hint,
    similar_issues,
)
from repo_triager.models import (
    Issue,
    RepoSnapshot,
    TriageDecision,
    TriageRecord,
    ValidationProblem,
)
from repo_triager.policy import OperatorPolicy
from repo_triager.tools import (
    ToolContext,
    stage_triage,
    get_issue,
    label_taxonomy,
    list_open_issues,
    search_duplicate_issues,
    triage_precheck,
    use_context,
)

AGENT_NAME = "repo-triager"
SKILL_ID = "repo-triager.triage-rubric"

SYSTEM_PROMPT = (
    "You are Repo Triager, a maintainer assistant for one GitHub repository. "
    "You triage a single open issue per turn and never write to GitHub: any "
    "write you produce is staged locally after an operator approves it. "
    "Follow the task message exactly, use the tools it names, and answer with "
    "the JSON object it specifies."
)

RUBRIC = """\
Rubric (severity)
- S1: data loss, corruption, security exposure, or a silent wrong result on a core path.
- S2: a documented feature fails, crashes, hangs, or regresses; no workaround.
- S3: degraded or environment-specific behaviour, performance, confusing errors, workarounds exist.
- S4: documentation, typos, cosmetic polish, questions, feature wishes.

Component
- Pick exactly one of the repository's own `area:*` labels, copied verbatim.
- If no area label fits, use an empty string and set next_action to needs-maintainer-input.

Duplicate handling
- Only report duplicate_of numbers that `search_duplicate_issues` returned,
  and only when the two issues describe the same defect. Score >= 0.45 is a
  signal, not proof.

Reply
- Labels must come from the repository taxonomy. One type label (bug,
  enhancement, question, documentation) plus the component is enough.
- The reply draft is the comment a maintainer would post: thank the reporter,
  state what you found, say what happens next, and never promise a fix date.
"""

OUTPUT_SCHEMA = """\
Return exactly one JSON object, no prose and no code fence, with these keys:
{
  "issue_number": <int>,
  "severity": "S1" | "S2" | "S3" | "S4",
  "severity_reason": "<one sentence>",
  "component": "<area:* label or empty string>",
  "issue_type": "bug" | "enhancement" | "question" | "documentation" | "other",
  "duplicate_of": [<issue numbers>],
  "duplicate_reason": "<one sentence>",
  "confidence": <0.0-1.0>,
  "labels": ["<label>", ...],
  "reply_draft": "<markdown comment>",
  "next_action": "ready-to-label" | "needs-maintainer-input" | "defer"
}
"""

STAGE_INSTRUCTIONS = (
    "You stage an already approved triage plan with the stage_triage tool. "
    "Call stage_triage once, with exactly the values given in the task "
    "message, then report the tool result in one sentence."
)

REMEMBER_INSTRUCTIONS = (
    "You record one durable triage decision with the memory.write tool so the "
    "next triage run stays consistent. Call memory.write once, then confirm."
)


@dataclass
class PhaseResult:
    text: str
    decision: TriageDecision | None = None
    metadata: dict = field(default_factory=dict)
    stats: dict = field(default_factory=dict)
    run_id: str | None = None
    session_id: str | None = None
    thread_id: str | None = None
    policy_events: list[dict] = field(default_factory=list)


# --------------------------------------------------------------- prompt text
def build_analysis_message(
    snapshot: RepoSnapshot,
    issue: Issue,
    *,
    scenario: str | None = None,
    max_similar: int = 4,
) -> str:
    severity, severity_reasons = severity_hint(issue)
    component, ranked = component_hint(
        issue, available={label.name for label in snapshot.labels}
    )
    similar = similar_issues(issue, snapshot.issues, limit=max_similar)
    lines = [
        f"Repository: {snapshot.repo}",
        f"Issue #{issue.number} — {issue.title}",
        f"Current labels: {', '.join(issue.labels) or '(none)'}",
        "",
        "Issue body:",
        (issue.body.strip() or "(empty)")[:1400],
        "",
        "Deterministic pre-check (heuristic, not a decision):",
        f"- severity suggestion: {severity} ({'; '.join(severity_reasons) or 'no strong signal'})",
        f"- component ranking: {', '.join(f'{name}={score}' for name, score in ranked[:4]) or '(none)'}",
        f"- type suggestion: {issue_type_hint(issue)}",
        "- nearest open issues: "
        + (
            ", ".join(f"#{candidate.number} ({candidate.score:.2f})" for candidate in similar)
            or "(none)"
        ),
        "",
        RUBRIC,
        "",
        "Steps",
        "1. Call triage_precheck for this issue number.",
        "2. Call get_issue and read the body.",
        "3. Call search_duplicate_issues with 3-6 distinctive terms from the title.",
        "4. If memory.search is available, search memory once for similar past decisions.",
        "5. Call label_taxonomy if you are unsure a label exists.",
        "6. Decide, then answer with the JSON object below.",
        "",
        OUTPUT_SCHEMA,
    ]
    if scenario:
        lines.append(f"SCENARIO:{scenario}")
    return "\n".join(lines)


def build_stage_message(decision: TriageDecision, scenario: str | None = None) -> str:
    payload = {
        "issue_number": decision.issue_number,
        "severity": decision.severity,
        "component": decision.component,
        "labels": decision.labels,
        "reply_draft": decision.reply_draft,
        "duplicate_of": decision.duplicate_of,
        "next_action": decision.next_action,
    }
    message = (
        "Approved triage plan for staging (dry run, local outbox only):\n"
        + json.dumps(payload, indent=2, ensure_ascii=False)
        + "\nCall stage_triage with exactly these values."
    )
    if scenario:
        message += f"\nSCENARIO:{scenario}"
    return message


def build_remember_message(
    decision: TriageDecision, snapshot: RepoSnapshot, scenario: str | None = None
) -> str:
    content = {
        "issue": decision.issue_number,
        "severity": decision.severity,
        "component": decision.component,
        "labels": decision.labels,
        "summary": decision.severity_reason[:300],
    }
    return (
        "Store this triage decision as a durable project convention so later "
        "runs stay consistent.\n"
        f"record_type: decision\n"
        f"key: triage:{snapshot.repo}:{decision.issue_number}\n"
        f"title: Triage decision for #{decision.issue_number}\n"
        f"content: {json.dumps(content, ensure_ascii=False)}\n"
        "tags: repo-triager, triage"
        + (f"\nSCENARIO:{scenario}" if scenario else "")
    )


def build_dedupe_message(snapshot: RepoSnapshot, issue: Issue) -> str:
    candidates = similar_issues(issue, snapshot.issues, limit=6)
    lines = [
        f"Repository: {snapshot.repo}",
        f"Primary issue #{issue.number} — {issue.title}",
        (issue.body.strip() or "(empty)")[:700],
        "",
        "Candidates:",
    ]
    for candidate in candidates:
        other = snapshot.issue(candidate.number)
        lines.append(
            f"- #{candidate.number} ({candidate.score:.2f}) {candidate.title}\n"
            f"  {(other.body.strip() if other else '')[:400]}"
        )
    lines += [
        "",
        "For each candidate say whether it describes the same defect as the "
        "primary issue. Answer with one line per candidate:",
        "DUP <number> <confidence 0-1> <one-sentence reason>",
        "NOTDUP <number> <one-sentence reason>",
    ]
    return "\n".join(lines)


# ------------------------------------------------------------------- runtime
def open_runtime(settings: Settings):
    """Create the shared ``APIRuntime`` for one CLI invocation."""

    from openminion.api import APIRuntime

    return APIRuntime.from_config_path(str(settings.config_path), logging_mode="interactive")


def _stats_of(result: Any, elapsed_ms: int) -> tuple[int, int]:
    metadata = getattr(result, "metadata", {}) or {}
    try:
        llm_calls = int(str(metadata.get("llm_calls_count", "0")))
    except ValueError:
        llm_calls = 0
    try:
        tool_calls = int(str(metadata.get("tool_calls_count", "0")))
    except ValueError:
        tool_calls = 0
    return llm_calls, tool_calls


class TriagerAgent:
    """One triage workflow instance bound to a snapshot and a runtime."""

    def __init__(
        self,
        settings: Settings,
        snapshot: RepoSnapshot,
        *,
        runtime: Any = None,
        provider_label: str = "",
    ) -> None:
        self.settings = settings
        self.snapshot = snapshot
        self._runtime = runtime
        self._owns_runtime = runtime is None
        self.provider_label = provider_label

    # -- lifecycle ----------------------------------------------------------
    @property
    def runtime(self):
        if self._runtime is None:
            self._runtime = open_runtime(self.settings)
        return self._runtime

    def close(self) -> None:
        if self._owns_runtime and self._runtime is not None:
            self._runtime.close()
            self._runtime = None

    def __enter__(self) -> "TriagerAgent":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- phase 1 ------------------------------------------------------------
    def analyse(
        self,
        issue: Issue,
        *,
        session_id: str,
        scenario: str | None = None,
        timeout_seconds: float = 180.0,
    ) -> tuple[TriageDecision, PhaseResult, ToolContext]:
        from openminion import Agent

        context = ToolContext(
            repo=self.snapshot.repo,
            snapshot=self.snapshot,
            outbox_dir=self.settings.outbox_dir,
            pending_decision=None,
        )
        message = build_analysis_message(self.snapshot, issue, scenario=scenario)
        started = time.time()
        with use_context(context):
            with Agent(
                runtime=self.runtime,
                name=AGENT_NAME,
                instructions=SYSTEM_PROMPT,
                tools=[
                    triage_precheck,
                    get_issue,
                    search_duplicate_issues,
                    label_taxonomy,
                    list_open_issues,
                    "memory.search",
                    "skill.get",
                ],
                output_type=TriageDecision,
                session_id=session_id,
            ) as agent:
                result = agent.run(message, timeout_seconds=timeout_seconds)
        elapsed_ms = int((time.time() - started) * 1000)
        llm_calls, tool_calls = _stats_of(result, elapsed_ms)
        phase = PhaseResult(
            text=result.text,
            decision=result.output,
            metadata=dict(result.metadata),
            stats=dict(result.stats),
            run_id=result.run_id,
            session_id=result.session_id,
            thread_id=result.thread_id,
        )
        phase.metadata.setdefault("llm_calls", llm_calls)
        phase.metadata.setdefault("tool_calls", tool_calls)
        decision = result.output
        assert isinstance(decision, TriageDecision)
        return decision, phase, context

    def analyse_or_fallback(
        self, issue: Issue, *, session_id: str, scenario: str | None = None
    ) -> tuple[TriageDecision, PhaseResult, ToolContext, list[str]]:
        """Run the analysis phase; fall back to the deterministic decision."""

        notes: list[str] = []
        try:
            decision, phase, context = self.analyse(
                issue, session_id=session_id, scenario=scenario
            )
            decision = decision.model_copy(
                update={"issue_number": issue.number, "source": "model"}
            )
            return decision, phase, context, notes
        except Exception as exc:  # noqa: BLE001 - degrade, never crash a batch
            notes.append(f"#{issue.number}: analysis failed ({type(exc).__name__}: {str(exc)[:200]}); used heuristic fallback")
            fallback, _ = heuristic_decision(issue, self.snapshot.labels, self.snapshot.issues)
            context = ToolContext(
                repo=self.snapshot.repo,
                snapshot=self.snapshot,
                outbox_dir=self.settings.outbox_dir,
            )
            return fallback, PhaseResult(text="", decision=fallback), context, notes

    # -- phase 2 ------------------------------------------------------------
    def stage(
        self,
        decision: TriageDecision,
        context: ToolContext,
        *,
        session_id: str,
        policy: OperatorPolicy,
        pause: bool = False,
        answer_stream: Any = None,
        scenario: str | None = None,
    ) -> PhaseResult:
        from openminion import Agent

        context.pending_decision = decision
        message = build_stage_message(decision, scenario=scenario)
        events: list[dict] = []
        started = time.time()
        with use_context(context):
            with Agent(
                runtime=self.runtime,
                name=f"{AGENT_NAME}-stage",
                instructions=STAGE_INSTRUCTIONS,
                tools=[stage_triage],
                forced_tools=["stage_triage"],
                session_id=session_id,
            ) as agent:
                if pause:
                    result = agent.run(message, timeout_seconds=120.0)
                    if result.metadata.get("respond_kind") == "policy_confirmation_prompt":
                        prompt = result.text.replace("openminion: ", "", 1)
                        if answer_stream is not None:
                            print(prompt, file=answer_stream)
                        else:
                            print(prompt)
                        if policy.mode == "auto":
                            answer = "yes"
                        elif policy.mode == "ask":
                            try:
                                typed = input("Allow this call? [y/N] ").strip().lower()
                            except EOFError:
                                typed = ""
                            answer = "yes" if typed in {"y", "yes"} else "no"
                        else:
                            answer = "no"
                        events.append(
                            {
                                "tool": "stage_triage",
                                "decision": "allow" if answer == "yes" else "deny",
                                "policy": f"paused turn answered {answer!r}",
                                "approval_id": result.thread_id or "",
                                "args_preview": "(runtime prompt)",
                            }
                        )
                        result = agent.run(answer, thread_id=result.thread_id)
                else:
                    result = agent.run(
                        message,
                        timeout_seconds=120.0,
                        approval_callback=policy.as_callback(),
                    )
                    events = policy.events_as_dicts
        elapsed_ms = int((time.time() - started) * 1000)
        llm_calls, tool_calls = _stats_of(result, elapsed_ms)
        return PhaseResult(
            text=result.text,
            metadata={
                **dict(result.metadata),
                "llm_calls": llm_calls,
                "tool_calls": tool_calls,
                "applied": context.applied,
                "outbox": context.outbox_paths,
            },
            stats=dict(result.stats),
            run_id=result.run_id,
            session_id=result.session_id,
            thread_id=result.thread_id,
            policy_events=events,
        )

    # -- phase 3 ------------------------------------------------------------
    def remember(
        self,
        decision: TriageDecision,
        *,
        session_id: str,
        timeout_seconds: float = 120.0,
        scenario: str | None = None,
    ) -> PhaseResult:
        from openminion import Agent

        message = build_remember_message(decision, self.snapshot, scenario=scenario)
        allowed = {"tool": "memory.write", "decision": "allow", "policy": "remember flag"}

        def approve(tool_name: str, args: dict, approval_id: str) -> bool:
            return tool_name == "memory.write"

        started = time.time()
        with Agent(
            runtime=self.runtime,
            name=f"{AGENT_NAME}-memory",
            instructions=REMEMBER_INSTRUCTIONS,
            tools=["memory.write"],
            forced_tools=["memory.write"],
            session_id=session_id,
        ) as agent:
            result = agent.run(
                message, timeout_seconds=timeout_seconds, approval_callback=approve
            )
        elapsed_ms = int((time.time() - started) * 1000)
        llm_calls, tool_calls = _stats_of(result, elapsed_ms)
        return PhaseResult(
            text=result.text,
            metadata={
                **dict(result.metadata),
                "llm_calls": llm_calls,
                "tool_calls": tool_calls,
                "memory_written": "memory.write" in str(result.text).lower()
                or tool_calls > 0,
            },
            run_id=result.run_id,
            session_id=result.session_id,
            policy_events=[allowed],
        )

    # -- delegation ---------------------------------------------------------
    def deep_dedupe(
        self, issue: Issue, *, session_id: str, scenario: str | None = None
    ) -> tuple[list[int], str, dict]:
        """Ask a bounded subagent to confirm duplicates; never blocks the run."""

        from openminion import Agent, subagent

        message = build_dedupe_message(self.snapshot, issue)
        if scenario:
            message += f"\nSCENARIO:{scenario}"
        try:
            with Agent(
                runtime=self.runtime,
                name=f"{AGENT_NAME}-parent",
                instructions="You coordinate a duplicate-analysis subagent.",
                session_id=session_id,
            ) as parent:
                scout = subagent(
                    parent,
                    name="duplicate-scout",
                    instructions=(
                        "Compare GitHub issues for duplicate defects and answer "
                        "with DUP/NOTDUP lines only."
                    ),
                    timeout_seconds=120,
                )
                result = scout.run(message)
        except Exception as exc:  # noqa: BLE001 - delegation is optional
            return [], f"delegation unavailable: {type(exc).__name__}: {str(exc)[:160]}", {}

        confirmed: list[int] = []
        reasons: list[str] = []
        for line in result.text.replace("openminion: ", "", 1).splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and parts[0].upper() == "DUP" and parts[1].isdigit():
                number = int(parts[1])
                try:
                    confidence = float(parts[2]) if len(parts) > 2 else 0.0
                except ValueError:
                    confidence = 0.0
                if confidence >= 0.5:
                    confirmed.append(number)
                    reasons.append(" ".join(parts[3:]) or f"#{number} confirmed")
        return confirmed, "; ".join(reasons) or "no duplicates confirmed", dict(result.metadata)


# ------------------------------------------------------------- validation
def validate_decision(
    decision: TriageDecision,
    issue: Issue,
    snapshot: RepoSnapshot,
) -> list[ValidationProblem]:
    problems: list[ValidationProblem] = []
    if decision.issue_number != issue.number:
        problems.append(
            ValidationProblem(
                field="issue_number",
                message=f"decision is for #{decision.issue_number}, expected #{issue.number}",
            )
        )
    unknown = [label for label in decision.labels if label not in snapshot.label_names]
    if unknown:
        problems.append(
            ValidationProblem(field="labels", message=f"labels not in taxonomy: {unknown}")
        )
    missing = [number for number in decision.duplicate_of if snapshot.issue(number) is None]
    if missing:
        problems.append(
            ValidationProblem(
                field="duplicate_of",
                message=f"duplicate_of refers to issues outside the snapshot: {missing}",
            )
        )
    if issue.number in decision.duplicate_of:
        problems.append(
            ValidationProblem(field="duplicate_of", message="an issue cannot duplicate itself")
        )
    if decision.component and decision.component not in snapshot.label_names:
        problems.append(
            ValidationProblem(
                field="component",
                message=f"component {decision.component!r} is not a repository label",
            )
        )
    if not decision.reply_draft.strip():
        problems.append(ValidationProblem(field="reply_draft", message="reply draft is empty"))
    return problems


def repair_decision(
    decision: TriageDecision,
    issue: Issue,
    snapshot: RepoSnapshot,
    problems: list[ValidationProblem],
) -> TriageDecision:
    """Drop what the model invented and keep what the repository supports."""

    labels = [label for label in decision.labels if label in snapshot.label_names]
    duplicates = [number for number in decision.duplicate_of if snapshot.issue(number)]
    component = decision.component if decision.component in snapshot.label_names else ""
    repaired = decision.model_copy(
        update={
            "issue_number": issue.number,
            "labels": labels[:4],
            "duplicate_of": duplicates,
            "component": component,
            "next_action": "needs-maintainer-input"
            if (not component or not labels)
            else decision.next_action,
            "confidence": min(decision.confidence, 0.6),
        }
    )
    return repaired


def build_record(
    decision: TriageDecision,
    issue: Issue,
    *,
    problems: list[ValidationProblem] | None = None,
    policy_events: list[dict] | None = None,
    applied: bool = False,
    outbox: list[str] | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
    llm_calls: int = 0,
    tool_calls: int = 0,
    elapsed_ms: int = 0,
) -> TriageRecord:
    return TriageRecord(
        decision=decision,
        issue_title=issue.title,
        issue_url=issue.url,
        validation=list(problems or []),
        policy=list(policy_events or []),
        applied=applied,
        outbox=list(outbox or []),
        run_id=run_id,
        session_id=session_id,
        llm_calls=llm_calls,
        tool_calls=tool_calls,
        elapsed_ms=elapsed_ms,
    )


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_label(settings: Settings) -> str:
    return f"{now_stamp()}-{settings.repo.replace('/', '_')}"


def resolve_script_scenario(issue: Issue) -> str:
    return f"issue-{issue.number}"


def plan_paths(settings: Settings, issue: Issue) -> tuple[Path, Path]:
    directory = settings.outbox_dir / settings.repo.replace("/", "_")
    stem = f"{issue.number:04d}"
    return directory / f"{stem}.md", directory / f"{stem}.json"
