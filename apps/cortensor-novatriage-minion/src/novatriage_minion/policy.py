"""Fail-closed approval policy gate for NovaTriage Minion write/destructive tools."""

from __future__ import annotations

from typing import Any

from .models import ApprovalDecisionRecord


class NovaTriageApprovalGate:
    """Enforces single-use write approval and default denial for dangerous tools."""

    def __init__(
        self,
        *,
        allow_report_write: bool = False,
        allow_dangerous_freeze: bool = False,
        allow_read_only_handoffs: bool = True,
    ) -> None:
        self.allow_report_write = allow_report_write
        self.allow_dangerous_freeze = allow_dangerous_freeze
        self.allow_read_only_handoffs = allow_read_only_handoffs
        self._write_consumed = False
        self.decisions: list[ApprovalDecisionRecord] = []

    def __call__(self, tool_name: str, args: dict[str, Any], approval_id: str) -> bool:
        normalized = str(tool_name or "").strip()
        if normalized in {
            "transfer_to_solidity_auditor_minion",
            "transfer_to_recon_minion",
        }:
            allowed = self.allow_read_only_handoffs
            self.decisions.append(
                ApprovalDecisionRecord(
                    approval_id=approval_id,
                    tool_name=normalized,
                    decision="approved" if allowed else "denied",
                    reason=(
                        "bounded_read_only_handoff_approved"
                        if allowed
                        else "handoff_denied_by_policy"
                    ),
                )
            )
            return allowed

        if normalized == "write_triage_report":
            if self.allow_report_write and not self._write_consumed:
                self._write_consumed = True
                self.decisions.append(
                    ApprovalDecisionRecord(
                        approval_id=approval_id,
                        tool_name=normalized,
                        decision="approved",
                        reason="single_use_write_report_approved",
                    )
                )
                return True
            reason = (
                "single_use_write_already_consumed"
                if self._write_consumed
                else "write_triage_report_denied_by_policy"
            )
            self.decisions.append(
                ApprovalDecisionRecord(
                    approval_id=approval_id,
                    tool_name=normalized,
                    decision="denied",
                    reason=reason,
                )
            )
            return False

        if normalized == "publish_emergency_freeze_notice":
            if self.allow_dangerous_freeze:
                self.decisions.append(
                    ApprovalDecisionRecord(
                        approval_id=approval_id,
                        tool_name=normalized,
                        decision="approved",
                        reason="explicit_operator_freeze_opt_in",
                    )
                )
                return True
            self.decisions.append(
                ApprovalDecisionRecord(
                    approval_id=approval_id,
                    tool_name=normalized,
                    decision="denied",
                    reason="destructive_freeze_denied_by_default",
                )
            )
            return False

        self.decisions.append(
            ApprovalDecisionRecord(
                approval_id=approval_id,
                tool_name=normalized,
                decision="denied",
                reason="fail_closed_unknown_or_unapproved_tool",
            )
        )
        return False
