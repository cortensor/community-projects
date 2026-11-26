"""Operator approval gate and decision ledger for OpenMinion policy callbacks."""

from __future__ import annotations

from typing import Any

from .models import ApprovalDecisionRecord


class ReleaseApprovalGate:
    """Deterministic OpenMinion ``approval_callback`` with an auditable ledger.

    - Read-only tools (``min_scope="READ_ONLY", idempotent=True``) bypass
      confirmations under OpenMinion's default action policy.
    - ``write_release_brief`` is allowed only when ``allow_write_brief=True``
      and only once per run (single-use approval).
    - ``create_release_tag`` (``dangerous=True``) is denied unless
      ``allow_release_tag=True`` is explicitly opted in.
    - Any unexpected tool is denied by default (fail-closed).
    """

    def __init__(
        self,
        *,
        allow_write_brief: bool = False,
        allow_release_tag: bool = False,
    ) -> None:
        self.allow_write_brief = allow_write_brief
        self.allow_release_tag = allow_release_tag
        self._brief_writes = 0
        self._tag_writes = 0
        self.decisions: list[ApprovalDecisionRecord] = []

    def __call__(
        self,
        tool_name: str,
        args: dict[str, Any],
        approval_id: str,
    ) -> bool:
        allowed = False
        reason = f"denied_by_default:{tool_name}"

        if tool_name == "write_release_brief":
            if self.allow_write_brief and self._brief_writes == 0:
                self._brief_writes += 1
                allowed = True
                reason = "allowed_once:write_release_brief"
            elif self.allow_write_brief:
                reason = "denied:single_use_brief_write_already_consumed"
            else:
                reason = "denied:write_brief_not_enabled"
        elif tool_name == "create_release_tag":
            if self.allow_release_tag and self._tag_writes == 0:
                self._tag_writes += 1
                allowed = True
                reason = "allowed_once:create_release_tag"
            elif self.allow_release_tag:
                reason = "denied:single_use_tag_already_consumed"
            else:
                reason = "denied:dangerous_tag_not_enabled"

        self.decisions.append(
            ApprovalDecisionRecord(
                tool_name=tool_name,
                approval_id=approval_id,
                allowed=allowed,
                reason=reason,
                args_keys=sorted(str(k) for k in args.keys()),
            )
        )
        return allowed
