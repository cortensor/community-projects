"""Operator policy for the write gate.

OpenMinion's action policy decides *whether a tool needs confirmation*; this
module decides *what the operator answers*.  Every answer is recorded so the
run report shows exactly which tool was confirmed, for which arguments, and by
which policy.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

WRITE_TOOL = "stage_triage"


@dataclass
class PolicyEvent:
    tool: str
    args_preview: str
    decision: str
    policy: str
    approval_id: str = ""
    at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def as_dict(self) -> dict:
        return {
            "tool": self.tool,
            "args_preview": self.args_preview,
            "decision": self.decision,
            "policy": self.policy,
            "approval_id": self.approval_id,
            "at": self.at,
        }


def preview_args(args: dict, limit: int = 240) -> str:
    try:
        text = json.dumps(args, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        text = str(args)
    return text if len(text) <= limit else text[:limit] + "…"


@dataclass
class OperatorPolicy:
    """``mode`` is the CLI decision for the write tool."""

    mode: str = "ask"  # auto | ask | deny
    events: list[PolicyEvent] = field(default_factory=list)
    stream: object | None = None  # file-like sink for operator prompts

    def _emit(self, text: str) -> None:
        sink = self.stream
        if sink is None:
            print(text)
        else:
            print(text, file=sink)

    def decide(self, tool_name: str, args: dict, approval_id: str = "") -> bool:
        if tool_name != WRITE_TOOL:
            self.events.append(
                PolicyEvent(tool_name, preview_args(args), "deny", "not-this-agent's-gate", approval_id)
            )
            return False

        preview = preview_args(args)
        if self.mode == "deny":
            allowed, policy = False, "operator-flag: deny"
        elif self.mode == "auto":
            allowed, policy = True, "operator-flag: auto (non-interactive)"
        else:
            allowed, label = self._ask(preview)
            policy = "interactive prompt"
            self.events.append(
                PolicyEvent(tool_name, preview, "allow" if allowed else "deny", policy, approval_id)
            )
            return allowed
        self.events.append(
            PolicyEvent(tool_name, preview, "allow" if allowed else "deny", policy, approval_id)
        )
        return allowed

    def _ask(self, preview: str) -> tuple[bool, str]:
        self._emit("")
        self._emit("┌─ approval required ─────────────────────────────────────────")
        self._emit("│ tool: stage_triage  (local dry-run write: outbox/ only)")
        self._emit(f"│ args: {preview}")
        self._emit("└─────────────────────────────────────────────────────────────")
        try:
            answer = input("Stage this triage plan? [y/N] ").strip().lower()
        except EOFError:  # non-interactive stdin: treat as "no"
            self._emit("(no input available — treated as no)")
            answer = ""
        return answer in {"y", "yes", "allow_once", "approve"}, answer

    def as_callback(self) -> Callable[[str, dict, str], bool]:
        return self.decide

    @property
    def events_as_dicts(self) -> list[dict]:
        return [event.as_dict() for event in self.events]


def describe_runtime_prompt(thread_id: str | None) -> str:
    return (
        "runtime asked for the operator decision on thread "
        f"{thread_id or '(none)'}; answer with `yes` or `no` in the pause flow"
    )


def default_mode() -> str:
    return os.environ.get("REPO_TRIAGER_APPROVE", "").strip() or "ask"
