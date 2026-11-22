"""Immutable event bus, schemas, secret redaction, and negative-control tripwire."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import os
import re
from threading import Lock
from typing import Any

_REDACT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bAIzaSy[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\b0x[a-fA-F0-9]{64}\b"),
)


class KernelIntegrityError(RuntimeError):
    """Raised when a kernel invariant or negative-control gate fails."""


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 seconds resolution."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def corrupt_gate_active() -> bool:
    """Return True when CORRUPT_GATE_CONTROL=1 negative-control tripwire is active."""
    return os.environ.get("CORRUPT_GATE_CONTROL", "").strip() == "1"


def redact_secrets(text: str, extra_env_keys: tuple[str, ...] = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "CORTENSOR_API_KEY", "OPENAI_API_KEY")) -> str:
    """Scrub secret tokens and live credential env values from any string before persistence."""
    cleaned = str(text or "")
    for env_name in extra_env_keys:
        val = os.environ.get(env_name, "").strip()
        if len(val) >= 8 and val in cleaned:
            cleaned = cleaned.replace(val, f"[REDACTED:{env_name}]")
    for pat in _REDACT_PATTERNS:
        cleaned = pat.sub("[REDACTED:SECRET]", cleaned)
    return cleaned


@dataclass(frozen=True)
class KernelEvent:
    """Immutable ledger record emitted across vertical-slice bricks."""

    seq: int
    event_type: str
    source_brick: str
    timestamp_utc: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TriageTarget:
    """Workspace target audited by Minionbench Ops."""

    workspace_root: str
    project_slug: str
    hackathon_id: int
    openminion_version: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ToolCallRecord:
    """Sanitized record of an OpenMinion @tool invocation."""

    tool_name: str
    min_scope: str
    idempotent: bool
    arguments: dict[str, Any]
    result_preview: str
    invoked_at_utc: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MinionTurnReceipt:
    """Verifiable receipt of an OpenMinion Agent turn."""

    session_id: str
    run_id: str
    run_state: str
    agent_id: str
    provider_transport: str
    model_id: str
    endpoint_base_url: str
    openminion_version: str
    latency_ms: float
    live_neural_model: bool
    tool_invocations: tuple[ToolCallRecord, ...]
    final_text: str
    hosted_probe_note: str
    sanitized: bool
    recorded_at_utc: str

    def verify_invariants(self) -> None:
        if corrupt_gate_active():
            raise KernelIntegrityError(
                "CORRUPT_GATE_CONTROL=1 injected: MinionTurnReceipt invariant tripwire triggered."
            )
        if not self.session_id.strip():
            raise KernelIntegrityError("MinionTurnReceipt.session_id must be non-empty.")
        if not self.sanitized:
            raise KernelIntegrityError("MinionTurnReceipt must be sanitized before export.")
        if len(self.tool_invocations) == 0:
            raise KernelIntegrityError("MinionTurnReceipt requires at least one @tool invocation.")
        for pat in _REDACT_PATTERNS:
            if pat.search(self.final_text) or pat.search(self.hosted_probe_note):
                raise KernelIntegrityError("Secret pattern leaked inside MinionTurnReceipt.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "run_id": self.run_id,
            "run_state": self.run_state,
            "agent_id": self.agent_id,
            "provider_transport": self.provider_transport,
            "model_id": self.model_id,
            "endpoint_base_url": self.endpoint_base_url,
            "openminion_version": self.openminion_version,
            "latency_ms": self.latency_ms,
            "live_neural_model": self.live_neural_model,
            "tool_invocations": [item.to_dict() for item in self.tool_invocations],
            "final_text": self.final_text,
            "hosted_probe_note": self.hosted_probe_note,
            "sanitized": self.sanitized,
            "recorded_at_utc": self.recorded_at_utc,
        }


@dataclass(frozen=True)
class BuildingBlockProbeResult:
    """Empirical OpenMinion 0.1.24 building-block diagnostic probe outcome."""

    probe_id: str
    title: str
    sdk_surface: str
    passed: bool
    latency_ms: float
    summary: str
    evidence: dict[str, Any]
    product_feedback: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DiagnosticReport:
    """Complete Minionbench Ops diagnostic ledger snapshot."""

    generated_at_utc: str
    openminion_version: str
    target: TriageTarget
    live_receipt: MinionTurnReceipt
    probes: tuple[BuildingBlockProbeResult, ...]
    cortensor_posture: dict[str, Any]
    learned_findings: tuple[dict[str, str], ...]

    def verify_invariants(self) -> None:
        if corrupt_gate_active():
            raise KernelIntegrityError(
                "CORRUPT_GATE_CONTROL=1 injected: DiagnosticReport integrity gate rejected snapshot."
            )
        self.live_receipt.verify_invariants()
        if len(self.probes) < 6:
            raise KernelIntegrityError(f"Expected 6 building-block probes, got {len(self.probes)}.")
        failed = [p.probe_id for p in self.probes if not p.passed]
        if failed:
            raise KernelIntegrityError(f"Building-block probes failed: {', '.join(failed)}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at_utc": self.generated_at_utc,
            "openminion_version": self.openminion_version,
            "target": self.target.to_dict(),
            "live_receipt": self.live_receipt.to_dict(),
            "probes": [p.to_dict() for p in self.probes],
            "cortensor_posture": dict(self.cortensor_posture),
            "learned_findings": [dict(item) for item in self.learned_findings],
        }


class EventBus:
    """Append-only thread-safe kernel event ledger with immutable snapshots."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._events: list[KernelEvent] = []

    def publish(self, event_type: str, *, source_brick: str, payload: dict[str, Any] | None = None) -> KernelEvent:
        if corrupt_gate_active() and event_type == "gate.check":
            raise KernelIntegrityError("CORRUPT_GATE_CONTROL=1 blocked gate.check event.")
        safe_payload = dict(payload or {})
        with self._lock:
            seq = len(self._events) + 1
            event = KernelEvent(
                seq=seq,
                event_type=event_type.strip(),
                source_brick=source_brick.strip(),
                timestamp_utc=utc_now_iso(),
                payload=safe_payload,
            )
            self._events.append(event)
            return event

    def snapshot(self) -> tuple[KernelEvent, ...]:
        with self._lock:
            if corrupt_gate_active():
                return ()
            return tuple(self._events)

    def tool_call_records(self) -> tuple[ToolCallRecord, ...]:
        records: list[ToolCallRecord] = []
        for event in self.snapshot():
            if event.event_type == "tool.invoked":
                p = event.payload
                records.append(
                    ToolCallRecord(
                        tool_name=str(p.get("tool_name", "")),
                        min_scope=str(p.get("min_scope", "")),
                        idempotent=bool(p.get("idempotent", False)),
                        arguments=dict(p.get("arguments") or {}),
                        result_preview=redact_secrets(str(p.get("result_preview", ""))),
                        invoked_at_utc=event.timestamp_utc,
                    )
                )
        return tuple(records)
